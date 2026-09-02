#!/usr/bin/env python3
"""Проверки поведения разбора, а не кода возврата.

Заведены после того, как выяснилось: пять правок из семи держались тестами,
которые смотрели только `rc`, и откат любой из них проходил молча. Здесь каждый
ассерт привязан к конкретному правилу спеки и падает, если правило откатить.

Каждый тест назван правилом, которое защищает. Если тест не может покраснеть от
отката этого правила — он бесполезен и его надо переписать, а не оставлять для
счёта.
"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from kanon_format import parse  # noqa: E402

HEAD = """---
task: t
opened: 2026-09-02
closed: {closed}
slots: {slots}
source: -
---

## Gathered

- x · y

## Acceptance

"""

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"ok    {name}")
    else:
        print(f"ОШИБКА {name}" + (f" — {detail}" if detail else ""))
        failures.append(name)


def doc(items: str, closed: str = "null", slots: str = "null", age_days: int = 0):
    path = pathlib.Path(tempfile.mkdtemp()) / "c.md"
    path.write_text(HEAD.format(closed=closed, slots=slots) + items, encoding="utf-8")
    if age_days:
        old = dt.datetime.now().timestamp() - age_days * 86400
        os.utime(path, (old, old))
    return parse(path)


# --- правило 3: доказательство, а не отметка ------------------------------

d = doc("- [x] 1. r · check: c · proof: готово · 2026-09-02\n")
check("стоп-лист не обходится хвостом после пустого утверждения",
      not d.items[0].has_proof, f"proof={d.items[0].fields.get('proof')!r}")

d = doc("- [x] 1. r · check: c · proof: done · see above\n")
check("стоп-лист посегментно и на английском", not d.items[0].has_proof)

d = doc("- [x] 1. r · check: c · proof: h.png\n")
check("порога длины нет: путь к файлу — доказательство", d.items[0].has_proof)

d = doc("- [x] 1. r · check: c · proof: out.txt · строка 2 · строка 3\n")
check("сегмент без ключа приклеивается, а не отбрасывается",
      d.items[0].has_proof and "строка 3" in d.items[0].fields["proof"],
      f"proof={d.items[0].fields.get('proof')!r}")

# --- правило 4: метка «без проверки» --------------------------------------

d = doc("- [ ] 1. описать соглашение [no check] в доке · check: c\n")
check("[no check] внутри текста не делает пункт непроверяемым",
      not d.items[0].no_check, f"text={d.items[0].text!r}")

d = doc("- [ ] 1. r · [no check]\n")
check("[no check] отдельным сегментом опознаётся", d.items[0].no_check)

# --- правило 1 и разбор разделов -----------------------------------------

d = doc("- [x] 1. res · proof: коммит a1b2c3d\n- [ ] без номера · check: c\n")
check("строка, похожая на пункт и не разобравшаяся, попадает в malformed",
      len(d.malformed) == 1, f"malformed={d.malformed}")

path = pathlib.Path(tempfile.mkdtemp()) / "b.md"
path.write_text(HEAD.format(closed="null", slots="null").replace(
    "## Acceptance", "## Приёмка / Acceptance") + "- [x] 1. r · proof: коммит a1b2c3d\n",
    encoding="utf-8")
d = parse(path)
check("двуязычный заголовок раздела распознан", len(d.items) == 1 and d.had_acceptance_section)

path = pathlib.Path(tempfile.mkdtemp()) / "e.md"
path.write_text(HEAD.format(closed="null", slots="null"), encoding="utf-8")
d = parse(path)
check("пустой раздел приёмки виден как пустой",
      d.had_acceptance_section and not d.items)

# --- состояния: таблица States спеки --------------------------------------

d = doc("- [x] 1. r · check: c · proof: коммит a1b2c3d\n", age_days=30)
check("stale при закрытых пунктах: closed пусто И 14 дней",
      d.state == "stale", f"state={d.state}")

d = doc("- [ ] 1. r · check: c\n", age_days=30)
check("stale при открытых пунктах", d.state == "stale", f"state={d.state}")

d = doc("- [ ] 1. r · check: c\n", age_days=3)
check("свежий незакрытый — open", d.state == "open", f"state={d.state}")

d = doc("- [ ] 1. r · check: c\n", closed="2026-08-20", age_days=30)
check("проставленный closed сильнее возраста", d.state == "closed", f"state={d.state}")

# --- смешение языков -------------------------------------------------------

d = doc("- [x] 1. кнопка работает · check: скрин · подтв: out/скрин.png, коммит a1b2c3d\n")
check("смешанные ключи и кириллица в значении", d.items[0].has_proof)

# --- границы, которые держат таблицы States и Lifetime -------------------

d = doc("- [ ] 1. r · check: c\n", age_days=14)
check("граница stale ровно на 14 дне", d.state == "stale", f"state={d.state}")

d = doc("- [ ] 1. r · check: c\n", age_days=13)
check("13 дней — ещё open", d.state == "open", f"state={d.state}")

today = dt.date.today()
d = doc("- [x] 1. r · check: c · proof: коммит a1b2c3d\n",
        closed=str(today - dt.timedelta(days=7)))
check("closed истекает ровно на седьмой день", d.expires_in == 0, f"expires_in={d.expires_in}")

d = doc("- [x] 1. r · check: c · proof: коммит a1b2c3d\n",
        closed=str(today - dt.timedelta(days=6)))
check("на шестой день ещё не истёк", d.expires_in == 1, f"expires_in={d.expires_in}")

# --- находки Codex: границы представлений ---------------------------------

d = doc("- [ ] 1. результат без проверки и без пометки\n")
check("пункт без check: и без [no check] распознан как таковой",
      not d.items[0].fields.get("check") and not d.items[0].no_check)

path = pathlib.Path(tempfile.mkdtemp()) / "f.md"
path.write_text(HEAD.format(closed="null", slots="null")
                + "- [x] 1. r · check: c · proof: коммит a1b2c3d\n"
                + "\n## Failures\n\n[!] 1 · tried: собрать · returned: ошибка · 2026-09-02\n",
                encoding="utf-8")
d = parse(path)
check("поля провала разбираются",
      d.failures and d.failures[0][1].get("tried") and d.failures[0][1].get("returned"),
      f"failures={d.failures}")

path = pathlib.Path(tempfile.mkdtemp()) / "g.md"
path.write_text(HEAD.format(closed="null", slots="null")
                + "- [x] 1. r · check: c · proof: коммит a1b2c3d\n"
                + "\n## Failures\n\n[!] один · tried: x · returned: y\n", encoding="utf-8")
d = parse(path)
check("нечитаемая запись провала не исчезает", len(d.malformed) == 1, f"malformed={d.malformed}")

from kanon_format import valid_date  # noqa: E402
check("2026-99-99 — не дата", not valid_date("2026-99-99"))
check("2026-09-02 — дата", valid_date("2026-09-02"))

d = doc("- [x] 1. r · check: c · proof: p.png\n", closed="2026-99-99")
check("невалидная closed не роняет expires_in", d.expires_in is None)

path = pathlib.Path(tempfile.mkdtemp()) / "h.md"
path.write_text(HEAD.format(closed="null", slots="null").replace("- x · y", "- ")
                + "- [x] 1. r · check: c · proof: коммит a1b2c3d\n", encoding="utf-8")
d = parse(path)
check("пустой буллет не считается собранным материалом", not d.gathered)

if failures:
    print(f"\nпровалено: {len(failures)}")
    sys.exit(1)
print("\nразбор соответствует спеке")
