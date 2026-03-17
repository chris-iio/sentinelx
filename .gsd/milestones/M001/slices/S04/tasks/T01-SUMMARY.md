---
id: T01
parent: S04
milestone: M001
provides:
  - Three server-rendered .enrichment-section containers in _enrichment_slot.html
  - JS routing dispatches provider rows to context, reputation, or no-data sections
  - Simplified sortDetailRows (no context-pinning) and injectSectionHeadersAndNoDataSummary (no header injection)
  - CSS empty-section hiding via :has() selector
key_files:
  - app/templates/partials/_enrichment_slot.html
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/input.css
  - app/static/dist/main.js
  - app/static/dist/style.css
key_decisions:
  - Context rows now append (not prepend) within their section since the static header is the first child
patterns_established:
  - Section containers are server-rendered in Jinja template; JS routes rows into them at render time
  - Empty sections auto-hide via CSS :has() — no JS visibility management needed
observability_surfaces:
  - document.querySelectorAll('.enrichment-section').length per slot = 3 (always present)
  - getComputedStyle(el).display on .enrichment-section reveals whether rows were routed there
  - .no-data-expanded class on .enrichment-section--no-data (not .enrichment-details)
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Add template sections and wire JS routing to section containers

**Promote enrichment section structure from JS-injected headers to server-rendered template containers with per-section JS routing**

## What Happened

Delivered the core GRP-01 structural change across 4 source files:

1. **Template** (`_enrichment_slot.html`): Added three `.enrichment-section` child divs inside `.enrichment-details`, each with a static `.provider-section-header`. The `.enrichment-details` div remains the immediate next sibling of `.chevron-toggle` (chevron adjacency preserved).

2. **JS routing** (`enrichment.ts`): `renderEnrichmentResult()` now routes context provider rows to `.enrichment-section--context`, no-data/error rows to `.enrichment-section--no-data`, and reputation rows to `.enrichment-section--reputation`. `sortDetailRows()` receives only the reputation section container. Context-pinning block removed from `sortDetailRows()` since context rows live in their own section.

3. **Post-enrichment cleanup** (`row-factory.ts`): `injectSectionHeadersAndNoDataSummary()` stripped of all VIS-03 header injection logic (no more `createSectionHeader()` calls). Retargeted no-data collapse logic to query within `.enrichment-section--no-data` and toggle `.no-data-expanded` on that section element. `createSectionHeader()` function definition retained for T02 assessment.

4. **CSS** (`input.css`): Added `.enrichment-section:not(:has(.provider-detail-row)) { display: none; }` to auto-hide empty sections. Updated `.no-data-expanded` selector to `.enrichment-section--no-data.no-data-expanded`. Increased `.enrichment-details.is-open` max-height from 600px to 750px.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle 184.7kb ✅
- `make css` — Tailwind rebuild ✅
- Template: `grep -o "enrichment-section" _enrichment_slot.html | wc -l` = 6 ✅
- `createSectionHeader` exists in row-factory.ts but NOT called from `injectSectionHeadersAndNoDataSummary` ✅
- Context pinning (`insertBefore(cr, detailsContainer.firstChild)`) removed from enrichment.ts ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero actual usage (only a comment in graph.ts) ✅

## Diagnostics

- `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` = 3 (always present, server-rendered)
- `getComputedStyle(sectionEl).display` — `none` when no `.provider-detail-row` children, otherwise `block`
- `document.querySelector('.enrichment-section--no-data').classList` — check for `no-data-expanded` after toggle
- Failure state: visible header with no rows = CSS `:has()` not applied; rows outside sections = JS routing bug

## Deviations

- Changed context row insertion from `insertBefore(row, section.firstChild)` to `appendChild(row)` — the plan said to keep the prepend, but with the static `.provider-section-header` as first child, prepending would place rows before the header. Appending after the header is correct.

## Known Issues

- None

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — Added three `.enrichment-section` containers with static `.provider-section-header` headers
- `app/static/src/ts/modules/enrichment.ts` — Routing targets section-specific containers; `sortDetailRows` simplified (no context pinning)
- `app/static/src/ts/modules/row-factory.ts` — `injectSectionHeadersAndNoDataSummary()` simplified to no-data summary only, scoped to `.enrichment-section--no-data`
- `app/static/src/input.css` — Empty-section hiding rule, updated no-data-expanded selector, max-height 750px
- `app/static/dist/main.js` — Rebuilt JS bundle
- `app/static/dist/style.css` — Rebuilt CSS
- `.gsd/milestones/M001/slices/S04/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
