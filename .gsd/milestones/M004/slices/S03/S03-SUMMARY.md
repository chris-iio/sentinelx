# S03 Summary: Frontend tightening — TypeScript + CSS audit

**Status:** Complete  
**Duration:** ~20m (T01: 8m, T02: 12m)  
**Outcome:** Dead code removed from TS and CSS. Five O(N²) performance patterns fixed per R023. TypeScript strict-mode clean. All 944 tests pass (105 E2E, 839 unit).

## What This Slice Delivered

### T01: Dead code removal
- **row-factory.ts** — Removed `export` from `getOrCreateSummaryRow` (function preserved, still called internally by `updateSummaryRow`).
- **verdict-compute.ts** — Deleted `computeConsensus()` (18 lines) and `consensusBadgeClass()` (13 lines) entirely. Neither had any importers — Phase 3 leftovers superseded by the verdict micro-bar.
- **input.css** — Deleted `.alert-success` (5 lines), `.alert-warning` (5 lines), and the `.consensus-badge` family (comment header + 4 rules, ~30 lines). None referenced in templates or TS.

### T02: Five R023 O(N²) performance fixes
1. **`findCopyButtonForIoc()`** → single `querySelector` attribute selector with `CSS.escape()`, replacing `querySelectorAll` iteration.
2. **`updateDashboardCounts()` + `sortCardsBySeverity()`** → moved outside per-result loop, called once per poll tick guarded by `results.length > 0`.
3. **`applyFilter()`** → debounced at 100ms on search input `input` event via `clearTimeout`/`setTimeout`. Click handlers remain synchronous.
4. **`verdictSeverityIndex()`** → uses `SEVERITY_MAP` (`ReadonlyMap<string, number>` built at module load) instead of `Array.indexOf()`.
5. **Graph edge loop** → pre-built `nodeIndexMap` (`Map<string, number>`) replaces `.find()` + `.indexOf()`.

## Verification Evidence

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `make js` | ✅ 26.2kb bundle |
| `make css` | ✅ builds clean |
| 7 dead-code grep assertions | ✅ all pass |
| 6 R023 grep assertions | ✅ all pass |
| 105 E2E tests | ✅ all pass (37s) |
| 944 total tests | ✅ all pass (46s) |

## Requirements Validated

- **R023** → validated. All 5 O(N²) patterns fixed and verified by grep + E2E.

## Files Changed

- `app/static/src/ts/modules/row-factory.ts` — un-exported `getOrCreateSummaryRow`
- `app/static/src/ts/modules/verdict-compute.ts` — deleted `computeConsensus`, `consensusBadgeClass`
- `app/static/src/input.css` — deleted 6 dead CSS rules (~40 lines)
- `app/static/src/ts/modules/enrichment.ts` — attribute selector for copy-btn, batched dashboard/sort
- `app/static/src/ts/modules/filter.ts` — debounced search filter (100ms)
- `app/static/src/ts/types/ioc.ts` — `SEVERITY_MAP` pre-built Map
- `app/static/src/ts/modules/graph.ts` — `nodeIndexMap` pre-built Map
- `tests/e2e/pages/results_page.py` — 150ms wait in `search()` for debounce settling

## Patterns Established

- **E2E POM debounce awareness:** When adding debounce to a filter/search handler, update the corresponding Page Object Model method to include a wait ≥ debounce duration after `fill()`. The `search()` method now waits 150ms.

## What the Next Slice Should Know

- S03 is independent of S01/S02 — no backend changes.
- TypeScript is strict-mode clean. Bundle is 26.2kb.
- The debounced `applyFilter()` means any future E2E test that types into the search field must account for 100ms+ delay before assertions.
- `SEVERITY_MAP` and `nodeIndexMap` are the established pattern for O(1) lookups — prefer `Map` over `indexOf`/`find` in future TS code.
