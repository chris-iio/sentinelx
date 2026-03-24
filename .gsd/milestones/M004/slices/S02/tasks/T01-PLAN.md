---
estimated_steps: 5
estimated_files: 5
---

# T01: Implement ?since= polling cursor in routes.py, enrichment.ts, and api.ts

**Slice:** S02 — IO Performance & Polling Protocol
**Milestone:** M004

## Description

The polling endpoint currently re-serializes and re-transmits the full accumulated results list on every 750ms tick. For a 50-IOC batch, final ticks transmit 50 results when only 1-2 are new — O(N²) total work. This task implements the `?since=` cursor protocol (Decision D033): the server accepts an integer cursor, returns only `results[since:]`, and sends back `next_since` for the client to use on the next tick. The frontend removes the `rendered` dedup map and uses the cursor instead.

This is the only cross-boundary change in S02 (Python ↔ TypeScript) and must be correct — an off-by-one produces skipped or duplicate results. Covers requirement R019.

## Steps

1. **routes.py — Add `?since=` cursor to `enrichment_status()`**
   - Read `since = request.args.get("since", 0, type=int)` at the top of the function
   - After building `serialized_results`, slice: `sliced = serialized_results[since:]`
   - Add `"next_since": len(serialized_results)` to the response JSON (this is the total count of completed results, not `since + len(sliced)` — the former is simpler and handles edge cases)
   - Return `sliced` as the `"results"` field instead of the full list
   - Keep backward compatibility: if `since` is absent, it defaults to 0, returning all results (existing tests work without modification)

2. **api.ts — Add `next_since` to `EnrichmentStatus` interface**
   - Add `next_since: number;` field to the `EnrichmentStatus` interface at `app/static/src/ts/types/api.ts` line ~104

3. **enrichment.ts — Replace `rendered` dedup map with `since` cursor**
   - Remove the `const rendered: Record<string, boolean> = {};` declaration (~line 511)
   - Add `let since = 0;` in its place
   - Change the fetch URL from `"/enrichment/status/" + jobId` to `"/enrichment/status/" + jobId + "?since=" + since`
   - Remove the `if (!rendered[dedupKey])` check and the `rendered[dedupKey] = true;` line — all returned results are new by contract
   - Keep the `dedupKey` variable computation for the existing warning-banner check logic (it uses `result.ioc_value` and `result.provider`), but the dedup map itself is removed
   - After the results loop, add `since = data.next_since;` to advance the cursor
   - **Important:** The `allResults.push(result)` call stays — it accumulates for export. Only the `rendered` dedup gate is removed.

4. **test_routes.py — Add cursor unit tests**
   - Add `test_enrichment_status_since_returns_slice()`: inject an orchestrator with 3 results, request `?since=2`, assert only 1 result returned and `next_since == 3`
   - Add `test_enrichment_status_since_zero_returns_all()`: same setup, `?since=0`, assert all 3 results and `next_since == 3`
   - Add `test_enrichment_status_no_since_returns_all()`: no `since` param, assert all 3 results returned (backward compat) and `next_since == 3`
   - Add `test_enrichment_status_since_beyond_length()`: `?since=99`, assert 0 results and `next_since == 3`

5. **E2E conftest.py — Add `next_since` to mock response**
   - Add `"next_since": 2` to `MOCK_ENRICHMENT_RESPONSE_8888` (it has 2 results, so `next_since` should be 2)
   - This ensures the frontend's `since = data.next_since` assignment works during E2E tests

## Must-Haves

- [ ] `enrichment_status()` accepts `?since=` and returns `results[since:]` + `next_since`
- [ ] `EnrichmentStatus` interface has `next_since: number`
- [ ] `rendered` dedup map removed from enrichment.ts
- [ ] Frontend sends `?since=N` on each poll tick and updates from `data.next_since`
- [ ] Backward compatible: missing `since` param returns full results
- [ ] E2E mock includes `next_since`
- [ ] All existing enrichment_status tests still pass
- [ ] New cursor tests pass

## Verification

- `python3 -m pytest tests/test_routes.py -v -k enrichment_status` — all pass including new cursor tests
- `grep -c 'rendered' app/static/src/ts/modules/enrichment.ts` returns 0
- `grep 'next_since' app/static/src/ts/types/api.ts` — field present
- `grep 'next_since' tests/e2e/conftest.py` — present in mock
- `grep 'since' app/routes.py | grep -c 'request.args\|next_since\|results\[since'` returns ≥3

## Inputs

- `app/routes.py` — current `enrichment_status()` function (lines 334-375) that returns full results list
- `app/static/src/ts/modules/enrichment.ts` — polling loop (lines 510-580) using `rendered` dedup map
- `app/static/src/ts/types/api.ts` — `EnrichmentStatus` interface (line 104) without `next_since`
- `tests/test_routes.py` — existing enrichment_status tests (lines 375-500)
- `tests/e2e/conftest.py` — `MOCK_ENRICHMENT_RESPONSE_8888` dict (line 117) and `setup_enrichment_route_mock()` (line 148)

## Expected Output

- `app/routes.py` — `enrichment_status()` accepts `?since=`, returns sliced results + `next_since`
- `app/static/src/ts/modules/enrichment.ts` — polling loop uses `since` counter, no `rendered` map
- `app/static/src/ts/types/api.ts` — `EnrichmentStatus` includes `next_since: number`
- `tests/test_routes.py` — 4 new cursor tests added
- `tests/e2e/conftest.py` — `MOCK_ENRICHMENT_RESPONSE_8888` includes `next_since: 2`
