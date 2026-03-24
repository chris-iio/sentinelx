---
id: S04
parent: M001
milestone: M001
provides:
  - Three server-rendered .enrichment-section containers (context, reputation, no-data) in _enrichment_slot.html
  - JS routing dispatches each provider row to the correct section container at render time
  - Simplified sortDetailRows — operates on reputation section only, no context-pinning
  - Simplified injectSectionHeadersAndNoDataSummary — no-data summary only, no header injection
  - CSS :has()-based empty-section hiding (zero JS visibility management)
  - Dead code removal of createSectionHeader() confirming complete JS→template migration
requires:
  - slice: S03
    provides: row-factory.ts (createDetailRow, createContextRow, injectSectionHeadersAndNoDataSummary), enrichment.ts (renderEnrichmentResult, sortDetailRows, markEnrichmentComplete), input.css (provider-section-header, provider-row--no-data, no-data-expanded rules)
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
  - Section structure promoted from JS-injected (S03) to server-rendered Jinja template — eliminates timing dependency on post-enrichment injection
  - Empty sections hidden via CSS :has() — no JS visibility management needed
  - Context rows append (not prepend) within their section since static header is the first child
  - Removed createSectionHeader() entirely — zero call sites after template migration
patterns_established:
  - Section containers are server-rendered in Jinja template; JS routes rows into them at render time
  - CSS :has() for structural visibility — sections self-hide when empty, self-show when populated
  - Dead code detection via make typecheck — removed exports trigger build errors if still referenced
observability_surfaces:
  - document.querySelectorAll('.enrichment-section').length per slot = 3 (always present, server-rendered)
  - getComputedStyle(sectionEl).display reveals whether section is hidden (none) or has rows (block)
  - .enrichment-section--no-data.no-data-expanded class presence tracks collapse toggle state
  - grep -rn "createSectionHeader" app/static/src/ts/ returns zero results (migration complete)
drill_down_paths:
  - .gsd/milestones/M001/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S04/tasks/T02-SUMMARY.md
duration: ~45m (2 tasks)
verification_result: passed
completed_at: 2026-03-17
---

# S04: Template Restructuring

**Server-rendered three-section enrichment structure (Reputation, Infrastructure Context, No Data) with per-section JS routing and CSS :has() empty-section hiding**

## What Happened

S03 proved the section concept (headers injected post-enrichment by JS). S04 promoted that structure into the Jinja template as a permanent, server-rendered backbone.

**T01** delivered the core GRP-01 change across 4 files atomically. The `_enrichment_slot.html` template gained three `.enrichment-section` child divs (context, reputation, no-data) inside `.enrichment-details`, each with a static `.provider-section-header`. JS routing in `enrichment.ts` was updated so `renderEnrichmentResult()` dispatches each provider row to the correct section container based on provider type and verdict. `sortDetailRows()` was simplified to receive only the reputation section — no more context-pinning logic. `injectSectionHeadersAndNoDataSummary()` in `row-factory.ts` was stripped of all header injection — it now only creates the no-data summary row, scoped to `.enrichment-section--no-data`. A CSS `:has()` rule auto-hides sections with no `.provider-detail-row` children, eliminating all JS visibility management.

**T02** ran the full E2E suite (89 pass, 2 fail — pre-existing title-case baseline), confirmed `createSectionHeader()` had zero remaining call sites, and removed the dead function and its export from `row-factory.ts`. Bundle size dropped from 184.7kb to 183.8kb.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle succeeds ✅
- `make css` — Tailwind rebuild succeeds ✅
- `python3 -m pytest tests/ -m e2e --tb=short -q` — **89 passed, 2 failed** (pre-existing title-case) ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero actual usage (SEC-08) ✅
- `grep -rn "createSectionHeader" app/static/src/ts/` — zero results (dead code removed) ✅
- Template: `grep -o "enrichment-section" _enrichment_slot.html | wc -l` = 6 (3 divs × 2 class refs) ✅

## Requirements Advanced

- None (GRP-01 is validated, not merely advanced)

## Requirements Validated

- **GRP-01** — Provider results are grouped into three sections. Three server-rendered `.enrichment-section` containers in template, JS routing to correct section per provider type, CSS `:has()` auto-hiding empty sections. E2E suite 89/2 baseline confirms no regressions. Template grep confirms structure. Zero innerHTML usage.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- **VIS-03** — Category labels are now server-rendered in the template (static `.provider-section-header` elements) rather than JS-injected post-enrichment as S03 delivered. The S03 JS injection code was removed. VIS-03 remains validated but its implementation moved from JS to HTML.

## Deviations

- **Context row insertion order changed:** Plan said to keep prepend behavior for context rows. Changed to `appendChild()` because with the static `.provider-section-header` as first child of each section, prepending would place rows *before* the header. Appending after the header is correct. No functional impact.

## Known Limitations

- CSS `:has()` requires Chrome 105+, Firefox 121+, Safari 15.4+. Older browsers will show empty section headers with no rows beneath them. This is acceptable — SentinelX targets analyst workstations with modern evergreen browsers.
- 2 pre-existing E2E failures: `test_page_title[chromium]` and `test_settings_page_title_tag[chromium]` — title case mismatch ("sentinelx" vs "SentinelX"). Not introduced by this slice.

## Follow-ups

- None — all planned work completed cleanly.

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — Added three `.enrichment-section` containers with static `.provider-section-header` headers
- `app/static/src/ts/modules/enrichment.ts` — JS routing targets section-specific containers; `sortDetailRows` simplified (no context pinning)
- `app/static/src/ts/modules/row-factory.ts` — `injectSectionHeadersAndNoDataSummary()` simplified to no-data summary only; `createSectionHeader()` removed
- `app/static/src/input.css` — Empty-section hiding via `:has()`, updated `.no-data-expanded` selector, max-height 750px
- `app/static/dist/main.js` — Rebuilt JS bundle (183.8kb)
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- The `.enrichment-details` div now has 3 `.enrichment-section` children (context, reputation, no-data). S05's context fields (CTX-01) should target `.enrichment-section--context` rows or the IOC card header — the section structure is stable and server-rendered.
- The `.enrichment-details` div remains the immediate next sibling of `.chevron-toggle` — this adjacency constraint is preserved and must stay intact.
- `injectSectionHeadersAndNoDataSummary()` now only handles no-data summary creation. If S05 needs to inject staleness indicators (CTX-02), it should use a similar post-enrichment hook in `markEnrichmentComplete()` or add to the existing function.

### What's fragile
- **CSS `:has()` rule** — `.enrichment-section:not(:has(.provider-detail-row)) { display: none; }` is the sole mechanism hiding empty sections. If a row gets appended with a different class name, the section will show as empty (visible header, no content). Any new row type must include `.provider-detail-row` in its class list.
- **Section routing in `renderEnrichmentResult()`** — uses `querySelector('.enrichment-section--context')` etc. on the `enrichmentDetails` container. If the template structure changes or class names are renamed, rows will fail to route (they won't appear at all, not silently misroute).

### Authoritative diagnostics
- `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` — must be exactly 3. If not, template was modified.
- `document.querySelectorAll('.enrichment-details > .provider-detail-row').length` — must be 0. Any non-zero count means rows are orphaned outside section containers (JS routing bug).
- `document.querySelectorAll('.provider-section-header').length` per slot — must be exactly 3. More than 3 means JS is still injecting duplicate headers.

### What assumptions changed
- **S03 assumed section headers were JS-injected post-enrichment** — S04 moved them to server-rendered HTML. The `createSectionHeader()` function and all calls to it were removed. Any code that assumed headers are created dynamically needs updating.
- **Context-pinning in sortDetailRows() is gone** — context rows now live in their own `.enrichment-section--context` container. `sortDetailRows()` only touches `.enrichment-section--reputation`. If S05 needs to sort context rows, it must target the context section separately.
