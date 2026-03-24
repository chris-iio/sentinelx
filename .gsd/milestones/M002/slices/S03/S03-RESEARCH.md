# S03: Inline expand + progressive disclosure — Research

**Date:** 2026-03-18
**Depth:** Light research — the expand/collapse mechanism is 90% wired from S01/S02. This slice is wiring the remaining interaction model and adding the expanded-view detail link.

## Summary

The inline expand mechanism is almost entirely built. `enrichment.ts` already has `wireExpandToggles()` which binds click handlers on `.chevron-toggle` buttons, toggling `.is-open` on the sibling `.enrichment-details` container. CSS already transitions `max-height: 0` → `max-height: 750px` with `ease-out-quart`. The three section containers (context, reputation, no-data) are server-rendered in `_enrichment_slot.html` and populated by `row-factory.ts` during enrichment. Empty sections auto-hide via `:not(:has(.provider-detail-row))`. The no-data collapse with summary row is already wired by `injectSectionHeadersAndNoDataSummary()`.

What's missing is small but user-facing: (1) R004 says "clicking an IOC row" should expand — currently only the tiny chevron button toggles; (2) the detail page link must be available from the expanded view per D012; (3) the `max-height: 750px` hard cap could clip IOCs with 14+ providers and rich context fields; (4) the expanded panel needs visual refinement to feel like a polished production tool.

Primary recommendation: Make the summary row (`.ioc-summary-row`) the click target for expand/collapse instead of the separate chevron — this gives a larger touch target and natural "click the summary to see details" affordance. Keep the chevron as a visual indicator but make the summary row the interaction surface. Add a "View full detail →" link inside the expanded panel. Fix the `max-height` clipping issue.

## Recommendation

**Approach: Summary-row-as-toggle + detail link injection + CSS polish**

1. **Make `.ioc-summary-row` the expand toggle.** Wire click on the summary row to toggle `.is-open` on the sibling `.enrichment-details`. The chevron remains as a visual rotation indicator but moves into the summary row. This is more intuitive than clicking a separate button — the summary row is the natural "see more" affordance.

2. **Move or duplicate chevron into summary row.** Currently the chevron button sits between the summary row and details container. Restructure: the chevron icon becomes part of the summary row (leftmost or rightmost). The separate `.chevron-toggle` button becomes the summary row itself.

3. **Add detail page link in expanded view.** Inject a footer row at the bottom of `.enrichment-details` with "View full detail →" linking to `/detail/<type>/<value>`. The href pattern is already in the card header's `.btn-detail` — the value can be read from the parent `.ioc-card[data-ioc-type][data-ioc-value]`.

4. **Fix max-height clipping.** Replace `max-height: 750px` with a larger value or use a JS-measured approach. Given that the no-data section collapses by default, 750px is likely sufficient for most cases, but with 14 providers and rich context, it could clip. A safe approach: increase to `2000px` (generous upper bound) — the transition timing is proportional to actual content height via `ease-out-quart`, so excess max-height just means a slightly faster perceived animation, not visible delay.

5. **CSS polish.** Add subtle background tint and left-border accent on `.enrichment-details.is-open` to visually separate the expanded panel from the row above. Ensure the expanded state has a clean bottom edge.

## Implementation Landscape

### Key Files

- `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()` (lines ~273-285) is the expand wiring entry point. Needs refactoring to wire on `.ioc-summary-row` instead of `.chevron-toggle`, plus inject the detail link into `.enrichment-details`.
- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()` (lines ~232-247) and `updateSummaryRow()` (lines ~255-316) build the summary row. The chevron icon needs to move into the summary row structure.
- `app/templates/partials/_enrichment_slot.html` — Template has the `.chevron-toggle` button between summary row and details container. Restructure: move the chevron into the summary row or remove it from the template and let JS inject it into the summary row.
- `app/static/src/input.css` — `.chevron-toggle` styles (line ~1326), `.enrichment-details` expand styles (line ~1356), `.ioc-summary-row` styles (line ~1215). CSS changes for: summary row cursor/hover, chevron repositioned, max-height fix, expanded panel visual treatment.
- `app/templates/partials/_ioc_card.html` — Reference only. The `.btn-detail` href pattern (`url_for('main.ioc_detail', ...)`) is here — S03 needs to replicate this pattern in the expanded view via JS using `data-ioc-type` and `data-ioc-value` from the `.ioc-card` root.

### Build Order

**Task 1: Restructure expand interaction model (TS + template)**
- Modify `_enrichment_slot.html`: remove standalone `.chevron-toggle` button. The chevron icon will be injected into the summary row by JS.
- Modify `row-factory.ts` `updateSummaryRow()`: append a chevron icon element to the summary row. Add `role="button"`, `tabindex="0"`, `aria-expanded`, `cursor: pointer` via CSS class.
- Modify `enrichment.ts` `wireExpandToggles()`: wire click on `.ioc-summary-row` instead of `.chevron-toggle`. Toggle `.is-open` on `.enrichment-details` (same logic). Toggle `.is-open` on the summary row itself (for chevron rotation). Handle keyboard Enter/Space.
- **Why first:** This is the core interaction change. Everything else builds on it.

**Task 2: Add detail page link in expanded view + CSS polish**
- In `enrichment.ts` or `row-factory.ts`: after enrichment completes (in `markEnrichmentComplete()` or lazily on first expand), inject a footer element into `.enrichment-details` with a "View full detail →" link. Read `data-ioc-type` and `data-ioc-value` from the ancestor `.ioc-card` to construct the href: `/detail/${iocType}/${encodeURIComponent(iocValue)}`.
- CSS changes: fix `max-height` (increase to 2000px or use `max-height: none` with a separate height animation technique), add summary row hover state, add expanded panel subtle background tint, ensure `.chevron-icon` rotation works when the `.is-open` class is on the summary row instead of `.chevron-toggle`.
- **Why second:** Depends on the interaction model from Task 1. The detail link is additive — doesn't affect the expand mechanism.

### Verification Approach

- `make typecheck` — zero errors (no `any` types introduced)
- `make css` — exit 0
- `make js-dev` — exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 tests pass (no regression)
- **Manual checks** (documented for human UAT):
  - Click summary row → enrichment details expand with smooth animation
  - Click summary row again → details collapse
  - Chevron rotates on expand/collapse
  - Multiple rows can be independently expanded (no accordion collapse-others)
  - "View full detail →" link visible in expanded view, navigates to correct detail page
  - Keyboard: Tab to summary row, Enter/Space toggles expand
  - Pre-enrichment: summary row not present, no expand possible (correct — nothing to show)
  - Post-enrichment: `.enrichment-slot--loaded` present, expand works

## Constraints

- **SEC-08:** All DOM construction must use `createElement` + `textContent` — no `innerHTML`. The detail link `href` must be set via `setAttribute`, not string interpolation into HTML.
- **CSP:** No inline styles via JS — the `max-height` animation is already CSS-driven. The only inline style currently used is `seg.style.width` for micro-bar segments (already established pattern).
- **No new dependencies.** This is pure DOM wiring + CSS.
- **D015:** Preserve `.ioc-card`, `.enrichment-slot`, `.enrichment-details` selector names — no renaming.
- **`.enrichment-slot--loaded` gating:** The expand toggle must not be accessible before enrichment loads. Current CSS hides `.chevron-toggle` when `--loaded` is absent. The new summary-row-as-toggle needs the same guard — either hide the summary row itself or make it non-interactive when `--loaded` is absent. Since `updateSummaryRow()` only creates the summary row when results arrive, and it always follows `slot.classList.add("enrichment-slot--loaded")`, the guard is implicit: no summary row exists until `--loaded` is set.

## Common Pitfalls

- **`max-height` transition timing.** With `max-height: 2000px` and actual content height of 300px, the `ease-out-quart` transition will feel faster than expected because the browser computes the transition rate against the full 2000px range. This is actually desirable — the expand feels snappy. The collapse direction will have a brief delay before visible shrinking starts. If this bothers users, consider using `500ms` for collapse vs `250ms` for expand.
- **Chevron state sync.** If the chevron icon is inside the summary row, the `.is-open` class for rotation must be on an ancestor that CSS can select. The cleanest approach: put `.is-open` on the `.enrichment-slot` itself (or keep it on `.enrichment-details` and use `~` or parent-based selector). Since CSS doesn't have a parent selector, the simplest pattern is: toggle `.is-open` on both the summary row and the details container. Then `.ioc-summary-row.is-open .chevron-icon { transform: rotate(90deg); }`.
- **Detail link URL encoding.** IOC values can contain special characters (URLs with query params, IPs with colons for IPv6). The href must use `encodeURIComponent()` on the IOC value. The Flask `url_for()` in the template handles this automatically, but the JS version needs explicit encoding.

## Open Risks

- **E2E test stability.** The 36 existing tests don't test expand/collapse on the results page, so there's no direct regression risk. However, removing the `.chevron-toggle` button from the template changes the DOM structure — any future test that queries for `.chevron-toggle` would break. Since S05 updates E2E selectors anyway, this is acceptable.
- **Content clipping with max-height.** If a provider returns extremely rich context (many tags, long lists), even 2000px might clip. This is a long-tail edge case — the no-data collapse reduces visible content significantly. Monitor during UAT.
