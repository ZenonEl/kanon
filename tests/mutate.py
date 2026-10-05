#!/usr/bin/env python3
"""Remove known defenses and require the selftest to fail.

Reject unchanged replacements as bench errors. This protects known paths,
not every hostile input representation. Usage: mutate.py [name-fragment]."""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Each replacement removes one defense: name, path, original snippet, replacement.
MUTATIONS: list[tuple[str, str, str, str]] = [
    ("чужой-индекс-переписывается", "scripts/sweep.py",
     "    if not owns_index(target):", "    if False:"),
    ("опознание-индекса-всегда-да", "scripts/sweep.py",
     "return fh.readline().strip() == INDEX_HEADER", "return True"),
    ("режим-индекса-всегда-0644", "scripts/sweep.py",
     "mode = stat.S_IMODE(target.stat().st_mode)", "mode = 0o644"),
    ("chmod-после-записи-снят", "scripts/sweep.py",
     "        os.chmod(tmp, mode)", "        pass"),
    ("подмена-имени-снята", "scripts/sweep.py",
     "        os.replace(tmp, target)", "        pass"),
    ("усечение-молчит", "scripts/sweep.py",
     "        if len(doc.open_items) > 5:", "        if False:"),
    ("номера-без-ограничения", "scripts/kanon_format.py",
     r"(\d{1,6})\.", r"(\d+)\."),
    ("o-nofollow-при-чтении-снят", "scripts/kanon_format.py",
     'os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)', "os.O_RDONLY"),
    ("жёсткая-ссылка-читается", "scripts/kanon_format.py",
     "        if os.fstat(fd).st_nlink > 1:", "        if False:"),
    ("симлинк-чеклист-читается", "scripts/kanon_format.py",
     "        if path.is_symlink():", "        if False:"),
    ("malformed-теряется", "scripts/kanon_format.py",
     "                doc.malformed.append((n, stripped))", "                pass"),
    ("заголовок-по-равенству", "scripts/kanon_format.py",
     "            pos = low.find(alias)", "            pos = 0 if low == alias else -1"),
    ("стоп-лист-по-всей-строке", "scripts/kanon_format.py",
     'bare = value.split("·")[0].strip(" .!·").lower()',
     'bare = value.strip(" .!·").lower()'),
    ("пустой-буллет-материал", "scripts/kanon_format.py",
     "            if entry:  # empty bullets are not gathered material", "            if True:"),
    ("нечитаемый-провал-тонет", "scripts/kanon_format.py",
     '            elif stripped.startswith("[!]"):', "            elif False:"),
    ("stale-с-третьим-условием", "scripts/kanon_format.py",
     "            if age.days >= 14:", "            if age.days >= 14 and self.open_items:"),
    ("порог-длины-вернулся", "scripts/kanon_format.py",
     "        return bare not in EMPTY_PROOF",
     "        return bare not in EMPTY_PROOF and len(bare) >= 6"),
    ("legacy-каталог-забыт", "scripts/kanon_format.py",
     'LEGACY_DIRS = (".kanon",)', "LEGACY_DIRS = ()"),
    ("kanon-dir-игнорируется", "scripts/kanon_format.py",
     'override = os.environ.get("KANON_DIR")', "override = None"),
    ("дата-провала-не-проверяется", "scripts/check-checklist.py",
     "        if not valid_date(stamp):", "        if False:"),
    ("провал-без-попытки-разрешён", "scripts/check-checklist.py",
     "        if missing:", "        if False:"),
    ("дубли-номеров-разрешены", "scripts/check-checklist.py",
     "    if duplicates:", "    if False:"),
    ("пункт-без-check-разрешён", "scripts/check-checklist.py",
     '        if not item.fields.get("check"):', "        if False:"),
    ("даты-по-форме", "scripts/check-checklist.py",
     "    if not valid_date(opened):", "    if False:"),
    ("slots-не-обязателен", "scripts/check-checklist.py",
     '    if "slots" not in doc.meta:', "    if False:"),
    ("slots-без-длины", "scripts/check-checklist.py",
     "slots.isascii() and slots.isdigit() and len(slots) <= 6",
     "slots.isdigit()"),
    ("пустая-приёмка-разрешена", "scripts/check-checklist.py",
     "    elif not doc.items:", "    elif False:"),
    ("правило-6-не-проверяется", "scripts/check-checklist.py",
     "    if doc.had_gathered_section and not doc.gathered:", "    if False:"),
    ("битый-файл-ослепляет", "scripts/check-checklist.py",
     "        except (OSError, UnicodeDecodeError, ValueError) as exc:",
     "        except ZeroDivisionError as exc:"),
    ("severity-по-подстроке", "scripts/check-checklist.py",
     '        if any(level == "error" for level, _ in problems):', "        if False:"),
    ("хук-голым-stdout", "hooks/kanon-hook.py",
     "    if event in PLAIN_STDOUT_EVENTS:", "    if True:"),
    ("хук-всегда-json", "hooks/kanon-hook.py",
     "    if event in PLAIN_STDOUT_EVENTS:", "    if False:"),
    ("хук-глушится-только-open", "hooks/kanon-hook.py",
     'd.state in ("open", "stale")', 'd.state == "open"'),
    ("маркер-канонизацией", "hooks/kanon-hook.py",
     '    return hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:32]',
     '    return "".join(c for c in session_id if c.isalnum() or c in "-_")[:64] or "u"'),
    ("сбор-не-опознан", "hooks/kanon-hook.py",
     'GATHERING_TOOLS = {"Read", "Grep", "Glob", "WebSearch", "WebFetch", "NotebookRead"}',
     'GATHERING_TOOLS = {"NOPE"}'),
    ("bash-слеп-на-запись", "hooks/kanon-hook.py",
     '    if tool_name == "Bash":', "    if False:"),
    ("bash-слеп-на-сбор", "hooks/kanon-hook.py",
     '        elif name == "Bash":', "        elif False:"),
    ("bash-любая-команда-запись", "hooks/kanon-hook.py",
     "    return bool(_REDIRECT.search(command) or _INPLACE.search(command))",
     "    return True"),
    ("зарубка-сбора-не-пишется", "hooks/kanon-hook.py",
     "            _tally_gathering(session_id, 1)", "            pass"),
    ("зарубка-сбора-не-читается", "hooks/kanon-hook.py",
     "                   _tally_gathering(session_id, 0))", "                   0)"),
    ("apply-patch-не-опознан", "hooks/kanon-hook.py",
     '    elif tool_name == "apply_patch":', "    elif False:"),
    ("пути-патча-не-читаются", "hooks/kanon-hook.py",
     '        targets = PATCH_PATH.findall(str(tool_input.get("command", ""))) or [""]',
     '        targets = [""]'),
    ("session-start-онемел", "hooks/kanon-hook.py",
     '    return _run("sweep.py", "--quiet")', '    return ""'),
    ("архив-потерял-исходник", "scripts/retire.py",
     "payload = data + MARKER", "payload = b'' + MARKER"),
    ("архив-не-убран-из-активного", "scripts/retire.py",
     "                    remove_source(base_fd, path.name, data, info)", "                    pass"),
    ("архив-без-следа-удаления", "scripts/retire.py",
     "                append_trail(archive_fd, data, doc, record, args.evidence_in)", "                pass"),
    ("архив-ложное-завершение", "scripts/retire.py",
     '        if args.disposition == "completed":', "        if False:"),
    ("архив-без-адреса-доказательств", "scripts/retire.py",
     '            if any(item.has_proof for item in doc.items) and not args.evidence_in.strip():', "            if False:"),
    ("архив-без-проверки-хеша", "scripts/retire.py",
     '    if digest(original) != record.get("original_sha256"):', "    if False:"),
    ("архив-теряет-маркеры-пунктов", "scripts/retire.py",
     "        lines.append(source_lines[item.line - 1])",
     '        lines.append(f"- {item.number}. {item.text}")'),
    ("архив-не-читает-crlf", "scripts/kanon_format.py",
     '    text = text.replace("\\r\\n", "\\n").replace("\\r", "\\n")',
     '    text = text'),
]


def run_one(name: str, rel: str, old: str, new: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "_kanon", ".kanon", "reviews"))
        target = work / rel
        before = target.read_text(encoding="utf-8")
        if old not in before:
            # An unchanged target means a broken mutation bench, not a test outcome.
            return "СТЕНД"
        target.write_text(before.replace(old, new, 1), encoding="utf-8")
        result = subprocess.run(["bash", "tests/selftest.sh"], cwd=work,
                                capture_output=True, text=True)
        return "ok" if result.returncode != 0 else "ПРОБЕЛ"


def main(argv: list[str]) -> int:
    needle = argv[0] if argv else ""
    chosen = [m for m in MUTATIONS if needle in m[0]]
    if not chosen:
        print(f"нет мутаций по «{needle}»")
        return 1

    width = max(len(m[0]) for m in chosen)
    gaps, bench = 0, 0
    for name, rel, old, new in chosen:
        verdict = run_one(name, rel, old, new)
        print(f"  {verdict:<6} {name:<{width}}  {rel}")
        gaps += verdict == "ПРОБЕЛ"
        bench += verdict == "СТЕНД"

    print(f"\nвсего {len(chosen)} · пробелов {gaps} · холостых {bench}")
    if bench:
        print("холостая мутация — дефект стенда: шаблон не совпал с файлом, "
              "и прогон ничего не проверил")
    return 1 if (gaps or bench) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
