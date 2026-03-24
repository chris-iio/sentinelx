# S03: Frontend tightening — TypeScript + CSS audit

**Goal:** Dead code removed from TS modules and CSS. Five O(N²) performance patterns fixed per R023. TypeScript strict-mode clean. E2E tests confirm no visual regressions.
**Demo:** `npx tsc --noEmit` passes. `grep` confirms dead exports/functions/CSS rules absent. R023 patterns verified by grep (attribute selectors, pre-built Maps, debounce). All 105 E2E tests pass.

## Must-Haves

- Dead TS exports removed: `getOrCreateSummaryRow` un-exported, `computeConsensus` and `consensusBadgeClass` deleted entirely
- Dead CSS rules removed: `.alert-success`, `.alert-warning`, `.consensus-badge` family (6 rules, ~30 lines)
- R023 pattern 1: `findCopyButtonForIoc()` uses `querySelector` attribute selector, not `querySelectorAll` iteration
- R023 pattern 2: `updateDashboardCounts()` and `sortCardsBySeverity()` called once per poll tick after the result loop, not per-result
- R023 pattern 3: `applyFilter()` debounced ≥100ms on search input `input` event (click handlers remain synchronous)
- R023 pattern 4: `verdictSeverityIndex()` uses pre-built `Map<string, number>`, not `Array.indexOf()`
- R023 pattern 5: Graph edge loop uses pre-built `Map` for node index lookup, not `.find()` + `.indexOf()`
- `npx tsc --noEmit` passes with zero errors
- All E2E tests pass (no visual regressions from CSS removal)

## Verification

- `npx tsc --noEmit` — zero errors
- `make js` — builds `app/static/dist/main.js` without errors
- `make css` — builds `app/static/dist/style.css` without errors
- Dead code grep assertions:
  - `! grep -q 'computeConsensus' app/static/src/ts/modules/verdict-compute.ts`
  - `! grep -q 'consensusBadgeClass' app/static/src/ts/modules/verdict-compute.ts`
  - `! grep -q 'export function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts`
  - `! grep -q 'alert-success' app/static/src/input.css`
  - `! grep -q 'alert-warning' app/static/src/input.css`
  - `! grep -q 'consensus-badge' app/static/src/input.css`
- R023 grep assertions:
  - `grep -q 'querySelector.*copy-btn.*data-value' app/static/src/ts/modules/enrichment.ts`
  - `! grep -q 'querySelectorAll.*copy-btn' app/static/src/ts/modules/enrichment.ts`
  - `grep -q 'new Map' app/static/src/ts/types/ioc.ts`
  - `! grep -q 'indexOf' app/static/src/ts/types/ioc.ts`
  - `grep -q 'new Map' app/static/src/ts/modules/graph.ts`
- `python3 -m pytest tests/e2e/ -x -q` — 105 E2E tests pass

## Tasks

- [x] **T01: Remove dead TS exports/functions and dead CSS rules** `est:20m`
  - Why: Eliminates dead code that inflates bundle size and confuses readers. Covers R022 (TypeScript tightening) and the CSS portion of R023.
  - Files: `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/verdict-compute.ts`, `app/static/src/input.css`
  - Do: (1) Remove `export` keyword from `getOrCreateSummaryRow` in row-factory.ts (keep the function, just un-export it). (2) Delete `computeConsensus()` and `consensusBadgeClass()` functions entirely from verdict-compute.ts (both are dead — never imported anywhere). (3) Delete `.alert-success` (line 327, 5 lines), `.alert-warning` (line 333, 5 lines), and the `.consensus-badge` family (lines 1237-1265, comment header + 4 rules ~28 lines) from input.css.
  - Verify: `npx tsc --noEmit` passes; grep confirms all dead code absent; `make js` and `make css` succeed
  - Done when: Zero dead exports, zero dead CSS rules, builds clean

- [x] **T02: Apply five R023 O(N²) performance patterns** `est:40m`
  - Why: Fixes five O(N²) DOM/computation patterns specified in R023. These cause measurable waste during enrichment of 50+ IOCs.
  - Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/filter.ts`, `app/static/src/ts/types/ioc.ts`, `app/static/src/ts/modules/graph.ts`
  - Do: (1) Replace `findCopyButtonForIoc()` body with `document.querySelector('.copy-btn[data-value="' + CSS.escape(iocValue) + '"]')` — single O(1) attribute selector. (2) Move `updateDashboardCounts()` and `sortCardsBySeverity()` calls from inside `renderEnrichmentResult()` to after the for-loop in the poll tick handler (after the `results` loop, before `since = data.next_since`). Keep `updateCardVerdict()` inside per-result. (3) Add debounce ≥100ms to `applyFilter()` call in search input `input` handler using `setTimeout`/`clearTimeout` pattern (same as sortCardsBySeverity debounce in cards.ts). Keep click handlers (verdict buttons, type pills, dashboard badges) synchronous. (4) In ioc.ts, build `const SEVERITY_MAP = new Map(VERDICT_SEVERITY.map((v, i) => [v, i]))` at module load; change `verdictSeverityIndex()` to `return SEVERITY_MAP.get(verdict) ?? -1`. (5) In graph.ts, before the edge loop, build `const nodeIndexMap = new Map(providerNodes.map((n, i) => [n.id, i]))`. Inside the loop, replace `providerNodes.find(n => n.id === edge.to)` + `providerNodes.indexOf(targetNode)` with `nodeIndexMap.get(edge.to)`.
  - Verify: `npx tsc --noEmit` passes; grep confirms new patterns present and old patterns absent; `python3 -m pytest tests/e2e/ -x -q` passes
  - Done when: All five R023 patterns applied, TypeScript clean, E2E green

## Files Likely Touched

- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/input.css`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/filter.ts`
- `app/static/src/ts/types/ioc.ts`
- `app/static/src/ts/modules/graph.ts`

## Observability / Diagnostics

- **Runtime signals:** No new runtime signals — this slice removes dead code and optimizes existing patterns. Bundle size reduction is observable via `make js` output (byte count). CSS size reduction via `make css` output.
- **Inspection surfaces:** `npx tsc --noEmit` is the primary type-safety gate. `grep` assertions confirm dead code removal. E2E tests confirm no visual regressions.
- **Failure visibility:** TypeScript compiler errors surface immediately via `npx tsc --noEmit`. Build failures are caught by `make js` / `make css`. Visual regressions caught by the 105 E2E tests.
- **Redaction constraints:** None — no secrets or PII involved in frontend static assets.
