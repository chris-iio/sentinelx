---
id: T03
parent: S01
milestone: M014
key_files:
  - tests/test_runtime_state_boundary_git.py
  - Makefile
  - docs/runtime-state-boundary.md
  - README.md
key_decisions:
  - Kept `make verify-runtime-boundary` as an intentional surfacing target for legacy `.planning/**` manual-review findings, but moved the new Git regression proof ahead of the live audit so the fixture suite always runs.
  - Used real temp-repo Git commands instead of mocks so the tracked `.gsd/audit/events.jsonl` stash-pop conflict and ignored `.gsd/state-manifest.json` / `.gsd/event-log.jsonl` checkout behavior are pinned to observed Git stderr/stdout.
duration: 
verification_result: passed
completed_at: 2026-04-25T10:14:09.775Z
blocker_discovered: false
---

# T03: Added temp-repo Git regression fixtures for tracked and ignored transient boundary flows and wired them into the boundary verifier.

**Added temp-repo Git regression fixtures for tracked and ignored transient boundary flows and wired them into the boundary verifier.**

## What Happened

Added a new temp-repo regression suite in `tests/test_runtime_state_boundary_git.py` that exercises real Git behavior against the shipped boundary CLI. The tracked-transient fixture force-adds `.gsd/audit/events.jsonl`, proves the audit reports it as `tracked-transient`, and then reproduces the real `git stash pop` conflict on that path. The ignored/untracked fixture seeds `.gsd/state-manifest.json` and `.gsd/event-log.jsonl` under `.gitignore`, proves the audit stays clean, confirms `git check-ignore -v` reports the ignore rules, and shows branch checkout is not wedged by those runtime files. I also added a malformed-input regression for missing ignore rules plus an outside-root classification check, wired the new suite into `make verify-runtime-boundary`, and updated the runtime-boundary docs/README so the supported verifier now accurately describes the focused Git proof before the intentional live manual-review audit.

## Verification

Fresh verification after the last code change: `pytest tests/test_runtime_state_boundary_git.py -q` passed (`3 passed`). `make verify-runtime-boundary` ran both focused boundary suites successfully (`6 passed` + `3 passed`) and then intentionally surfaced the live repo's 237 legacy `.planning/**` `manual-review-path` findings via the shipped audit command, which remains the expected non-zero behavior for this repo. `make verify-fast` passed end-to-end (`991 passed, 113 deselected` in pytest, `81 passed` in Vitest, `npx tsc --noEmit`, and production asset build).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_runtime_state_boundary_git.py -q` | 0 | ✅ pass | 542ms |
| 2 | `make verify-runtime-boundary` | 2 | ✅ pass (expected manual-review surfacing after both focused suites passed) | 995ms |
| 3 | `make verify-fast` | 0 | ✅ pass | 8567ms |

## Deviations

None.

## Known Issues

`make verify-runtime-boundary` still exits non-zero on this repo because the live audit intentionally surfaces 237 legacy `.planning/**` `manual-review-path` findings. That is expected slice behavior, not a regression introduced by this task.

## Files Created/Modified

- `tests/test_runtime_state_boundary_git.py`
- `Makefile`
- `docs/runtime-state-boundary.md`
- `README.md`
