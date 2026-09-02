---
description: Acceptance — run the whole checklist and say whether it is finished
argument-hint: Optionally the checklist name
---

Use the **kanon:task-to-checklist** skill.

Run the file, not your memory. Report:

- closed with proof — how many of how many;
- ticked without proof — these are open;
- marked `[no check]`;
- empty slots;
- items that failed and what came back.

Print proofs **verbatim**: the linter sees only non-emptiness, and telling a
report from "confirmed: done" is a person's job.

"Done" is only said when the first number equals the total. Otherwise list the
shortfall.

Start with:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check-checklist.py"
```

It refuses ticks without proof, slot counts that do not match, and lines that do
not parse as acceptance items.

$ARGUMENTS
