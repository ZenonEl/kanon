# Install

**License:** CC BY-SA 4.0 · Russian: [`INSTALL.ru.md`](INSTALL.ru.md)

One repository serves two hosts. The difference between them matters and is
worth knowing before you install.

| | Claude Code | Codex |
|---|---|---|
| Entry points | skills **and** slash commands | **skills only** |
| Manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| Marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |
| Hooks | shipped by the plugin | same file, since Codex 0.149 — after trust review in `/hooks` |

Codex has no slash commands as a class. All of kanon's work is therefore
reachable through the `task-to-checklist` skill; the `/kanon:*` commands are
shortcuts over it. Under Codex the same result is reached in words, and the
scripts are run directly.

Requirements: Python 3.10+ for the scripts and hooks. Nothing else.

## Claude Code

### From the marketplace

```
/plugin marketplace add ZenonEl/kanon
/plugin install kanon@kanon
```

### Locally, for development

```
git clone https://github.com/ZenonEl/kanon.git
/plugin marketplace add ./kanon
/plugin install kanon@kanon
```

### Verify

```
/plugin
```

`kanon` should be listed as enabled. Then, in a fresh session and **without
naming the plugin**, say something like "we gathered the material, now build
it". The skill should raise itself. If it does not, the problem is routing, not
the files — see below.

## Codex

```
codex plugin marketplace add https://github.com/ZenonEl/kanon.git
codex plugin add kanon --marketplace kanon
```

A bare clone into a plugins directory is **not** enough: the host discovers
plugins through a marketplace, and a copied tree is reported as
`No marketplace plugins found`. Verified against the current CLI.

**Hooks run under Codex too** (measured live on 0.149.0, 2026-09-03). Codex
reads the same `hooks/hooks.json`, speaks the same wire — `tool_name` is `Bash`
for shell and `apply_patch` for edits, with the patch text in
`tool_input.command` — substitutes `${CLAUDE_PLUGIN_ROOT}` in hook commands and
shows `systemMessage`. What differs: every hook must be **trusted once** in
`/hooks` before it runs, and `transcript_path` is either empty or a rollout in
Codex's own format, so kanon counts gathering by its own tally of the `Bash`
calls that pass through the hook rather than by the transcript.

`${CLAUDE_PLUGIN_ROOT}` is set for hook commands only. In the skill body, under
Codex, call the scripts by the plugin cache path:
`~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/scripts/check-checklist.py`.

## What the hooks do

Shipped in `hooks/hooks.json` and active in Claude Code only. **None of them
block anything** — they only speak.

| Event | When it speaks |
|---|---|
| `SessionStart` | a checklist is stale, or a closed one has expired |
| `PreToolUse` on a write | gathering happened, no checklist exists, production started — **once per session**. A write is `Write`/`Edit`, or a `Bash` command that redirects into a file, uses `tee` or `sed -i`; gathering is `Read`/`Grep`/`Glob`, or a `Bash` command whose head is a reader (`cat`, `sed -n`, `git log`…) |
| `Stop` | open items remain; lists them |

Bash is classified by content because a session in bypass mode is told by the
host to read and write through the shell, and a sensor counting only tool names
is blind there by construction. A misclassification costs one extra reminder.

The pre-write reminder deliberately stays silent when: an open checklist already
exists, the write targets `_kanon/` itself, fewer than three gathering
operations happened in the session, or it already spoke once.

A hook that fails exits 0 and says nothing. A broken hook is worse than no hook.

Plain stdout only reaches the transcript for `SessionStart`, `UserPromptSubmit`
and `UserPromptExpansion`; for everything else the host writes it to the debug
log. So `PreToolUse` and `Stop` emit JSON with a `systemMessage` field instead.
Neither sets `decision` or `permissionDecision` — that would block, and nothing
here blocks.

## If the skill does not fire

Diagnose in this order, most common first:

1. **The skill is not in the list.** Then it is placement, not wording: the path
   is `skills/<name>/SKILL.md`, `SKILL.md` in capitals, valid YAML frontmatter,
   and the directory existed when the session started.
2. **Listed but not raised.** Then it is the `description`: routing reads only
   that, and never the body. The phrases you actually say must appear in it
   verbatim, in your language.
3. **Raised at the wrong time.** The threshold is documented in the skill: kanon
   stays silent on small edits by design. That is not a fault.

Form is checked mechanically:

```
python3 scripts/check-skills.py
```

It sees form only — file, frontmatter, required fields, description length.
Whether a live phrase raises the skill it cannot know. That is measured by a run
(`claude plugin eval`, currently in early access) or by keeping a log.

## Working files

Checklists are written to `_kanon/` in the working project root and are **not
committed**: scaffolding, not results. Add to the project's `.gitignore`:

```
_kanon/
```

Done already in this repository, and CI checks separately that `_kanon/` never
entered version control.
