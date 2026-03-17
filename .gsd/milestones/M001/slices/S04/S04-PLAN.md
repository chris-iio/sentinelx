# S04: Template Restructuring

**Goal:** HTML template delivers three explicit sections — Reputation, Infrastructure Context, No Data — as the structural backbone of each IOC card, replacing the JS-injected section headers from S03.
**Demo:** After enrichment completes, each `.enrichment-details` container has three `.enrichment-section` children with static `.provider-section-header` elements rendered from the Jinja template. Provider rows route to the correct section at render time. Empty sections are hidden via CSS. The no-data collapse toggle continues to work within the no-data section. All 89 E2E tests pass.

## Must-Haves

- Three `.enrichment-section` containers (`.enrichment-section--context`, `.enrichment-section--reputation`, `.enrichment-section--no-data`) inside `.enrichment-details` in `_enrichment_slot.html`
- Static `.provider-section-header` elements in the template (not JS-injected)
- `enrichment.ts` routes context rows to `.enrichment-section--context`, reputation rows to `.enrichment-section--reputation`, no-data/error rows to `.enrichment-section--no-data`
- `sortDetailRows()` targets `.enrichment-section--reputation` only (no context-pinning logic)
- `injectSectionHeadersAndNoDataSummary()` simplified: no header injection, only no-data summary row creation targeting the no-data section
- Empty sections hidden via CSS (`:has()` selector or JS class toggle)
- `.provider-row--no-data` visible inside `.enrichment-section--no-data` (CSS override)
- `.enrichment-details.is-open` max-height increased to accommodate section wrapper chrome
- Chevron toggle adjacency preserved (`.enrichment-details` remains next sibling of `.chevron-toggle`)
- Zero `innerHTML` in TypeScript (SEC-08)
- No new Flask template variables

## Proof Level

- This slice proves: integration
- Real runtime required: no (build + E2E)
- Human/UAT required: yes (visual confirmation of section layout)

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero results (SEC-08)
- Template inspection: `_enrichment_slot.html` has three `.enrichment-section` divs with `.provider-section-header` children
- Source inspection: `enrichment.ts` routes context rows to `.enrichment-section--context`, reputation rows to `.enrichment-section--reputation`
- Source inspection: `sortDetailRows()` no longer has context-pinning block
- Source inspection: `injectSectionHeadersAndNoDataSummary()` does not call `createSectionHeader()`
- Source inspection: CSS hides `.enrichment-section` containers that have no `.provider-detail-row` children
- Source inspection: `.provider-row--no-data` is visible (not `display:none`) when inside `.enrichment-section--no-data`
- **Failure-path check:** If all providers return no-data for an IOC, the reputation section is hidden and the no-data section renders with summary row — verify CSS rule `.enrichment-section:not(:has(.provider-detail-row))` hides reputation section correctly
- **Failure-path check:** For hash IOCs with no context providers, `.enrichment-section--context` is hidden — verify no orphaned "Infrastructure Context" header visible

## Observability / Diagnostics

- Runtime signals: `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` = 3 (always present in template). `document.querySelectorAll('.enrichment-section .provider-detail-row').length` shows distribution across sections.
- Inspection surfaces: `document.querySelectorAll('.enrichment-section--reputation .provider-detail-row').length` — reputation row count. `document.querySelectorAll('.enrichment-section--context .provider-detail-row').length` — context row count. `document.querySelectorAll('.enrichment-section--no-data .provider-detail-row').length` — no-data row count. `getComputedStyle(el).display` on each `.enrichment-section` to verify empty-section hiding.
- Failure visibility: Empty section with visible header = CSS `:has()` rule not applied. Rows appearing outside any section = JS routing targeting wrong container. Duplicate section headers = `injectSectionHeadersAndNoDataSummary()` not fully simplified.
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: S03's `row-factory.ts` (createSectionHeader, injectSectionHeadersAndNoDataSummary, createDetailRow, createContextRow), S03's `enrichment.ts` (renderEnrichmentResult, sortDetailRows, markEnrichmentComplete), S03's `input.css` (provider-section-header, provider-row--no-data, no-data-expanded rules)
- New wiring introduced in this slice: Template-level section containers in `_enrichment_slot.html`; JS routing from flat `.enrichment-details` to section-specific containers
- What remains before the milestone is truly usable end-to-end: S05 (context fields in header + staleness indicator)

## Tasks

- [x] **T01: Add template sections and wire JS routing to section containers** `est:45m`
  - Why: Delivers the core GRP-01 structural change — three explicit section containers in the HTML template, with JS routing each provider row to the correct section. This is atomic: template, JS routing, sort simplification, post-enrichment cleanup, and CSS must all change together.
  - Files: `app/templates/partials/_enrichment_slot.html`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/input.css`
  - Do: (1) Add three `.enrichment-section` divs with `.provider-section-header` children inside `.enrichment-details` in the template. (2) Update `renderEnrichmentResult()` in enrichment.ts to route context rows to `.enrichment-section--context`, no-data/error rows to `.enrichment-section--no-data`, and reputation rows to `.enrichment-section--reputation`. (3) Update `sortDetailRows()` to target `.enrichment-section--reputation` and remove context-pinning block. (4) Simplify `injectSectionHeadersAndNoDataSummary()` in row-factory.ts to remove header injection, keep only no-data summary row creation, retarget queries to `.enrichment-section--no-data`. (5) Add CSS: hide empty sections via `:has()`, override `.provider-row--no-data` display:none inside `.enrichment-section--no-data`, increase `.enrichment-details.is-open` max-height to 750px. Constraint: SEC-08 (no innerHTML), preserve chevron adjacency, no new Flask template variables.
  - Verify: `make typecheck && make js-dev && make css` all pass. Template has 3 `.enrichment-section` divs. `sortDetailRows()` has no context-pinning. `injectSectionHeadersAndNoDataSummary()` has no `createSectionHeader` calls.
  - Done when: Build succeeds with zero type errors, template has three section containers with static headers, JS routes rows to correct sections.

- [x] **T02: Run E2E suite and clean up dead code** `est:20m`
  - Why: Confirms the atomic change from T01 didn't break any E2E tests, removes dead code paths (createSectionHeader export if unused, context-pinning comments), and verifies edge cases (empty sections hidden, no-data collapse still works).
  - Files: `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts`
  - Do: (1) Run full E2E suite. (2) Verify `createSectionHeader` — if only called internally by `injectSectionHeadersAndNoDataSummary()` and no longer needed, remove the export or the function entirely. (3) Grep for innerHTML (SEC-08 gate). (4) Verify no duplicate section headers in rendered output by checking that `injectSectionHeadersAndNoDataSummary` doesn't create headers. (5) Confirm `.enrichment-details.is-open` max-height is sufficient (750px). (6) Run `make js-dev && make css` for final build.
  - Verify: `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing). `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero results.
  - Done when: E2E suite passes at pre-existing baseline (89 pass, 2 pre-existing failures), zero innerHTML usage, no dead code remaining from the section-header migration.

## Files Likely Touched

- `app/templates/partials/_enrichment_slot.html`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/input.css`
- `app/static/dist/main.js` (rebuilt)
- `app/static/dist/style.css` (rebuilt)
