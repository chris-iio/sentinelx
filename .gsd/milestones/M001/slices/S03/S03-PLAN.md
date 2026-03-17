# S03: Visual Redesign

**Goal:** Four targeted visual improvements to the results page — verdict badge prominence, micro-bar replacing consensus text, category section headers, and no-data collapse — all confined to `row-factory.ts`, `enrichment.ts`, and `input.css` with zero E2E regression.
**Demo:** IOC card header verdict badge is visually dominant (larger, bolder than row badges); summary row shows proportional micro-bar instead of `[2/5]` text; expanded details show "Reputation" / "Infrastructure Context" section headers; no-data providers are hidden behind a clickable "N had no record" summary row.

## Must-Haves

- VIS-01: `.verdict-label` in card header is visually larger (0.875rem, font-weight 700, larger padding) than `.verdict-badge` in provider rows (0.72rem)
- VIS-02: `updateSummaryRow()` produces `.verdict-micro-bar` with proportional segments instead of `.consensus-badge` text; title attribute encodes exact counts for accessibility
- VIS-03: "Reputation" and "Infrastructure Context" section headers injected into `.enrichment-details` post-enrichment, positioned correctly relative to sorted rows
- GRP-02: No-data/error rows get `.provider-row--no-data` class (CSS `display:none`); `.no-data-summary-row` shows count; click toggles `.no-data-expanded` on container
- All 24 E2E-locked CSS selectors preserved; no class renames
- 89/91 E2E baseline maintained after every task

## Proof Level

- This slice proves: operational
- Real runtime required: yes (browser rendering of DOM changes)
- Human/UAT required: yes (VIS-01 badge size hierarchy is visual-only; no pixel test in suite)

## Verification

- `make typecheck` — zero TS errors after each task
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89/91 baseline maintained (no new failures)
- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` returns zero results (confirms safe to remove)
- DOM structure verified: `.verdict-micro-bar` contains `.micro-bar-segment` children with percentage widths
- DOM structure verified: `.provider-section-header` elements appear before their respective row groups
- DOM structure verified: `.provider-row--no-data` elements have `display:none` by default; `.no-data-summary-row` shows correct count
- Failure-path check: `computeVerdictCounts()` with empty `VerdictEntry[]` returns `{total:0}` and micro-bar renders gracefully (no NaN widths)
- Failure-path check: `injectSectionHeadersAndNoDataSummary()` with zero rows produces no section headers and no summary row (no crash)

## Observability / Diagnostics

- Runtime signals: New DOM elements (`.verdict-micro-bar`, `.provider-section-header`, `.no-data-summary-row`, `.provider-row--no-data`) are inspectable via browser DevTools `document.querySelectorAll()`; the micro-bar `title` attribute exposes exact verdict counts; `.no-data-summary-row[aria-expanded]` tracks collapse state
- Inspection surfaces: Browser DevTools element inspector on any IOC card; `document.querySelectorAll('.verdict-micro-bar').length` to confirm micro-bars created; `document.querySelectorAll('.provider-section-header').length` for section headers; `document.querySelectorAll('.no-data-summary-row').length` for collapse summaries
- Failure visibility: TypeScript compilation errors via `make typecheck`; CSS build errors via `make css`; E2E regressions surface as test count drops below 89; runtime JS errors visible in browser console; micro-bar with `NaN%` widths visible in element inspector
- Redaction constraints: none — no secrets or PII in DOM elements

## Integration Closure

- Upstream surfaces consumed: `row-factory.ts` (DOM builders from S02), `enrichment.ts` (orchestrator from S02), `verdict-compute.ts` (VerdictEntry type, computeConsensus), `input.css` (CSS layer from S01), `CSS-CONTRACTS.md` (locked selectors from S01)
- New wiring introduced in this slice: `injectSectionHeadersAndNoDataSummary()` called from `markEnrichmentComplete()` in enrichment.ts — connects post-enrichment event to new DOM injection
- What remains before the milestone is truly usable end-to-end: S04 (template restructuring for static 3-section layout), S05 (context fields + staleness indicator)

## Tasks

- [x] **T01: Enlarge verdict badge and replace consensus badge with micro-bar** `est:45m`
  - Why: Delivers VIS-01 (badge prominence) and VIS-02 (micro-bar) — the header/summary row visual hierarchy that makes each IOC card scannable at a glance
  - Files: `app/static/src/input.css`, `app/static/src/ts/modules/row-factory.ts`
  - Do: (1) In `input.css`, increase `.verdict-label` to `font-size: 0.875rem`, `font-weight: 700`, `padding: 0.25rem 0.75rem`. (2) Add new CSS classes: `.verdict-micro-bar` (flex container, 6px height, rounded), `.micro-bar-segment` (height 100%, transition), `.micro-bar-segment--malicious/suspicious/clean/no_data` (verdict color tokens). (3) In `row-factory.ts`, add `computeVerdictCounts(entries)` helper returning `{malicious, suspicious, clean, noData, total}`. (4) In `updateSummaryRow()`, replace consensus badge block with micro-bar: create `.verdict-micro-bar` div, compute percentage widths per segment, skip zero-count segments, set `title` attribute with counts. (5) Remove `consensusBadgeClass` import if no longer used. (6) Guard against `total === 0` to prevent NaN widths.
  - Verify: `make css && make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q`
  - Done when: `.verdict-label` has 0.875rem/700 in CSS; `updateSummaryRow()` creates `.verdict-micro-bar` instead of `.consensus-badge`; typecheck passes; 89/91 E2E baseline holds

- [x] **T02: Add category section headers and no-data collapse** `est:1h`
  - Why: Delivers VIS-03 (section headers) and GRP-02 (no-data collapse) — the details container changes that group providers by category and reduce noise from no-data results
  - Files: `app/static/src/input.css`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts`
  - Do: (1) In `input.css`, add CSS for `.provider-section-header` (uppercase, muted, small, border-top separator), `.provider-row--no-data` (`display:none`), `.no-data-expanded .provider-row--no-data` (`display:flex`), `.no-data-summary-row` (muted, clickable, border-top). (2) In `row-factory.ts`, export `createSectionHeader(label)` returning a `.provider-section-header` div. (3) In `createDetailRow()`, add `.provider-row--no-data` class when verdict is `"no_data"` or `"error"`. (4) In `row-factory.ts`, export `injectSectionHeadersAndNoDataSummary(slot)` — scans sorted rows in `.enrichment-details`, inserts "Reputation" header before first non-context row and "Infrastructure Context" header before first context row; then counts `.provider-row--no-data` elements, inserts `.no-data-summary-row` before the first one with count text, wires click handler to toggle `.no-data-expanded` on the details container and set `aria-expanded`. (5) In `enrichment.ts`, import and call `injectSectionHeadersAndNoDataSummary()` from `markEnrichmentComplete()` for each `.enrichment-slot` on the page. (6) Handle edge cases: zero no-data rows → no summary row; zero verdict rows in a category → no header for that category; empty details container → no-op.
  - Verify: `make css && make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q`
  - Done when: `createDetailRow()` adds `.provider-row--no-data` for no_data/error verdicts; `markEnrichmentComplete()` calls injection function; section headers appear in correct positions relative to sorted rows; no-data rows hidden by default with summary count; click toggles visibility; typecheck passes; 89/91 E2E baseline holds

## Files Likely Touched

- `app/static/src/input.css`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/enrichment.ts`
