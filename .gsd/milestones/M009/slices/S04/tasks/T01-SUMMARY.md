---
id: T01
parent: S04
milestone: M009
provides: []
requires: []
affects: []
key_files: ["app/static/src/ts/modules/shared-rendering.ts", "app/static/src/ts/modules/enrichment.ts", "app/static/src/ts/modules/history.ts"]
key_decisions: ["Parameterized initExportButton with allResults array argument instead of closing over module state", "sortDetailRows exported as synchronous core; enrichment.ts retains debounce wrapper calling sharedSortDetailRows"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "make typecheck passes (tsc --noEmit, zero errors). make js passes (esbuild bundle, 28.7kb). Grep confirms zero private copies of the 4 extracted functions remain in enrichment.ts or history.ts."
completed_at: 2026-03-29T20:14:00.631Z
blocker_discovered: false
---

# T01: Extract 4 duplicated functions into shared-rendering.ts and update enrichment.ts + history.ts to import from shared module

> Extract 4 duplicated functions into shared-rendering.ts and update enrichment.ts + history.ts to import from shared module

## What Happened
---
id: T01
parent: S04
milestone: M009
key_files:
  - app/static/src/ts/modules/shared-rendering.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
key_decisions:
  - Parameterized initExportButton with allResults array argument instead of closing over module state
  - sortDetailRows exported as synchronous core; enrichment.ts retains debounce wrapper calling sharedSortDetailRows
duration: ""
verification_result: passed
completed_at: 2026-03-29T20:14:00.632Z
blocker_discovered: false
---

# T01: Extract 4 duplicated functions into shared-rendering.ts and update enrichment.ts + history.ts to import from shared module

**Extract 4 duplicated functions into shared-rendering.ts and update enrichment.ts + history.ts to import from shared module**

## What Happened

Created app/static/src/ts/modules/shared-rendering.ts with ResultDisplay interface and 4 exported functions (computeResultDisplay, injectDetailLink, sortDetailRows, initExportButton) extracted from duplicate private copies in enrichment.ts and history.ts. Updated both consumer files to import from the shared module, removing all private duplicates. The enrichment.ts debounce wrapper for sortDetailRows is retained, delegating to the shared synchronous core. initExportButton is parameterized with allResults instead of closing over module state.

## Verification

make typecheck passes (tsc --noEmit, zero errors). make js passes (esbuild bundle, 28.7kb). Grep confirms zero private copies of the 4 extracted functions remain in enrichment.ts or history.ts.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `PATH=./node_modules/.bin:$PATH make typecheck` | 0 | ✅ pass | 2500ms |
| 2 | `npx esbuild app/static/src/ts/main.ts --bundle --format=iife --platform=browser --target=es2022 --minify --outfile=app/static/dist/main.js` | 0 | ✅ pass | 5ms |
| 3 | `grep -c private function copies in enrichment.ts and history.ts` | 0 | ✅ pass | 50ms |


## Deviations

Installed typescript npm package as devDependency (was not present). Used npx esbuild instead of tools/esbuild binary (absent in this environment).

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/shared-rendering.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`


## Deviations
Installed typescript npm package as devDependency (was not present). Used npx esbuild instead of tools/esbuild binary (absent in this environment).

## Known Issues
None.
