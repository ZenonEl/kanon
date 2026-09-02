#!/usr/bin/env python3
"""Срок жизни чеклистов: что истекло, что показать, что не трогать.

Считает программа, а не агент. Даты, посчитанные в уме между делом, считаются
неправильно и не считаются вовсе.

Принцип: истекает тара, а не содержимое. Ничего не удаляется само — команда
только показывает и предлагает исход. Молчаливое удаление незакрытого чеклиста
стёрло бы ровно ту недостачу, ради которой он заводился.

The container expires, the content does not. Nothing is deleted automatically:
this only reports and proposes an outcome.

Usage:
    sweep.py            # отчёт / report
    sweep.py --quiet    # только то, что требует внимания (для хуков)
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kanon_format import find, parse  # noqa: E402


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    paths = find()
    if not paths:
        if not quiet:
            print("чеклистов нет / no checklists")
        return 0

    buckets: dict[str, list] = {"open": [], "closed": [], "stale": []}
    for path in paths:
        doc = parse(path)
        buckets[doc.state].append(doc)

    lines: list[str] = []

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
