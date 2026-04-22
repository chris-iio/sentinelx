---
id: T01
parent: S01
milestone: M012
key_files:
  - app/routes/_helpers.py
  - app/enrichment/orchestrator.py
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_orchestrator.py
key_decisions:
  - Used an additive top-level status contract (`status`, `terminal`, `terminal_reason`, `error`) instead of replacing existing `complete`/cursor fields so current polling semantics remain intact while future UI code can detect terminal failures.
  - Represented evicted jobs as bounded tombstones at both the helper registry and orchestrator layers so pollers can distinguish eviction from a never-seen job id.
duration: 
verification_result: passed
completed_at: 2026-04-22T03:51:49.182Z
blocker_discovered: false
---

# T01: Added additive terminal enrichment status semantics for unknown, evicted, and failed jobs while preserving cursor polling fields.

**Added additive terminal enrichment status semantics for unknown, evicted, and failed jobs while preserving cursor polling fields.**

## What Happened

I inspected the current enrichment status helper, orchestrator lifecycle, and existing route/API tests to find the smallest safe contract change. I kept the existing progress fields (`total`, `done`, `complete`, `results`, `next_since`) intact and added top-level terminal metadata (`status`, `terminal`, `terminal_reason`, `error`) so downstream UI work can distinguish running, successful completion, unknown jobs, helper/orchestrator eviction, and hard job failure without breaking cursor semantics.

In `app/routes/_helpers.py` I introduced normalized status payload helpers and helper-level tombstones so registry eviction no longer collapses into an undifferentiated 404. In `app/enrichment/orchestrator.py` I added explicit job metadata for running/complete/failed states, preserved eviction as a terminal tombstone instead of returning `None`, and marked unexpected worker exceptions as `job_failed` terminal states with an error message. I then updated backend route/API/orchestrator tests to pin the new contract and the evicted/failed distinctions.

This task establishes the backend runtime-verification surface for the slice. Analyst-visible terminal rendering and end-to-end live-path proof remain for T02/T03.

## Verification

Ran the task verification suite with `python3 -m pytest tests/test_routes.py tests/test_api.py tests/test_orchestrator.py -q`. The focused backend route/API/orchestrator tests all passed (78 passed). This proves the additive status contract, cursor behavior continuity, explicit unknown/evicted terminal payloads, and explicit orchestrator failed-job semantics. Slice-level UI visibility proof is intentionally still pending later tasks T02/T03.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_routes.py tests/test_api.py tests/test_orchestrator.py -q` | 0 | ✅ pass | 13600ms |

## Deviations

The task plan named `tests/test_routes_helpers.py`, but that file does not exist in this checkout. I applied the planned helper-route coverage to the real status-route test module `tests/test_routes.py` and kept the rest of the scope unchanged.

## Known Issues

None.

## Files Created/Modified

- `app/routes/_helpers.py`
- `app/enrichment/orchestrator.py`
- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_orchestrator.py`
