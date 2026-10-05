#!/usr/bin/env python3
"""Validate skill and command routing metadata.

Checks file placement, frontmatter, required fields and description length.
These structural checks do not measure automatic selection on a live prompt."""
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
    errors.append("skills/: no SKILL.md files")

for path in skills:
    rel = path.relative_to(ROOT)
    fields = frontmatter(path)
    if fields is None:
        errors.append(f"{rel}: missing frontmatter")
        continue
    name = fields.get("name")
    description = fields.get("description", "")
    if not name:
        errors.append(f"{rel}: missing name field")
    elif name != path.parent.name:
        errors.append(f"{rel}: name={name!r} does not match directory {path.parent.name!r}")
    if not description:
        errors.append(f"{rel}: missing description field — skill cannot be selected")
    elif len(description) < MIN_DESCRIPTION:
        errors.append(f"{rel}: description shorter than {MIN_DESCRIPTION} characters; "
                      "insufficient space for triggers")
    print(f"  {rel}  name={name}  description={len(description)} chars")

for path in sorted((ROOT / "commands").glob("*.md")):
    rel = path.relative_to(ROOT)
    fields = frontmatter(path)
    if fields is None:
        errors.append(f"{rel}: missing frontmatter")
        continue
    if not fields.get("description"):
        errors.append(f"{rel}: missing description field")
    print(f"  {rel}  description={len(fields.get('description', ''))} chars")

if errors:
    print()
    for e in errors:
        print(f"  ERROR: {e}")
    sys.exit(1)

print("\nskill and command metadata structurally valid for routing")
