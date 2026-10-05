# Checklist cleanup

**License:** [CC BY-SA 4.0](../SPEC/LICENSE) · [Русский](CLEANUP.ru.md)

## Choose a disposition

A checklist with one or two unfinished items does not have to stay in the active
list forever. Choose what happened to the task:

| Decision | What survives |
|---|---|
| Deferred | Open items, attempts, a continuation address and a return condition |
| Cancelled | Open items and the owner's cancellation decision |
| Superseded | Open items and an address where the replacement retains them |
| Completed | Every item's proof and destinations for evidence worth keeping |

Archiving never completes an unfinished item. Difficulty, silence and elapsed
time do not authorize cancellation. Reuse an existing owner decision; ask only
when there is no decision or the proposed disposition changes agreed scope.

## Preview and archive

Run from the working project. Replace `/path/to/kanon` with the installed plugin
path. Tool messages are English; reasons and decision sources follow the user's
language. CLI flags remain canonical.

```bash
python3 /path/to/kanon/scripts/retire.py archive _kanon/task.md \
  --disposition deferred \
  --reason 'Return after launch' \
  --decision-source 'issue #42, owner decision' \
  --continued-in 'issue #43, remaining items' \
  --revisit 'After launch'
```

Without `--apply`, the command prints a plan and changes nothing. Verify that
issue #43 exists and retains the remaining work and relevant attempts, then add
`--apply` to the same command when the disposition is authorized.

For cancellation use `--disposition cancelled` with the reason and decision
source. For replacement use `--disposition superseded` and `--continued-in`.
For completed work use `--disposition completed`; the CLI refuses open items or
linter errors. It does not insert a completion date or manufacture proof.

Archived filenames contain the date, original stem and a content-hash prefix.
The original bytes and a retirement record are preserved. Existing destinations
are never overwritten. `_kanon/archive/` stays outside active reminders.

## Inspect and return to work

```bash
python3 /path/to/kanon/scripts/retire.py report
python3 /path/to/kanon/scripts/retire.py restore _kanon/archive/<archived-file>.md
```

The report shows the disposition, open count, reason, decision source and
continuation. At 30 days, it suggests manual review. It deletes nothing.
`restore` previews by default; add `--apply` to return the exact original bytes
and save the retirement decision in the archive log. An existing active file
with the same name is not overwritten.

The active index links to the archive. A deferred task is still wanted work:
its absence from Stop reminders is not a statement that it is done.

## Permanently remove a container

First move valuable evidence to a durable destination. Check that deferred or
replaced work survives at its continuation address. Then preview:

```bash
python3 /path/to/kanon/scripts/retire.py purge _kanon/archive/<archived-file>.md \
  --evidence-in 'issue #43 and reports/final.txt'
```

The CLI requires `--evidence-in` when the file contains proof. It verifies the
presence of addresses, not the truth of external material; inspect destinations
before applying. Add `--apply` only when this specific removal is authorized.

Before removal, `archive/LOG.md` retains the task, disposition, decision source,
remaining-item text, failed attempts and surviving addresses. Log failure prevents
removal. Keep that compact trail during cleanup. Age never triggers purge, and
no command recursively deletes a directory.

## Failure and platform limits

The retirement CLI needs Linux/macOS filesystem APIs. It refuses source/log
links, special files, linked archive directories and destination collisions.
Content hashes protect against restoring a changed archive. If source revalidation
fails after the destination is written, both copies remain for inspection.

Retirement commands serialize one another using an advisory lock. Avoid editing
that same file with another tool during a mutation; unrelated writers do not
participate in the lock. Archives and logs remain working data and must stay
outside git. [Normative contract](../SPEC/RETIREMENT.md).
