# S04: Template Restructuring

**Goal:** The HTML template delivers three explicit sections — Reputation, Infrastructure Context, No Data — as the structural backbone of each IOC card (GRP-01).
**Demo:** Each IOC card visibly organizes provider results under three labeled sections; empty sections auto-hide via CSS `:has()`; no-data collapse toggle scoped to the no-data section; chevron expand/collapse still works; all `data-*` attributes on `.ioc-card` untouched; 89/91 E2E tests pass (2 pre-existing title-case failures).

## Must-Haves

- Three server-rendered `.enrichment-section` containers (context, reputation, no-data) inside `.enrichment-details` with static `.provider-section-header` elements (GRP-01)
- JS routing dispatches each provider row to the correct section container at render time
- `sortDetailRows()` simplified — no context-pinning block; operates on reputation section only
- `injectSectionHeadersAndNoDataSummary()` simplified — no header injection; only no-data summary row creation
- CSS `:has()`-based empty-section hiding (no JS visibility management)
- `data-ioc-value`, `data-ioc-type`, `data-verdict` attributes remain on `.ioc-card` root element
- `.enrichment-details` remains immediate next sibling of `.chevron-toggle` (adjacency constraint)
- Zero `innerHTML`/`insertAdjacentHTML` usage in TypeScript (SEC-08)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (E2E suite exercises full rendering pipeline)
- Human/UAT required: no (structural change verified by E2E + grep + build gates)

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero actual usage (SEC-08)
- `grep -rn "createSectionHeader" app/static/src/ts/` — zero results (dead code removed)
- Template: `grep -c "enrichment-section" app/templates/partials/_enrichment_slot.html` — 6 matches (3 divs × 2 class refs)
- **Diagnostic check — empty-section hiding:** `document.querySelectorAll('.enrichment-section')` per slot returns 3 elements; `getComputedStyle(el).display` returns `none` for sections with no `.provider-detail-row` children (CSS `:has()` rule active)
- **Failure-path check — misrouted rows:** `document.querySelectorAll('.enrichment-details > .provider-detail-row')` returns 0 (all rows inside section containers, none orphaned at `.enrichment-details` level)
- **Failure-path check — duplicate headers:** `document.querySelectorAll('.provider-section-header').length` per slot = 3 (template-static only, no JS-injected duplicates)

## Observability / Diagnostics

- Runtime signals: `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` = 3 (always present, server-rendered); `getComputedStyle(sectionEl).display` reveals whether section is hidden (`none`) or has rows (`block`); `.enrichment-section--no-data.no-data-expanded` class presence tracks collapse toggle state
- Inspection surfaces: Browser DevTools → each `.enrichment-slot` contains exactly 3 `.enrichment-section` children inside `.enrichment-details`; `document.querySelectorAll('.enrichment-section--reputation .provider-detail-row').length` counts reputation rows; same pattern for `--context` and `--no-data`
- Failure visibility: (1) Visible header with no rows = CSS `:has()` not applied or unsupported browser. (2) Rows outside any `.enrichment-section` = JS routing bug (querySelector returned null). (3) Duplicate section headers = `injectSectionHeadersAndNoDataSummary()` still calling `createSectionHeader()`. (4) Sort not working = `sortDetailRows` receiving wrong container
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S03's `row-factory.ts` (createDetailRow, createContextRow, injectSectionHeadersAndNoDataSummary), S03's `enrichment.ts` (renderEnrichmentResult, sortDetailRows, markEnrichmentComplete), S03's `input.css` (provider-section-header, provider-row--no-data, no-data-expanded rules)
- New wiring introduced in this slice: Template `_enrichment_slot.html` now defines the section container structure; JS routes rows into these containers instead of into the flat `.enrichment-details` div
- What remains before the milestone is truly usable end-to-end: S05 (context fields in card header + staleness indicator)

## Tasks

- [x] **T01: Add template sections and wire JS routing to section containers** `est:30m`
  - Why: Core GRP-01 structural change — promotes section structure from JS-injected to server-rendered, requiring atomic template + JS routing + CSS changes
  - Files: `app/templates/partials/_enrichment_slot.html`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/input.css`
  - Do: Add three `.enrichment-section` divs with static `.provider-section-header` in template; update `renderEnrichmentResult()` to route rows to correct section containers; remove context-pinning from `sortDetailRows()`; simplify `injectSectionHeadersAndNoDataSummary()` to no-data summary only; add CSS empty-section hiding via `:has()`; increase max-height to 750px
  - Verify: `make typecheck && make js-dev && make css` all pass; template grep confirms 6 enrichment-section matches; zero innerHTML usage; context pinning removed
  - Done when: Template has 3 section containers, JS routes to them, builds pass, SEC-08 clean

- [x] **T02: Run E2E suite and clean up dead code** `est:15m`
  - Why: Verify the atomic change doesn't break E2E tests; remove dead `createSectionHeader()` confirming complete JS→template migration
  - Files: `app/static/src/ts/modules/row-factory.ts`, `app/static/dist/main.js`
  - Do: Run full E2E suite; assess and remove `createSectionHeader()` if no call sites remain; run SEC-08 gate; final rebuild
  - Verify: `pytest tests/ -m e2e --tb=short -q` — 89 pass / 2 fail baseline; `grep -rn "createSectionHeader" app/static/src/ts/` — zero results; `make typecheck && make js-dev && make css` all pass
  - Done when: E2E baseline matches, dead code removed, all builds pass

## Files Likely Touched

- `app/templates/partials/_enrichment_slot.html`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/input.css`
- `app/static/dist/main.js`
- `app/static/dist/style.css`
