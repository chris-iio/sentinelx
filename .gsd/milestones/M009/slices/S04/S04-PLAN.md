# S04: CSS audit + frontend TypeScript dedup

**Goal:** Dead CSS rules audited (finding: none to remove). Duplicated TypeScript functions extracted from enrichment.ts and history.ts into shared-rendering.ts. Both files import from the shared module. make css && make js && make typecheck pass.
**Demo:** After this: After this: Dead CSS rules removed. Shared TS module extracts duplicated functions from enrichment.ts and history.ts. make css && make js && make typecheck pass.

## Tasks
- [x] **T01: Extract 4 duplicated functions into shared-rendering.ts and update enrichment.ts + history.ts to import from shared module** — Create app/static/src/ts/modules/shared-rendering.ts with 4 exported functions extracted from the duplicate private copies in enrichment.ts and history.ts. Update both consumer files to import from the shared module.

## Steps

1. Create `app/static/src/ts/modules/shared-rendering.ts` with these exports:
   - `computeResultDisplay(result: EnrichmentItem): ResultDisplay` — extract the ~45-line verdict/statText/summaryText computation block that is duplicated verbatim in `renderEnrichmentResult()` (enrichment.ts lines ~240-285) and `replayResult()` (history.ts lines ~140-185). Return a `ResultDisplay` interface with fields: `verdict: VerdictKey`, `statText: string`, `summaryText: string`, `detectionCount: number`, `totalEngines: number`. Import `EnrichmentItem` from `../types/api`, `VerdictKey` from `../types/ioc`, `formatDate` from `./row-factory`.
   - `injectDetailLink(slot: HTMLElement): void` — copy the identical implementation from either file. Import nothing beyond DOM types.
   - `sortDetailRows(container: HTMLElement): void` — extract the synchronous core sort logic from history.ts's `sortDetailRows()` (no debounce). Import `VerdictKey` and `verdictSeverityIndex` from `../types/ioc`.
   - `initExportButton(allResults: EnrichmentItem[]): void` — extract from either file but **parameterize** the `allResults` argument instead of closing over module state. Import `exportJSON`, `exportCSV`, `copyAllIOCs` from `./export`.

2. Update `enrichment.ts`:
   - Add import: `import { computeResultDisplay, injectDetailLink, sortDetailRows as sharedSortDetailRows, initExportButton as sharedInitExportButton } from './shared-rendering';`
   - Remove the private `injectDetailLink()` function entirely.
   - Remove the private `initExportButton()` function entirely. Replace the call in `init()` with `sharedInitExportButton(allResults);`.
   - In the private debounced `sortDetailRows()`, replace the inner sort logic (the setTimeout callback body) with a call to `sharedSortDetailRows(detailsContainer)`. Keep the debounce wrapper and timer map.
   - In `renderEnrichmentResult()`, replace the ~45-line inline verdict/statText/summaryText computation with `const { verdict, statText, summaryText, detectionCount, totalEngines } = computeResultDisplay(result);`. Remove the now-unused local `let` declarations for those variables.

3. Update `history.ts`:
   - Add import: `import { computeResultDisplay, injectDetailLink, sortDetailRows, initExportButton } from './shared-rendering';`
   - Remove the private `injectDetailLink()` function.
   - Remove the private `initExportButton()` function. Replace the call in `init()` with `initExportButton(allResults);`.
   - Remove the private `sortDetailRows()` function.
   - In `replayResult()`, replace the inline verdict/statText/summaryText computation with `const { verdict, statText, summaryText, detectionCount, totalEngines } = computeResultDisplay(result);`.
   - Remove `verdictSeverityIndex` from the import of `../types/ioc` (now unused — used only by the removed sortDetailRows).
   - Remove `exportJSON, exportCSV, copyAllIOCs` from the import of `./export` (now unused — used only by the removed initExportButton).
   - Remove `formatDate` from any imports if present (now unused — used only by the removed computeResultDisplay logic, which calls formatDate internally).

4. Run `make typecheck` — must pass with zero errors.
5. Run `make js` — must succeed (esbuild bundle).

## Must-Haves

- [ ] shared-rendering.ts exports ResultDisplay interface and 4 functions
- [ ] enrichment.ts has zero private copies of the 4 extracted functions (debounce wrapper retained for sortDetailRows)
- [ ] history.ts has zero private copies of the 4 extracted functions
- [ ] `make typecheck` passes
- [ ] `make js` passes
  - Estimate: 30m
  - Files: app/static/src/ts/modules/shared-rendering.ts, app/static/src/ts/modules/enrichment.ts, app/static/src/ts/modules/history.ts
  - Verify: make typecheck && make js && echo 'T01 verified'
- [x] **T02: Confirmed zero dead CSS rules in input.css, fixed Makefile typecheck to use npx tsc, and verified full slice: make typecheck + make js + make css all pass with 84-line net TS reduction** — Confirm the CSS audit finding (no dead CSS rules in input.css) by cross-referencing selectors. Verify the full frontend build chain and measure LOC reduction from the TypeScript dedup.

## Steps

1. Verify CSS audit: run a sampling check — pick 5-10 CSS class selectors from input.css and confirm each appears in at least one template (.html) or TypeScript (.ts) file via `rg`. Document that all selectors are actively referenced. This confirms R046 finding: no dead CSS exists.

2. Run `make css` — must succeed. Confirm `app/static/dist/style.css` is generated.

3. Run `make typecheck` — must pass with zero errors.

4. Run `make js` — must succeed.

5. Measure LOC: run `wc -l` on shared-rendering.ts, enrichment.ts, and history.ts. Compare against baseline (enrichment.ts: 582, history.ts: 355). Confirm net reduction ≥ 80 lines.

6. Verify no private copies remain: `grep -c 'function injectDetailLink' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/history.ts` should return 0 for both. Same for `function initExportButton` and the standalone `function sortDetailRows` in history.ts.

## Must-Haves

- [ ] CSS audit confirmed: no dead selectors found in input.css
- [ ] `make css` passes
- [ ] `make typecheck` passes
- [ ] `make js` passes
- [ ] Net TypeScript LOC reduction ≥ 80 lines
- [ ] Zero private copies of extracted functions remain in enrichment.ts or history.ts
  - Estimate: 15m
  - Files: app/static/src/input.css, app/static/src/ts/modules/shared-rendering.ts, app/static/src/ts/modules/enrichment.ts, app/static/src/ts/modules/history.ts
  - Verify: make typecheck && make js && make css && echo 'S04 fully verified'
