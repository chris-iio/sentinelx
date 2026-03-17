---
id: T02
parent: S03
milestone: M001
provides:
  - Category section headers (VIS-03) grouping provider rows under "Reputation" and "Infrastructure Context"
  - No-data collapse (GRP-02) hiding no_data/error rows behind clickable count summary
key_files:
  - app/static/src/input.css
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
key_decisions:
  - Post-enrichment injection via markEnrichmentComplete() to avoid header misplacement during live sorting
  - Keyboard accessibility (Enter/Space) on no-data summary row for a11y compliance
patterns_established:
  - Post-enrichment DOM injection pattern: non-.provider-detail-row elements inserted after sortDetailRows() finalizes order, immune to re-sorting
  - Toggle pattern: class on container (.no-data-expanded) controls child visibility via CSS; aria-expanded on trigger tracks state
observability_surfaces:
  - document.querySelectorAll('.provider-section-header') — section header count per card
  - document.querySelectorAll('.no-data-summary-row') — collapse summary presence
  - document.querySelectorAll('.provider-row--no-data').length — hidden no-data row count
  - .no-data-summary-row[aria-expanded] — tracks collapse toggle state
duration: 1 session (resumed)
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Add category section headers and no-data collapse

**Added category section headers ("Infrastructure Context" / "Reputation") and no-data collapse summary row to enrichment details**

## What Happened

Implemented VIS-03 and GRP-02 in three files:

1. **CSS** (`input.css`): Added `.provider-section-header` (uppercase, muted, small with border-top separator), `.provider-row--no-data` (display:none default), `.no-data-expanded .provider-row--no-data` (display:flex when toggled), and `.no-data-summary-row` (clickable, muted, hover state).

2. **row-factory.ts**: Modified `createDetailRow()` to append `.provider-row--no-data` class for `no_data`/`error` verdicts. Added exported `createSectionHeader(label)` helper. Added exported `injectSectionHeadersAndNoDataSummary(slot)` which scans final DOM order post-sort, inserts "Infrastructure Context" header before first `.provider-context-row` and "Reputation" header before first non-context row, then creates a clickable no-data summary row with correct count and aria-expanded toggle. Keyboard a11y (Enter/Space) wired on summary row.

3. **enrichment.ts**: Imported `injectSectionHeadersAndNoDataSummary` and called it for all `.enrichment-slot` elements at the end of `markEnrichmentComplete()`, ensuring it runs after sorting is finalized.

All edge cases handled: zero no-data rows (no summary created), zero context rows (no "Infrastructure Context" header), zero verdict rows (no "Reputation" header), empty container (early return).

## Verification

- `make css` — builds clean
- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundles (188KB)
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case failures), baseline maintained
- `grep` confirms all new functions/classes present in row-factory.ts and enrichment.ts

## Diagnostics

- Inspect section headers: `document.querySelectorAll('.provider-section-header')` — should show headers with `data-section-label` attribute
- Inspect collapse: click `.no-data-summary-row` to toggle; check `aria-expanded` attribute and `.no-data-expanded` class on parent `.enrichment-details`
- Count hidden rows: `document.querySelectorAll('.provider-row--no-data').length`
- If headers missing after enrichment completes: check console for JS errors in `injectSectionHeadersAndNoDataSummary`

## Deviations

- Added keyboard accessibility (Enter/Space handlers) on no-data summary row — not in plan but necessary for a11y since element has `role="button"`

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css` — Added CSS for `.provider-section-header`, `.provider-row--no-data`, `.no-data-expanded`, `.no-data-summary-row`
- `app/static/src/ts/modules/row-factory.ts` — Added `.provider-row--no-data` class in `createDetailRow()`, exported `createSectionHeader()` and `injectSectionHeadersAndNoDataSummary()`
- `app/static/src/ts/modules/enrichment.ts` — Imported and called `injectSectionHeadersAndNoDataSummary` in `markEnrichmentComplete()`
- `app/static/dist/main.js` — Rebuilt bundle
- `app/static/dist/style.css` — Rebuilt CSS
