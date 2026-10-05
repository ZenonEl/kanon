#!/usr/bin/env python3
"""Validate checklist form against SPEC/FORMAT.md.

The linter detects missing or empty proof, not proof authenticity. Acceptance
readers must inspect the evidence itself. Usage: check-checklist.py [path ...]
or --quiet to show errors only."""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kanon_format import Checklist, find, parse, valid_date  # noqa: E402

# Quantity detection suggests review; the reader decides whether it counts results.
QUANTITY = re.compile(
    r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten|"
    r"два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|"
    r"несколько|several|multiple)\b", re.I)


def check(doc: Checklist) -> list[tuple[str, str]]:
    errors: list[str] = []
    warn: list[str] = []

    if not doc.meta:
        return [("error", "нет frontmatter")]

    if not doc.meta.get("task"):
        errors.append("нет поля task")

    opened = doc.meta.get("opened", "")
    if not valid_date(opened):
        errors.append(f"opened={opened!r} — не существующая дата YYYY-MM-DD")

    if doc.closed_on and not valid_date(doc.closed_on):
        errors.append(f"closed={doc.closed_on!r} — не существующая дата YYYY-MM-DD")

    # A required slots key makes omitted quantities visible; null explicitly means no quantity.
    if "slots" not in doc.meta:
        errors.append("нет поля slots — поставь число, если задача называла "
                      "количество, иначе null")
    slots = (doc.meta.get("slots") or "").strip().lower()
    if slots in ("", "null", "none", "-"):
        # A numeral with slots=null is a warning: the machine cannot infer what it counts.
        found = QUANTITY.search(doc.meta.get("task", ""))
        if found:
            warn.append(f"в задаче есть «{found.group(0)}», а slots=null — "
                        f"если это про число результатов, поставь его")
    elif not (slots.isascii() and slots.isdigit() and len(slots) <= 6):
        errors.append(f"slots={slots!r} — не целое число")
    elif int(slots) != len(doc.items):
        errors.append(
            f"slots={slots}, а пунктов приёмки {len(doc.items)} — "
            f"задача называла количество, недостача не видна"
        )

    # An unparsed acceptance line is an error, never an invisible missing item.
    for line, raw in doc.malformed:
        errors.append(f"строка {line}: не разобрано как пункт приёмки — "
                      f"нужен вид «- [ ] N. текст»: {raw[:60]!r}")

    if not doc.had_acceptance_section:
        errors.append("нет раздела Приёмка (Acceptance) — приёмке нечего проверять")
    elif not doc.items:
        errors.append("раздел Acceptance пуст — приёмке нечего проверять")

    # A tick without proof does not close an item.
    for item in doc.ticked_without_proof:
        value = item.fields.get("proof", "")
        why = "нет поля proof" if not value else \
              f"proof={value!r} — пустое утверждение"
        errors.append(f"строка {item.line}: пункт {item.number} отмечен, но {why}")

    # A failure references a real item and carries an attempt.
    numbers = [i.number for i in doc.items]
    for number, fields in doc.failures:
        if number not in numbers:
            errors.append(f"провал ссылается на несуществующий пункт {number}")
        missing = [k for k in ("tried", "returned") if not fields.get(k)]
        # valid_date("") already rejects a missing date; avoid a redundant branch.
        stamp = fields.get("date", "")
        if not valid_date(stamp):
            errors.append(f"провал по пункту {number}: дата {stamp!r} отсутствует или "
                          f"не существует")
        if missing:
            errors.append(f"провал по пункту {number} без полей {', '.join(missing)} — "
                          f"след без попытки следом не является")

    # Duplicate numbers make failure and acceptance references ambiguous.
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        errors.append(f"номера пунктов повторяются: {duplicates} — "
                      f"ссылка на пункт перестаёт быть однозначной")

    # An item without a check must carry the explicit no-check marker.
    for item in doc.items:
        if item.empty_slot or item.no_check:
            continue
        if not item.fields.get("check"):
            errors.append(f"строка {item.line}: пункт {item.number} без «check:» и без "
                          f"пометки [no check]")

    # Gathered material must have a source beyond the model context.
    if doc.had_gathered_section and not doc.gathered:
        errors.append("раздел Gathered пуст — «я помню» не источник")
    elif not doc.had_gathered_section:
        warn.append("раздела Gathered нет — если сбор был, это дефект")

    # No-check items are allowed and reported; prohibiting subjective checks would discourage use.
    if doc.unchecked:
        share = len(doc.unchecked) / max(len(doc.items), 1)
        note = f"{len(doc.unchecked)} из {len(doc.items)} пунктов без проверки"
        if share >= 0.5:
            note += " — больше половины результата ни на чём не держится"
        warn.append(note)

    # Keep severity separate from text: user content may itself contain the warning marker.
    return ([("error", e) for e in errors]
            + ([("warn", w) for w in warn] if not errors else []))


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    args = [a for a in argv if not a.startswith("--")]
    skipped: list[pathlib.Path] = []
    if args:
        paths = [pathlib.Path(a) for a in args]
    else:
        paths, skipped = find()

    failed = False

    # Report skipped links; silent absence would conceal work.
    for link in skipped:
        print(f"  {link}: симлинк пропущен — чеклист читается только как "
              f"обычный файл")
        failed = True

    if not paths:
        if not quiet and not skipped:
            print("чеклистов нет")
        return 1 if failed else 0

    for path in paths:
        if not path.exists():
            print(f"  {path}: файла нет")
            failed = True
            continue
        try:
            doc = parse(path)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            # Isolate each file, including failures caused by oversized numeric fields.
            print(f"  {path}: не прочитан ({exc.__class__.__name__})")
            failed = True
            continue
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
