---
id: S03
parent: M001
milestone: M001
provides:
  - Enlarged verdict badge (VIS-01) — 0.875rem/700 font dominates IOC card headers
  - Verdict micro-bar replacing consensus badge text (VIS-02) — proportional colored segments for malicious/suspicious/clean/no_data
  - Category section headers (VIS-03) — "Reputation" and "Infrastructure Context" labels injected post-enrichment
  - No-data collapse (GRP-02) — no_data/error rows hidden by default with clickable count summary and keyboard a11y
requires:
  - slice: S02
    provides: row-factory.ts DOM builders, enrichment.ts orchestrator, verdict-compute.ts VerdictEntry type
affects:
  - S04
key_files:
  - app/static/src/input.css
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/verdict-compute.ts
key_decisions:
  - Kept .consensus-badge CSS as dead CSS for safe rollback; only removed DOM creation
  - Post-enrichment injection via markEnrichmentComplete() for section headers — avoids misplacement during live sorting
  - CSS-driven no-data toggle: .no-data-expanded class on container controls child visibility via CSS; aria-expanded on trigger tracks state
patterns_established:
  - Micro-bar pattern: flex container with percentage-width segment divs, title attribute for accessibility, zero-count segments skipped
  - Visual hierarchy via font-size gap: summary verdict-label 0.875rem/700 vs provider verdict-badge 0.72rem/600
  - Post-enrichment DOM injection pattern: non-.provider-detail-row elements inserted after sortDetailRows() finalizes order, immune to re-sorting
  - Toggle pattern: class on container controls child visibility via CSS; aria-expanded on trigger tracks state
observability_surfaces:
  - document.querySelectorAll('.verdict-micro-bar') — micro-bar count per page
  - .verdict-micro-bar[title] attribute — exact verdict counts accessible on hover
  - document.querySelectorAll('.provider-section-header') — section header count per card
  - document.querySelectorAll('.no-data-summary-row') — collapse summary presence
  - .no-data-summary-row[aria-expanded] — collapse toggle state ("true"/"false")
  - document.querySelectorAll('.provider-row--no-data').length — hidden no-data row count
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md
duration: ~45m across 2 tasks
verification_result: passed
completed_at: 2026-03-17
---

# S03: Visual Redesign

**Verdict badge prominence, micro-bar replacing consensus text, category section headers, and no-data collapse — delivering the visual hierarchy for provider results**

## What Happened

Two tasks delivered four visual requirements confined to row-factory.ts and input.css:

**T01 (VIS-01 + VIS-02):** Enlarged `.verdict-label` from 0.7rem/600 to 0.875rem/700 with larger padding, making the worst verdict the dominant scan target in each IOC card header. Replaced the `[n/m]` consensus badge text span with a proportional `.verdict-micro-bar` — a flex container where colored segments represent the distribution of malicious/suspicious/clean/no_data verdicts. Added `computeVerdictCounts()` helper in row-factory.ts. Zero-count segments are skipped; `Math.max(1, total)` guards division-by-zero. Dead `.consensus-badge` CSS retained for rollback; DOM creation and imports removed.

**T02 (VIS-03 + GRP-02):** Added `injectSectionHeadersAndNoDataSummary()` to row-factory.ts, called from `markEnrichmentComplete()` in enrichment.ts after all results arrive and sorting finalizes. This function scans the final DOM order and inserts "Reputation" and "Infrastructure Context" section headers before each category's first row. No-data/error provider rows get a `.provider-row--no-data` class (hidden by default via CSS). A clickable `.no-data-summary-row` shows the count and toggles a `.no-data-expanded` class on the container. Keyboard accessibility (Enter/Space) and `aria-expanded` state tracking are wired. All edge cases handled: zero no-data rows (no summary), zero context rows (no header), zero verdict rows (no header), empty container (early return).

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle succeeds (194.9KB) ✅
- `make css` — Tailwind rebuild succeeds ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case) ✅
- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — zero results (safe removal confirmed) ✅
- `grep -n "consensusBadge" row-factory.ts` — zero results (import cleaned up) ✅
- `grep -n "injectSectionHeaders" enrichment.ts` — confirms import (line 26) and call (line 185) ✅
- All 24 E2E-locked CSS selectors preserved — no class renames ✅

## Requirements Advanced

- VIS-01 — `.verdict-label` CSS enlarged to 0.875rem/700 with 0.25rem×0.75rem padding; visually dominant over provider-row `.verdict-badge` (0.72rem/600). Awaits live browser UAT for human visual confirmation.
- VIS-02 — Consensus badge DOM creation replaced by `.verdict-micro-bar` with proportional colored segments. Title attribute encodes exact counts. Awaits live browser UAT.
- VIS-03 — "Reputation" and "Infrastructure Context" section headers injected post-enrichment via `injectSectionHeadersAndNoDataSummary()`. Awaits live browser UAT.
- GRP-02 — No-data/error rows hidden by default; clickable `.no-data-summary-row` toggles visibility with `aria-expanded` and keyboard a11y. Awaits live browser UAT.

## Requirements Validated

- none — all four requirements advanced but require live runtime UAT for visual confirmation (per plan's proof level: "human/UAT required: yes")

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Added keyboard accessibility (Enter/Space handlers) on no-data summary row — not explicitly in plan but necessary for a11y compliance since element has `role="button"`
- Fixed stray duplicate line at end of row-factory.ts (lines 405-406) from a prior interrupted edit session — required for typecheck to pass

## Known Limitations

- Visual hierarchy (VIS-01) is CSS-only — the font-size gap between verdict-label and verdict-badge creates dominance, but human eye confirmation of the specific gap is needed in live browser
- Micro-bar proportions are correct mathematically but perceptual effectiveness depends on real data distributions — edge cases like 1 malicious among 13 clean may produce a thin segment
- Dead `.consensus-badge` CSS remains in input.css — zero cost but should be cleaned in a future pass
- Section headers are injected post-enrichment via JS — S04 will promote these to server-rendered template elements (per D004/D005)
- `computeConsensus` and `consensusBadgeClass` exports remain in verdict-compute.ts for API stability — no consumers exist but exports preserved

## Follow-ups

- S04 will replace JS-injected section headers with server-rendered template structure, simplifying the JS to row-routing only
- Dead `.consensus-badge` CSS can be removed once rollback period passes
- Unused `computeConsensus`/`consensusBadgeClass` exports in verdict-compute.ts can be removed after S04 confirms the micro-bar pattern is stable

## Files Created/Modified

- `app/static/src/input.css` — Enlarged `.verdict-label` (VIS-01); added `.verdict-micro-bar`, `.micro-bar-segment--*` (VIS-02); added `.provider-section-header`, `.provider-row--no-data`, `.no-data-expanded`, `.no-data-summary-row` (VIS-03, GRP-02)
- `app/static/src/ts/modules/row-factory.ts` — Added `computeVerdictCounts()` helper and micro-bar creation in `updateSummaryRow()` (VIS-02); added `.provider-row--no-data` class in `createDetailRow()`; exported `createSectionHeader()` and `injectSectionHeadersAndNoDataSummary()` (VIS-03, GRP-02)
- `app/static/src/ts/modules/enrichment.ts` — Imported and called `injectSectionHeadersAndNoDataSummary` in `markEnrichmentComplete()` (VIS-03, GRP-02)
- `app/static/src/ts/modules/verdict-compute.ts` — Added API stability comment to legacy exports
- `app/static/dist/main.js` — Rebuilt bundle
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- Section headers ("Reputation", "Infrastructure Context") are currently injected post-enrichment by `injectSectionHeadersAndNoDataSummary()` in row-factory.ts, called from `markEnrichmentComplete()` in enrichment.ts. S04 plans to replace these with server-rendered template containers — when doing so, remove or refactor the JS injection function to avoid duplicate headers.
- The no-data collapse feature creates a `.no-data-summary-row` inside `.enrichment-section--no-data` — S04's template restructuring needs to preserve this container class or update the JS that targets it.
- `computeVerdictCounts()` is a private function in row-factory.ts that could be useful for S05's context fields if verdict distribution is needed elsewhere.

### What's fragile
- The post-enrichment injection timing depends on `markEnrichmentComplete()` being called exactly once per enrichment slot after all results arrive — if the completion signal changes or fires multiple times, section headers could duplicate. S04's template promotion eliminates this fragility.
- `.provider-row--no-data` class is applied in `createDetailRow()` based on verdict being `no_data` or `error` — if new verdict types are added, the `isNoData` check needs updating.

### Authoritative diagnostics
- `document.querySelectorAll('.verdict-micro-bar')` — confirms micro-bars rendered; count should equal number of IOC cards with results
- `.verdict-micro-bar[title]` hover tooltip — shows exact verdict distribution per card (e.g. "2 malicious, 0 suspicious, 3 clean, 1 no data")
- `document.querySelectorAll('.provider-section-header')` — confirms section headers injected; check `data-section-label` attribute for category name
- `document.querySelector('.no-data-summary-row')?.getAttribute('aria-expanded')` — confirms toggle state tracking

### What assumptions changed
- No assumptions changed — implementation matched plan. The keyboard a11y addition was additive, not a plan deviation.
