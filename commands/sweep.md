---
description: Lifetime — what expired, what to extract, what to surface
---

Use the **kanon:task-to-checklist** skill.

Run:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sweep.py"
```

It derives the state of every checklist in `_kanon/` per `SPEC/FORMAT.md`:

- `open` — active work has no expiry;
- `closed` older than 7 days — review evidence destinations before explicit retirement;
- `stale` — surface open items; continue or explicitly retire an inactive task.

For inactive work use `scripts/retire.py`: `archive`, `restore`, `report`,
`purge`. Read `SPEC/RETIREMENT.md`. Archive is not completion; deferred,
cancelled and superseded work keeps its remaining items. Reuse an existing
owner decision; ask only if a disposition changes agreed scope without authority.
Every mutation previews by default and applies only with `--apply`.

The container expires, the content does not. Before deleting anything, make sure
the proofs moved somewhere long-lived. A file that feels too valuable to delete
is a sign of unclosed work, not a reason to extend the deadline.

Silent deletion is forbidden in all three cases.
