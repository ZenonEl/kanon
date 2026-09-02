---
description: Open an acceptance checklist — before the work, while the context is fresh
argument-hint: The task in one line
---

Use the **kanon:task-to-checklist** skill.

Create `_kanon/<YYYY-MM-DD>-<slug>.md` following `SPEC/FORMAT.md`. Write it in
the user's language, using that language's aliases for the machine tokens.

Three questions, each producing lines in the file:

1. what must exist at the end — observable results, not actions;
2. what proves each item — a command, a path, a commit; otherwise `[no check]`;
3. what from the gathered material must reach the result — a digest, not
   "I remember".

A number in the task goes into `slots:` and becomes that many lines. Do not
start producing before the file exists.

Then run `python3 scripts/check-checklist.py` (or the plugin's copy) to confirm
the file is well formed.

$ARGUMENTS
