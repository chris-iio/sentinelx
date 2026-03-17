---
id: S04
parent: M001
milestone: M001
provides:
  - Three server-rendered .enrichment-section containers (context, reputation, no-data) in _enrichment_slot.html
  - JS routing dispatches provider rows to the correct section container at render time
  - Simplified sortDetailRows() (reputation section only, no context-pinning)
  - Simplified injectSectionHeadersAndNoDataSummary() (no header injection, no-data summary only)
  - CSS :has()-based empty-section hiding (no JS visibility management)
  - Dead code removal of createSectionHeader() confirming complete JS→template migration
requires:
  - slice: S03
    provides: row-factory.ts (createSectionHeader, injectSectionHeadersAndNoDataSummary, createDetailRow, createContextRow), enrichment.ts (renderEnrichmentResult, sortDetailRows, markEnrichmentComplete), input.css (provider-section-header, provider-row--no-data, no-data-expanded rules)
affects:
  - S05
key_files:
  - app/templates/partials/_enrichment_slot.html
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/input.css
  - app/static/dist/main.js
  - app/static/dist/style.css
key_decisions:
  - Server-rendered section containers in Jinja template replace JS-injected section headers from S03
  - CSS :has() selector hides empty sections — no JS visibility management needed
  - Context rows append (not prepend) within their section since the static header is the first child
  - createSectionHeader() removed entirely — zero call sites after template migration
patterns_established:
  - Section structure is server-rendered; JS only routes rows into existing containers
  - Empty sections auto-hide via CSS :has() — structural visibility is a CSS concern, not JS
  - Dead code detection via make typecheck — removed exports trigger build errors if still referenced
observability_surfaces:
  - document.querySelectorAll('.enrichment-section').length per .enrichment-slot = 3 (always present, server-rendered)
  - getComputedStyle(el).display on .enrichment-section — 'none' when no .provider-detail-row children
  - document.querySelectorAll('.enrichment-section--reputation .provider-detail-row').length — reputation row count
  - document.querySelectorAll('.enrichment-section--context .provider-detail-row').length — context row count
  - document.querySelectorAll('.enrichment-section--no-data .provider-detail-row').length — no-data row count
  - .no-data-expanded class on .enrichment-section--no-data (not .enrichment-details)
drill_down_paths:
  - .gsd/milestones/M001/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S04/tasks/T02-SUMMARY.md
duration: ~20m across 2 tasks
verification_result: passed
completed_at: 2026-03-17
---

# S04: Template Restructuring

**Server-rendered three-section layout (Reputation, Infrastructure Context, No Data) replaces JS-injected section headers, with per-section row routing and CSS-driven empty-section hiding**

## What Happened

S03 introduced section headers by injecting them from JavaScript after enrichment completed. S04 promotes that structure into the Jinja template itself, making the three-section layout a server-rendered structural backbone rather than a runtime afterthought.

**T01** delivered the atomic change across four source files simultaneously:
- **Template** (`_enrichment_slot.html`): Three `.enrichment-section` divs (`.enrichment-section--context`, `.enrichment-section--reputation`, `.enrichment-section--no-data`) added inside `.enrichment-details`, each with a static `.provider-section-header` child. Chevron toggle adjacency preserved.
- **JS routing** (`enrichment.ts`): `renderEnrichmentResult()` now routes context rows to `.enrichment-section--context`, no-data/error rows to `.enrichment-section--no-data`, and reputation rows to `.enrichment-section--reputation`. `sortDetailRows()` simplified to target only the reputation section — context-pinning block removed since context rows live in their own section.
- **Post-enrichment cleanup** (`row-factory.ts`): `injectSectionHeadersAndNoDataSummary()` stripped of all header injection logic (no more `createSectionHeader()` calls). Function now only creates the no-data summary row, scoped to `.enrichment-section--no-data`. The `.no-data-expanded` class toggles on the no-data section element.
- **CSS** (`input.css`): `.enrichment-section:not(:has(.provider-detail-row))` hides empty sections automatically. `.enrichment-section--no-data.no-data-expanded .provider-row--no-data` overrides visibility within the no-data section. `.enrichment-details.is-open` max-height increased to 750px.

**T02** confirmed the E2E baseline (89 pass, 2 pre-existing title-case failures) and removed the now-dead `createSectionHeader()` function from `row-factory.ts`. Bundle size dropped from 184.7kb to 183.8kb.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle 183.8kb ✅
- `make css` — Tailwind rebuild succeeds ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case) ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08) ✅
- Template has 3 `.enrichment-section` divs with `.provider-section-header` children ✅
- JS routes to `.enrichment-section--context` and `.enrichment-section--reputation` ✅
- `sortDetailRows()` has no context-pinning block ✅
- `injectSectionHeadersAndNoDataSummary()` has no `createSectionHeader()` calls ✅
- `createSectionHeader` fully removed from codebase ✅
- CSS `.enrichment-section:not(:has(.provider-detail-row))` hides empty sections ✅
- `.provider-row--no-data` visible inside `.enrichment-section--no-data.no-data-expanded` ✅
- `.enrichment-details.is-open` max-height is 750px ✅

## Requirements Advanced

- **GRP-01** — Provider results are now grouped into three explicit sections (Reputation, Infrastructure Context, No Data) via server-rendered template structure. JS routes rows into the correct section at render time. Empty sections auto-hide via CSS. This is the structural backbone the requirement describes.

## Requirements Validated

- None — GRP-01 needs live UAT visual confirmation to move to validated.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- **VIS-03** — Implementation note updated: section headers are now server-rendered in the Jinja template (S04), not JS-injected post-enrichment (S03). The visual presentation is identical, but the implementation mechanism changed.

## Deviations

- **Context row insertion order changed**: T01 switched from `insertBefore(row, section.firstChild)` (prepend) to `appendChild(row)` (append). The plan implied keeping prepend behavior, but with the static `.provider-section-header` as first child of each section, prepending would place rows before the header. Appending after the header is the correct behavior.

## Known Limitations

- CSS `:has()` selector used for empty-section hiding is not supported in Firefox < 121 (Dec 2023). All modern evergreen browsers support it.
- The `.enrichment-details.is-open` max-height of 750px may need further increase in S05 when context fields are added to the card header.
- 2 pre-existing E2E failures (`test_page_title`, `test_settings_page_title_tag`) remain — title case mismatch unrelated to this slice.

## Follow-ups

- None — all planned work completed cleanly.

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — Added three `.enrichment-section` containers with static `.provider-section-header` headers
- `app/static/src/ts/modules/enrichment.ts` — Routing targets section-specific containers; `sortDetailRows` simplified (no context pinning)
- `app/static/src/ts/modules/row-factory.ts` — `injectSectionHeadersAndNoDataSummary()` simplified to no-data summary only; `createSectionHeader()` removed
- `app/static/src/input.css` — Empty-section hiding rule, updated no-data-expanded selector, max-height 750px
- `app/static/dist/main.js` — Rebuilt JS bundle (183.8kb)
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- The three section containers are always present in the DOM (server-rendered). They hide themselves via CSS when empty. S05's context fields in the IOC card header are a *separate* concern from the section containers inside `.enrichment-details`.
- `.no-data-expanded` class now lives on `.enrichment-section--no-data`, not on `.enrichment-details`. Any code toggling no-data visibility must target the section element.
- `injectSectionHeadersAndNoDataSummary()` still exists but only creates the no-data summary row and wires the collapse toggle. It does NOT inject headers anymore — the name is now slightly misleading but was kept for git-blame continuity.

### What's fragile
- **CSS `:has()` empty-section hiding** — If a non-`.provider-detail-row` element is accidentally added inside a section, the `:has()` rule won't hide it even when there are no real provider rows. The rule specifically checks for `.provider-detail-row` children.
- **Max-height 750px** — This is a fixed cap. If S05 adds content that pushes total height beyond 750px, the expand animation will clip. May need to increase or switch to a JS-measured approach.

### Authoritative diagnostics
- `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` = 3 — if not 3, template rendering failed
- `getComputedStyle(sectionEl).display` — 'none' means empty (CSS :has() working), 'block' means rows were routed there
- `grep -rn "createSectionHeader" app/static/src/ts/` — should return zero results (migration complete)

### What assumptions changed
- **Original assumption (S03):** Section headers injected by JS post-enrichment is sufficient → **S04 reality:** Moving them to the template is cleaner — headers are structural, not behavioral, so they belong in HTML. JS only routes rows; CSS handles visibility.
