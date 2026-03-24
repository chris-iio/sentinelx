# S03: Visual Redesign

**Goal:** Provider rows display a clear visual hierarchy with verdict prominence, a breakdown micro-bar, category labels, and no-data rows collapsed by default — all changes confined to row-factory.ts and input.css.
**Demo:** Worst verdict badge is visually dominant in card header (VIS-01); micro-bar replaces text consensus badge (VIS-02); category labels distinguish Reputation from Infrastructure (VIS-03); no-data providers collapsed with count summary (GRP-02).

## Must-Haves

- VIS-01: `.verdict-label` enlarged to 0.875rem/700 with 0.25rem 0.75rem padding — visually dominant over provider-row `.verdict-badge` (0.72rem/600)
- VIS-02: `.consensus-badge` DOM creation removed from `updateSummaryRow()`; replaced by `.verdict-micro-bar` with proportional colored segments (malicious/suspicious/clean/no_data) and accessible `title` attribute
- VIS-03: "Reputation" and "Infrastructure Context" section headers injected post-enrichment, positioned before each category's first row in final sorted DOM order
- GRP-02: No-data/error rows hidden by default via `.provider-row--no-data` class; clickable `.no-data-summary-row` shows count and toggles `.no-data-expanded` class on container; `aria-expanded` tracks state; keyboard accessible (Enter/Space)
- All 24 E2E-locked CSS selectors preserved — no class renames
- Zero-count micro-bar segments skipped; `Math.max(1, total)` guards division-by-zero
- Edge cases: zero no-data rows (no summary), zero context rows (no Infrastructure header), zero verdict rows (no Reputation header), empty container (early return)
- `make typecheck && make js-dev && make css` all pass after every change
- 89/91 E2E baseline maintained (2 pre-existing title-case failures)

## Proof Level

- This slice proves: operational
- Real runtime required: yes (live browser rendering for visual confirmation)
- Human/UAT required: yes (VIS-01 badge hierarchy is visual-only; micro-bar proportions need human eye)

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing)
- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — zero results (confirms safe removal)
- DOM inspection: `document.querySelectorAll('.verdict-micro-bar').length` > 0 after enrichment — micro-bars rendered
- DOM inspection: `document.querySelectorAll('.provider-section-header').length` >= 1 per IOC card after enrichment completes — section headers present
- DOM inspection: `document.querySelectorAll('.no-data-summary-row').length` > 0 when no-data providers exist — collapse summary present
- **Failure-path check:** If `injectSectionHeadersAndNoDataSummary()` throws, zero `.provider-section-header` elements will exist when `.provider-detail-row` elements are present — detectable via `document.querySelectorAll('.provider-section-header').length === 0 && document.querySelectorAll('.provider-detail-row').length > 0` in browser DevTools
- **Failure-path check:** Micro-bar segments with `NaN%` in `style.width` indicate a division-by-zero bug — inspectable via `document.querySelectorAll('.micro-bar-segment[style*="NaN"]').length` (expected: 0)
- **Failure-path check:** `.no-data-summary-row` without `aria-expanded` attribute indicates toggle wiring failed — check via `document.querySelector('.no-data-summary-row:not([aria-expanded])')` (expected: null after click)

## Observability / Diagnostics

- Runtime signals: `.verdict-micro-bar[title]` attribute on each summary row encodes exact verdict counts (e.g. "2 malicious, 0 suspicious, 3 clean, 1 no data"); `.no-data-summary-row[aria-expanded]` tracks collapse/expand state as `"true"`/`"false"`
- Inspection surfaces: Browser DevTools element queries — `document.querySelectorAll('.verdict-micro-bar')` (micro-bar count), `.provider-section-header` (section header count), `.no-data-summary-row` (collapse summary presence), `.provider-row--no-data` (hidden row count)
- Failure visibility: Zero `.provider-section-header` elements when `.provider-detail-row` elements exist indicates `injectSectionHeadersAndNoDataSummary()` was not called or threw; `NaN%` segment widths indicate `computeVerdictCounts()` guard bypassed; absent `aria-expanded` on `.no-data-summary-row` after click indicates toggle handler not wired
- Redaction constraints: none — all data is derived from public enrichment results

## Integration Closure

- Upstream surfaces consumed: `row-factory.ts` DOM builders (S02), `enrichment.ts` orchestrator (S02), `verdict-compute.ts` `VerdictEntry` type (S02), `CONTEXT_PROVIDERS` set (existing), CSS variable tokens in `:root` (existing)
- New wiring introduced in this slice: `markEnrichmentComplete()` in `enrichment.ts` calls `injectSectionHeadersAndNoDataSummary()` for all `.enrichment-slot` elements post-enrichment
- What remains before the milestone is truly usable end-to-end: S04 template restructuring (static section containers), S05 context fields + staleness indicator

## Tasks

- [x] **T01: Enlarge verdict badge and replace consensus badge with micro-bar** `est:30m`
  - Why: Delivers VIS-01 (verdict badge prominence) and VIS-02 (micro-bar replacing consensus badge text) — the header/summary row visual hierarchy changes
  - Files: `app/static/src/input.css`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/verdict-compute.ts`
  - Do: Increase `.verdict-label` CSS (0.7rem→0.875rem, weight 600→700, padding enlarged). Add `.verdict-micro-bar` and `.micro-bar-segment--{verdict}` CSS classes. Add `computeVerdictCounts()` private helper in row-factory.ts. Replace `consensusBadge` span creation in `updateSummaryRow()` with micro-bar div containing percentage-width colored segments. Remove unused `consensusBadgeClass` import. Leave `.consensus-badge` CSS as dead CSS for rollback. Guard `total === 0` with `Math.max(1, total)`.
  - Verify: `make typecheck && make js-dev && make css` pass; `pytest tests/ -m e2e --tb=short -q` maintains 89/91 baseline; `grep -n "consensusBadge" row-factory.ts` returns zero
  - Done when: `.verdict-label` CSS enlarged, micro-bar replaces consensus badge in `updateSummaryRow()`, zero TS errors, E2E baseline maintained

- [x] **T02: Add category section headers and no-data collapse** `est:45m`
  - Why: Delivers VIS-03 (category section headers) and GRP-02 (no-data collapse) — the enrichment details structural changes that run post-enrichment via `markEnrichmentComplete()`
  - Files: `app/static/src/input.css`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts`
  - Do: Add CSS for `.provider-section-header`, `.provider-row--no-data` (hidden by default), `.no-data-expanded .provider-row--no-data` (visible on toggle), `.no-data-summary-row`. Modify `createDetailRow()` to add `.provider-row--no-data` class for no_data/error verdicts. Export `createSectionHeader()` and `injectSectionHeadersAndNoDataSummary(slot)` from row-factory.ts. The injection function scans final sorted DOM, inserts headers before each category's first row, counts no-data rows and creates clickable summary with `aria-expanded` toggle. Wire keyboard a11y (Enter/Space). Call from `markEnrichmentComplete()` in enrichment.ts for all `.enrichment-slot` elements.
  - Verify: `make typecheck && make js-dev && make css` pass; `pytest tests/ -m e2e --tb=short -q` maintains 89/91 baseline; `grep -n "injectSectionHeaders" enrichment.ts` confirms wiring
  - Done when: Section headers appear after enrichment for each category with rows; no-data rows hidden by default with clickable count summary; `aria-expanded` toggles on click; keyboard accessible; zero TS errors; E2E baseline maintained

## Files Likely Touched

- `app/static/src/input.css`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/dist/main.js` (rebuilt)
- `app/static/dist/style.css` (rebuilt)
