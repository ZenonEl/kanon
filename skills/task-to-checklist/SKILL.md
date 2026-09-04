---
name: task-to-checklist
description: "Use at the moment work turns from gathering into producing — when research, a brief, a spec or a plan is about to become code, layout, a document or a design. Turns the task into an acceptance checklist in a file while the context is still fresh, so the work survives compaction and a new session. Also use when closing an item with proof, or when asking whether the work is actually finished. Triggers on: now build it, go ahead and build, start implementing, let's produce, we gathered enough, follow the plan and make it, make several variants, check all the screens, is it done, can we ship, what is left, acceptance, I finished, prove it. Триггеры: иди делай, теперь делай, приступай, начинай верстать, собрали приступаем, по этому плану сделай, сделай несколько вариантов, проверь все экраны, всё ли готово, можно сдавать, что ещё осталось, приёмка, я всё сделал, готово, чем докажешь."
---

# Task to checklist

A task in words becomes an acceptance checklist in a file — observable results
and the proof each one requires — written **before** production starts.

## Language

This skill is written in English. **The checklist is not.**

Write it in the language the user speaks — headings, item text, your own
wording. Do not produce an English file for a Russian-speaking user, or the
reverse, unless they ask for it. The language of these instructions says nothing
about the language of the output.

If the user's language cannot be determined, default to English: it is the
better working language for a model, and a wrong guess costs one correction.

**Never translate what you are quoting.** `returned:` is verbatim — the error
text as it appeared. A Gathered entry quoting a brief or a requirement keeps the
source's words. A proof that is command output stays that output. Translating
evidence destroys what made it evidence: it can no longer be checked against
where it came from.

So one checklist may mix languages — your prose in the user's language, quotes
in their sources' languages. That is correct, and the linter parses it.

Machine tokens are fixed — `check:`, `proof:`, `tried:`, `returned:`,
`[no check]` and the section names — and each has documented aliases per
language in [`SPEC/FORMAT.md`](../../SPEC/FORMAT.md). Use the aliases of the
user's language. Never force a language on someone to satisfy a parser.

## Why

Gathering eats the context window. Production starts afterwards and runs on
what is left. The agent does not ignore the research — it cannot see it.

Recognisable symptoms:

- the material was collected but is absent from the result — "did it from
  memory";
- an instruction given once in chat was not followed;
- one screen out of ten was checked, not all;
- one version was produced where several were asked for;
- every step ends with "what next?" instead of work;
- "it is not in the log, so it never ran" — from a log that never lists what
  ran; a conclusion from absence, built on nothing;
- the failing part was removed instead of diagnosed, and the item was closed —
  easier, not more correct.

Post-mortems explain this through character — rushed, read it carelessly,
thought I could manage. Those explanations cannot be fixed; hurry is not
patchable.

The real cause is the same for all of them: between *understood the task* and
*started working* there was no step that turns the task into a list where a
shortfall is visible. None of the failures had a check that could go red.

**The file is written while the context is fresh.** From then on it is the
source: the context may be compacted, the session may restart, the work may be
picked up by someone else.

## Threshold: when to stay silent

A skill that fires on "fix this typo" gets switched off on the second day.

Act when at least one holds:

- the task followed a **gathering** phase — files were read, searches ran,
  material arrived;
- the task names a **number** — "several variants", "ten screens", "all routes";
- the work spans more than one step and someone will accept its result.

None of these — say nothing. A small edit needs no checklist.

## Three questions

Each must produce lines in the file. Answering in your head does not count.

### 1. What must exist for the task to count as done?

A list of items, phrased as observable results rather than actions: not "lay out
the header" but "the header renders and opens at 360px".

**A number in the task becomes a number of slots.** "Several variants" — ask how
many, record it in `slots:`, create that many lines. "Check the screens" — list
all ten by name. An empty slot is visible; "as many as I manage" is not.

### 2. What proves each item?

Next to the item: a command, a screenshot path, a file, a commit hash, a test
run.

An item with no check is **allowed** but marked `[no check]`. Acceptance then
shows how many there are. Three out of five unchecked is not a checklist but a
list of intentions — better to learn that before delivery.

**A proof by absence needs a positive control.** "Not in the log" proves
nothing until the same log is shown to list something that *is* there. Write
the control into the check: `check: X absent in <log>; Y (known present) listed
in the same log`. Without the second half the check is a guess dressed as a
grep — and the reader who insists on it is right to.

**Removing the thing is not closing the item.** If an item is closed because the
failing part was taken out, the task has changed, not been done. The old item
gets a failure line (`tried: … · returned: …`), and the new state gets its own
item in words that say so: "works *without* Z" is a different result from
"works". The easier fix is allowed; hiding that it was the easier fix is not.

**For an item that says "cause found", the proof is the mechanism.** The chain
from trigger to failure; independent occurrences converging on the same point;
the attribution of each clue checked against its source rather than assumed;
and — the part that closes it — the diagnosis explaining the observation that
contradicted the first story. "Removed X, it runs" proves the workaround, not
the cause.

### 3. What from the gathered material must reach the result?

A digest into the same file: requirements, constraints, decisions found,
prohibitions.

**"I remember" is not a source.** Material left only in the context will not
survive to production.

## Where the file goes, and its shape

Four things that cost a rewrite the first time they were learned in the field:

- **One item is one line.** The parser reads line by line; an item wrapped onto
  a second line stops parsing at the wrap. Keep `check:` and `proof:` on the
  item's line. A long item is a sign the result is not yet one observable
  thing — split it rather than wrap it.
- **`_kanon/` is never committed.** In your own repository add it to
  `.gitignore`. In someone else's — a client project, a shared tree — use
  `.git/info/exclude` instead: no commit, nothing for other people to review,
  and it covers every worktree of that repository. Do this yourself as part of
  opening the checklist and mention it; do not stop to ask.
- **The file lives where the work is.** In a worktree, write it in that
  worktree's `_kanon/`. The hooks look in the session's working directory: if
  the session sits in the main tree while the work happens in a worktree, set
  `KANON_DIR` to the worktree's `_kanon/`, or the sensors will not see the file.
- **Your own decisions go into the file, not into chat.** An item that rests on
  a judgement call of yours — not the user's, not the source's — carries that
  provenance in Gathered: `<decision> · this session's call, not the client's,
  awaiting confirmation`. Chat evaporates; the file is what acceptance reads.

## How an item is closed

The one rule without which this degrades into paperwork:

> **An item is closed by inserting proof, not by ticking a box.**

No command output, no screenshot path, no commit hash — the item is open.
"Checked", "done", "works" are not proof: they are claims with nothing to argue
against.

Read the proof line with a stranger's eyes. `commit a1b2c3d + out/screens/07.png`
is proof. `done` is its absence.

The linter refuses the laziest cases mechanically, in any supported language —
see [Running the scripts](#running-the-scripts) below. It sees non-emptiness only — judging whether a proof is real
stays with the reader.

## If an item fails

A failure is not redone quietly. It leaves a line:

```
[!] 4 · tried: <action> · returned: <verbatim> · YYYY-MM-DD
```

Otherwise the third attempt knows nothing of the first two and the work circles
— especially after a session change. Those two fields are also ready material if
the block later has to be explained to someone.

**`returned:` is what you saw, not what the workaround did.** If the stack was in
front of you when you chose to take the part out, the stack goes into the line
— the chain of calls, verbatim — and `tried:` says so: `workaround, cause not
found`. The line is written at the moment the easy path is taken, because that
is the only moment when the evidence and the decision are both in view. A
post-mortem the next day can only say "I saw it in the morning and did not dig".

## Acceptance

At the end, run the file, not your memory:

- how many items are closed **with proof**;
- how many are ticked without proof (those are open);
- how many are marked `[no check]`;
- which slots are still empty;
- which items failed and what came back.

Print proofs **verbatim** rather than reporting that they exist: the machine
sees only non-emptiness, and the difference between a report and "confirmed:
done" is visible to a person alone.

"Done" is only said when the first number equals the total. Otherwise list the
shortfall.

## Do not ask "what next?"

While the file holds open items there is nothing to ask: next is the next open
item.

A "what next?" after every step is a symptom of a missing check — when there is
no way to verify yourself, all that remains is to ask a human. The file takes
that role.

## Lifetime

A checklist is scaffolding, not a building. **The container expires, the content
does not.**

| State | Lifetime |
|---|---|
| open | never expires |
| closed | 7 days, then dropped |
| stale (not closed, 14 days idle) | **surfaced, never dropped** |

Dropping an unclosed checklist silently erases the very shortfall it exists to
show.

Three outcomes on expiry: **drop** (default for closed), **extract** (proofs
move somewhere long-lived, container deleted), **keep** (rare — the checklist
became a document).

**Expiry is also a check.** If the file feels too valuable to delete, the proof
never moved anywhere, which means the work is not closed. That is a reason to
ask why, not to extend the deadline.

`sweep.py` computes this — see [Running the scripts](#running-the-scripts).
Dates worked out in passing are worked out wrong.

## Running the scripts

Two scripts back the rules above: `check-checklist.py` (refuses a tick without
proof, a slot count that does not match, a line that does not parse) and
`sweep.py` (derives lifetime, rebuilds the index).

They live in `scripts/` **inside the plugin**, not in the user's project, so the
path depends on the host:

- **Claude Code** — the plugin root is in `${CLAUDE_PLUGIN_ROOT}`:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-checklist.py"`
- **Codex and anything else** — that variable is not set in your shell. Use the
  plugin cache path, e.g.
  `python3 ~/.codex/plugins/cache/kanon/kanon/<version>/scripts/check-checklist.py`
  (`ls ~/.codex/plugins/cache/kanon/kanon/` shows the version).

Resolve the path once at the start of the work and reuse it. If neither form
resolves, say so plainly and continue without the machine check rather than
inventing a path — an unrun check reported as run is worse than an admitted gap.

## Boundary with planning

A plan answers **"how to do it"**. A checklist answers **"how will I know it is
done"**. Different questions; having the first does not supply the second.

The common failure looks exactly like this: the plan was detailed, every step
executed, the result still wrong.

If a plan already exists, do not rewrite it — extract the observable results and
their proofs from it.

## Optional link to a requirements registry

Self-contained; no external archive is required.

If the project has one, each item may carry a requirement identifier, and a
closed item then yields ready evidence for that requirement. Evidence
accumulated during the work is more honest than evidence recalled afterwards.

## What this does not do

**It does not judge taste.** A default palette or a templated composition is not
a shortfall in a list. That is a constraint to state in the task.

**It does not check the quality of the decomposition.** The checklist measures
completeness against what was written into it, not against what was needed. A
badly split task yields a green checklist over a bad split.

That limit is structural and is cured only by a second pair of eyes on the
checklist itself, **before** the work starts.

**It does not replace review.** A closed checklist means *nothing was
forgotten*, not *this is good*.
