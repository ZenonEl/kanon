# Checklist format

**Format version:** 0.2
**Status:** normative. The single source of truth about the file.
**License:** CC BY-SA 4.0 (see [`LICENSE`](LICENSE))

Skills, commands and scripts in this repository are consumers of this format. A
disagreement between a tool's behaviour and the text below is a defect of the
tool, not a reason to rewrite the spec.

Russian translation of this document: [`FORMAT.ru.md`](FORMAT.ru.md).

## Language

A checklist is written in **the language its author works in**. The machine
tokens below are fixed ASCII keys so that the linter parses a checklist
regardless of that language.

Every token has documented aliases. The linter accepts any of them; new
translations are added by extending the alias table, never by changing the
canonical key.

| Canonical | Aliases accepted |
|---|---|
| `## Gathered` | `## Собрано`, `## Из собранного` |
| `## Acceptance` | `## Приёмка` |
| `## Failures` | `## Провалы` |
| `check:` | `проверка:` |
| `proof:` | `подтв:`, `подтверждено:` |
| `tried:` | `пробовал:` |
| `returned:` | `вернулось:` |
| `[no check]` | `[без проверки]` |

Frontmatter keys are always canonical ASCII and are never translated.

## Location

```
.kanon/<YYYY-MM-DD>-<slug>.md
```

`.kanon/` sits in the working project root and goes into its `.gitignore`. A
checklist is not committed: it is scaffolding, not a result. Anything that must
outlive the work has to live elsewhere by the time the file expires.

`slug` — a short kebab-case name taken from the task.

## Body

```markdown
---
task: <the task in one line, as it was given>
opened: YYYY-MM-DD
closed: YYYY-MM-DD | null
slots: <integer | null>
source: <where the material came from: branch, issue, export, link>
---

## Gathered

- <requirement or constraint> · <where from>
- <prohibition> · <where from>

## Acceptance

- [ ] 1. <observable result> · check: <command | path | commit>
- [x] 2. <observable result> · check: <...> · proof: <the evidence itself>
- [ ] 3. <observable result> · [no check]
- [ ] 4. <empty slot, awaiting>

## Failures

[!] 2 · tried: <action> · returned: <verbatim> · YYYY-MM-DD
```

## Rules

1. **An item states an observable result, not an action.** "The header opens at
   360px" is checkable; "lay out the header" is not.

2. **A number in the task becomes a number of slots.** If the task names a
   quantity ("three variants", "ten screens"), `slots:` records it and the
   Acceptance section must hold that many lines, empty ones included. An empty
   slot is visible; an intention to do "as many as I manage" is not.

   `slots: null` means the task named no quantity. Omitting the field when the
   task did name one is a defect: the rule becomes unverifiable.

3. **An item is closed by proof, not by a tick.** `[x]` without a `proof:` field
   is invalid and reads as open. Proof is command output, a path to a file or
   screenshot, a commit hash, a link to a run. "Done", "checked", "works" are
   not proof.

4. **An item with no check is allowed, but marked** `[no check]`. Forbidding it
   is wrong: part of any work is honestly verified only by eye. Hiding it is
   wrong too — acceptance must show what share of the result rests on nothing.

5. **A failure leaves a trace.** Redoing an item without an entry in Failures is
   not allowed: the next attempt must know about the previous ones. A failure
   entry references an existing item number.

6. **"I remember" is not a source.** Gathered is filled in before production
   starts, while the material is still in context. An empty Gathered section
   after a gathering phase is a defect.

## States

State is **derived**, never stored:

| State | Condition |
|---|---|
| `closed` | `closed` is non-empty |
| `stale` | `closed` is empty AND the file has not changed for 14 days |
| `open` | otherwise |

A stored status is a claim with nothing to argue against. One derived from a
date and the file's content can be checked.

## Lifetime

| State | Lifetime |
|---|---|
| `open` | never expires |
| `closed` | 7 days from the `closed` date, then dropped |
| `stale` | **never dropped; surfaced** with its open items listed |

The principle: **the container expires, the content does not.** By expiry
everything valuable must live somewhere else — in a commit, in a requirement, in
a findings log.

Expiry doubles as a check: a file you are reluctant to delete means the proof
never moved anywhere, which means the work is not closed.

Three outcomes:

1. `drop` — delete (the default for `closed`);
2. `extract` — move the proof somewhere long-lived, delete the container;
3. `keep` — preserve whole (rare; the checklist became a document).

## Optional link to a requirements registry

An acceptance item may carry the identifier of an external requirement:

```markdown
- [x] 2. <result> · req: t042 · check: <...> · proof: <evidence>
```

The `proof:` field is then a ready value for that registry's evidence field.

The link is one-way: kanon knows about the registry, the registry does not know
about kanon and does not need to. Its absence does not affect anything.

## What the linter checks

`scripts/check-checklist.py` verifies form only:

- frontmatter present and parseable, `opened` a valid date;
- `slots:` present when the task names a quantity, and matching the number of
  acceptance lines;
- no `[x]` without `proof:`;
- `proof:` not in the stop list of empty affirmations, in any supported
  language;
- failure entries reference existing item numbers;
- Gathered is not empty.

It cannot check whether a proof is real or an item well chosen. A machine sees
non-emptiness; only a person tells a report from the words "confirmed: done".
That is why acceptance prints proofs verbatim instead of reporting that they
exist.
