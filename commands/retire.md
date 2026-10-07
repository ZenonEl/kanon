---
description: Retire inactive checklists without claiming completion; archive, restore or purge explicitly
argument-hint: Operation, checklist path, reason and decision source
---

Use the **kanon:task-to-checklist** skill and `SPEC/RETIREMENT.md`.

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/retire.py"` with the selected
operation. `archive` requires `--disposition`, `--reason` and `--decision-source`.
Deferred work needs `--continued-in` and `--revisit`; superseded work needs
`--continued-in`. Resolve those addresses and verify the remaining work survives.

`restore` returns the original checklist. `report` reads the archive. `purge`
permanently removes one archived file after saving a decision trail; use
`--evidence-in` when proof must survive elsewhere and verify that destination.

Mutation commands preview by default; `--apply` performs an already-authorized
operation. Existing owner decisions do not need repeated approval. Never mark
open items complete as part of archiving. Never clean checklists by recursively
deleting their directory. Explain the outcome in the user's language.

$ARGUMENTS
