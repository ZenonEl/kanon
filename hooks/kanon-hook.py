#!/usr/bin/env python3
"""Хуки kanon: срабатывание до и после работы, а не только по ручному вызову.

Скил поднимается, когда переход от сбора к производству объявлен словами. Он
объявляется не всегда: агент часто пересекает границу молча. Хуки закрывают
именно этот промежуток — они видят события, а не формулировки.

  SessionStart  — что заброшено и что истекло;
  PreToolUse    — сбор был, файла нет, а уже пишем: напомнить (один раз);
  Stop          — в чеклисте остались незакрытые пункты: перечислить.

Три правила, нарушать которые дорого:

1. **Ничего не блокируется.** Хук, мешающий работать, выключают вместе с
   плагином. Все три только говорят.
2. **Хук не падает.** Любая ошибка внутри — это выход 0 и тишина: сломанный
   хук хуже отсутствующего, потому что ломает чужую работу.
3. **PreToolUse говорит один раз за сессию.** Напоминание на каждую запись
   превращается в шум, а шум перестают читать.

Hooks fire on events, not on phrasing: they cover the gap where the move from
gathering to producing is never announced in words. Nothing blocks, nothing
raises, and the pre-write reminder speaks once per session.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

GATHERING_TOOLS = {"Read", "Grep", "Glob", "WebSearch", "WebFetch", "NotebookRead"}
GATHERING_THRESHOLD = 3
SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"


def _run(script: str, *args: str) -> str:
    try:
        out = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            capture_output=True, text=True, timeout=10,
        )
        return (out.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _checklists() -> list:
    sys.path.insert(0, str(SCRIPTS))
    try:
        from kanon_format import find, parse  # noqa: PLC0415
        return [parse(p) for p in find()]
    except Exception:  # noqa: BLE001
        return []


def _gathering_count(transcript: str | None) -> int:
    """Сколько раз в этой сессии читали, искали и ходили в сеть."""
    if not transcript:
        return 0
    path = pathlib.Path(transcript)
    if not path.is_file():
        return 0
    count = 0
    try:
        with path.open(encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                for name in GATHERING_TOOLS:
                    if f'"name":"{name}"' in line or f'"name": "{name}"' in line:
                        count += 1
                        break
    except Exception:  # noqa: BLE001
        return 0
    return count


def _once_per_session(session_id: str) -> bool:
    """True, если в этой сессии ещё не говорили."""
    if not session_id:
        return True
    marker = pathlib.Path(tempfile.gettempdir()) / f"kanon-reminded-{session_id[:40]}"
    if marker.exists():
        return False
    try:
        marker.touch()
    except OSError:
        pass
    return True


# --- события / events -----------------------------------------------------


def on_session_start(_: dict) -> str:
    return _run("sweep.py", "--quiet")


def on_pre_tool_use(payload: dict) -> str:
    target = str(payload.get("tool_input", {}).get("file_path", ""))
    # Запись самого чеклиста — не производство.
    if any(f"{os.sep}{d}{os.sep}" in target or target.startswith(d)
               for d in ("_kanon", ".kanon")):
        return ""

    docs = [d for d in _checklists() if d.state == "open"]
    if docs:
        return ""

    if _gathering_count(payload.get("transcript_path")) < GATHERING_THRESHOLD:
        return ""

    if not _once_per_session(str(payload.get("session_id", ""))):
        return ""

    return (
        "kanon: собранное сейчас живёт только в контексте, а производство уже "
        "началось — при сжатии или в новой сессии оно не доживёт.\n"
        "Заведи чеклист приёмки (/kanon:open или навык task-to-checklist): "
        "что должно быть на выходе, чем проверяется, что из собранного обязано "
        "попасть в результат.\n"
        "kanon: gathered material lives only in this context while production has "
        "already started; it will not survive compaction or a new session."
    )


def on_stop(_: dict) -> str:
    lines: list[str] = []
    for doc in _checklists():
        if doc.state != "open":
            continue
        open_items = doc.open_items
        if not open_items:
            continue
        lines.append(f"kanon · {doc.path.name}: "
                     f"{len(doc.items) - len(open_items)}/{len(doc.items)} "
                     f"закрыто доказательством / closed with proof")
        for item in open_items[:5]:
            mark = "отмечен без доказательства" if item.ticked else "открыт"
            lines.append(f"    {item.number}. {item.text or '<пустой слот>'} — {mark}")
        if len(open_items) > 5:
            lines.append(f"    …и ещё {len(open_items) - 5}")
    if lines:
        lines.append("«сделано» звучит, когда закрыты все. иначе — перечисли недостачу.")
    return "\n".join(lines)


HANDLERS = {
    "SessionStart": on_session_start,
    "PreToolUse": on_pre_tool_use,
    "Stop": on_stop,
}


def main() -> int:
    try:
        event = sys.argv[1] if len(sys.argv) > 1 else ""
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        payload = json.loads(raw) if raw.strip() else {}
        handler = HANDLERS.get(event)
        if handler:
            message = handler(payload)
            if message:
                print(message)
    except Exception:  # noqa: BLE001
        pass  # сломанный хук хуже отсутствующего
    return 0


if __name__ == "__main__":
    sys.exit(main())
