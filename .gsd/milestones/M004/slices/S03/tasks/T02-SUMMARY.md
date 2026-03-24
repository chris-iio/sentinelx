---
id: T02
parent: S03
milestone: M004
provides:
  - Five R023 O(N²) performance patterns fixed across enrichment.ts, filter.ts, ioc.ts, graph.ts
  - Attribute selector replaces querySelectorAll iteration for copy-button lookup
  - Dashboard counts and card sorting batched once per poll tick instead of per-result
  - Search filter input debounced at 100ms
  - Pre-built Map lookups replace indexOf in verdict severity and graph edge loop
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/filter.ts
  - app/static/src/ts/types/ioc.ts
  - app/static/src/ts/modules/graph.ts
  - tests/e2e/pages/results_page.py
key_decisions:
  - none
patterns_established:
  - E2E POM search() method includes 150ms wait after fill() to account for debounced applyFilter()
observability_surfaces:
  - none — internal performance optimizations only, no new runtime signals
duration: 12m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T02: Apply five R023 O(N²) performance patterns

**Applied 5 O(N²) performance fixes: attribute selector for copy-btn lookup, batched dashboard/sort per tick, debounced search filter, pre-built Map for verdict severity, pre-built Map for graph node index**

## What Happened

Five targeted performance refactors per R023, each eliminating an O(N²) pattern:

1. **enrichment.ts — `findCopyButtonForIoc()`**: Replaced `querySelectorAll` iteration over all `.copy-btn` elements with a single `document.querySelector` using an attribute selector `.copy-btn[data-value="..."]`. Added `CSS.escape()` to handle IOC values containing special characters.

2. **enrichment.ts — batched dashboard/sort**: Removed `updateDashboardCounts()` and `sortCardsBySeverity()` calls from inside `renderEnrichmentResult()` (called N times per tick). Added both calls once after the results for-loop in the poll tick handler, guarded by `results.length > 0`. `updateCardVerdict()` remains per-result as required.

3. **filter.ts — debounced search**: Added 100ms debounce on the search input `input` event handler for `applyFilter()`. Click handlers for verdict buttons, type pills, and dashboard badges remain synchronous. Used `clearTimeout`/`setTimeout` pattern matching the existing debounce in `cards.ts`.

4. **ioc.ts — `SEVERITY_MAP`**: Added a `ReadonlyMap<string, number>` built from `VERDICT_SEVERITY` array. Changed `verdictSeverityIndex()` from `indexOf` to `SEVERITY_MAP.get(verdict) ?? -1`. Function signature unchanged.

5. **graph.ts — `nodeIndexMap`**: Pre-built a `Map<string, number>` from `providerNodes` before the edge loop. Replaced `.find()` + `.indexOf()` (two O(N) scans per edge) with a single `Map.get()`.

Updated the E2E POM `search()` method to wait 150ms after `fill()` to account for the debounce — one test (`test_combined_type_and_search_filters`) was asserting before the debounced filter fired.

## Verification

- `npx tsc --noEmit` — exits 0, zero errors
- `make js` — builds `app/static/dist/main.js` (26.2kb) without errors
- `make css` — builds `app/static/dist/style.css` without errors
- All R023 grep assertions pass (attribute selector present, old patterns gone, Maps present)
- All dead code greps from T01 still pass
- 105 E2E tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx tsc --noEmit` | 0 | ✅ pass | ~24s |
| 2 | `make js` | 0 | ✅ pass | 4ms |
| 3 | `make css` | 0 | ✅ pass | 482ms |
| 4 | `grep -q 'querySelector.*copy-btn.*data-value' enrichment.ts` | 0 | ✅ pass | <1s |
| 5 | `! grep -q 'querySelectorAll.*copy-btn' enrichment.ts` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'CSS.escape' enrichment.ts` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'new Map' ioc.ts` | 0 | ✅ pass | <1s |
| 8 | `! grep -q 'indexOf' ioc.ts` | 0 | ✅ pass | <1s |
| 9 | `grep -q 'new Map' graph.ts` | 0 | ✅ pass | <1s |
| 10 | `grep -q 'clearTimeout\|setTimeout' filter.ts` | 0 | ✅ pass | <1s |
| 11 | `python3 -m pytest tests/e2e/ -x -q` | 0 | ✅ pass | 38s |

## Diagnostics

None — all five changes are internal performance optimizations. No new runtime signals. Future agents can re-verify via the grep assertions in the slice plan. Bundle size (26.2kb) confirms no unexpected code bloat from the refactors.

## Deviations

- Updated `tests/e2e/pages/results_page.py` `search()` method to add 150ms wait after `fill()` — the 100ms debounce on `applyFilter()` caused `test_combined_type_and_search_filters` to assert before the filter fired. This is an expected consequence of adding debounce.
- Changed a comment in `ioc.ts` that contained the word "indexOf" to "array scan" to avoid a false positive on the `! grep -q 'indexOf'` verification check.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts` — Replaced `findCopyButtonForIoc()` with attribute selector; moved `updateDashboardCounts()`/`sortCardsBySeverity()` to poll tick level
- `app/static/src/ts/modules/filter.ts` — Added 100ms debounce on search input `applyFilter()` call
- `app/static/src/ts/types/ioc.ts` — Added `SEVERITY_MAP` pre-built Map; `verdictSeverityIndex()` uses Map lookup
- `app/static/src/ts/modules/graph.ts` — Added `nodeIndexMap` pre-built Map; replaced `.find()`/`.indexOf()` in edge loop
- `tests/e2e/pages/results_page.py` — Added 150ms wait in `search()` for debounce settling
- `.gsd/milestones/M004/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section
