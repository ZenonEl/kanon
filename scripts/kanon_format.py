#!/usr/bin/env python3
"""Shared checklist parser for linting, acceptance and hooks.

SPEC/FORMAT.md is normative. Canonical fields are ASCII; EN/RU aliases remain
accepted so that human prose and quoted evidence can use their own languages."""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import re
from dataclasses import dataclass, field

# Keep the directory visible; the underscore sorts working checklists near the top.
#
# The directory is visible, not hidden: a tool that hides its own files hides
# the shortfall it exists to show.
CHECKLIST_DIR = "_kanon"
LEGACY_DIRS = (".kanon",)
INDEX_NAME = "INDEX.md"

# --- aliases -------------------------------------------------------------

SECTIONS: dict[str, tuple[str, ...]] = {
    "gathered": ("gathered", "собрано", "из собранного"),
    "acceptance": ("acceptance", "приёмка", "приемка"),
    "failures": ("failures", "провалы"),
}

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "check": ("check", "проверка"),
    "proof": ("proof", "подтв", "подтверждено"),
    "tried": ("tried", "пробовал"),
    "returned": ("returned", "вернулось"),
    "req": ("req",),
    "date": ("date", "дата"),
}

NO_CHECK = ("[no check]", "[без проверки]")

# The stop list detects empty affirmations; readers judge actual proof quality.
EMPTY_PROOF = {
    "done", "ok", "okay", "works", "working", "checked", "fixed", "yes", "good",
    "готово", "сделано", "работает", "проверил", "проверено", "исправлено", "да",
}
# No minimum length: a short screenshot path or issue number is valid proof.

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
# Bound numeric fields to prevent ValueError from hiding neighboring files; malformed lines remain visible.
_ITEM = re.compile(r"^-\s*\[([ xX])\]\s*(\d{1,6})\.\s*(.*)$")
_FAILURE = re.compile(r"^\[!\]\s*(\d{1,6})\s*·?\s*(.*)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valid_date(value: str) -> bool:
    """Validate a real calendar date, not just its shape.

    An impossible date would otherwise crash lifetime calculation and silence a hook."""
    if not _DATE.match(value or ""):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True

_FIELD_LOOKUP = {a: key for key, aliases in FIELD_ALIASES.items() for a in aliases}


def _section_of(heading: str) -> str:
    """Match the earliest section alias contained in a heading.

    Containment accepts bilingual headings instead of silently losing their items."""
    low = heading.strip().lower()
    best, at = "", len(low) + 1
    for key, aliases in SECTIONS.items():
        for alias in aliases:
            pos = low.find(alias)
            if pos != -1 and pos < at:
                best, at = key, pos
    return best


@dataclass
class Item:
    number: int
    ticked: bool
    text: str
    fields: dict[str, str] = field(default_factory=dict)
    no_check: bool = False
    line: int = 0

    @property
    def has_proof(self) -> bool:
        """Accept proof whose first segment is not an empty affirmation.

        Checking the joined value would let an appended date bypass the stop list."""
        value = self.fields.get("proof", "").strip()
        if not value:
            return False
        bare = value.split("·")[0].strip(" .!·").lower()
        return bare not in EMPTY_PROOF

    @property
    def empty_slot(self) -> bool:
        return not self.text.strip()

    @property
    def closed(self) -> bool:
        return self.ticked and self.has_proof


@dataclass
class Checklist:
    path: pathlib.Path
    meta: dict[str, str] = field(default_factory=dict)
    gathered: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    failures: list[tuple[int, dict[str, str]]] = field(default_factory=list)
    had_gathered_section: bool = False
    had_acceptance_section: bool = False
    malformed: list[tuple[int, str]] = field(default_factory=list)

    # --- derived state -------------------------------------------------------

    @property
    def closed_on(self) -> str:
        value = (self.meta.get("closed") or "").strip()
        return "" if value in ("", "null", "none", "-") else value

    @property
    def state(self) -> str:
        if self.closed_on:
            return "closed"
        try:
            # Age and an empty closed date define stale, even if every item already has proof.
            age = _dt.date.today() - _dt.date.fromtimestamp(self.path.stat().st_mtime)
            if age.days >= 14:
                return "stale"
        except OSError:
            pass
        return "open"

    @property
    def open_items(self) -> list[Item]:
        return [i for i in self.items if not i.closed]

    @property
    def ticked_without_proof(self) -> list[Item]:
        return [i for i in self.items if i.ticked and not i.has_proof]

    @property
    def unchecked(self) -> list[Item]:
        return [i for i in self.items if i.no_check]

    @property
    def empty_slots(self) -> list[Item]:
        return [i for i in self.items if i.empty_slot]

    @property
    def expires_in(self) -> int | None:
        """Return days until closed-container review; None means no expiry."""
        if not valid_date(self.closed_on):
            return None
        closed = _dt.date.fromisoformat(self.closed_on)
        return 7 - (_dt.date.today() - closed).days


def _split_fields(tail: str) -> tuple[str, dict[str, str], bool]:
    """Split item text, fields and the standalone no-check marker.

    Unkeyed segments attach to the preceding field or text: a separator inside proof
    must not silently truncate it. A marker embedded in prose is not a field."""
    segments = [s.strip() for s in tail.split("·")]
    no_check = False
    kept: list[str] = []
    for segment in segments:
        if segment.lower() in NO_CHECK:
            no_check = True
            continue
        kept.append(segment)

    text = kept[0].strip("*").strip() if kept else ""
    fields: dict[str, str] = {}
    last: str | None = None
    for part in kept[1:]:
        key, sep, value = part.partition(":")
        canonical = _FIELD_LOOKUP.get(key.strip().lower()) if sep else None
        if canonical:
            fields[canonical] = value.strip().strip("*")
            last = canonical
        elif last:
            fields[last] = f"{fields[last]} · {part}".strip()
        else:
            text = f"{text} · {part}".strip() if text else part
    return text, fields, no_check


def open_checklist(path: pathlib.Path) -> str:
    """Bind link validation to the opened file.

    O_NOFOLLOW refuses a symlink at open time; fstat refuses hard-linked files.
    A discovery-time pathname check alone would leave a check/use race."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if os.fstat(fd).st_nlink > 1:
            raise OSError(f"{path.name}: несколько имён у файла, не читаем")
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            return fh.read()
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def parse(path: pathlib.Path) -> Checklist:
    text = open_checklist(path)
    return parse_text(path, text)


def parse_text(path: pathlib.Path, text: str) -> Checklist:
    """Parse a previously opened snapshot without reopening its pathname."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    doc = Checklist(path=path)

    m = _FRONTMATTER.match(text)
    if m:
        for line in m.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep:
                doc.meta[key.strip().lower()] = value.strip()
        text = text[m.end():]
        offset = m.group(0).count("\n")
    else:
        offset = 0

    section = ""
    for n, raw in enumerate(text.splitlines(), start=offset + 1):
        heading = _HEADING.match(raw)
        if heading:
            section = _section_of(heading.group(1))
            if section == "gathered":
                doc.had_gathered_section = True
            elif section == "acceptance":
                doc.had_acceptance_section = True
            continue

        if section == "gathered" and raw.strip().startswith("-"):
            entry = raw.strip()[1:].strip()
            if entry:  # empty bullets are not gathered material
                doc.gathered.append(entry)
            continue

        if section == "acceptance":
            stripped = raw.strip()
            item = _ITEM.match(stripped)
            if not item and stripped.startswith("- ["):
                # An item-shaped line must not disappear when parsing fails.
                doc.malformed.append((n, stripped))
            if item:
                body, fields, no_check = _split_fields(item.group(3))
                doc.items.append(Item(
                    number=int(item.group(2)),
                    ticked=item.group(1).lower() == "x",
                    text=body,
                    fields=fields,
                    no_check=no_check,
                    line=n,
                ))
            continue

        if section == "failures":
            stripped = raw.strip()
            fail = _FAILURE.match(stripped)
            if fail:
                # Extract the failure date before unkeyed segments attach to the preceding field.
                tail, stamp = fail.group(2), ""
                head, sep, last = tail.rpartition("·")
                if sep and _DATE.match(last.strip()):
                    tail, stamp = head.strip(), last.strip()
                _, fields, _nc = _split_fields("x · " + tail)
                fields["date"] = stamp
                doc.failures.append((int(fail.group(1)), fields))
            elif stripped.startswith("[!]"):
                # Preserve malformed failure lines instead of losing the attempt history.
                doc.malformed.append((n, stripped))

    return doc


def directory(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find the active directory, honoring KANON_DIR and the legacy name."""
    root = root or pathlib.Path.cwd()
    override = os.environ.get("KANON_DIR")
    if override:
        candidate = pathlib.Path(override)
        candidate = candidate if candidate.is_absolute() else root / candidate
        return candidate if candidate.is_dir() else None
    for name in (CHECKLIST_DIR, *LEGACY_DIRS):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


def find(root: pathlib.Path | None = None) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Discover active files shallowly and report skipped symlinks.

    Archived files live in a subdirectory and never become active reminders."""
    folder = directory(root)
    if folder is None:
        return [], []
    found, skipped = [], []
    for path in sorted(folder.glob("*.md")):
        if path.name == INDEX_NAME:
            continue
        if path.is_symlink():
            skipped.append(path)
        elif path.is_file():
            found.append(path)
    return found, skipped
