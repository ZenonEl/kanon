# kanon

[![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/code-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-CC%20BY--SA%204.0-lightgrey.svg)](SPEC/LICENSE)

**English** · [Русский](README.ru.md)

Kanon is a Claude Code plugin and Codex skill that turns a task into an
acceptance checklist — a file of observable results and the proof each one
requires — **before** production starts, while the gathered context is still
fresh.

The name is the Greek κανών: not a canon in the sense of dogma, but a
carpenter's measuring rod. The thing you lay against the work to see whether it
is straight.

## The problem

Gathering eats the context window. Production starts afterwards and runs on
what is left. The agent does not ignore the research — it cannot see it.

The symptoms are recognisable:

- the material was collected but is absent from the result — "I did it from
  memory";
- an instruction given once in chat was not followed;
- one screen out of ten was checked, not all of them;
- one version was produced where several were asked for;
- every step ends with "what next?" instead of work.

Post-mortems usually explain this through character — *rushed*, *read it
carelessly*, *thought I could manage*. Those explanations cannot be fixed. You
cannot patch hurry.

The real cause is the same for all of them: between *understood the task* and
*started working* there was no step that turns the task into a list where a
shortfall is visible. None of the failures had a check that could go red.

## What it does

Three questions, each of which must produce lines in a file:

1. **What must exist for the task to count as done?** Observable results, not
   actions. A number in the task becomes a number of slots — an empty slot is
   visible, "as many as I manage" is not.
2. **What proves each item?** A command, a screenshot path, a commit hash. An
   item with no check is allowed but marked, and acceptance shows how many
   there are.
3. **What from the gathered material must reach the result?** A digest, written
   down. *"I remember"* is not a source.

Then one rule that keeps the rest from rotting:

> **An item is closed by inserting proof, not by ticking a box.**

`[x]` without evidence reads as open. "Done", "checked", "works" are claims with
nothing to argue against.

## Why the file, not the context

Because the file survives what the context does not: compaction, a new session,
a different agent picking the work up. It is written early — right after
gathering, before the first line of production — for exactly that reason.

## What it deliberately does not do

- **It does not judge taste.** A default palette or a templated composition is
  not a shortfall in a list.
- **It does not check the quality of the decomposition.** A badly split task
  yields a green checklist over a bad split. The only cure is a second pair of
  eyes on the checklist itself, before the work starts.
- **It does not replace review.** A closed checklist means *nothing was
  forgotten*, not *this is good*.

The boundary is deliberate. A tool that promises more than it verifies is worse
than no tool: a green list starts being read as a guarantee.

## Sensors, not just rules

A rule nobody enforces holds for about a week. So the checkable rules are
checked by a program, and the tool fires on events rather than on phrasing.

| Piece | What it does |
|---|---|
| `scripts/check-checklist.py` | refuses `[x]` without proof, proof from the stop list of empty affirmations, a slot count that does not match, a failure pointing at a missing item |
| `scripts/sweep.py` | derives lifetime — `open` / `closed` / `stale` — and proposes an outcome. Deletes nothing by itself |
| `hooks/` | speaks at session start (stale, expired), once before production begins with no checklist, and at stop with the open items |

**Nothing blocks.** A hook that gets in the way is uninstalled along with the
plugin, and a hook that crashes is worse than none — so any internal error exits
0 in silence. The pre-write reminder speaks once per session.

## Languages

Write the checklist in whatever language you work in. Only the machine tokens
are fixed ASCII — `check:`, `proof:`, `tried:`, `returned:`, `[no check]` and
the section names — and each has documented aliases per language, so the linter
parses either. English and Russian ship today; a new language is one row in the
alias table.

## Install

See [`docs/INSTALL.md`](docs/INSTALL.md) for Claude Code and Codex.

## Documentation

| Document | What is in it |
|---|---|
| [`SPEC/FORMAT.md`](SPEC/FORMAT.md) | normative file format, states, lifetime ([ru](SPEC/FORMAT.ru.md)) |
| [`docs/CONCEPTS.md`](docs/CONCEPTS.md) | why it is built this way — harness, guides and sensors, proof over ticks ([ru](docs/CONCEPTS.ru.md)) |
| [`docs/INSTALL.md`](docs/INSTALL.md) | installation for both hosts, what the hooks do ([ru](docs/INSTALL.ru.md)) |
| [`skills/task-to-checklist/SKILL.md`](skills/task-to-checklist/SKILL.md) | the behaviour itself |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | versioning, CI, how to change things |

## Related

- [mnemo](https://github.com/ZenonEl/mnemo) — a citable archive of client
  material and requirements. Optional one-way link: a checklist item may carry a
  requirement id, and closing it yields ready evidence for that requirement.
- [ephemeris](https://github.com/ZenonEl/ephemeris) — issue-based daily handoffs
  between sessions.

Kanon is self-contained and requires neither of them.

## Licenses

| Path | License |
|---|---|
| `SPEC/`, `docs/` — text | [CC BY-SA 4.0](SPEC/LICENSE) |
| everything else — skills, commands, scripts | [AGPL-3.0-or-later](LICENSE) |
