---
description: Lifetime — what expired, what to extract, what to surface
---

Use the **kanon:task-to-checklist** skill.

Run `python3 scripts/sweep.py`. It derives the state of every checklist in
`_kanon/` per `SPEC/FORMAT.md`:

- `open` — never expires, leave alone;
- `closed` older than 7 days — propose an outcome: `drop` / `extract` / `keep`;
- `stale` — **surfaced, never dropped**: list the open items and ask.

The container expires, the content does not. Before deleting anything, make sure
the proofs moved somewhere long-lived. A file that feels too valuable to delete
is a sign of unclosed work, not a reason to extend the deadline.

Silent deletion is forbidden in all three cases.
