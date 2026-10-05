#!/usr/bin/env python3
"""Check plugin versions in four manifests and two README badges.

Hosts compare the version when updating, so a stale manifest prevents delivery.
Each release also requires a matching CHANGELOG entry."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read(path, get):
    p = ROOT / path
    if not p.exists():
        return path, None, "файла нет"
    try:
        return path, get(json.loads(p.read_text(encoding="utf-8"))), None
    except Exception as exc:  # noqa: BLE001
        return path, None, str(exc)


def badge(path):
    p = ROOT / path
    if not p.exists():
        return path, None, "файла нет"
    m = re.search(r"badge/version-([0-9]+\.[0-9]+\.[0-9]+)-", p.read_text(encoding="utf-8"))
    return path, (m.group(1) if m else None), (None if m else "бейдж версии не найден")


found = [
    read(".claude-plugin/plugin.json", lambda d: d["version"]),
    read(".claude-plugin/marketplace.json", lambda d: d["plugins"][0]["version"]),
    read(".agents/plugins/marketplace.json", lambda d: d["plugins"][0]["version"]),
    read(".codex-plugin/plugin.json", lambda d: d["version"]),
    badge("README.md"),
    badge("README.ru.md"),
]

width = max(len(p) for p, _, _ in found)
versions = set()
broken = False

for path, version, err in found:
    if err:
        print(f"  {path:<{width}}  ОШИБКА: {err}")
        broken = True
        continue
    print(f"  {path:<{width}}  {version}")
    versions.add(version)

if broken:
    sys.exit(1)

if len(versions) != 1:
    print("\nверсии разошлись — обновлённый плагин не доедет до установленных копий")
    sys.exit(1)

version = versions.pop()

if not SEMVER.match(version):
    print(f"\n{version!r} — не semver вида X.Y.Z")
    sys.exit(1)

for filename in ("CHANGELOG.md", "CHANGELOG.ru.md"):
    changelog = ROOT / filename
    if not changelog.exists() or f"## {version}" not in changelog.read_text(encoding="utf-8"):
        print(f"\nВ {filename} нет записи '## {version}' — версия без описания изменений")
        sys.exit(1)

print(f"\nверсии совпадают: {version}, запись в CHANGELOG есть")
