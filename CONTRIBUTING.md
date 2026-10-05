# Contributing

**License:** [CC BY-SA 4.0](SPEC/LICENSE) · [Русский](CONTRIBUTING.ru.md)

## Source of truth

`SPEC/FORMAT.md` defines the checklist; `SPEC/RETIREMENT.md` defines cleanup.
Skills, commands and scripts consume those contracts. A mismatch is a tool bug,
not a reason to quietly weaken the contract. Concepts explain the choices.

## Language and licenses

Agent instructions, code comments/docstrings and normative contracts are English.
Human guides have English primary and Russian translations. Checklist prose and
agent conversation follow the user's language; quoted evidence stays verbatim.
Runtime messages and generated indexes default to Russian. Keep EN/RU aliases
and canonical ASCII fields stable.

`SPEC/`, `docs/` and `CONTRIBUTING*.md` use CC BY-SA 4.0. Other paths use
AGPL-3.0-or-later, including root README files and the agent instructions.
Standard license texts must remain verbatim. Do not silently relicense a file
when moving or translating it; keep README license tables consistent.

## Versions

The plugin version appears in six places:

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
.agents/plugins/marketplace.json
.codex-plugin/plugin.json
README.md
README.ru.md
```

All must agree, and both changelogs must have the release entry. Hosts use the
version when updating: a stale manifest can prevent changed behavior reaching an
installed copy. SemVer: patch for compatible corrections; minor for additive
commands/fields; major for incompatible changes requiring migration.

The format version is independent. Bump it only when the format contract changes.
Marketplace mirrors must remain byte-identical.

## Change process

1. State the observable result and proof for the change.
2. Update the relevant contract before implementation if behavior changes.
3. Add a regression that reproduces the failure or tests the new user outcome.
4. Implement a small complete change; keep behavior and presentation edits separable.
5. Synchronize both human-documentation versions, plugin versions and changelog.
6. Run the checks below and inspect the diff before committing.

```bash
python3 scripts/check-versions.py
python3 scripts/check-skills.py
python3 scripts/check-docs.py
bash tests/selftest.sh
python3 tests/mutate.py
diff .claude-plugin/marketplace.json .agents/plugins/marketplace.json
git diff --check
```

The selftest includes parser, hook, lifetime and retirement cases. Mutation tests
must prove their replacement actually happened; an unchanged target is a broken
bench, not a passing test. Mutations cover known regressions and do not replace
adversarial inputs or an independent review.

## Working data

Never commit `_kanon/`, `.kanon/`, archives/logs, source transcripts, private
review reports, client names, credentials, internal service addresses or personal
filesystem paths. Use synthetic examples. Check the current tree and reachable
history before making a repository public; changing HEAD does not remove history.
Publishing and history transformations require explicit owner authorization.

## Hook and filesystem rules

Hooks never block. Internal hook errors exit zero. PreToolUse reminds once per
session; preserve the gathering threshold. Archiving is explicit and does not
complete open items. Age never authorizes deletion. File operations must preserve
recoverable content, refuse links and destination collisions, and save disposal
history before removing the container.

## Routing

`check-skills.py` checks placement and metadata shape, not automatic selection.
Record actual input, host/plugin version and whether invocation was natural,
manual or prompted by a hook. K7 is an evaluation with a comparable no-plugin
run. Do not assume access to a particular host's evaluation feature.
