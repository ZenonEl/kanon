#!/usr/bin/env python3
"""Event sensors for checklist work.

SessionStart surfaces stale/expired work. PreToolUse reminds once after gathering
when production starts without a checklist. Stop lists outstanding items.
Nothing blocks; all internal failures exit zero without affecting the host.

SessionStart uses plain stdout. PreToolUse and Stop emit systemMessage JSON;
plain stdout for those events may reach only the host debug log. Decision fields
are intentionally absent. Bash is classified by content to cover shell-based
reading/writing. Codex also needs a local gathering tally when its transcript
is missing or uses another representation. Hook trust and wire compatibility
were measured on Codex 0.149.0; documentation names that historical measurement."""
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

# Classify Bash by its reading head and the absence of writing syntax.
BASH_READ_HEADS = {"cat", "head", "tail", "less", "sed", "grep", "rg", "ag", "find",
                   "fd", "ls", "tree", "wc", "stat", "file", "awk", "git"}
GIT_READ_SUBCOMMANDS = {"log", "show", "diff", "status", "blame", "ls-files", "grep",
                        "branch", "remote", "rev-parse", "describe", "tag"}
# Detect file redirection, tee, and in-place sed/perl; ignore null output and FD redirects.
_REDIRECT = re.compile(r"(?<![0-9&<])>{1,2}(?!&)\s*(?!/dev/null\b)\S")
_INPLACE = re.compile(r"\b(?:tee\b|sed\s+(?:-[a-zA-Z]*i|--in-place)|perl\s+-[a-zA-Z]*i)")
_LEADING = re.compile(r"^(?:\s*(?:cd\s+\S+\s*(?:&&|;)\s*|[A-Za-z_][A-Za-z0-9_]*=\S*\s+|sudo\s+|command\s+))*")


def bash_writes(command: str) -> bool:
    """Detect file writes; a heredoc without file redirection is not a write."""
    return bool(_REDIRECT.search(command) or _INPLACE.search(command))


def bash_gathers(command: str) -> bool:
    """Detect a reading command head with no writing syntax."""
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
    """Isolate unreadable files so one malformed checklist cannot hide its neighbors."""
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
            continue  # including oversized numeric fields
    return docs


def _gathering_in_line(line: str) -> int:
    """Count gathering calls in one transcript record.

    Read-like tools use their names; Bash uses command content. Legacy unparsed
    lines retain substring detection."""
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
    """Count gathering calls, stopping once the reminder threshold is reached."""
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
                    # Stop reading once the threshold is known; full rescans could exhaust the hook timeout.
                    return count
    except Exception:  # noqa: BLE001
        return 0
    return count


def _session_folder() -> pathlib.Path:
    return pathlib.Path(tempfile.gettempdir()) / f"kanon-{os.getuid()}"


def _session_key(session_id: str) -> str:
    # Hash session IDs so distinct IDs cannot collide after character removal.
    return hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:32]


def _tally_gathering(session_id: str, add: int) -> int:
    """Count gathering calls observed by this hook when no usable transcript exists.

    Only matched Bash calls reach this tally. The reminder uses the larger count
    from this tally and the transcript, avoiding double counting."""
    if not session_id:
        return 0
    folder = _session_folder()
    path = folder / f"gather-{_session_key(session_id)}"
    try:
        folder.mkdir(mode=0o700, exist_ok=True)
        # Append one byte per call: size counts gathering without a read-modify-write race.
        if add:
            with open(path, "ab", 0) as fh:
                fh.write(b"." * add)
        return path.stat().st_size
    except OSError:
        return 0


def _once_per_session(session_id: str) -> bool:
    """Create a private exclusive reminder marker.

    Atomic creation prevents duplicate reminders; a private directory prevents other
    users from suppressing a session by precreating a predictable marker."""
    if not session_id:
        return True
    safe = _session_key(session_id)
    folder = _session_folder()
    try:
        folder.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(folder / f"reminded-{safe}",
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError:
        return True  # prefer a reminder if marking failed


# --- events --------------------------------------------------------------


def _sweep_markers(days: int = 7) -> None:
    """Remove reminder and gathering markers older than one week."""
    try:
        cutoff = time.time() - days * 86400
        folder = pathlib.Path(tempfile.gettempdir()) / f"kanon-{os.getuid()}"
        for marker in (*folder.glob("reminded-*"), *folder.glob("gather-*")):
            try:
                if marker.stat().st_mtime < cutoff:
                    marker.unlink(missing_ok=True)
            except OSError:
                continue  # isolate individual cleanup failures
    except Exception:  # noqa: BLE001
        pass


def on_session_start(_: dict) -> str:
    _sweep_markers()
    return _run("sweep.py", "--quiet")


PATCH_PATH = re.compile(r"^\*\*\* (?:Add|Update|Delete|Move to) File: (.+)$", re.M)


def _in_kanon_dir(path: str, names: set) -> bool:
    return any(f"{os.sep}{d}{os.sep}" in path or path.startswith(f"{d}{os.sep}")
               or path == d for d in names)


def on_pre_tool_use(payload: dict) -> str:
    tool_input = payload.get("tool_input", {})
    tool_name = payload.get("tool_name")
    session_id = str(payload.get("session_id", ""))
    names = {"_kanon", ".kanon"}
    override = os.environ.get("KANON_DIR")
    if override:
        names.add(pathlib.PurePath(override).name)

    if tool_name == "Bash":
        # Reading Bash commands count as gathering; redirection or in-place editing is production.
        command = str(tool_input.get("command", ""))
        if bash_gathers(command):
            _tally_gathering(session_id, 1)
            return ""
        if not bash_writes(command):
            return ""
        targets = [command]
    elif tool_name == "apply_patch":
        # Codex provides the whole patch in tool_input.command; headers name targets.
        targets = PATCH_PATH.findall(str(tool_input.get("command", ""))) or [""]
    else:
        targets = [str(tool_input.get("file_path", ""))]

    # Checklist writes are not production. Honor the same directory override as the parser.
    if targets and all(_in_kanon_dir(t, names) for t in targets):
        return ""
    # A stale checklist still exists; SessionStart reports it rather than demanding a duplicate.
    if [d for d in _checklists() if d.state in ("open", "stale")]:
        return ""

    gathered = max(_gathering_count(payload.get("transcript_path")),
                   _tally_gathering(session_id, 0))
    if gathered < GATHERING_THRESHOLD:
        return ""

    if not _once_per_session(session_id):
        return ""

    return (
        "kanon: собранное сейчас живёт только в контексте, а производство уже "
        "началось — при сжатии или в новой сессии оно не доживёт.\n"
        "Заведи чеклист приёмки (/kanon:open или навык task-to-checklist): "
        "что должно быть на выходе, чем проверяется, что из собранного обязано "
        "попасть в результат.\n"
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
                     f"закрыто доказательством")
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

# SessionStart uses stdout; the other events need systemMessage JSON.
PLAIN_STDOUT_EVENTS = {"SessionStart"}
SYSTEM_MESSAGE_LIMIT = 4000


def emit(event: str, message: str) -> None:
    """Use the output representation that reaches the event recipient."""
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
        pass  # a hook failure must not break the host
    return 0


if __name__ == "__main__":
    sys.exit(main())
