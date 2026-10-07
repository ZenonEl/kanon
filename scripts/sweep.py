#!/usr/bin/env python3
"""Report checklist lifetime and rebuild the derived active index.

No deletion is automatic. Valuable proof must outlive the checklist container.
Usage: sweep.py [--quiet] [--no-index]."""
from __future__ import annotations

import os
import pathlib
import stat
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kanon_format import INDEX_NAME, directory, find, parse  # noqa: E402


# The ownership header is stable; a directory name is not authorization.
INDEX_HEADER = "# kanon · checklists"

STATE_LABEL = {
    "open": "open",
    "closed": "closed",
    "stale": "stale",
}


def archive_count(folder: pathlib.Path) -> int:
    """Count regular archive containers without following an archive symlink."""
    archive = folder / "archive"
    if archive.is_symlink() or not archive.is_dir():
        return 0
    return sum(1 for path in archive.glob("*.md")
               if path.name != "LOG.md" and not path.is_symlink() and path.is_file())


def owns_index(target: pathlib.Path) -> bool:
    """Recognize our index by its ownership header, not its directory name.

    SessionStart may run in any project, so a familiar name is not write permission."""
    try:
        if not target.exists():
            return True
        with target.open(encoding="utf-8", errors="replace") as fh:
            return fh.readline().strip() == INDEX_HEADER
    except OSError:
        return False


def write_index(docs: list) -> pathlib.Path | None:
    """Rebuild the owned derived index; manual changes are overwritten."""
    folder = directory()
    if folder is None:
        return None
    target = folder / INDEX_NAME
    if not owns_index(target):
        raise PermissionError(f"{INDEX_NAME} not owned by Kanon — left untouched")
    lines = [INDEX_HEADER, "",
             "Derived file — rebuilt by `sweep.py`. Do not edit manually.",
             "",
             "| Checklist | State | Closed with proof | Task |",
             "|---|---|---|---|"]
    for doc in sorted(docs, key=lambda d: (d.state != "stale", d.path.name)):
        closed = len([i for i in doc.items if i.closed])
        task = (doc.meta.get("task", "") or "").replace("|", "\\|")
        lines.append(f"| [{doc.path.name}]({doc.path.name}) "
                     f"| {STATE_LABEL.get(doc.state, doc.state)} "
                     f"| {closed}/{len(doc.items)} | {task} |")
    if not docs:
        lines.append("| — | — | — | empty |")
    count = archive_count(folder)
    if count:
        lines.extend(["", f"[Archive: {count} files](archive/) — excluded from active acceptance.",
                      "Decisions and return conditions: `retire.py report`."])
    payload = "\n".join(lines) + "\n"

    # Replace a temporary file by name rather than writing through an existing inode.
    #
    # Name replacement protects symbolic and hard-link targets and prevents partial indexes.
    #
    # Preserve the previous mode: a replacement inode must not expose private task names.
    try:
        mode = stat.S_IMODE(target.stat().st_mode)
    except OSError:
        mode = 0o644

    tmp = folder / f".{INDEX_NAME}.tmp-{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.chmod(tmp, mode)  # preserve mode despite umask
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    paths, skipped = find()

    docs = []
    unreadable: list[str] = []
    for path in paths:
        try:
            docs.append(parse(path))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            # Isolate each unreadable file, including ValueError from numeric fields.
            unreadable.append(f"{path.name} ({exc.__class__.__name__})")

    if not docs and not skipped and not unreadable:
        if "--no-index" not in argv:
            try:
                # An empty directory updates only an index carrying our ownership header.
                write_index([])
            except (OSError, PermissionError):
                pass
        if not quiet:
            print("no checklists")
            count = archive_count(directory()) if directory() else 0
            if count:
                print(f"Archive: {count} files. Decisions and continuation: retire.py report.")
        return 0
    buckets: dict[str, list] = {"open": [], "closed": [], "stale": []}
    for doc in docs:
        buckets[doc.state].append(doc)

    lines: list[str] = []
    index_failed = ""
    if "--no-index" not in argv:
        try:
            write_index(docs)
        except OSError as exc:
            # Index-write failure must not suppress the lifetime report.
            index_failed = (f"  INDEX.md not written "
                            f"({exc.strerror or exc.args[0] if exc.args else exc})")

    # Surface stale work without deleting it.
    for doc in buckets["stale"]:
        lines.append(f"  STALE  {doc.path.name}")
        lines.append(f"      {doc.meta.get('task', '')}")
        for item in doc.open_items[:5]:
            lines.append(f"      open: {item.number}. {item.text or '<empty slot>'}")
        if len(doc.open_items) > 5:
            # Report truncation rather than silently hiding the sixth open item.
            lines.append(f"      …and another {len(doc.open_items) - 5}")
        lines.append("      → continue or explicitly archive: defer, cancel, supersede")

    # Suggest a disposition when a closed container reaches review age.
    for doc in buckets["closed"]:
        left = doc.expires_in
        if left is None:
            lines.append(f"  {doc.path.name}: closed={doc.closed_on!r} not parsed")
        elif left <= 0:
            lines.append(f"  EXPIRED   {doc.path.name}  ({-left} days ago)")
            lines.append("      → preserve proof, then archive or retain")
        elif not quiet:
            lines.append(f"  closed, review in {left} days  {doc.path.name}")

    if not quiet:
        for doc in buckets["open"]:
            closed = len([i for i in doc.items if i.closed])
            lines.append(f"  open  {doc.path.name}  "
                         f"{closed}/{len(doc.items)} closed with proof")
        folder = directory()
        count = archive_count(folder) if folder else 0
        if count:
            lines.append(f"  archive: {count} files — retire.py report")

    for link in skipped:
        lines.append(f"  symlink skipped: {link.name} — checklists must be "
                     f"regular files")
    for bad in unreadable:
        lines.append(f"  not read: {bad}")

    if index_failed:
        lines.append(index_failed)

    if not lines:
        return 0

    print("kanon · lifetime")
    print("\n".join(lines))

    if buckets["stale"] or any(d.expires_in is not None and d.expires_in <= 0
                               for d in buckets["closed"]):
        print("\ncontainers expire, not content: before deletion, verify that "
              "proof survives elsewhere.\nA file too valuable to delete indicates "
              "unfinished work; preserve it before disposal.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
