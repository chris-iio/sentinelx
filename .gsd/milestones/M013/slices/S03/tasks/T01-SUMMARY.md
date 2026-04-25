---
id: T01
parent: S03
milestone: M013
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
key_decisions:
  - Kept `get_status()` as the full-snapshot/history contract and treated `get_incremental_status()` as the additive polling hot-path accessor.
duration: 
verification_result: passed
completed_at: 2026-04-25T04:53:49.433Z
blocker_discovered: false
---

# T01: Confirmed the lock-safe orchestrator incremental status snapshot API and its tail/marker/full-snapshot invariants with focused pytest coverage.

**Confirmed the lock-safe orchestrator incremental status snapshot API and its tail/marker/full-snapshot invariants with focused pytest coverage.**

## What Happened

I inspected `app/enrichment/orchestrator.py` and confirmed the additive hot-path API already exists as `get_incremental_status()` without weakening `get_status()`. The incremental path snapshots scalar fields, `results[since:]`, aligned `_cached_markers` entries, and `next_since` under the orchestrator lock, while the existing full-snapshot path continues to return a copied full results list for history persistence and legacy callers. I then inspected `tests/test_orchestrator.py` and verified the suite already pins the task’s required behaviors: tail-only reads, marker alignment, mutation safety, preserved negative-`since` compatibility, out-of-range empty tails, failed/evicted tombstones, unknown-job handling, and the preserved full-snapshot contract. No code patch was required because the checked-in implementation already satisfied the T01 contract.

## Verification

Ran `pytest tests/test_orchestrator.py -q` and it passed (`38 passed in 0.11s`). This verifies the orchestrator-level incremental snapshot path, confirms `next_since` is derived from retained result length, proves cached-marker alignment stays tail-scoped, and confirms `get_status()` remains the full-snapshot API for full-history callers.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_orchestrator.py -q` | 0 | ✅ pass | 351ms |

## Deviations

None. I adapted execution only by validating that the repository already contained the planned implementation and focused coverage, so no source edits were necessary.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/orchestrator.py`
- `tests/test_orchestrator.py`
