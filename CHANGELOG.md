# Changelog

[Русский](CHANGELOG.ru.md). Plugin versions follow SemVer; format versions are independent.

## 0.13.0

- Added explicit checklist retirement: archive as deferred, cancelled, superseded
  or completed; exact-byte restore; archive report; purge with a saved decision
  trail. Mutations preview by default and apply only with `--apply`.
- Preserved outstanding items, proof and failures outside active reminders.
  Deferred work requires a continuation address and return condition. File age
  never authorizes deletion; closed files are reviewed after seven days and
  archived files after thirty. Added the retirement contract; format 0.7.
- Added `/kanon:retire` and retirement regressions, including collisions, links,
  changed sources, corrupt archives and write/log failures. CRLF inputs retain
  exact original bytes; disposal logs retain original open-item markers.
- Standardized English agent/code instructions and EN-primary/RU human guides.
  Runtime messages and generated indexes default to Russian. Synchronized
  license tables, installation and documentation checks.
- Retired the proposed aggressive hook. Existing hook thresholds, frequency and
  nonblocking behavior are unchanged. No repository publication or history change.

## 0.12.1

- Failure results retain the clue visible at the decision, rather than replacing
  it with the workaround's result. A cause-found claim requires a mechanism
  explaining contradictory observations and independently attributed evidence.

## 0.12.0

- Proof by absence requires a positive control from the same observation source.
- Removing a failing part does not complete its original acceptance item: retain
  the failure and state the narrower result separately.

## 0.11.0

- Added a local Bash gathering tally for Codex transcripts that are missing or
  incompatible; use the larger count from the tally and transcript.
- Recognized Codex `apply_patch` writes and excluded checklist-only patches.
- Documented hook compatibility measured on Codex 0.149.0, hook trust and cache
  script paths. Added three regressions and four mutations.

## 0.10.0

- Classified Bash by command content so shell reads and writes reach sensors.
  Recognized redirection, tee and in-place edits; excluded null/FD redirection.
- Clarified one-line items, git exclusions, worktree placement and the provenance
  of the agent's own decisions. Added five Bash regressions and three mutations.

## 0.9.0

- Required an ownership header before replacing an index, including empty folders.
- Preserved index permissions; bounded numeric item fields; isolated ValueError.
- Bound checklist link checks to the opened descriptor and refused hard links.
- Required calendar-valid failure dates and hashed session marker names.
- Added a mutation runner that rejects unchanged targets. Historical verification:
  36 mutations, zero gaps or empty replacements; 94 checks.

## 0.8.1

- Replaced index contents through a temporary file and atomic name replacement,
  protecting hard-linked targets as well as symbolic links and avoiding partial
  indexes. Tested cleanup after successful and failed replacement.

## 0.8.0

- Protected index writes and checklist reads against symbolic links; reported
  skipped links and isolated unreadable files.
- Required a check or explicit no-check marker, unique item numbers and attempted
  action/result fields for failures. Preserved malformed failure records.
- Validated calendar dates; warned about quantities with null slots; exposed
  truncated open-item reports and excluded empty Gathered bullets.
- Updated empty-folder indexes, rejected Unicode slots safely, stopped transcript
  scans at the threshold, honored KANON_DIR in hooks and created private atomic
  session markers. Corrected Codex marketplace installation.
- Independent review demonstrated that mutations of known rules do not replace
  adversarial representation-boundary inputs.

## 0.7.0

- Used `systemMessage` JSON for PreToolUse and Stop while keeping plain
  SessionStart output and omitting blocking decision fields.
- Required the slots key; null remains valid. Replaced ineffective discovery
  fixtures and added output-shape and lifetime-boundary regressions.

## 0.6.0

- Applied the proof stop list to the first segment so appended dates cannot bypass it.
- Documented host-specific script paths; an unresolved path must be reported,
  never represented as a completed check.
- Suppressed new-checklist reminders for stale active files; separated error
  severity from user text. Added parser-value and index-failure regressions.

## 0.5.0

- Defined checklist prose in the author's language and preserved quoted material
  verbatim. Mixed-language checklists are valid. Format 0.4.

## 0.4.0

- Reported malformed or absent/empty acceptance sections instead of silently
  accepting missing items. Recognized bilingual headings.
- Removed the undocumented proof-length threshold; preserved unkeyed segments
  and recognized no-check only as a standalone field.
- Matched stale state to the specification; preserved sweep output on index-write
  failure; corrected command script paths and cleaned old reminder markers.
- Tested hook output, not just its always-zero exit code; eight mutations failed.

## 0.3.0

- Introduced visible `_kanon/`, retaining `.kanon/` and KANON_DIR compatibility.
- Added a derived INDEX.md and `--no-index`; excluded it from checklist discovery.
  Checklist files remain authoritative without a separate manifest. Format 0.3.

## 0.2.0

- Added parser, EN/RU aliases, linter, lifetime report and three nonblocking hooks.
- Introduced slots and canonical ASCII field names; added Russian documentation
  and bilingual fixtures. Format 0.2.

## 0.1.0

- Introduced format, skill, open/close/accept/sweep commands, installation and
  concept guides, split licenses, version/skill checks and CI.
