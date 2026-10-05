# Road to 1.0

**License:** [CC BY-SA 4.0](../SPEC/LICENSE) · [Русский](RELEASE.ru.md)

## Current state

0.13.0 adds explicit retirement and prepares the public documentation. Reliable
automatic skill selection remains unproved. The contract covers acceptance
items, proof, failure records and retirement; mnemo integration is optional.

## Candidate schedule

Aim for a 1.0 decision around 2026-10-12 after a week of ordinary use. This is
a candidate date, not a scheduled release. First two days: installation and
updates; next four: real tasks and reproduced defects; last day: evidence and
release review.

## Release criteria

- Install and update on Claude Code and Codex. Record host/plugin versions,
  cache paths and fresh-session hook checks. Updates must not leave a session
  repeatedly calling a removed cache version.
- On each host, run three gathering-to-production tasks and two tasks that do
  not need a checklist, repeated in fresh sessions. Keep prompts, observed
  selection and checklist timing. Compare the positive cases with the plugin
  disabled. Count manual invocation and hook reminders separately from automatic
  selection; report misses.
- Retire real deferred/cancelled work, including a task with open items. Verify
  its continuation, restored contents and surviving proof. Age-based deletion
  and false completion are unacceptable.
- Pass versions, metadata, bilingual documentation, selftest and mutation
  checks. Resolve required review findings and record remaining limitations.
- Review public files and historical metadata. Claude coauthor attribution is
  separate from session URLs. Decide what can be exposed before changing
  visibility; history transformations need the owner's explicit instruction.

If routing remains unreliable, keep 0.x or describe 1.0 as an explicit/manual
workflow with that limitation stated. Do not promise unobserved automatic coverage.

## Public presentation

English is primary for README, guides, changelog, contribution guidance and
repository metadata. Human documentation has adjacent Russian translations.
Agent instructions, code comments, CI step names and normative contracts use
English. Conversation and checklist prose follow the user; CLI/hook messages
default to Russian and quoted evidence stays verbatim.

Topics: `ai-agents`, `claude-code`, `codex`, `agent-skills`, `acceptance-testing`,
`developer-tools`, `python`. Keep the code/docs license split visible. Release
tags identify tested commits; create `v1.0.0` after the release decision.

## Outside the 1.0 requirement

Mnemo proof transfer (K8) is optional. The aggressive hook (K9) is retired.
Public visibility, release publication and historical URL removal are separate
owner decisions. See the [backlog](../BACKLOG.md) and [cleanup guide](CLEANUP.md).
