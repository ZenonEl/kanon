#!/usr/bin/env python3
"""Разбор формата чеклиста. Общий модуль для линтера, приёмки и хуков.

Формат описан в SPEC/FORMAT.md и является источником истины. Машинные ключи —
фиксированный ASCII, человеческие подписи свободны: чеклист пишется на языке
автора, а разбирается одинаково. Новый язык добавляется строкой в таблицу
псевдонимов, канонический ключ при этом не меняется.

The format is described in SPEC/FORMAT.md, which is the source of truth. Machine
tokens are fixed ASCII, human labels are free: a checklist is written in its
author's language and parsed the same way regardless. A new language is added by
extending the alias table; canonical keys never change.
"""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import re
from dataclasses import dataclass, field

# Каталог виден, а не спрятан: инструмент, который прячет свои файлы, прячет и
# недостачу, ради показа которой заведён. Подчёркивание — как у соседних
# инструментов, сортируется наверх.
#
# The directory is visible, not hidden: a tool that hides its own files hides
# the shortfall it exists to show.
CHECKLIST_DIR = "_kanon"
LEGACY_DIRS = (".kanon",)
INDEX_NAME = "INDEX.md"

# --- псевдонимы / aliases -------------------------------------------------

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
}

NO_CHECK = ("[no check]", "[без проверки]")

# Пустые утверждения, выдаваемые за доказательство. Список принципиально
# неполон: машина ловит самые ленивые случаи, отличить отчёт от «подтверждено:
# сделано» может только человек.
EMPTY_PROOF = {
    "done", "ok", "okay", "works", "working", "checked", "fixed", "yes", "good",
    "готово", "сделано", "работает", "проверил", "проверено", "исправлено", "да",
}
# Порога длины здесь НЕТ намеренно. Он был и отвергал «h.png» и «#482» —
# путь к скриншоту и ссылку на задачу, которые спека перечисляет как валидные
# доказательства. Спека — источник истины, критерий в ней один: стоп-лист.

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_ITEM = re.compile(r"^-\s*\[([ xX])\]\s*(\d+)\.\s*(.*)$")
_FAILURE = re.compile(r"^\[!\]\s*(\d+)\s*·?\s*(.*)$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valid_date(value: str) -> bool:
    """Дата, а не строка, похожая на дату.

    Проверки формы мало: `2026-99-99` ей удовлетворяет, проходит линтер, а потом
    роняет sweep на fromisoformat — и хук, глотающий исключение, теряет весь
    отчёт вместе с ним.
    """
    if not _DATE.match(value or ""):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True

_FIELD_LOOKUP = {a: key for key, aliases in FIELD_ALIASES.items() for a in aliases}


def _section_of(heading: str) -> str:
    """Какой раздел назван заголовком.

    По вхождению, а не по равенству: двуязычные заголовки вида
    «## Приёмка / Acceptance» естественны в этом репозитории, а точное сравнение
    их не узнавало — и весь блок пунктов молча выпадал из разбора.
    Побеждает псевдоним, встретившийся раньше: заголовок разбирается
    детерминированно.
    """
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
        """Доказательство есть, если первый его сегмент — не пустое утверждение.

        Проверять склеенную строку целиком нельзя: склейка сегментов сделала
        `подтв: готово · 2026-09-02` непохожим на «готово», и любой хвост —
        например дата, которую приписать естественно, — снимал стоп-лист.
        Сравнивается то, что человек написал ответом на «чем докажешь».
        """
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

    # --- выведенное состояние / derived state ---

    @property
    def closed_on(self) -> str:
        value = (self.meta.get("closed") or "").strip()
        return "" if value in ("", "null", "none", "-") else value

    @property
    def state(self) -> str:
        if self.closed_on:
            return "closed"
        try:
            # Условия ровно два, как в спеке. Третьего («есть открытые пункты»)
            # тут стояло, и из-за него чеклист, где всё доказано, а `closed:` не
            # проставлен, никогда не всплывал — то есть ровно тот случай, когда
            # доказательства никуда не переехали, а тара не закрыта.
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
        """Дней до истечения тары. None — не истекает."""
        if not valid_date(self.closed_on):
            return None
        closed = _dt.date.fromisoformat(self.closed_on)
        return 7 - (_dt.date.today() - closed).days


def _split_fields(tail: str) -> tuple[str, dict[str, str], bool]:
    """Разобрать хвост строки пункта на текст, поля и метку «без проверки».

    Сегмент без ключа НЕ отбрасывается, а приклеивается обратно к предыдущему
    полю (или к тексту). Иначе точка внутри доказательства обрезала бы его
    молча — а обрезанное доказательство линтер объявлял бы отсутствующим.

    Метка «без проверки» опознаётся только как отдельный сегмент: иначе пункт
    «описать соглашение [no check]» объявлялся бы непроверяемым.
    """
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


def parse(path: pathlib.Path) -> Checklist:
    text = path.read_text(encoding="utf-8")
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
            if entry:  # пустой буллет материалом не является
                doc.gathered.append(entry)
            continue

        if section == "acceptance":
            stripped = raw.strip()
            item = _ITEM.match(stripped)
            if not item and stripped.startswith("- ["):
                # Строка выглядит пунктом, но не разобралась. Молча пропустить
                # её нельзя: пункт исчезнет из приёмки, а линтер напечатает «ok».
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
                _, fields, _nc = _split_fields("x · " + fail.group(2))
                doc.failures.append((int(fail.group(1)), fields))
            elif stripped.startswith("[!]"):
                # Строка выглядит записью провала и не разобралась: пропустить
                # её молча значит потерять след попытки, ради которого раздел
                # и существует.
                doc.malformed.append((n, stripped))

    return doc


def directory(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Каталог чеклистов. Опознаётся по имени, но имя — рекомендация.

    KANON_DIR переопределяет. Исторические имена принимаются: проверка, чьи
    предупреждения учатся пропускать, хуже отсутствующей.
    """
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
    """Чеклисты и отдельно — пропущенные симлинки.

    Симлинк в каталоге чеклистов не читается. Хуки запускаются автоматически в
    любом каталоге, куда зашла сессия, а `read_text` идёт по ссылке: подложенный
    `link.md` на файл вне проекта выдал бы его содержимое в чужую сессию.
    Пропуск не молчаливый — пропущенные возвращаются отдельным списком и
    показываются.
    """
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
