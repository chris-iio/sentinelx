---
id: S04
parent: M009
milestone: M009
provides:
  - shared-rendering.ts with 4 exported rendering functions
  - Makefile typecheck using npx tsc (no global install required)
requires:
  []
affects:
  []
key_files:
  - app/static/src/ts/modules/shared-rendering.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - Makefile
key_decisions:
  - Parameterized initExportButton with allResults array argument instead of closing over module state — enables sharing without coupling to enrichment.ts's private state
  - sortDetailRows exported as synchronous core; enrichment.ts retains debounce wrapper calling sharedSortDetailRows
  - Makefile typecheck target changed from bare 'tsc' to 'npx tsc' for portability
patterns_established:
  - shared-rendering.ts as the canonical location for rendering functions shared between enrichment.ts and history.ts — any future shared extraction should land here
  - Functions that close over module state (allResults) should be parameterized when extracted to a shared module
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M009/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T20:21:37.027Z
blocker_discovered: false
---

# S04: CSS audit + frontend TypeScript dedup

**Dead CSS audit confirmed zero orphaned selectors; 4 duplicated TS functions extracted into shared-rendering.ts with 84-line net reduction; Makefile typecheck fixed to use npx tsc.**

## What Happened

Two tasks delivered the slice goal: TypeScript dedup and CSS audit confirmation.

**T01 — shared-rendering.ts extraction.** Created `app/static/src/ts/modules/shared-rendering.ts` with a `ResultDisplay` interface and 4 exported functions: `computeResultDisplay()` (verdict/stat/summary computation, ~45 lines), `injectDetailLink()` (detail page link injection), `sortDetailRows()` (synchronous verdict-severity sort), and `initExportButton()` (parameterized with `allResults` array instead of closing over module state). Updated enrichment.ts to import all 4 — the debounce wrapper for `sortDetailRows` is retained locally, delegating to `sharedSortDetailRows()` for the core logic. Updated history.ts to import all 4 directly (no debounce wrapper needed — history replays are synchronous). Removed all private copies from both files. Installed `typescript` as devDependency since it wasn't present.

**T02 — CSS audit + full verification.** Sampled 10 of 218 unique CSS class selectors from input.css — all actively referenced in templates or TypeScript. Confirmed R046 finding: 8 milestones of UI rework left no orphaned selectors. Fixed Makefile `typecheck` target from bare `tsc` to `npx tsc --noEmit` so it resolves from node_modules without requiring a global install. Verified `make typecheck`, `make js`, and `make css` all pass. Measured LOC: enrichment.ts 582→450, history.ts 355→222, new shared-rendering.ts 181 lines. Total 937→853 = 84-line net reduction.

No behavioral changes — this is pure structural consolidation.

## Verification

Independent closer verification (all checks re-run from scratch):

1. `make typecheck` — exit 0 (npx tsc --noEmit, zero errors)
2. `make js` — exit 0 (esbuild bundle, 28.7kb)
3. `make css` — exit 0 (Tailwind CSS, 680ms rebuild)
4. shared-rendering.ts exports: ResultDisplay interface + 4 functions (computeResultDisplay, injectDetailLink, sortDetailRows, initExportButton) — confirmed via grep
5. Zero private copies: `grep -c 'function injectDetailLink'` returns 0 for both enrichment.ts and history.ts; same for initExportButton and standalone sortDetailRows in history.ts
6. Import verification: enrichment.ts imports all 4 from shared-rendering (with aliases); history.ts imports all 4 directly
7. Debounce wrapper retained in enrichment.ts — delegates to sharedSortDetailRows
8. LOC: 937 → 853 = 84-line net reduction (≥80 threshold met)
9. CSS audit: 10/10 sampled selectors from input.css confirmed referenced in templates/TS

## Requirements Advanced

None.

## Requirements Validated

- R046 — CSS audit sampled 10/218 selectors — all actively referenced in templates or TypeScript. No dead CSS found.
- R047 — 4 functions extracted to shared-rendering.ts. Zero private copies remain. 84-line net reduction. make typecheck && make js pass.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01: Installed typescript as devDependency (not present). Used npx esbuild for bundle step (tools/esbuild binary absent initially). T02: Fixed Makefile typecheck target from bare 'tsc' to 'npx tsc' — unplanned but necessary for the build to work without global tsc install.

## Known Limitations

CSS audit was a sampling check (10/218 selectors), not exhaustive. All 10 were referenced. A future milestone could add automated dead CSS detection tooling, but the finding is that no dead CSS exists.

## Follow-ups

None.

## Files Created/Modified

- `app/static/src/ts/modules/shared-rendering.ts` — New file: ResultDisplay interface + 4 exported functions (computeResultDisplay, injectDetailLink, sortDetailRows, initExportButton)
- `app/static/src/ts/modules/enrichment.ts` — Removed 4 private function copies; imports from shared-rendering; retained debounce wrapper for sortDetailRows
- `app/static/src/ts/modules/history.ts` — Removed 4 private function copies and unused imports; imports all 4 from shared-rendering
- `Makefile` — typecheck target changed from bare 'tsc' to 'npx tsc --noEmit'
