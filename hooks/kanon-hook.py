#!/usr/bin/env python3
"""Хуки kanon: срабатывание до и после работы, а не только по ручному вызову.

Скил поднимается, когда переход от сбора к производству объявлен словами. Он
объявляется не всегда: агент часто пересекает границу молча. Хуки закрывают
именно этот промежуток — они видят события, а не формулировки.

  SessionStart  — что заброшено и что истекло;
  PreToolUse    — сбор был, файла нет, а уже пишем: напомнить (один раз);
  Stop          — в чеклисте остались незакрытые пункты: перечислить.

Как хук говорит. Голый stdout доходит до адресата НЕ у всех событий: хост
показывает его только у SessionStart, UserPromptSubmit и UserPromptExpansion, а
у остальных отправляет в отладочный лог. Поэтому PreToolUse и Stop печатают JSON
с полем systemMessage — оно валидируется хостом и показывается человеку.
Проверено чтением бандла, а 2026-09-03 — живой сессией: Stop с 13/15 и двумя
открытыми пунктами дошёл до человека в том виде, в каком напечатан.

Поле decision у Stop и permissionDecision у PreToolUse НЕ задаются намеренно:
любое из них завело бы блокировку, а правило проекта — ничего не блокировать.

Три правила, нарушать которые дорого:

1. **Ничего не блокируется.** Хук, мешающий работать, выключают вместе с
   плагином. Все три только говорят.
2. **Хук не падает.** Любая ошибка внутри — это выход 0 и тишина: сломанный
   хук хуже отсутствующего, потому что ломает чужую работу.
3. **PreToolUse говорит один раз за сессию.** Напоминание на каждую запись
   превращается в шум, а шум перестают читать.

Bash — тоже сбор и тоже запись. Первый же промах обкатки показал: сессия в
режиме без подтверждений читает через `cat`/`sed -n` и пишет через heredoc и
`sed -i`, потому что хост сам просит гонять всё через shell. Сенсор, который
считает только Read/Write по именам инструментов, в таком режиме слеп по
построению. Поэтому команда Bash классифицируется по содержимому: голова
команды из читающих — сбор; перенаправление в файл, `tee`, `sed -i` —
производство. Ошибка классификации стоит одного лишнего напоминания, и оно
всё равно одно за сессию.

Hooks fire on events, not on phrasing: they cover the gap where the move from
gathering to producing is never announced in words. Nothing blocks, nothing
raises, and the pre-write reminder speaks once per session.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

GATHERING_TOOLS = {"Read", "Grep", "Glob", "WebSearch", "WebFetch", "NotebookRead"}
GATHERING_THRESHOLD = 3

# Bash по содержимому. Голова команды из этого множества — чтение, если в
# команде нет признака записи. `git` — только с читающим подкомандой.
BASH_READ_HEADS = {"cat", "head", "tail", "less", "sed", "grep", "rg", "ag", "find",
                   "fd", "ls", "tree", "wc", "stat", "file", "awk", "git"}
GIT_READ_SUBCOMMANDS = {"log", "show", "diff", "status", "blame", "ls-files", "grep",
                        "branch", "remote", "rev-parse", "describe", "tag"}
# Признаки записи: перенаправление в файл (не в /dev/null и не 2>&1), tee,
# sed/perl «на месте».
_REDIRECT = re.compile(r"(?<![0-9&<])>{1,2}(?!&)\s*(?!/dev/null\b)\S")
_INPLACE = re.compile(r"\b(?:tee\b|sed\s+(?:-[a-zA-Z]*i|--in-place)|perl\s+-[a-zA-Z]*i)")
_LEADING = re.compile(r"^(?:\s*(?:cd\s+\S+\s*(?:&&|;)\s*|[A-Za-z_][A-Za-z0-9_]*=\S*\s+|sudo\s+|command\s+))*")


def bash_writes(command: str) -> bool:
    """Команда пишет в файл. Heredoc без перенаправления не пишет."""
    return bool(_REDIRECT.search(command) or _INPLACE.search(command))


def bash_gathers(command: str) -> bool:
    """Команда читает, а не пишет: голова из читающих и признаков записи нет."""
    if bash_writes(command):
        return False
    body = _LEADING.sub("", command, count=1)
    words = body.split()
    if not words:
        return False
    head = words[0].rsplit("/", 1)[-1]
    if head == "git":
        return len(words) > 1 and words[1] in GIT_READ_SUBCOMMANDS
    return head in BASH_READ_HEADS
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
    """Чеклисты каталога. Один битый файл не ослепляет остальные.

    Раньше весь разбор стоял под одним обработчиком: единственный чеклист с
    битой кодировкой возвращал пустой список, и хук вёл себя так, будто
    чеклистов нет вовсе — то есть требовал завести новый при живом.
    """
    sys.path.insert(0, str(SCRIPTS))
    try:
        from kanon_format import find, parse  # noqa: PLC0415
        paths, _skipped = find()
    except Exception:  # noqa: BLE001
        return []
    docs = []
    for path in paths:
        try:
            docs.append(parse(path))
        except Exception:  # noqa: BLE001
            continue  # включая ValueError от гигантских чисел
    return docs


def _gathering_in_line(line: str) -> int:
    """Сколько собирающих вызовов в одной записи транскрипта.

    Read/Grep/Glob — по имени. Bash — по содержимому команды: `cat`, `sed -n`,
    `git log` собирают так же, как Read, и в режиме без подтверждений хост сам
    направляет чтение туда. Строка, которая не разбирается как JSON, считается
    по подстроке, как раньше.
    """
    try:
        entry = json.loads(line)
    except ValueError:
        return sum(1 for name in GATHERING_TOOLS
                   if f'"name":"{name}"' in line or f'"name": "{name}"' in line)
    content = entry.get("message", {}).get("content", []) if isinstance(entry, dict) else []
    if not isinstance(content, list):
        return 0
    count = 0
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name")
        if name in GATHERING_TOOLS:
            count += 1
        elif name == "Bash":
            command = block.get("input", {}).get("command", "")
            if isinstance(command, str) and bash_gathers(command):
                count += 1
    return count


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
                count += _gathering_in_line(line)
                if count >= GATHERING_THRESHOLD:
                    # Ответ уже известен: дочитывать транскрипт до конца при
                    # каждой записи — линейный ввод-вывод впустую, и на большом
                    # он упирается в таймаут хука, то есть сенсор молча гаснет.
                    return count
    except Exception:  # noqa: BLE001
        return 0
    return count


def _once_per_session(session_id: str) -> bool:
    """True, если в этой сессии ещё не говорили.

    Создание исключительное (O_EXCL) и в приватном подкаталоге: проверка
    существования отдельно от создания оставляла окно, в котором два
    параллельных вызова оба считали себя первыми, а предсказуемое имя в общем
    /tmp позволяло чужому процессу заглушить напоминание, создав файл заранее.
    """
    if not session_id:
        return True
    # Хеш, а не вычистка символов: канонизация склеивала разные идентификаторы
    # в одно имя («review-a/b» и «review-ab»), и вторая сессия молча теряла своё
    # единственное напоминание.
    safe = hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:32]
    folder = pathlib.Path(tempfile.gettempdir()) / f"kanon-{os.getuid()}"
    try:
        folder.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(folder / f"reminded-{safe}",
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return True  # не смогли отметить — лучше сказать, чем промолчать


# --- события / events -----------------------------------------------------


def _sweep_markers(days: int = 7) -> None:
    """Убрать старые метки «уже говорили»: они лежат в общем /tmp."""
    try:
        cutoff = time.time() - days * 86400
        folder = pathlib.Path(tempfile.gettempdir()) / f"kanon-{os.getuid()}"
        for marker in folder.glob("reminded-*"):
            try:
                if marker.stat().st_mtime < cutoff:
                    marker.unlink(missing_ok=True)
            except OSError:
                continue  # одна неудача не должна прерывать уборку
    except Exception:  # noqa: BLE001
        pass


def on_session_start(_: dict) -> str:
    _sweep_markers()
    return _run("sweep.py", "--quiet")


def on_pre_tool_use(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    if payload.get("tool_name") == "Bash":
        # Запись через shell: heredoc в файл, sed -i, tee. Команда, которая
        # только читает, производством не является — и не напоминает.
        target = str(tool_input.get("command", ""))
        if not bash_writes(target):
            return ""
    else:
        target = str(tool_input.get("file_path", ""))
    # Запись самого чеклиста — не производство. Имя каталога берём то же, что
    # видит разбор: иначе KANON_DIR переопределяет его для линтера, но не для
    # хука, и создание чеклиста вызывает требование создать чеклист.
    names = {"_kanon", ".kanon"}
    override = os.environ.get("KANON_DIR")
    if override:
        names.add(pathlib.PurePath(override).name)
    if any(f"{os.sep}{d}{os.sep}" in target or target.startswith(d) for d in names):
        return ""

    # Заброшенный чеклист — всё равно чеклист: заводить второй не надо, а про
    # заброшенность скажет SessionStart. Раньше глушилка смотрела только на
    # "open", и файл, где всё доказано, а closed не проставлен, вызывал
    # требование завести новый.
    if [d for d in _checklists() if d.state in ("open", "stale")]:
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

# У SessionStart голый stdout доходит сам; у остальных — только через JSON.
PLAIN_STDOUT_EVENTS = {"SessionStart"}
SYSTEM_MESSAGE_LIMIT = 4000


def emit(event: str, message: str) -> None:
    """Напечатать так, чтобы адресат это увидел."""
    if event in PLAIN_STDOUT_EVENTS:
        print(message)
        return
    print(json.dumps({"systemMessage": message[:SYSTEM_MESSAGE_LIMIT]},
                     ensure_ascii=False))


def main() -> int:
    try:
        event = sys.argv[1] if len(sys.argv) > 1 else ""
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        payload = json.loads(raw) if raw.strip() else {}
        handler = HANDLERS.get(event)
        if handler:
            message = handler(payload)
            if message:
                emit(event, message)
    except Exception:  # noqa: BLE001
        pass  # сломанный хук хуже отсутствующего
    return 0


if __name__ == "__main__":
    sys.exit(main())
