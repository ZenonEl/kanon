#!/usr/bin/env python3
"""Линтер чеклиста: проверяет форму, а не смысл.

Правило, ради которого он написан: «пункт закрывается доказательством, а не
отметкой». Правило, которое некому держать, держится примерно неделю — потом
чеклист начинает зеленеть сам от себя. Поэтому проверка машинная и отказывает,
а не предупреждает: предупреждение, которое можно пропустить, пропускают.

Чего линтер НЕ умеет и не должен: судить, настоящее ли доказательство и верно ли
разложена задача. Машина видит непустоту. Отличить отчёт от «подтверждено:
сделано» может только человек — поэтому приёмка печатает доказательства
дословно, а не сообщает, что они есть.

Usage:
    check-checklist.py [path ...]     # по умолчанию — все в .kanon/
    check-checklist.py --quiet        # только ошибки, для хуков
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kanon_format import _DATE, Checklist, find, parse  # noqa: E402


def check(doc: Checklist) -> list[tuple[str, str]]:
    errors: list[str] = []
    warn: list[str] = []

    if not doc.meta:
        return [("error", "нет frontmatter / no frontmatter")]

    if not doc.meta.get("task"):
        errors.append("нет поля task / missing task")

    opened = doc.meta.get("opened", "")
    if not _DATE.match(opened):
        errors.append(f"opened={opened!r} — не дата вида YYYY-MM-DD / not a date")

    if doc.closed_on and not _DATE.match(doc.closed_on):
        errors.append(f"closed={doc.closed_on!r} — не дата вида YYYY-MM-DD / not a date")

    # Правило 2: число в задаче становится числом слотов.
    # Отсутствие ключа и `slots: null` — разные вещи, и спека их различает:
    # null означает «количество не называлось», а пропуск делает правило
    # непроверяемым. Без этого задача «сделай три варианта» с одним пунктом
    # проходила как «ok» — буквально симптом, ради которого правило есть.
    if "slots" not in doc.meta:
        errors.append("нет поля slots — поставь число, если задача называла "
                      "количество, иначе null / missing slots key")
    slots = (doc.meta.get("slots") or "").strip().lower()
    if slots in ("", "null", "none", "-"):
        pass  # задача не называла количества
    elif not slots.isdigit():
        errors.append(f"slots={slots!r} — не целое число / not an integer")
    elif int(slots) != len(doc.items):
        errors.append(
            f"slots={slots}, а пунктов приёмки {len(doc.items)} — "
            f"задача называла количество, недостача не видна / slot count mismatch"
        )

    # Пункт, который не разобрался, — ошибка, а не тишина. Иначе он исчезает
    # из приёмки, а линтер печатает «ok»: проверка, которая не может покраснеть.
    for line, raw in doc.malformed:
        errors.append(f"строка {line}: не разобрано как пункт приёмки — "
                      f"нужен вид «- [ ] N. текст» / unparsed acceptance line: {raw[:60]!r}")

    if not doc.had_acceptance_section:
        errors.append("нет раздела Acceptance / Приёмка — приёмке нечего проверять")
    elif not doc.items:
        errors.append("раздел Acceptance пуст — приёмке нечего проверять / empty Acceptance")

    # Правило 3: отметка без доказательства недействительна.
    for item in doc.ticked_without_proof:
        value = item.fields.get("proof", "")
        why = "нет поля proof / no proof field" if not value else \
              f"proof={value!r} — пустое утверждение / empty affirmation"
        errors.append(f"строка {item.line}: пункт {item.number} отмечен, но {why}")

    # Правило 5: провал ссылается на существующий пункт.
    numbers = {i.number for i in doc.items}
    for number, _ in doc.failures:
        if number not in numbers:
            errors.append(f"провал ссылается на несуществующий пункт {number} / dangling failure")

    # Правило 6: «я помню» не источник.
    if doc.had_gathered_section and not doc.gathered:
        errors.append("раздел Gathered пуст — «я помню» не источник / empty Gathered")
    elif not doc.had_gathered_section:
        warn.append("раздела Gathered нет — если сбор был, это дефект / no Gathered section")

    # Правило 4: пункт без проверки РАЗРЕШЁН, но виден. Отказывать нельзя —
    # часть работы честно проверяется только глазами, и запрет выгнал бы её из
    # чеклиста вовсе. Линтер называет долю; судит человек.
    if doc.unchecked:
        share = len(doc.unchecked) / max(len(doc.items), 1)
        note = f"{len(doc.unchecked)} из {len(doc.items)} пунктов без проверки"
        if share >= 0.5:
            note += " — больше половины результата ни на чём не держится"
        warn.append(note)

    # Пара (уровень, текст), а не подстрока «(!)» в готовой строке: в текст
    # ошибки подставляется пользовательский ввод, и пункт вида «- [ ] (!) 2. …»
    # печатал ошибку с кодом возврата 0 — а код возврата смотрит CI.
    return ([("error", e) for e in errors]
            + ([("warn", w) for w in warn] if not errors else []))


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    args = [a for a in argv if not a.startswith("--")]
    paths = [pathlib.Path(a) for a in args] or find()

    if not paths:
        if not quiet:
            print("чеклистов нет / no checklists")
        return 0

    failed = False
    for path in paths:
        if not path.exists():
            print(f"{path}: файла нет / missing")
            failed = True
            continue
        doc = parse(path)
        problems = check(doc)
        if any(level == "error" for level, _ in problems):
            failed = True
        if problems:
            for level, message in problems:
                mark = "" if level == "error" else "(!) "
                print(f"  {path}: {mark}{message}")
        elif not quiet:
            print(f"  {path}: ok · {len([i for i in doc.items if i.closed])}"
                  f"/{len(doc.items)} закрыто доказательством · {doc.state}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
