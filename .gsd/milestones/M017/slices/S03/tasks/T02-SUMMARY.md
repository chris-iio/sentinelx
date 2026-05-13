---
id: T02
parent: S03
milestone: M017
key_files:
  - app/enrichment/orchestrator.py
  - app/routes/_helpers.py
  - tests/test_orchestrator.py
  - tests/test_routes.py
  - .gsd/milestones/M017/M017-AUDIT.md
key_decisions:
  - Treated the already-present tail-only incremental status implementation as satisfying T02 after source inspection and focused/full verification.
  - Preserved `get_status()` unchanged for call sites that intentionally need full snapshots.
duration: 
verification_result: passed
completed_at: 2026-05-13T08:30:14.820Z
blocker_discovered: false
---

# T02: Verified and shipped the tail-only enrichment status polling path already implemented in the orchestrator and route helper.

**Verified and shipped the tail-only enrichment status polling path already implemented in the orchestrator and route helper.**

## What Happened

Inspected `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`, `tests/test_orchestrator.py`, and `tests/test_routes.py` against the T02 contract. The orchestrator already exposes `get_incremental_status(job_id, since=since)` with scalar status fields, copied `results[since:]`, `next_since`, and tail-aligned `cached_markers` under `_lock`; `get_status()` remains intact for full snapshots and history/diagnostic call sites. The route helper already calls `orchestrator.get_incremental_status()` for normal polling, serializes only the returned tail, passes tail marker maps into `_serialize_result()`, preserves the documented status/terminal/error/next_since response fields, and keeps 404 behavior limited to unknown/evicted terminal states while returning job_failed as a truthful terminal payload. No source edits were required.

## Verification

Ran the focused incremental status tests, the full route/orchestrator regression suite, and the M017 audit target. All commands exited successfully. The focused route tests assert that `_get_enrichment_status()` uses `get_incremental_status()` and does not fall back to `get_status()`; orchestrator tests cover tail-only deltas, negative/beyond-range cursors, terminal failure cursor fallback, eviction tombstones, cached marker alignment, and full snapshot preservation.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py -k "IncrementalStatusSnapshot or enrichment_status"` | 0 | ✅ pass | 454ms |
| 2 | `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py` | 0 | ✅ pass | 859ms |
| 3 | `make audit-m017` | 0 | ✅ pass | 210ms |

## Deviations

No code changes were made because the requested implementation and hardening were already present in the inspected source files.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `tests/test_orchestrator.py`
- `tests/test_routes.py`
- `.gsd/milestones/M017/M017-AUDIT.md`
