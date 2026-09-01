#!/usr/bin/env python3
"""Проверить, что скилы и команды вообще смогут сработать.

Скил, до которого не доходит маршрутизация, не «редко срабатывает» — он не
существует. Проверяется то, что можно проверить машиной: наличие файла, валидный
frontmatter, обязательные поля, имя каталога, совпадающее с `name`, и непустое
описание достаточной длины, чтобы в нём поместились триггеры.

Содержательное качество описания машина не проверяет и не должна: она видит
только форму. Смысловая проверка — на человеке.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
MIN_DESCRIPTION = 80

errors: list[str] = []


def frontmatter(path: pathlib.Path) -> dict[str, str] | None:
    m = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not m:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^[a-z-]+:", line):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")
        elif key:
            fields[key] += " " + line.strip()
    return fields


skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
if not skills:
    errors.append("skills/: ни одного SKILL.md")

for path in skills:
    rel = path.relative_to(ROOT)
    fields = frontmatter(path)
    if fields is None:
        errors.append(f"{rel}: нет frontmatter")
        continue
    name = fields.get("name")
    description = fields.get("description", "")
    if not name:
        errors.append(f"{rel}: нет поля name")
    elif name != path.parent.name:
        errors.append(f"{rel}: name={name!r} не совпадает с каталогом {path.parent.name!r}")
    if not description:
        errors.append(f"{rel}: нет поля description — скил не будет подниматься")
    elif len(description) < MIN_DESCRIPTION:
        errors.append(f"{rel}: description короче {MIN_DESCRIPTION} символов, "
                      "в него не помещаются триггеры")
    print(f"  {rel}  name={name}  description={len(description)} симв.")

for path in sorted((ROOT / "commands").glob("*.md")):
    rel = path.relative_to(ROOT)
    fields = frontmatter(path)
    if fields is None:
        errors.append(f"{rel}: нет frontmatter")
        continue
    if not fields.get("description"):
        errors.append(f"{rel}: нет поля description")
    print(f"  {rel}  description={len(fields.get('description', ''))} симв.")

if errors:
    print()
    for e in errors:
        print(f"  ОШИБКА: {e}")
    sys.exit(1)

print("\nскилы и команды формально пригодны к маршрутизации")
