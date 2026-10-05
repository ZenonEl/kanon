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
    "open": "в работе",
    "closed": "закрыт",
    "stale": "заброшен",
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
        raise PermissionError(f"{INDEX_NAME} создан не нами — не трогаем")
    lines = [INDEX_HEADER, "",
             "Производный файл — пересобирается `sweep.py`. Руками не править.",
             "",
             "| Чеклист | Состояние | Закрыто доказательством | Задача |",
             "|---|---|---|---|"]
    for doc in sorted(docs, key=lambda d: (d.state != "stale", d.path.name)):
        closed = len([i for i in doc.items if i.closed])
        task = (doc.meta.get("task", "") or "").replace("|", "\\|")
        lines.append(f"| [{doc.path.name}]({doc.path.name}) "
                     f"| {STATE_LABEL.get(doc.state, doc.state)} "
                     f"| {closed}/{len(doc.items)} | {task} |")
    if not docs:
        lines.append("| — | — | — | пока пусто |")
    count = archive_count(folder)
    if count:
        lines.extend(["", f"[Архив: {count} файлов](archive/) — не входит в активную приёмку.",
                      "Просмотр решений и условий возвращения: `retire.py report`."])
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
            print("чеклистов нет")
            count = archive_count(directory()) if directory() else 0
            if count:
                print(f"Архив: {count} файлов. Решения и продолжение: retire.py report.")
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
            index_failed = (f"  INDEX.md не записан "
                            f"({exc.strerror or exc.args[0] if exc.args else exc})")

    # Surface stale work without deleting it.
    for doc in buckets["stale"]:
        lines.append(f"  ЗАБРОШЕН  {doc.path.name}")
        lines.append(f"      {doc.meta.get('task', '')}")
        for item in doc.open_items[:5]:
            lines.append(f"      открыт: {item.number}. {item.text or '<пустой слот>'}")
        if len(doc.open_items) > 5:
            # Report truncation rather than silently hiding the sixth open item.
            lines.append(f"      …и ещё {len(doc.open_items) - 5}")
        lines.append("      → продолжить работу или явно архивировать: отложить, отменить, заменить")

    # Suggest a disposition when a closed container reaches review age.
    for doc in buckets["closed"]:
        left = doc.expires_in
        if left is None:
            lines.append(f"  {doc.path.name}: closed={doc.closed_on!r} не разобрано")
        elif left <= 0:
            lines.append(f"  ИСТЁК   {doc.path.name}  ({-left} дн. назад)")
            lines.append("      → сохранить доказательства, затем архивировать или оставить")
        elif not quiet:
            lines.append(f"  закрыт, истекает через {left} дн.  {doc.path.name}")

    if not quiet:
        for doc in buckets["open"]:
            closed = len([i for i in doc.items if i.closed])
            lines.append(f"  в работе  {doc.path.name}  "
                         f"{closed}/{len(doc.items)} закрыто доказательством")
        folder = directory()
        count = archive_count(folder) if folder else 0
        if count:
            lines.append(f"  архив: {count} файлов — retire.py report")

    for link in skipped:
        lines.append(f"  симлинк пропущен: {link.name} — чеклист читается только "
                     f"как обычный файл")
    for bad in unreadable:
        lines.append(f"  не прочитан: {bad}")

    if index_failed:
        lines.append(index_failed)

    if not lines:
        return 0

    print("kanon · срок жизни")
    print("\n".join(lines))

    if buckets["stale"] or any(d.expires_in is not None and d.expires_in <= 0
                               for d in buckets["closed"]):
        print("\nистекает тара, а не содержимое: перед удалением убедись, что "
              "доказательства переехали.\nфайл, который жалко удалить, — признак "
              "незакрытой работы, а не повод продлить срок.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
