---
estimated_steps: 4
estimated_files: 8
skills_used:
  - review
  - verify-before-complete
---

# T01: Review the workflow seam and capture closure findings

**Slice:** S04 — Verification, review, and refactor closure
**Milestone:** M014

## Description

Load the `review` skill first and inspect the shipped workflow seam as code, not summary text. Re-read `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, and the highest-signal integration tests to identify only real drift or maintainability risks, then write a durable review artifact at `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`. Keep the review conservative: no style churn, no second path-policy table, no `.planning/**` auto-cleanup, and no second local-server workflow besides `make dev-server-*` / `tools/dev_server.py`.

## Steps

1. Load the `review` skill, inspect the boundary/repair/dev-server/API seam files, and cross-check them against the focused Git/lifecycle proof files instead of relying on prior slice summaries.
2. In `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`, record the seam invariants that must not change: classifier-owned repair policy, report-only `.planning/**`, thin Make wrappers, local-only dev-server ownership, and secret-free status/health output.
3. Record the minimal justified refactor to land in T02, explicitly deciding whether the duplicated health contract between `app/routes/api.py` and `tools/dev_server.py` should be retired now.
4. Record any accepted no-change areas so T02 stays seam-local and does not broaden scope beyond the review findings.

## Must-Haves

- [ ] `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` names the files inspected and separates `refactor-now` findings from `leave-alone` seams.
- [ ] The review preserves `tools/runtime_state_boundary.py` as the sole path-policy source and keeps `.planning/**` manual-review behavior explicit.
- [ ] The review makes an explicit decision about the shared health contract seam instead of leaving the duplication implicit.
- [ ] The artifact is precise enough for a fresh executor to perform T02 without reopening the slice research.

## Verification

- `test -s .gsd/milestones/M014/slices/S04/S04-REVIEW.md`
- `rg -n "refactor-now|leave-alone|health contract|classifier-owned" .gsd/milestones/M014/slices/S04/S04-REVIEW.md`

## Inputs

- `tools/runtime_state_boundary.py` — authoritative boundary classifier and issue-code policy.
- `tools/runtime_state_repair.py` — classifier-backed repair action table and report behavior.
- `tools/dev_server.py` — supported local lifecycle implementation and health consumer.
- `app/routes/api.py` — health producer contract.
- `tests/test_runtime_state_boundary_git.py` — real Git proof for the stash/conflict class.
- `tests/test_runtime_state_repair_git.py` — real Git proof for conservative repair behavior.
- `tests/test_dev_server_process.py` — subprocess proof for crash/restart lifecycle behavior.

## Expected Output

- `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` — closure review artifact listing invariants, `refactor-now` items, and `leave-alone` seams.
