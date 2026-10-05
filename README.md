# kanon

[![Version](https://img.shields.io/badge/version-0.13.0-blue.svg)](CHANGELOG.md)
[![Code license](https://img.shields.io/badge/code-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Docs license](https://img.shields.io/badge/docs-CC%20BY--SA%204.0-lightgrey.svg)](SPEC/LICENSE)

**English** · [Русский](README.ru.md)

Kanon turns a coding agent's task into an acceptance checklist **before work
starts**: observable results, checks and the proof needed to close each item.
The file preserves requirements and decisions across context compaction, a new
session or a different agent.

It is a plugin for Claude Code and Codex, with a small Python CLI. The name comes
from Greek κανών, a carpenter's measuring rod.

## Why

Research can disappear from the working context while implementation continues.
A plan can be executed while a requested screen, variant or constraint is still
missing. Kanon writes those results down while the material is fresh, then makes
missing proof and unfilled slots visible at acceptance.

## Example

An item closes by adding evidence:

```markdown
- [ ] 1. All requested screens fit at 360 px · check: browser screenshots
- [x] 2. Import preserves existing entries · check: import regression · proof: reports/import.txt
```

`[x]` with `proof: done` is still open. A quantity in the task becomes a matching
number of acceptance slots. Gathered constraints and failed attempts stay in the
same file. [Full format](SPEC/FORMAT.md).

## Install

Claude Code:

```text
/plugin marketplace add ZenonEl/kanon
/plugin install kanon@kanon
```

Codex:

```bash
codex plugin marketplace add https://github.com/ZenonEl/kanon.git
codex plugin add kanon --marketplace kanon
```

The linter and hooks need Python 3.10+. The retirement CLI requires Linux/macOS
with POSIX directory descriptors. See [installation and verification](docs/INSTALL.md)
for hook trust, local development and script paths.

## Workflow

1. Gather the material, then write the checklist before production.
2. Keep one observable result per line, with its check or an explicit no-check marker.
3. Close items with evidence; record failures with the attempt and verbatim result.
4. At acceptance, read every item and its proof. Report what remains open.
5. Explicitly retire an inactive task instead of keeping it in the active list forever.

Claude Code provides `/kanon:open`, `/kanon:close`, `/kanon:accept`,
`/kanon:sweep` and `/kanon:retire`. Codex reaches the same operations through
the `task-to-checklist` skill and scripts.

## Cleanup without false completion

Active files live under `_kanon/`; retired files under `_kanon/archive/`.
Archive with a reason and a decision source as **deferred**, **cancelled**,
**superseded** or **completed**. Only the last means all items have proof.
Deferred work needs a continuation address and a return condition.

`retire.py` previews every mutation by default. `--apply` archives, restores or
purges one selected file. Restore returns the exact original bytes. Purge saves
a decision trail first and requires surviving destinations for evidence. Nothing
is deleted automatically by age. [Cleanup examples](docs/CLEANUP.md).

Keep `_kanon/` out of git: use `.gitignore` in your own project or
`.git/info/exclude` in a shared repository. Checklists are working data.

## Sensors

| Component | Role |
|---|---|
| `check-checklist.py` | Refuses missing/empty proof, malformed items and mismatched slot counts |
| `sweep.py` | Reports stale/expired containers and rebuilds the active index |
| Hooks | Surface stale work at session start, remind once before production without a checklist, and list open items at Stop |
| `retire.py` | Explicit archive, restore, archive report and permanent disposal |

Hooks do not block. Internal hook failures exit zero; the production reminder
speaks at most once per session. Archived work does not enter active reminders.
Automatic skill selection is still being evaluated; installing the plugin is
not proof that every suitable task will trigger it.

## Languages

English is primary for public documentation; Russian translations are provided
beside it. Agent instructions and technical contracts are English. Checklists
and agent conversation follow the user's language; quoted evidence is never
translated. CLI/hook messages and generated indexes default to Russian.
Canonical field names stay ASCII, with EN/RU parsing aliases.

## Limits

Kanon checks completeness against the written checklist. It cannot judge taste,
prove that a task was decomposed correctly or authenticate evidence. A closed
checklist does not replace code review or human acceptance.

## Documentation

- [Installation](docs/INSTALL.md) · [Concepts](docs/CONCEPTS.md) · [Cleanup](docs/CLEANUP.md)
- [Checklist format](SPEC/FORMAT.md) · [Retirement contract](SPEC/RETIREMENT.md)
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Backlog](BACKLOG.md)
- [Road to 1.0](docs/RELEASE.md)

Optional neighbors: [mnemo](https://github.com/ZenonEl/mnemo) stores source
material and requirements; [ephemeris](https://github.com/ZenonEl/ephemeris)
passes work between sessions through daily issues. Kanon requires neither.

## Licenses

| Paths | License |
|---|---|
| `SPEC/`, `docs/`, `CONTRIBUTING*.md` | [CC BY-SA 4.0](SPEC/LICENSE) |
| Other paths, including skills, commands, scripts, tests and root README files | [AGPL-3.0-or-later](LICENSE) |

Standard license texts are kept verbatim. The plugin manifest's license field
names the code license; the table above describes the repository's split.
