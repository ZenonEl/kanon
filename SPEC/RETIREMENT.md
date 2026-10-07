# Checklist retirement

**Version:** 1 · **Status:** normative · **License:** [CC BY-SA 4.0](LICENSE)

Retirement removes inactive checklists from the active list without completing
their outstanding work. Age never authorizes deletion. The existing active
states (`open`, `closed`, `stale`) remain unchanged.

## Decisions

| Disposition | Meaning | Required information |
|---|---|---|
| `deferred` | Still wanted, outside current work | Reason, decision source, continuation address, return date or condition |
| `cancelled` | No longer wanted | Reason and authoritative cancellation source |
| `superseded` | Another task replaces this one | Reason, decision source and replacement address |
| `completed` | Every acceptance item has proof | Valid checklist, reason and decision source |

An agent may use an existing owner decision. It cannot cancel agreed work merely
because a remaining item is difficult. The continuation/replacement must retain
remaining requirements and relevant failed attempts. Resolving external addresses
and checking their contents belongs to the agent or reader, as with proof fields;
the CLI verifies their presence, not the truth of their contents.

## Operations

`scripts/retire.py` provides `archive`, `restore`, `purge` and `report`. Mutation
commands are previews unless passed `--apply`. Each operates on exactly one file
directly in the configured active directory or its `archive/` subdirectory.
`KANON_DIR` and the historical `.kanon/` directory remain supported.

### Archive

Preserve the original UTF-8 file bytes, including frontmatter, acceptance items,
proofs and failures. Append this envelope:

```text
<original bytes>
\n<!-- kanon:retirement\n
<one JSON object>
\n-->\n
```

The JSON object carries `version: 1`, `original_name`, `original_sha256`,
`archived_on` (calendar date), `disposition`, `reason`, `decision_source`,
`continued_in` and `revisit`. Reason and decision source are nonempty. The last
two fields may be empty only when the disposition does not require them.
User-entered content stays in its original language; field names are canonical.
The envelope uses the final marker, so a similar string in original evidence is
not mistaken for the appended decision.

Archive under `<date>-<original-stem>-<first-12-sha256-chars>.md`. Refuse an
existing destination. Never tick items, add proof or fill `closed:` as a side
effect. A `completed` disposition requires the linter to accept the checklist
and every item to be closed with proof; other dispositions preserve partial work.

Create and sync the destination before revalidating and removing the source.
A failure before source removal leaves a recoverable source. If the source
changed, leave both copies and report the conflict instead of deleting new work.

### Restore

Validate the archive envelope and original content hash. Restore the exact
original bytes under `original_name`, without overwriting an existing active
file. Save the retirement decision in `archive/LOG.md` before removing the
archived container. Failure may leave both copies; it must not destroy either.

### Purge

Permanent removal is explicit. If any item carries proof, require `--evidence-in`
to name its surviving destination. Before applying, the agent verifies that
valuable evidence and deferred/replaced work actually survive at the supplied
addresses. Cancelled items are recorded as cancelled, never as completed.

Before deleting the archive, append and sync a record in `archive/LOG.md`:
task, disposition, reason, decision source, continuation, return condition,
evidence destination, archived file hash, full remaining-item text and fields,
and failure records. Log failure forbids deletion. Keep the log during cleanup.
Its ownership header is `# kanon · disposal log`; refuse a nonempty foreign log.
The log records past decisions, not the current state of requirements elsewhere.

### Report

List archived files with disposition, remaining-item count, reason, decision
source and continuation. At 30 days from `archived_on`, suggest manual review.
This threshold does not schedule or apply deletion. A malformed archive is
reported, not treated as absent.

## Discovery and file safety

Active discovery stays shallow. Files under `archive/` and its log never enter
active acceptance counts or Stop reminders. The active index links to the archive;
ordinary sweep reports its count. Quiet session-start sweep does not add archive
reminders, preserving current hook frequency.

Read and write through bound directory/file descriptors. Refuse symbolic links,
hard-linked sources/logs, special files, unsafe original names and an archive
directory that is a link. Destinations are exclusive and retain the source file
mode. Applied CLI mutations use an advisory lock to serialize other retirement
commands. Do not edit the same checklist concurrently from another tool: source
changes are checked, but advisory locking cannot control unrelated writers.
Never recurse to delete directories. The retirement CLI requires POSIX directory
descriptor support (Linux/macOS); the existing parser and linter stay independent.
