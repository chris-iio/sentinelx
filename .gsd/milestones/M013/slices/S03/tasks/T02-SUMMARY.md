---
id: T02
parent: S03
milestone: M013
key_files:
  - app/routes/_helpers.py
  - app/routes/api.py
  - app/routes/enrichment.py
  - tests/test_routes.py
  - tests/test_api.py
  - app/static/src/ts/types/api.ts
key_decisions:
  - Kept `_get_enrichment_status()` on the incremental polling accessor while leaving `_run_enrichment_and_save()` on the full-snapshot history path, preserving the additive contract established in T01.
duration: 
verification_result: passed
completed_at: 2026-04-25T06:28:42.825Z
blocker_discovered: false
---

# T02: Confirmed the helper and API status routes already use the orchestrator incremental snapshot without public-contract drift.

**Confirmed the helper and API status routes already use the orchestrator incremental snapshot without public-contract drift.**

## What Happened

I inspected `app/routes/_helpers.py`, `app/routes/api.py`, `app/routes/enrichment.py`, `tests/test_routes.py`, `tests/test_api.py`, and `app/static/src/ts/types/api.ts` against the T02 contract. `_get_enrichment_status()` is already on the hot-path incremental accessor via `orchestrator.get_incremental_status(job_id, since=since)` and does not reconstruct deltas from a full `get_status()` snapshot; `_run_enrichment_and_save()` remains on the full-snapshot path for history persistence as planned. The helper still preserves distinct terminal semantics for unknown jobs, helper-level evictions, and orchestrator-reported `job_failed` states, and still serializes `cached_at` only for rows whose cache markers are present in the returned tail. The thin `/enrichment/status/<job_id>` and `/api/status/<job_id>` wrappers already delegate to the shared helper, and the focused route/API tests already pin negative `since`, exact-length and beyond-range empty deltas, cached marker serialization, 404 terminal tombstones, and API/HTML parity. `app/static/src/ts/types/api.ts` still matches the returned top-level fields (`results`, `next_since`, `status`, `terminal`, `terminal_reason`, `error`) and the optional per-row `cached_at`, so no frontend type change was needed. No source patch was required because the checked-in implementation and tests already satisfy the task contract.

## Verification

Ran `pytest tests/test_routes.py tests/test_api.py -q` after inspection and it passed (`56 passed in 0.63s`), confirming the incremental polling helper path, cursor semantics, cached-marker serialization, terminal failure/eviction truthfulness, and API/HTML parity. I also checked Python LSP diagnostics for `app/routes/_helpers.py`, `app/routes/api.py`, and `app/routes/enrichment.py`; all reported no diagnostics. TypeScript LSP was unavailable for `app/static/src/ts/types/api.ts`, so I verified that file by direct inspection against the helper payload shape instead.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_routes.py tests/test_api.py -q` | 0 | ✅ pass | 1126ms |

## Deviations

No implementation patch was needed. I completed the task by validating that the repository already contains the planned incremental helper path and the required focused coverage.

## Known Issues

None.

## Files Created/Modified

- `app/routes/_helpers.py`
- `app/routes/api.py`
- `app/routes/enrichment.py`
- `tests/test_routes.py`
- `tests/test_api.py`
- `app/static/src/ts/types/api.ts`
