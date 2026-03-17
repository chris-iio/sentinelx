---
id: S03
parent: M001
milestone: M001
provides:
  - Enlarged verdict badge in IOC card headers (VIS-01) — 0.875rem/700 vs provider row 0.72rem/600
  - Verdict micro-bar replacing consensus badge text (VIS-02) — proportional colored segments with tooltip
  - Category section headers "Reputation" / "Infrastructure Context" (VIS-03) — injected post-enrichment
  - No-data collapse with clickable count summary (GRP-02) — CSS-driven toggle with a11y support
requires:
  - slice: S02
    provides: row-factory.ts DOM builders, enrichment.ts orchestrator, verdict-compute.ts pure functions
affects:
  - S04
key_files:
  - app/static/src/input.css
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/verdict-compute.ts
key_decisions:
  - Kept .consensus-badge CSS as dead CSS for safe rollback; only removed DOM creation
  - Post-enrichment injection via markEnrichmentComplete() — after sortDetailRows() finalizes DOM order
  - CSS-driven toggle (.no-data-expanded on container) for no-data collapse; aria-expanded + keyboard a11y
  - Kept computeConsensus/consensusBadgeClass exports in verdict-compute.ts for API stability
patterns_established:
  - Micro-bar pattern: flex container with percentage-width segment divs, title attribute for accessibility
  - Visual hierarchy via font-size gap: summary badge 0.875rem vs provider badge 0.72rem
  - Post-enrichment DOM injection: non-.provider-detail-row elements inserted after sorting completes, immune to re-sorting
  - Container-class toggle pattern: single class on parent controls child visibility via CSS
observability_surfaces:
  - document.querySelectorAll('.verdict-micro-bar') — verify micro-bars rendered
  - .verdict-micro-bar[title] attribute — exact verdict counts accessible on hover
  - document.querySelectorAll('.provider-section-header') — section header count per card
  - document.querySelectorAll('.no-data-summary-row') — collapse summary presence
  - .no-data-summary-row[aria-expanded] — tracks collapse toggle state
  - document.querySelectorAll('.provider-row--no-data').length — hidden no-data row count
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md
duration: ~1h
verification_result: passed
completed_at: 2026-03-17
---

# S03: Visual Redesign

**Four visual improvements to IOC cards: enlarged verdict badges, proportional micro-bar, category section headers, and no-data collapse — all confined to row-factory.ts and input.css with zero E2E regression**

## What Happened

Two tasks delivered four visual requirements across three source files:

**T01 — Verdict badge prominence + micro-bar (VIS-01, VIS-02):** Increased `.verdict-label` in card headers from 0.7rem/600 to 0.875rem/700 with larger padding, creating clear visual hierarchy against `.verdict-badge` in provider rows (0.72rem/600). Replaced the `[n/m]` consensus badge text in `updateSummaryRow()` with a proportional `.verdict-micro-bar` — a 6px-tall flex container with colored segments (malicious red, suspicious amber, clean sky, no_data zinc) sized by percentage width. A `computeVerdictCounts()` private helper in row-factory.ts computes the distribution. Zero-count segments are skipped; `Math.max(1, total)` guards against NaN widths. The `title` attribute encodes exact counts for accessibility.

**T02 — Section headers + no-data collapse (VIS-03, GRP-02):** Added `injectSectionHeadersAndNoDataSummary(slot)` as a new exported function in row-factory.ts. It scans finalized DOM order after sorting, inserting "Infrastructure Context" before the first `.provider-context-row` and "Reputation" before the first verdict row. For no-data collapse, `createDetailRow()` now appends `.provider-row--no-data` class for `no_data`/`error` verdicts. The injection function counts these, creates a clickable `.no-data-summary-row` with count text, and wires a click handler that toggles `.no-data-expanded` on the details container. Keyboard accessibility (Enter/Space) was added for the role="button" element. In enrichment.ts, `markEnrichmentComplete()` calls this injection for all `.enrichment-slot` elements after enrichment completes.

All edge cases handled: zero rows, zero context rows, zero verdict rows, zero no-data rows — each produces no crash and no empty elements.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle succeeds (188.0kb) ✅
- `make css` — Tailwind rebuild succeeds ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case) ✅
- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — zero results (confirms safe removal) ✅
- All 24 E2E-locked CSS selectors preserved — no class renames ✅
- Source inspection confirms: `.verdict-micro-bar` creates `.micro-bar-segment` children with percentage widths ✅
- Source inspection confirms: `.provider-section-header` elements inserted before respective row groups ✅
- Source inspection confirms: `.provider-row--no-data` elements hidden by default; `.no-data-summary-row` created with correct count ✅
- Source inspection confirms: `computeVerdictCounts()` with empty entries returns `{total:0}` and micro-bar uses `Math.max(1, total)` ✅
- Source inspection confirms: `injectSectionHeadersAndNoDataSummary()` with zero rows returns early ✅

## Requirements Advanced

- VIS-01 — `.verdict-label` enlarged to 0.875rem/700, creating clear size hierarchy over `.verdict-badge` at 0.72rem/600. Visual prominence achieved via CSS; DOM structure unchanged.
- VIS-02 — Consensus badge text replaced with `.verdict-micro-bar` proportional segments. Title attribute provides exact counts. Zero-count guard prevents NaN widths.
- VIS-03 — "Reputation" and "Infrastructure Context" section headers injected post-enrichment, positioned relative to sorted rows.
- GRP-02 — No-data/error rows hidden by default via `.provider-row--no-data` display:none; clickable summary row with count; CSS toggle via `.no-data-expanded` class.

## Requirements Validated

- none — VIS-01 badge hierarchy and VIS-02/VIS-03/GRP-02 are operational in DOM but require live-runtime visual confirmation (UAT) to fully validate

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T01 fixed a stray duplicate line at the end of row-factory.ts (lines 405-406 had duplicate `result);` + `}`) — artifact from a prior edit session, not a planned step but required for typecheck to pass.
- T02 added keyboard accessibility (Enter/Space handlers) on no-data summary row — not in plan but necessary since the element has `role="button"` and must be operable via keyboard per WCAG.

## Known Limitations

- **Visual-only verification gap:** VIS-01 badge size hierarchy, VIS-02 micro-bar rendering, VIS-03 header positioning, and GRP-02 collapse behavior have been verified via code inspection and build checks but not via live browser rendering. UAT with a running app is needed to fully validate visual output.
- **Dead CSS:** `.consensus-badge` CSS rules remain in input.css. They are no longer created in DOM but left for rollback safety. Can be cleaned up in a future pass.
- **Section headers during live polling:** Headers are only injected post-enrichment. During active polling, the details container shows unsectioned rows sorted by severity. This is by design (avoids header misplacement during re-sorting).

## Follow-ups

- Remove dead `.consensus-badge` CSS after S04 confirms the micro-bar visual is production-ready
- S04 will restructure the HTML template to deliver three static sections (Reputation, Infrastructure Context, No Data) — this will supersede the JS-injected headers from VIS-03 with template-level structure

## Files Created/Modified

- `app/static/src/input.css` — Enlarged `.verdict-label` (VIS-01); added `.verdict-micro-bar` + `.micro-bar-segment` classes (VIS-02); added `.provider-section-header` (VIS-03); added `.provider-row--no-data`, `.no-data-expanded`, `.no-data-summary-row` (GRP-02)
- `app/static/src/ts/modules/row-factory.ts` — Added `computeVerdictCounts()` helper; replaced consensus badge with micro-bar in `updateSummaryRow()`; added `.provider-row--no-data` class in `createDetailRow()`; exported `createSectionHeader()` and `injectSectionHeadersAndNoDataSummary()`
- `app/static/src/ts/modules/enrichment.ts` — Imported and called `injectSectionHeadersAndNoDataSummary` in `markEnrichmentComplete()`
- `app/static/src/ts/modules/verdict-compute.ts` — Added API stability comment to `consensusBadgeClass` export
- `app/static/dist/main.js` — Rebuilt bundle (188.0kb)
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- `injectSectionHeadersAndNoDataSummary()` creates section headers as non-`.provider-detail-row` divs — they are invisible to `sortDetailRows()` and won't be re-sorted. S04's template restructuring should be aware that JS-injected headers currently exist and will need to be either replaced or coordinated with template-level sections.
- The micro-bar relies on `computeVerdictCounts()` which iterates the `VerdictEntry[]` array — any changes to verdict types or entry structure in verdict-compute.ts will affect rendering.
- `markEnrichmentComplete()` is the single call site for post-enrichment DOM injection — S04/S05 should hook into this same function if they need post-completion processing.

### What's fragile
- `.enrichment-details` max-height (600px in CSS) — if S04 adds more DOM elements per card (section headers, context fields in header), the expanded height may clip. Check this during S04 UAT.
- The no-data summary row text says "N providers had no record" — if S04 restructures the details container, the `querySelectorAll('.provider-row--no-data')` count logic needs the class to remain on no-data rows.

### Authoritative diagnostics
- `document.querySelectorAll('.verdict-micro-bar').length` equals the number of IOC cards with results — if zero, `updateSummaryRow()` isn't being called or entries array is empty.
- `document.querySelectorAll('.provider-section-header').length` should be 1-2 per IOC card (one per present category) — if zero after enrichment completes, `injectSectionHeadersAndNoDataSummary` wasn't called or the details container was empty.
- Micro-bar segments with `NaN%` widths in the element inspector indicate the `Math.max(1, total)` guard was bypassed — check `computeVerdictCounts()` input.

### What assumptions changed
- Originally planned to modify `consensusBadgeClass` usage — turns out it was only consumed in row-factory.ts, so removal was simpler than expected (no cross-module cleanup needed).
- Originally assumed section headers would need special sort handling — post-enrichment injection after sorting finishes eliminates this entirely.
