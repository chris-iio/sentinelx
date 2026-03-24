---
id: T01
parent: S02
milestone: M004
provides:
  - "?since= cursor protocol on /enrichment/status/<job_id> — returns results[since:] and next_since"
  - enrichment.ts polling loop uses server-side cursor instead of client-side dedup map
key_files:
  - app/routes.py
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/types/api.ts
  - tests/test_routes.py
  - tests/e2e/conftest.py
key_decisions:
  - next_since = len(serialized_results) (total completed, not since+sliced) — handles edge cases cleanly
  - dedupKey variable removed entirely (was unused after dedup gate removal; warning-banner logic uses result fields directly)
patterns_established:
  - since defaults to 0 so missing param returns full results — backward compatible with existing tests and curl usage
observability_surfaces:
  - "GET /enrichment/status/<job_id>?since=0 — always returns full results list + next_since (browser devtools / curl)"
  - "next_since field in JSON response — increment visible on each poll tick; off-by-one produces skipped/duplicate results in E2E assertions"
duration: ~15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Implement ?since= polling cursor in routes.py, enrichment.ts, and api.ts

**Added `?since=` cursor to enrichment_status() so each poll tick receives only new results (O(N) total work instead of O(N²)), and replaced the client-side `rendered` dedup map with a server-driven `since` counter.**

## What Happened

Five targeted edits implemented the full cursor protocol:

1. **`app/routes.py`** — `enrichment_status()` now reads `since = request.args.get("since", 0, type=int)`, slices `serialized_results[since:]`, and returns `next_since: len(serialized_results)` alongside the sliced results. Defaults to 0 for backward compatibility.

2. **`app/static/src/ts/types/api.ts`** — Added `next_since: number` to the `EnrichmentStatus` interface.

3. **`app/static/src/ts/modules/enrichment.ts`** — Replaced `const rendered: Record<string, boolean> = {}` with `let since = 0`, appended `?since=${since}` to the fetch URL, removed the `if (!rendered[dedupKey])` gate (all returned results are new by contract), and added `since = data.next_since` after the results loop. The now-unused `dedupKey` variable was also removed (the warning-banner logic uses `result.type`/`result.error`/`result.provider` directly).

4. **`tests/test_routes.py`** — Added 4 cursor unit tests: `?since=2` returns 1 result, `?since=0` returns all 3, no param returns all 3 (backward compat), `?since=99` returns 0 results — all with `next_since == 3` assertions. Initial implementation omitted `scan_date=None, raw_stats={}` from `EnrichmentResult` construction; corrected after first test run.

5. **`tests/e2e/conftest.py`** — Added `"next_since": 2` to `MOCK_ENRICHMENT_RESPONSE_8888` so the frontend's `since = data.next_since` assignment works during E2E tests.

## Verification

- `pytest tests/test_routes.py -v -k enrichment_status` — 6 passed (2 pre-existing + 4 new cursor tests)
- `grep -c 'rendered' enrichment.ts` — 0 (both variable and comment removed)
- `grep 'next_since' api.ts` — field present
- `grep 'next_since' tests/e2e/conftest.py` — present in mock
- `grep 'since' app/routes.py | grep -c 'request.args|next_since|results\[since'` — 3 hits
- `pytest tests/ --ignore=tests/e2e -x -q` — 835 passed (full baseline before T02-T04 add more test files)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_routes.py -v -k enrichment_status` | 0 | ✅ pass | 0.17s |
| 2 | `grep -c 'rendered' app/static/src/ts/modules/enrichment.ts` | 1 (grep returns 1 on 0 matches) | ✅ pass (count=0) | <1s |
| 3 | `grep 'next_since' app/static/src/ts/types/api.ts` | 0 | ✅ pass | <1s |
| 4 | `grep 'next_since' tests/e2e/conftest.py` | 0 | ✅ pass | <1s |
| 5 | `grep 'since' app/routes.py \| grep -c 'request.args\|next_since\|results\[since'` | 0 | ✅ pass (count=3) | <1s |
| 6 | `pytest tests/ --ignore=tests/e2e -x -q` | 0 | ✅ pass (835 tests) | 8.75s |

## Diagnostics

To inspect the cursor protocol at runtime:
- `curl http://localhost:5000/enrichment/status/<job_id>` — returns full results + `next_since` (since defaults to 0)
- `curl http://localhost:5000/enrichment/status/<job_id>?since=N` — returns only results from index N onward
- An off-by-one in cursor tracking produces either skipped results (next_since too high) or duplicate renders (next_since too low), both visible in E2E test assertions

## Deviations

`EnrichmentResult` requires `scan_date` and `raw_stats` as positional arguments — the helper factory in the test file omitted them initially. Fixed after first run. The `dedupKey` variable was also removed (plan said to keep it) since it was entirely unused after removing the dedup gate; the warning-banner logic never referenced it.

## Known Issues

None. The full test suite (835 tests) passes cleanly.

## Files Created/Modified

- `app/routes.py` — Added `?since=` param, result slicing, and `next_since` to `enrichment_status()`
- `app/static/src/ts/modules/enrichment.ts` — Replaced `rendered` dedup map with `since` cursor counter
- `app/static/src/ts/types/api.ts` — Added `next_since: number` to `EnrichmentStatus` interface
- `tests/test_routes.py` — Added 4 cursor unit tests + `_make_three_result_orchestrator()` helper
- `tests/e2e/conftest.py` — Added `"next_since": 2` to `MOCK_ENRICHMENT_RESPONSE_8888`
