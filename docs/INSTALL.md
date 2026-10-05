# Installation

**License:** [CC BY-SA 4.0](../SPEC/LICENSE) · [Русский](INSTALL.ru.md)

## Requirements

Python 3.10+; no Python packages to install. The archive/restore/purge CLI needs
POSIX directory descriptors and advisory file locking (Linux/macOS).

Claude Code uses the skill and five slash commands. Codex uses the skill and
scripts. Both hosts can load `hooks/hooks.json`; host trust/settings determine
whether hooks run. Automatic skill selection must be observed separately.

## Claude Code

In Claude Code:

```text
/plugin marketplace add ZenonEl/kanon
/plugin install kanon@kanon
```

Check that Kanon is enabled with `/plugin`. For a local development checkout,
register its directory as a marketplace instead:

```text
/plugin marketplace add ./kanon
/plugin install kanon@kanon
```

Updating an installed copy uses the host's normal update flow; restart the
session after an update. Editing the development checkout does not itself update
an installed cache.

## Codex

```bash
codex plugin marketplace add https://github.com/ZenonEl/kanon.git
codex plugin add kanon --marketplace kanon
```

These command forms match the locally available CLI help. A copied checkout
alone does not register a marketplace. Use `codex plugin list` to inspect the
installation and the host's hook settings to review/trust hooks.

Hook compatibility was measured on Codex 0.149.0 on 2026-09-03: shell calls
arrived as `Bash`, patches as `apply_patch`, and `systemMessage` was visible.
That is a recorded measurement, not a guarantee about every future host version.
If hooks are absent or disabled, the skill and explicit CLI remain available.

## Script paths

Scripts belong to the plugin, not to the project being worked on. Run them from
that project's working directory and use the installed plugin's absolute path.

A Codex cache commonly places them under:

```text
~/.codex/plugins/cache/<marketplace>/kanon/<version>/scripts/
```

Claude Code has a similar cache under `~/.claude/plugins/cache/`. Locate the
actual version rather than assuming that a development checkout is installed.
Hook commands receive `${CLAUDE_PLUGIN_ROOT}` from their host; an ordinary shell
may not have it. If it is missing, use the verified cache path.

Examples after resolving the path:

```bash
python3 /path/to/kanon/scripts/check-checklist.py
python3 /path/to/kanon/scripts/sweep.py
python3 /path/to/kanon/scripts/retire.py report
```

`/path/to/kanon` is a placeholder. See [cleanup](CLEANUP.md) for mutation commands.
CLI/hook messages default to English; agent conversation follows your language.

## Hooks

| Event | Output |
|---|---|
| `SessionStart` | Stale active checklists and closed containers due for review |
| `PreToolUse` | One reminder when production starts after at least three gathering calls without an active checklist |
| `Stop` | Active items still open or ticked without proof |

Writes include `Write`, `Edit`, `NotebookEdit`, writing Bash commands and
`apply_patch`. Reading Bash commands count as gathering. The local Bash tally
covers sessions without a compatible transcript.

The production reminder is silent for checklist writes, when an open/stale
checklist already exists, below the gathering threshold, and after its first
reminder. Archived files do not trigger active reminders. No hook blocks work;
internal failures return zero. The thresholds are intentionally unchanged.

## Verify and diagnose

In a fresh session, give an ordinary task involving gathering followed by
production, without naming Kanon. Observe whether the skill is selected and a
checklist is created before implementation. If you invoke it manually, record
that separately: it does not prove automatic routing.

1. Missing from the skill list: check marketplace registration, enabled state,
   `skills/task-to-checklist/SKILL.md` and valid frontmatter.
2. Listed but not selected: record the exact prompt and plugin/host version.
   Routing reads the skill description; structural validation cannot diagnose it.
3. Selected for a tiny edit: check the skill's threshold before treating it as a bug.
4. Hooks silent: inspect host trust/settings and whether a compatible event reached
   the hook. A working Stop hook does not prove automatic skill selection.

From a development checkout:

```bash
python3 scripts/check-skills.py
```

This checks form only. Live selection needs observation or a routing evaluation
with a comparable no-plugin run; no availability claim about eval access is made.

## Working files

Add `_kanon/` to `.gitignore` in your project, or `.git/info/exclude` in a shared
repository. The plugin itself is safe to version; checklists, archives and logs
contain working material and stay out of commits.

Use `KANON_DIR` for another location. In a worktree, write the checklist where
work happens or point the session at that directory. Discovery is shallow:
`archive/` is separate from the active list, and `INDEX.md` is derived.
