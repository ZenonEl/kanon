#!/usr/bin/env python3
"""Retire inactive checklists without claiming that their work is complete.

All mutations default to a preview. Archive and restore preserve the original
bytes. Purge saves a disposition trail before removing the archived container.
Only the Python standard library is required; directory FDs bind operations to
the selected directories and prevent an archive symlink from redirecting writes.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import sys

from kanon_format import INDEX_NAME, directory, parse_text, valid_date

MARKER = b"\n<!-- kanon:retirement\n"
LOG_HEADER = "# kanon · disposal log\n"
DISPOSITIONS = {"deferred": "отложен", "cancelled": "отменён",
                "superseded": "заменён", "completed": "выполнен"}
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file(folder_fd: int, name: str) -> tuple[bytes, os.stat_result]:
    """Refuse links and special files before reading a bound file descriptor."""
    fd = os.open(name, os.O_RDONLY | NOFOLLOW | os.O_NONBLOCK, dir_fd=folder_fd)
    with os.fdopen(fd, "rb") as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Нужен обычный файл без символических и жёстких ссылок")
        return fh.read(), info


def write_new(folder_fd: int, name: str, data: bytes, mode: int) -> None:
    """Create exclusively; never overwrite a destination, including a link."""
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW,
                 mode, dir_fd=folder_fd)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fchmod(fh.fileno(), mode)
            os.fsync(fh.fileno())
        written, _ = read_file(folder_fd, name)
        if written != data:
            raise ValueError("Записанный файл не совпадает с исходным")
        os.fsync(folder_fd)
    except BaseException:
        # The original is still present. A failed new destination is ours.
        os.unlink(name, dir_fd=folder_fd)
        raise


def remove_source(folder_fd: int, name: str, data: bytes, info: os.stat_result) -> None:
    """Detect source changes before removal; retain both copies on failure."""
    current, current_info = read_file(folder_fd, name)
    if (current_info.st_dev, current_info.st_ino) != (info.st_dev, info.st_ino) or current != data:
        raise ValueError("Исходный файл изменился; обе копии оставлены, повтори проверку")
    os.unlink(name, dir_fd=folder_fd)
    os.fsync(folder_fd)


def unpack(data: bytes) -> tuple[bytes, dict]:
    """Validate the owned archive envelope and the preserved original bytes."""
    original, separator, tail = data.rpartition(MARKER)
    if not separator or not tail.endswith(b"\n-->\n"):
        raise ValueError("Нет записи архивирования Kanon")
    record = json.loads(tail[:-5].decode("utf-8"))
    if not isinstance(record, dict) or record.get("version") != 1:
        raise ValueError("Неизвестный формат записи архивирования")
    name = record.get("original_name", "")
    if (not isinstance(name, str) or pathlib.Path(name).name != name
            or name in ("", ".", "..", INDEX_NAME, "LOG.md") or not name.endswith(".md")):
        raise ValueError("Небезопасное исходное имя в архиве")
    if digest(original) != record.get("original_sha256"):
        raise ValueError("Содержимое архива не совпадает с сохранённым хешем")
    if record.get("disposition") not in DISPOSITIONS or not valid_date(record.get("archived_on", "")):
        raise ValueError("Некорректное решение об архивировании")
    for key in ("reason", "decision_source"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"В записи архивирования отсутствует {key}")
    if record["disposition"] in ("deferred", "superseded") and not record.get("continued_in"):
        raise ValueError("В архиве нет адреса продолжения")
    if record["disposition"] == "deferred" and not record.get("revisit"):
        raise ValueError("В архиве нет условия возвращения к работе")
    return original, record


def append_trail(folder_fd: int, data: bytes, doc, record: dict, evidence_in: str,
                 action: str = "удаление") -> None:
    """Persist outstanding work and failures before allowing permanent deletion."""
    lines = [f"\n## {dt.date.today()} · {action} · {record['original_name']}",
             f"Задача: {doc.meta.get('task', '')}",
             f"Решение: {DISPOSITIONS[record['disposition']]}",
             f"Причина: {record['reason']}",
             f"Источник решения: {record['decision_source']}",
             f"Продолжение: {record.get('continued_in') or 'не требуется'}",
             f"Вернуться: {record.get('revisit') or 'не требуется'}",
             f"Доказательства сохранены: {evidence_in or 'доказательств нет'}",
             f"Хеш удаляемого файла: {digest(data)}", "", "Незакрытые пункты:"]
    source_lines = data.decode("utf-8").splitlines()
    for item in doc.open_items:
        lines.append(source_lines[item.line - 1])
    if not doc.open_items:
        lines.append("- нет")
    lines.append("\nПровалы:")
    lines.extend(f"- {number} · {json.dumps(fields, ensure_ascii=False)}"
                 for number, fields in doc.failures)
    fd = os.open("LOG.md", os.O_RDWR | os.O_APPEND | os.O_CREAT | NOFOLLOW | os.O_NONBLOCK,
                 0o600, dir_fd=folder_fd)
    with os.fdopen(fd, "r+b") as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("Журнал удаления должен быть обычным файлом без ссылок")
        existing = fh.read()
        if existing and not existing.startswith(LOG_HEADER.encode()):
            raise ValueError("LOG.md создан не Kanon; чужой файл не трогаем")
        fh.write(("" if existing else LOG_HEADER).encode() + ("\n".join(lines) + "\n").encode())
        fh.flush()
        os.fsync(fh.fileno())
    os.fsync(folder_fd)


def operate(args, folder: pathlib.Path, base_fd: int, archive_fd: int | None) -> None:
    path = pathlib.Path(os.path.abspath(args.file))
    expected_parent = folder if args.action == "archive" else folder / "archive"
    if path.parent != expected_parent or path.name in (INDEX_NAME, "LOG.md") or path.suffix != ".md":
        raise ValueError(f"Выбери один чеклист непосредственно из {expected_parent}")
    source_fd = base_fd if args.action == "archive" else archive_fd
    if source_fd is None:
        raise ValueError("Архив отсутствует")
    data, info = read_file(source_fd, path.name)
    if args.action == "archive":
        doc = parse_text(path, data.decode("utf-8"))
        if not doc.meta or not doc.items or doc.malformed:
            raise ValueError("Чеклист не разобран; исправь форму перед архивированием")
        if args.disposition == "completed":
            spec = importlib.util.spec_from_file_location("kanon_check", pathlib.Path(__file__).with_name("check-checklist.py"))
            checker = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(checker)
            if doc.open_items or any(level == "error" for level, _ in checker.check(doc)):
                raise ValueError("Есть незакрытые пункты или ошибки формы; решение «выполнен» недопустимо")
        for key in ("reason", "decision_source"):
            if not getattr(args, key).strip():
                raise ValueError(f"Укажи {key}")
        if args.disposition in ("deferred", "superseded") and not args.continued_in.strip():
            raise ValueError("Укажи --continued-in: где остаётся незакрытая работа")
        if args.disposition == "deferred" and not args.revisit.strip():
            raise ValueError("Укажи --revisit: когда или при каком условии вернуться")
        record = dict(version=1, original_name=path.name, original_sha256=digest(data),
                      archived_on=dt.date.today().isoformat(), disposition=args.disposition,
                      reason=args.reason, decision_source=args.decision_source,
                      continued_in=args.continued_in, revisit=args.revisit)
        target = f"{record['archived_on']}-{path.stem}-{digest(data)[:12]}.md"
        payload = data + MARKER + json.dumps(record, ensure_ascii=False).encode() + b"\n-->\n"
        print(f"Архивирование: {path.name} → archive/{target}; {DISPOSITIONS[args.disposition]}")
        print(f"Незакрытые пункты: {', '.join(str(i.number) for i in doc.open_items) or 'нет'}")
        print(f"Причина: {args.reason}; источник решения: {args.decision_source}")
        if args.continued_in:
            print(f"Продолжение: {args.continued_in}; вернуться: {args.revisit or 'по замене'}")
        if args.apply:
            if archive_fd is None:
                os.mkdir("archive", 0o700, dir_fd=base_fd)
                archive_fd = os.open("archive", os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=base_fd)
                try:
                    write_new(archive_fd, target, payload, stat.S_IMODE(info.st_mode))
                    remove_source(base_fd, path.name, data, info)
                finally:
                    os.close(archive_fd)
            else:
                write_new(archive_fd, target, payload, stat.S_IMODE(info.st_mode))
                remove_source(base_fd, path.name, data, info)
    else:
        original, record = unpack(data)
        doc = parse_text(path, original.decode("utf-8"))
        if args.action == "restore":
            print(f"Восстановление: archive/{path.name} → {record['original_name']}")
            if args.apply:
                write_new(base_fd, record["original_name"], original, stat.S_IMODE(info.st_mode))
                append_trail(archive_fd, data, doc, record, "оригинал восстановлен", "восстановление")
                remove_source(archive_fd, path.name, data, info)
        else:
            if any(item.has_proof for item in doc.items) and not args.evidence_in.strip():
                raise ValueError("Укажи --evidence-in: где сохранены доказательства")
            print(f"Удаление: archive/{path.name}; след решения → archive/LOG.md")
            if args.apply:
                append_trail(archive_fd, data, doc, record, args.evidence_in)
                remove_source(archive_fd, path.name, data, info)
    print("Применено." if args.apply else "Это план. Для применения добавь --apply.")


def report(folder: pathlib.Path, archive_fd: int | None) -> None:
    if archive_fd is None:
        print("Архив пуст.")
        return
    for name in sorted(os.listdir(archive_fd)):
        if not name.endswith(".md") or name == "LOG.md":
            continue
        try:
            data, _ = read_file(archive_fd, name)
            original, record = unpack(data)
            doc = parse_text(folder / "archive" / name, original.decode("utf-8"))
            age = (dt.date.today() - dt.date.fromisoformat(record["archived_on"])).days
            print(f"{name}: {DISPOSITIONS[record['disposition']]}, незакрыто {len(doc.open_items)}, {age} дн.")
            print(f"  Причина: {record['reason']}; источник: {record['decision_source']}")
            if record.get("continued_in"):
                print(f"  Продолжение: {record['continued_in']}; вернуться: {record.get('revisit') or 'по замене'}")
            if age >= 30:
                print("  Пора пересмотреть: восстановить или явно удалить после сохранения следа.")
        except (OSError, ValueError, UnicodeError, TypeError) as exc:
            print(f"{name}: не прочитан ({exc})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Уборка чеклистов Kanon: архив, восстановление, удаление.")
    sub = parser.add_subparsers(dest="action", required=True)
    archive = sub.add_parser("archive", help="убрать неактивную задачу в архив")
    archive.add_argument("file")
    archive.add_argument("--disposition", choices=DISPOSITIONS, required=True)
    archive.add_argument("--reason", required=True)
    archive.add_argument("--decision-source", required=True)
    archive.add_argument("--continued-in", default="")
    archive.add_argument("--revisit", default="")
    restore = sub.add_parser("restore", help="вернуть чеклист в активную работу")
    restore.add_argument("file")
    purge = sub.add_parser("purge", help="сохранить след и удалить архивный файл")
    purge.add_argument("file")
    purge.add_argument("--evidence-in", default="")
    sub.add_parser("report", help="показать архив и условия возвращения к работе")
    for command in (archive, restore, purge):
        command.add_argument("--apply", action="store_true", help="применить; без флага только план")
    args = parser.parse_args(argv)
    try:
        folder = directory()
        if folder is None:
            raise ValueError("Каталог чеклистов отсутствует")
        folder = pathlib.Path(os.path.abspath(folder))
        with contextlib.ExitStack() as stack:
            base_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
            stack.callback(os.close, base_fd)
            if getattr(args, "apply", False):
                lock_fd = os.open(".retire.lock", os.O_WRONLY | os.O_CREAT | NOFOLLOW | os.O_NONBLOCK,
                                  0o600, dir_fd=base_fd)
                stack.callback(os.close, lock_fd)
                lock_info = os.fstat(lock_fd)
                if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
                    raise ValueError("Небезопасный файл блокировки")
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                archive_fd = os.open("archive", os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=base_fd)
                stack.callback(os.close, archive_fd)
            except FileNotFoundError:
                archive_fd = None
            if args.action == "report":
                report(folder, archive_fd)
            else:
                operate(args, folder, base_fd, archive_fd)
        return 0
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
