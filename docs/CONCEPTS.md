# Concepts

**License:** CC BY-SA 4.0 · Russian: [`CONCEPTS.ru.md`](CONCEPTS.ru.md)

Why kanon is built this way. The file format is normative in
[`SPEC/FORMAT.md`](../SPEC/FORMAT.md); the behaviour lives in
[`skills/task-to-checklist/SKILL.md`](../skills/task-to-checklist/SKILL.md).
This document is the reasoning both are derived from.

---

## 1. The harness: where this problem lives

**Agent = model + harness.** The harness is everything that is not the model:
the loop, tools, context, memory, instructions, checks, permissions, isolation,
logs.

A model remembers nothing between calls and does nothing in the world. Anything
that looks like an agent's competence is split across both layers, and the
quality of the work depends on both. The same model in a different harness
scores differently — on public benchmarks the spread rivals a change of model
generation.

The practical consequence: when an agent does the wrong thing, "is the model
stupid?" is almost always premature. Five other questions come first.

| # | Question | Layer |
|---|---|---|
| 1 | Did it know the rule at all? | guides — instructions, project rules |
| 2 | Could it learn that it did badly? | **sensors — checks that go red** |
| 3 | Could it see what it needed? | context |
| 4 | Did it have the means? | tools and permissions |
| 5 | All of the above yes? | now the model |

kanon lives entirely in 2 and 3.

## 2. Guides and sensors

A harness speaks to an agent two ways.

- **Guides** steer **before** the act: project rules, tool descriptions,
  instructions, skills.
- **Sensors** observe **after** and let it self-correct: tests, linters, hooks,
  screenshots, a judge.

Either can be **computational** (a deterministic check) or **inferential** (a
semantic judgement).

The key point: **a loop only means something if something improves between
attempts.** An agent with twenty tools and no sensor is not being stupid — it is
flying blind and generating plausible drafts twenty ways.

The typical imbalance in real setups: elaborate guides, no sensors. And the
usual cure is more guides — another paragraph of instructions. It does not help,
because not knowing was never the problem.

**kanon puts a sensor where people usually skip it:** on the acceptance of a
result, not on the syntax of the code.

## 3. Why acceptance is separate from the plan

A plan answers **"how to do it"**. A checklist answers **"how will I know it is
done"**.

They get confused because both look like lists. They are lists of different
kinds:

| | Plan | Acceptance checklist |
|---|---|---|
| Unit | an action | an observable result |
| Verified by | doing it | proof |
| Answers | what to do next | whether it is finished |
| Lives | until the work ends | until the container expires |

A detailed plan does **not** supply acceptance. The most common failure looks
exactly like that: the plan was thorough, every step executed, the result still
wrong — because nobody asked how they would know.

## 4. Proof instead of a tick

The central rule, and the one without which everything else rots:

> An item is closed by **inserting proof**, not by ticking a box.

The reason is verifiability, not discipline. A `[x]` is the agent's claim about
its own work and there is nothing to argue against it. `commit a1b2c3d +
out/screens/07.png` is a checkable fact: you can open it and look.

The caveat to keep in mind: **a machine can only check non-emptiness.**
"confirmed: done" is formally non-empty. Telling proof from its imitation is a
person's job — which is why acceptance prints proofs verbatim instead of
reporting that they exist.

`scripts/check-checklist.py` refuses the laziest cases via a stop list, in every
supported language. That is a floor, not a guarantee.

## 5. Why an unchecked item is allowed

The temptation is to forbid it. Then people stop writing checklists: part of any
work is honestly verified only by eye, and demanding "give me a command that
checks taste" turns the tool into an obstacle.

The compromise: **an unchecked item is allowed but marked** `[no check]`, and
acceptance shows what share of the result rests on nothing.

Three out of five unchecked is a list of intentions, not a checklist. Learning
that before delivery beats not writing one at all.

## 6. A number in the task becomes a number of slots

"Several variants", "ten screens", "all routes" — the quietest class of failure.
Nobody counts, and the shortfall is invisible: one variant got made and it looks
like work.

A slot fixes this mechanically. Ten screens, ten named lines. The `slots:` field
records what the task asked for so a machine can compare. An empty line is
visible; an intention is not.

The simplest sensor available, and among the most useful.

## 7. A failure leaves a trace

A failed item is not redone quietly. It leaves two fields: **what was tried**
and **what came back, verbatim**.

The practical reason: without a record the third attempt knows nothing of the
first two and the work circles — especially after a session change, when earlier
attempts are no longer in context.

The deeper reason: "stuck" with no attempt described is indistinguishable from
"did not dig". The first needs someone else to act, the second needs one more
try. They look identical and cost differently.

## 8. Lifetime: the container expires, the content does not

A checklist is ephemeral by nature: a task lives half a day, and files
accumulate by the hundred. Without a lifetime the directory becomes a dump and
people stop opening it.

But plain self-deletion breaks the point: **the proof would die with the file**,
and the proof is the whole purpose.

Hence the rule: by expiry everything valuable must live elsewhere — in a commit,
in a requirement, in a findings log. The file is scaffolding, not a building.

The clock starts at **closing**, not at creation; otherwise a checklist dies
mid-work.

### Expiry as a sensor

A side effect that turned out worth more than the tidying:

> If the file feels **too valuable to delete**, the proof never moved anywhere —
> which means the work is not closed.

That is a reason to ask why, not to extend the deadline. Housekeeping becomes a
check for free.

### A stale checklist is surfaced, not dropped

Fourteen days idle with open items is not grounds for quiet deletion. Dropping an
unclosed checklist erases exactly the shortfall it exists to show.

The general rule, applied in all three places: **silent deletion is forbidden.**
Whatever leaves, leaves visibly.

## 9. The threshold: when the tool must stay quiet

A skill that fires on "fix this typo" is switched off on the second day. The
threshold is not a convenience — it is a survival condition for the tool.

Acting is justified when at least one holds: the task followed a gathering
phase; the task names a number; the work spans more than one step and someone
will accept it. Otherwise, silence.

## 10. Context: why the file is written early

The most common form of failure looks like carelessness and is a loss of
context.

Gathering eats the window. Production starts afterwards and runs on the
remainder. "Did it from memory" describes this literally: the agent did not
ignore the material, it cannot see it.

Compaction keeps the current task, recent errors and file names; it loses
original instructions, intermediate decisions and rules. An instruction spoken
once mid-session does not survive to the end of the work.

Hence: **the file is filled in while the context is fresh** — right after
gathering, before the first line of production. From then on it is the source,
and the work survives compaction, a new session and a change of hands.

Research on agent memory arrives at the same principle independently: keep
structured state instead of a growing history. The difference is that here it is
applied by hand and from outside the runtime, because the runtime belongs to
someone else.

## 11. Firing on events, not on phrasing

A skill is raised when the move from gathering to producing is announced in
words. It is not always announced: an agent often crosses the boundary silently.

That gap is why kanon ships hooks. They see events rather than formulations:

- **SessionStart** — what is stale and what expired;
- **PreToolUse** on a write — gathering happened, no checklist exists, and
  production has begun: say so, **once per session**;
- **Stop** — items are still open: list them.

Three constraints, expensive to violate:

1. **Nothing blocks.** A hook that gets in the way is uninstalled along with the
   plugin. All three only speak.
2. **A hook never crashes.** Any internal error means exit 0 and silence: a
   broken hook is worse than none, because it breaks someone else's work.
3. **The pre-write reminder speaks once.** A reminder on every write is noise,
   and noise stops being read.

A fifth came from the first field run: **a sensor that counts tool names is
blind to the shell.** A session in bypass mode is told by the host to read with
`cat` and write with heredocs, and the transition it was built to catch went
through `Bash` from end to end while the hook counted `Read` and `Write`. Bash
is now classified by what the command does — a reading head is gathering, a
redirect into a file is production — because the event the sensor wants is
"a file is being written", not "a tool named Write is being called".

A sixth, from the same day: **the hooks run under Codex as well.** The docs
here said the opposite until a `Stop` message arrived from a Codex session. A
live probe showed Codex speaking Claude Code's hook wire — same events, same
`systemMessage`, `${CLAUDE_PLUGIN_ROOT}` substituted — with two differences
that matter: hooks need a one-time trust review, and the transcript is either
absent or in Codex's own format. The gathering sensor now keeps its own tally
of the shell reads it sees, and takes the larger of the two counts.

And a fourth, learned the hard way: **a hook has to speak in the form the host
listens to.** Plain stdout reaches the transcript only for a few event types;
elsewhere it goes to a debug log. Two of these three hooks printed text nobody
would ever see — and the tests, which asserted that the text was produced, were
green throughout. A sensor whose output does not arrive is indistinguishable
from a sensor that is not there.

## 12. Language

A checklist is written in the language its author works in. Only the machine
tokens are fixed ASCII, each with documented per-language aliases.

The alternative — one working language — would be a smaller tool. Forcing a
language on someone to satisfy a parser is a parser problem, not a user problem.

## 13. What kanon deliberately does not do

**It does not judge taste.** A default palette, a templated composition, the
modal answer from training — not a shortfall in a list. That is a constraint
stated in the task.

**It does not check the quality of the decomposition.** The checklist measures
completeness against what was written into it, not against what was needed. A
badly split task yields a green checklist over a bad split.

This limit is structural — the same class as a test that passes either way — and
is cured only one way: a second pair of eyes on the checklist itself, before the
work starts.

**It does not replace review.** A closed checklist means *nothing was
forgotten*, not *this is good*.

The boundary is deliberate. A tool that promises more than it verifies is worse
than no tool: a green list starts being read as a guarantee.

## 14. Where it sits

kanon is self-contained and needs nothing but a directory.

If a citable archive of client material and requirements sits alongside, the
link is one-way: an acceptance item may carry a requirement identifier, and a
closed item then yields ready evidence for that requirement.

That closes a known weakness of such archives: evidence is usually written at
the end and from memory — the very method this tool exists to replace. Evidence
accumulated during the work is more honest than evidence recalled afterwards.

There is no reverse dependency: the archive does not know about kanon and does
not need to.
