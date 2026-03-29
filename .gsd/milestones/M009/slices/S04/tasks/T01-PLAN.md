---
estimated_steps: 30
estimated_files: 3
skills_used: []
---

# T01: Extract shared-rendering.ts and update enrichment.ts + history.ts

Create app/static/src/ts/modules/shared-rendering.ts with 4 exported functions extracted from the duplicate private copies in enrichment.ts and history.ts. Update both consumer files to import from the shared module.

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

## Inputs

- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/ts/modules/export.ts`
- `app/static/src/ts/types/api.ts`
- `app/static/src/ts/types/ioc.ts`

## Expected Output

- `app/static/src/ts/modules/shared-rendering.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`

## Verification

make typecheck && make js && echo 'T01 verified'
