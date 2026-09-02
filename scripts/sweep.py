#!/usr/bin/env python3
"""Срок жизни чеклистов: что истекло, что показать, что не трогать.

Считает программа, а не агент. Даты, посчитанные в уме между делом, считаются
неправильно и не считаются вовсе.

Принцип: истекает тара, а не содержимое. Ничего не удаляется само — команда
только показывает и предлагает исход. Молчаливое удаление незакрытого чеклиста
стёрло бы ровно ту недостачу, ради которой он заводился.

The container expires, the content does not. Nothing is deleted automatically:
this only reports and proposes an outcome.

Заодно пересобирает INDEX.md — производный файл, как у соседних инструментов:
одна читаемая поверхность на все чеклисты. Руками не правится, при каждом
прогоне переписывается.

Usage:
    sweep.py            # отчёт + пересборка INDEX.md
    sweep.py --quiet    # только требующее внимания (для хуков), INDEX тоже
    sweep.py --no-index # без пересборки
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kanon_format import INDEX_NAME, directory, find, parse  # noqa: E402


STATE_LABEL = {
    "open": "в работе / open",
    "closed": "закрыт / closed",
    "stale": "заброшен / stale",
}


def write_index(docs: list) -> pathlib.Path | None:
    """Пересобрать INDEX.md. Производный файл: правки в нём затираются."""
    folder = directory()
    if folder is None:
        return None
    lines = ["# kanon · checklists", "",
             "Производный файл — пересобирается `sweep.py`. Руками не править.",
             "Derived file, rebuilt by `sweep.py`. Do not edit by hand.", "",
             "| Чеклист / checklist | Состояние / state | Закрыто доказательством / closed with proof | Задача / task |",
             "|---|---|---|---|"]
    for doc in sorted(docs, key=lambda d: (d.state != "stale", d.path.name)):
        closed = len([i for i in doc.items if i.closed])
        task = (doc.meta.get("task", "") or "").replace("|", "\\|")
        lines.append(f"| [{doc.path.name}]({doc.path.name}) "
                     f"| {STATE_LABEL.get(doc.state, doc.state)} "
                     f"| {closed}/{len(doc.items)} | {task} |")
    if not docs:
        lines.append("| — | — | — | пока пусто / empty |")
    target = folder / INDEX_NAME
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    paths = find()
    if not paths:
        if not quiet:
            print("чеклистов нет / no checklists")
        return 0

    docs = [parse(p) for p in paths]
    buckets: dict[str, list] = {"open": [], "closed": [], "stale": []}
    for doc in docs:
        buckets[doc.state].append(doc)

    lines: list[str] = []
    index_failed = ""
    if "--no-index" not in argv:
        try:
            write_index(docs)
        except OSError as exc:
            # Отчёт важнее производного файла: раньше падение записи уносило с
            # собой весь вывод про заброшенное и истёкшее, ради которого команду
            # и вызывают.
            index_failed = f"  INDEX.md не записан ({exc.strerror}) / index not written"

    # stale — показать, не удалять. Самый важный раздел.
    for doc in buckets["stale"]:
        lines.append(f"  ЗАБРОШЕН / STALE  {doc.path.name}")
        lines.append(f"      {doc.meta.get('task', '')}")
        for item in doc.open_items[:5]:
            lines.append(f"      открыт: {item.number}. {item.text or '<пустой слот>'}")
        lines.append("      → закрыть, вытащить доказательства или выбросить")

    # closed — предложить исход по истечении.
    for doc in buckets["closed"]:
        left = doc.expires_in
        if left is None:
            lines.append(f"  {doc.path.name}: closed={doc.closed_on!r} не разобрано")
        elif left <= 0:
            lines.append(f"  ИСТЁК / EXPIRED   {doc.path.name}  ({-left} дн. назад)")
            lines.append("      → drop | extract (доказательства наружу) | keep")
        elif not quiet:
            lines.append(f"  закрыт, истекает через {left} дн.  {doc.path.name}")

    if not quiet:
        for doc in buckets["open"]:
            closed = len([i for i in doc.items if i.closed])
            lines.append(f"  в работе  {doc.path.name}  "
                         f"{closed}/{len(doc.items)} закрыто доказательством")

    if index_failed:
        lines.append(index_failed)

    if not lines:
        return 0

    print("kanon · срок жизни / lifetime")
    print("\n".join(lines))

    if buckets["stale"] or any(d.expires_in is not None and d.expires_in <= 0
                               for d in buckets["closed"]):
        print("\nистекает тара, а не содержимое: перед удалением убедись, что "
              "доказательства переехали.\nфайл, который жалко удалить, — признак "
              "незакрытой работы, а не повод продлить срок.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
