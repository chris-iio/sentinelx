---
id: T03
parent: S01
milestone: M006
key_files:
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/main.ts
  - app/static/src/ts/modules/enrichment.ts
key_decisions:
  - Exported wireExpandToggles from enrichment.ts for reuse by history.ts — avoids duplicating event delegation setup while keeping the function's interface unchanged
  - History replay filters context providers out of verdict computation to match live enrichment behavior — context providers (IP Context, DNS Records, etc.) don't participate in card verdicts
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:19:04.923Z
blocker_discovered: false
---

# T03: Build JS history replay module that renders stored analysis results through the existing enrichment pipeline

**Build JS history replay module that renders stored analysis results through the existing enrichment pipeline**

## What Happened

Created `app/static/src/ts/modules/history.ts` — a JS module that detects the `data-history-results` attribute on `.page-results` (injected by the Flask `/history/<id>` route from T02) and replays all stored enrichment results through the same rendering pipeline used by live analysis.

The module:
1. Parses the JSON array from `data-history-results` (HTML-entity-decoded by the browser's `getAttribute()`)
2. Iterates each result and calls the existing building blocks: `findCardForIoc()`, `createContextRow()` + `updateContextLine()` for context providers, `createDetailRow()` for reputation providers, routed to `.enrichment-section--reputation` or `.enrichment-section--no-data`
3. After all results replayed: calls `updateSummaryRow()` per IOC, `computeWorstVerdict()` + `updateCardVerdict()` per IOC, then global `updateDashboardCounts()`, `sortCardsBySeverity()`, `injectSectionHeadersAndNoDataSummary()` per slot, `injectDetailLink()` per loaded slot
4. Marks enrichment complete (progress bar, export button enabled)
5. Wires expand/collapse toggles via the newly-exported `wireExpandToggles()` from enrichment.ts
6. Wires the export dropdown with its own `allResults` array populated during replay

Key design choices:
- No debouncing needed — all results are available synchronously, unlike the polling loop
- `injectDetailLink()` is duplicated from enrichment.ts (20 lines) since it's a private closure-bound function — simpler than refactoring the export surface
- `wireExpandToggles()` was exported from enrichment.ts for reuse (it's pure event delegation setup with no closure dependencies)
- Verdict computation filters out context providers before calling `computeWorstVerdict()` to match live behavior

Updated `main.ts` to import and call `initHistory()` after `initEnrichment()`. The guard on `data-history-results` ensures history replay only runs on history-loaded pages (live enrichment pages don't have the attribute).

## Verification

Ran the full verification pipeline: `make js && make css && python3 -m pytest --tb=short -q` — all three steps succeeded. JS bundle built at 29.9kb, CSS compiled successfully, all 977 Python tests passed in 46.66s with no regressions. The esbuild bundler successfully resolved all imports including the new history.ts module and the newly-exported wireExpandToggles from enrichment.ts.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make js` | 0 | ✅ pass | 5000ms |
| 2 | `make css` | 0 | ✅ pass | 4800ms |
| 3 | `python3 -m pytest --tb=short -q --ignore=tests/test_playwright` | 0 | ✅ pass | 46660ms |


## Deviations

Duplicated `injectDetailLink()` in history.ts rather than exporting from enrichment.ts — the function is private with no closure dependencies but the plan mentioned exporting it wasn't necessary since it's only 20 lines. Also duplicated `initExportButton()` since history.ts needs its own `allResults` array separate from enrichment.ts's module-private one. Copied esbuild and tailwindcss binaries from the main repo to the worktree's tools/ directory since git worktrees don't share untracked binary files.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/history.ts`
- `app/static/src/ts/main.ts`
- `app/static/src/ts/modules/enrichment.ts`
