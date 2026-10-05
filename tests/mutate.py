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
    ("foreign-index-overwritten", "scripts/sweep.py",
     "    if not owns_index(target):", "    if False:"),
    ("index-ownership-always-true", "scripts/sweep.py",
     "return fh.readline().strip() == INDEX_HEADER", "return True"),
    ("index-mode-always-0644", "scripts/sweep.py",
     "mode = stat.S_IMODE(target.stat().st_mode)", "mode = 0o644"),
    ("index-chmod-removed", "scripts/sweep.py",
     "        os.chmod(tmp, mode)", "        pass"),
    ("index-replacement-removed", "scripts/sweep.py",
     "        os.replace(tmp, target)", "        pass"),
    ("open-item-truncation-hidden", "scripts/sweep.py",
     "        if len(doc.open_items) > 5:", "        if False:"),
    ("unbounded-item-numbers", "scripts/kanon_format.py",
     r"(\d{1,6})\.", r"(\d+)\."),
    ("read-nofollow-removed", "scripts/kanon_format.py",
     'os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)', "os.O_RDONLY"),
    ("hard-linked-checklist-read", "scripts/kanon_format.py",
     "        if os.fstat(fd).st_nlink > 1:", "        if False:"),
    ("symlink-checklist-read", "scripts/kanon_format.py",
     "        if path.is_symlink():", "        if False:"),
    ("malformed-item-lost", "scripts/kanon_format.py",
     "                doc.malformed.append((n, stripped))", "                pass"),
    ("heading-exact-match-only", "scripts/kanon_format.py",
     "            pos = low.find(alias)", "            pos = 0 if low == alias else -1"),
    ("proof-stoplist-on-whole-string", "scripts/kanon_format.py",
     'bare = value.split("·")[0].strip(" .!·").lower()',
     'bare = value.strip(" .!·").lower()'),
    ("empty-bullet-gathered", "scripts/kanon_format.py",
     "            if entry:  # empty bullets are not gathered material", "            if True:"),
    ("malformed-failure-lost", "scripts/kanon_format.py",
     '            elif stripped.startswith("[!]"):', "            elif False:"),
    ("stale-requires-open-items", "scripts/kanon_format.py",
     "            if age.days >= 14:", "            if age.days >= 14 and self.open_items:"),
    ("proof-length-threshold", "scripts/kanon_format.py",
     "        return bare not in EMPTY_PROOF",
     "        return bare not in EMPTY_PROOF and len(bare) >= 6"),
    ("legacy-directory-forgotten", "scripts/kanon_format.py",
     'LEGACY_DIRS = (".kanon",)', "LEGACY_DIRS = ()"),
    ("kanon-dir-ignored", "scripts/kanon_format.py",
     'override = os.environ.get("KANON_DIR")', "override = None"),
    ("failure-date-not-validated", "scripts/check-checklist.py",
     "        if not valid_date(stamp):", "        if False:"),
    ("failure-attempt-not-required", "scripts/check-checklist.py",
     "        if missing:", "        if False:"),
    ("duplicate-numbers-allowed", "scripts/check-checklist.py",
     "    if duplicates:", "    if False:"),
    ("item-check-not-required", "scripts/check-checklist.py",
     '        if not item.fields.get("check"):', "        if False:"),
    ("invalid-dates-accepted", "scripts/check-checklist.py",
     "    if not valid_date(opened):", "    if False:"),
    ("slots-not-required", "scripts/check-checklist.py",
     '    if "slots" not in doc.meta:', "    if False:"),
    ("unbounded-slot-number", "scripts/check-checklist.py",
     "slots.isascii() and slots.isdigit() and len(slots) <= 6",
     "slots.isdigit()"),
    ("empty-acceptance-allowed", "scripts/check-checklist.py",
     "    elif not doc.items:", "    elif False:"),
    ("empty-gathered-allowed", "scripts/check-checklist.py",
     "    if doc.had_gathered_section and not doc.gathered:", "    if False:"),
    ("bad-file-hides-neighbors", "scripts/check-checklist.py",
     "        except (OSError, UnicodeDecodeError, ValueError) as exc:",
     "        except ZeroDivisionError as exc:"),
    ("severity-ignored", "scripts/check-checklist.py",
     '        if any(level == "error" for level, _ in problems):', "        if False:"),
    ("hook-always-plain-stdout", "hooks/kanon-hook.py",
     "    if event in PLAIN_STDOUT_EVENTS:", "    if True:"),
    ("hook-always-json", "hooks/kanon-hook.py",
     "    if event in PLAIN_STDOUT_EVENTS:", "    if False:"),
    ("hook-ignores-stale-checklist", "hooks/kanon-hook.py",
     'd.state in ("open", "stale")', 'd.state == "open"'),
    ("session-marker-collision", "hooks/kanon-hook.py",
     '    return hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:32]',
     '    return "".join(c for c in session_id if c.isalnum() or c in "-_")[:64] or "u"'),
    ("gathering-tools-forgotten", "hooks/kanon-hook.py",
     'GATHERING_TOOLS = {"Read", "Grep", "Glob", "WebSearch", "WebFetch", "NotebookRead"}',
     'GATHERING_TOOLS = {"NOPE"}'),
    ("bash-writes-forgotten", "hooks/kanon-hook.py",
     '    if tool_name == "Bash":', "    if False:"),
    ("bash-reads-forgotten", "hooks/kanon-hook.py",
     '        elif name == "Bash":', "        elif False:"),
    ("all-bash-commands-are-writes", "hooks/kanon-hook.py",
     "    return bool(_REDIRECT.search(command) or _INPLACE.search(command))",
     "    return True"),
    ("gathering-tally-not-written", "hooks/kanon-hook.py",
     "            _tally_gathering(session_id, 1)", "            pass"),
    ("gathering-tally-not-read", "hooks/kanon-hook.py",
     "                   _tally_gathering(session_id, 0))", "                   0)"),
    ("apply-patch-forgotten", "hooks/kanon-hook.py",
     '    elif tool_name == "apply_patch":', "    elif False:"),
    ("patch-paths-not-read", "hooks/kanon-hook.py",
     '        targets = PATCH_PATH.findall(str(tool_input.get("command", ""))) or [""]',
     '        targets = [""]'),
    ("session-start-silent", "hooks/kanon-hook.py",
     '    return _run("sweep.py", "--quiet")', '    return ""'),
    ("archive-original-lost", "scripts/retire.py",
     "payload = data + MARKER", "payload = b'' + MARKER"),
    ("archive-source-remains-active", "scripts/retire.py",
     "                    remove_source(base_fd, path.name, data, info)", "                    pass"),
    ("archive-purged-without-trail", "scripts/retire.py",
     "                append_trail(archive_fd, data, doc, record, args.evidence_in)", "                pass"),
    ("archive-false-completion", "scripts/retire.py",
     '        if args.disposition == "completed":', "        if False:"),
    ("archive-proof-destination-optional", "scripts/retire.py",
     '            if any(item.has_proof for item in doc.items) and not args.evidence_in.strip():', "            if False:"),
    ("archive-checksum-ignored", "scripts/retire.py",
     '    if digest(original) != record.get("original_sha256"):', "    if False:"),
    ("archive-item-markers-lost", "scripts/retire.py",
     "        lines.append(source_lines[item.line - 1])",
     '        lines.append(f"- {item.number}. {item.text}")'),
    ("archive-crlf-rejected", "scripts/kanon_format.py",
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
            return "BENCH"
        target.write_text(before.replace(old, new, 1), encoding="utf-8")
        result = subprocess.run(["bash", "tests/selftest.sh"], cwd=work,
                                capture_output=True, text=True)
        return "ok" if result.returncode != 0 else "GAP"


def main(argv: list[str]) -> int:
    needle = argv[0] if argv else ""
    chosen = [m for m in MUTATIONS if needle in m[0]]
    if not chosen:
        print(f"no mutations matching {needle!r}")
        return 1

    width = max(len(m[0]) for m in chosen)
    gaps, bench = 0, 0
    for name, rel, old, new in chosen:
        verdict = run_one(name, rel, old, new)
        print(f"  {verdict:<6} {name:<{width}}  {rel}")
        gaps += verdict == "GAP"
        bench += verdict == "BENCH"

    print(f"\ntotal {len(chosen)} · gaps {gaps} · empty replacements {bench}")
    if bench:
        print("empty replacement is a bench defect: snippet did not match; "
              "the run tested nothing")
    return 1 if (gaps or bench) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
