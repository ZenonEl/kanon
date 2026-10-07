# Concepts

**License:** [CC BY-SA 4.0](../SPEC/LICENSE) · [Русский](CONCEPTS.ru.md)

The [format](../SPEC/FORMAT.md) is normative. This document explains the choices
behind it; it is not a second format specification.

## Context and acceptance

An agent's behavior comes from both the model and its harness: context,
instructions, tools and checks. When a requested result is missing, ask whether
the agent had the requirement, could detect a failure, and still had the source
material. Kanon addresses visible omissions and context loss.

The checklist is written between gathering and production, while the sources
are still available. A file survives compaction and session changes more reliably
than an intention left in conversation.

## Plans and checklists

A plan answers how to proceed. Acceptance asks which results exist and what
proves them. Keep an existing plan; extract its expected results into the
checklist. Executing every planned action does not establish every result.

## Evidence

Ticking a box is easy. Attaching evidence makes a completion claim inspectable.
The linter catches absent proof and empty affirmations; a reader still needs to
open the file, screenshot, commit or run and decide whether it proves the item.
No minimum string length is imposed: a short screenshot path can be real proof.

Absence needs a positive control. Before inferring that a component never ran
because a log does not mention it, show that the same log lists something known
to have run. A log that lists nothing cannot support that inference.

Removing a failing component can provide a workaround, but it changes the
result being accepted. Record the attempt and create a result that says what
works without that component. A claim that the cause was found needs a mechanism
explaining the observed failure, including evidence against the initial theory.

## Counts and uncheckable items

A requested quantity becomes that many acceptance slots. Missing variants or
screens then appear as empty places, rather than a vague intention to do more.
The parser cannot decide whether every number in a brief counts deliverables;
its quantity heuristic warns rather than refusing on that assumption.

An item may explicitly have no check. Reporting that share is more useful than
forcing a fabricated test or discouraging a checklist for subjective work.

## Failed attempts

Failures keep the item number, attempted action, verbatim return and date.
They tell the next attempt or session what has already happened. When a clue
was visible before choosing a workaround, retain that clue at the time of the
decision; do not replace it with the later workaround result.

## Events and routing

The skill description routes explicit task transitions. Event sensors cover
some transitions that happen without being announced: session start, production
writes and stopping. Shell classification prevents a workflow using only Bash
from being invisible to reading/writing sensors.

A hook reminder and automatic skill selection are separate observations.
Structural skill checks do not measure routing. Live evaluation needs comparable
prompts and a no-plugin reference run, or a journal distinguishing natural and
manual invocations. Keep reminder thresholds: noisy hooks are soon ignored.

## Lifetime and retirement

The checklist is a working container. Valuable evidence should survive elsewhere
by the time the container is removed. Closed files reach review after seven days;
unclosed files idle for fourteen days are surfaced. No age causes deletion.

A partially finished task can be deferred, cancelled or replaced. Archiving it
preserves missing results and the decision while removing it from active
reminders. This prevents clutter without pretending that every item was done.
A continuation address keeps deferred work visible at its new home.

Restoration returns the original bytes. Permanent disposal separately saves a
compact trail with open items, attempts and surviving addresses. Keep that trail;
do not grow the active folder or a full-file archive forever just to preserve why
work stopped. [Retirement contract](../SPEC/RETIREMENT.md).

## Language

English technical instructions and EN/RU human guides serve different readers.
The checklist follows the user's language. Quoted evidence remains in its source
language because translating it breaks comparison with the original. Runtime
messages default to English; canonical keys are stable ASCII with parsing aliases.

## Boundaries and neighboring tools

Kanon measures completeness against the written checklist. It does not establish
that decomposition was correct, judge visual taste or replace review.

[mnemo](https://github.com/ZenonEl/mnemo) retains source material and requirements.
A checklist item may name its requirement ID and supply proof back to that
registry. [ephemeris](https://github.com/ZenonEl/ephemeris) hands work between
sessions through daily issues. Kanon itself requires neither tool.
