---
task: ship the export endpoint
opened: 2026-09-02
closed: null
slots: 2
source: issue #12
---

## Gathered

- rate limit is 100 rpm · issue #12

## Acceptance

- [x] 1. endpoint returns 200 · check: curl · proof: run 33597596724, body ok
- [ ] 2. errors are logged · check: pytest tests/test_log.py
