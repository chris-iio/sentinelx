---
estimated_steps: 23
estimated_files: 3
skills_used: []
---

# T03: Build JS history replay module and verify end-to-end build

Create `app/static/src/ts/modules/history.ts` — a JS module that detects stored history results on the page and replays them through the existing rendering pipeline, making a history-loaded results page look identical to a completed live analysis.

The module:
1. Checks for `data-history-results` attribute on `.page-results`
2. If present, parses the JSON array of enrichment results
3. Iterates each result and calls the existing rendering building blocks:
   - `findCardForIoc()` to locate the card
   - For context providers (check `CONTEXT_PROVIDERS` set): `createContextRow()` + `updateContextLine()`
   - For reputation providers: `createDetailRow()` to build the row, append to the correct `.enrichment-section--reputation` or `.enrichment-section--no-data` container
   - Track `iocVerdicts` and `iocResultCounts` locally (same shape as enrichment.ts)
   - Call `updateSummaryRow()` per IOC after all its results are processed
   - Call `updateCardVerdict()` per IOC with computed worst verdict
4. After all results replayed: call `updateDashboardCounts()`, `sortCardsBySeverity()`, `injectSectionHeadersAndNoDataSummary()` per slot, `injectDetailLink()` per loaded slot
5. Wire expand/collapse toggles (call same pattern as enrichment.ts `wireExpandToggles`)
6. Mark enrichment complete (enable export button, add .complete class to progress)

Import and init from `main.ts` — add `import { init as initHistory } from './modules/history'` and call `initHistory()` after `initEnrichment()`.

Also need to export `wireExpandToggles` and `markEnrichmentComplete` from enrichment.ts (or duplicate the small wireExpandToggles in history.ts since it's event delegation setup). Actually, history.ts should have its own `wireExpandToggles` call since it sets up the same event delegation pattern — and `wireExpandToggles` in enrichment.ts only runs when `mode=online && jobId` which won't be true for history mode. So history.ts needs to call `wireExpandToggles`-equivalent setup.

Simplest approach: extract `wireExpandToggles` into its own export from enrichment.ts, or just duplicate the event delegation in history.ts (it's 20 lines of DOM event wiring). Research recommends reuse — so export `wireExpandToggles` from enrichment.ts.

Key constraints:
- The `renderEnrichmentResult` function in enrichment.ts is private and uses closures — do NOT try to import it. Use the exported building blocks directly.
- For history replay, there's no debouncing needed (all results available synchronously)
- The `allResults` array in enrichment.ts is module-private — history.ts should build its own for export functionality
- `data-history-results` JSON is HTML-entity-encoded by Jinja2's `{{ }}` — parse with standard JSON.parse after reading the attribute

Verify the full build pipeline: `make js` succeeds, `make css` succeeds, all Python tests still pass.

## Inputs

- ``app/templates/results.html` — contains data-history-results attribute (from T02)`
- ``app/static/src/ts/modules/enrichment.ts` — wireExpandToggles to export, renderEnrichmentResult as reference`
- ``app/static/src/ts/modules/row-factory.ts` — createDetailRow, createContextRow, updateSummaryRow, CONTEXT_PROVIDERS, injectSectionHeadersAndNoDataSummary, updateContextLine, formatDate`
- ``app/static/src/ts/modules/cards.ts` — findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity`
- ``app/static/src/ts/modules/verdict-compute.ts` — computeWorstVerdict, VerdictEntry type`
- ``app/static/src/ts/types/api.ts` — EnrichmentItem, EnrichmentResultItem types`
- ``app/static/src/ts/main.ts` — entry point to add history init`

## Expected Output

- ``app/static/src/ts/modules/history.ts` — history replay module that reads data-history-results and renders through existing pipeline`
- ``app/static/src/ts/main.ts` — updated with initHistory() call`
- ``app/static/src/ts/modules/enrichment.ts` — wireExpandToggles exported for reuse`

## Verification

make js && make css && python3 -m pytest --tb=short -q 2>&1 | tail -3
