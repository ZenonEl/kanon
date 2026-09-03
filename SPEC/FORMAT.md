# Checklist format

**Format version:** 0.6
**Status:** normative. The single source of truth about the file.
**License:** CC BY-SA 4.0 (see [`LICENSE`](LICENSE))

Skills, commands and scripts in this repository are consumers of this format. A
disagreement between a tool's behaviour and the text below is a defect of the
tool, not a reason to rewrite the spec.

Russian translation of this document: [`FORMAT.ru.md`](FORMAT.ru.md).

## Language

A checklist is written in **the language its author works in** — not in the
language of this document. If that language cannot be determined, English is the
default: it is the better working language for a model, and a wrong guess is
cheap to correct.

**Quoted material is never translated.** What came from somewhere else stays in
the words it came in: `returned:` is verbatim, a Gathered entry quoting a brief
or a requirement keeps the source's language, a proof that is a command's output
is that output. Translating evidence destroys what made it evidence — it stops
being checkable against the thing it came from.

A single checklist may therefore mix languages: its own prose in the author's
language, its quotes in the sources' languages. That is correct, not sloppy, and
the linter parses it.

The machine tokens below are fixed ASCII keys so that a checklist parses
regardless of any of this.

Every token has documented aliases. The linter accepts any of them; new
translations are added by extending the alias table, never by changing the
canonical key.

A section heading is matched by **containment**, so bilingual headings such as
`## Приёмка / Acceptance` are recognised.

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
_kanon/
├── INDEX.md                  derived — rebuilt by sweep.py, never hand-written
└── <YYYY-MM-DD>-<slug>.md    one checklist per task
```

`_kanon/` sits in the working project root and goes into its `.gitignore` — or,
in a repository that is not yours to commit to, into `.git/info/exclude`, which
also covers every worktree of it. A checklist is not committed: it is scaffolding, not a result. Anything that must
outlive the work has to live elsewhere by the time the file expires.

The directory is **visible, not hidden**: a tool that hides its own files hides
the shortfall it exists to show. The leading underscore sorts it to the top.

**The name is a recommendation, not a rule.** `.kanon/` from earlier versions is
still accepted, and `KANON_DIR` overrides both. A check whose warnings people
learn to skip is worse than no check.

`INDEX.md` is derived. Edits to it are overwritten on the next `sweep.py`.

It is rewritten **only if it is ours**, recognised by its first line. A directory
name is not permission to replace files inside it: the index is written
automatically from a hook in whatever directory a session opened. The write goes
to a temporary file and is renamed into place, so neither a symbolic nor a hard
link diverts it, and an existing index keeps its file mode.

A checklist that is a symbolic link, or that has more than one name, is not read
and is reported as skipped — for the same reason.

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

   **The key is always present.** `slots: null` means the task named no
   quantity; omitting the key altogether makes the rule unverifiable and is
   rejected by the linter — the two are not the same thing.

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
- an Acceptance section exists and is not empty;
- every line in it that begins with `- [` parses as an item — a line that looks
  like an item but does not parse is an error, never a silent skip;
- the `slots:` key is present (`null` is a valid value) and, when numeric,
  matches the number of acceptance lines. A quantity word in `task:` with
  `slots: null` raises a **warning**, not an error: a machine sees the numeral,
  not whether it counts results;
- no `[x]` without `proof:`;
- `proof:` not in the stop list of empty affirmations, in any supported
  language. **The stop list is the only criterion** — there is no minimum
  length: `h.png` and `#482` are valid proofs;
- failure entries parse, reference existing item numbers, and carry both
  `tried:` and `returned:` — a trace with no attempt in it is not a trace;
- item numbers are unique: failures and acceptance output reference them;
- an item carries either `check:` or the `[no check]` marker;
- dates are real dates, not merely `YYYY-MM-DD`-shaped — including the date
  on every failure record, which is required;
- Gathered is not empty.

It cannot check whether a proof is real or an item well chosen. A machine sees
non-emptiness; only a person tells a report from the words "confirmed: done".
That is why acceptance prints proofs verbatim instead of reporting that they
exist.
