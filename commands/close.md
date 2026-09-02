---
description: Close a checklist item with proof
argument-hint: Item number and the proof
---

Use the **kanon:task-to-checklist** skill.

An item is closed by inserting a `proof:` field, not by ticking `[x]`. Proof is
command output, a path to a file or screenshot, a commit hash, a link to a run.
"Done", "checked", "works" are not proof: `[x]` without `proof:` reads as open,
and the linter refuses it.

If the item failed, do not redo it quietly — add a line to Failures: what was
tried and what came back, verbatim.

$ARGUMENTS
