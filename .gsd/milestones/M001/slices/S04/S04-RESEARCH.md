# S04 (Template Restructuring) — Research

**Date:** 2026-03-17

## Summary

S04 delivers GRP-01: "Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data." The S03 slice already injects section headers and no-data collapse via JavaScript post-enrichment (`injectSectionHeadersAndNoDataSummary` called from `markEnrichmentComplete`). S04 promotes this from JS-injected structure into the HTML template itself — the `_enrichment_slot.html` partial delivers three explicit section containers inside `.enrichment-details`, and enrichment.ts routes each provider row to the correct container at render time.

This is straightforward restructuring: the organizational concept already exists in JavaScript; we're moving its backbone into the server-rendered HTML. The key constraint is that `.enrichment-details` must remain as the outer expand/collapse container (chevron toggle depends on `nextElementSibling` adjacency), and all `data-*` attributes on `.ioc-card` must stay untouched. The template change, JS routing update, and post-enrichment simplification must be atomic — they cannot be deployed independently without breaking the section structure.

## Recommendation

Add three `<div class="enrichment-section">` containers inside `.enrichment-details` in `_enrichment_slot.html` — one each for context, reputation, and no-data. Each section gets a static `.provider-section-header` in the template. Then update `enrichment.ts` to route rows to the correct section container based on provider type and verdict. Simplify `injectSectionHeadersAndNoDataSummary()` in `row-factory.ts` to only create the no-data summary row (headers are now template-rendered). Remove the context-row-pinning logic from `sortDetailRows()` since context rows live in their own section.

Hide empty sections with CSS (`.enrichment-section:not(:has(.provider-detail-row))` or a JS class toggle) so sections without results don't show orphaned headers.

## Implementation Landscape

### Key Files

- `app/templates/partials/_enrichment_slot.html` (21 LOC) — Currently has a single `.enrichment-details` div. Needs three `.enrichment-section` children with static `.provider-section-header` elements. The `.spinner-wrapper`, `.chevron-toggle`, and `.enrichment-details` outer structure stay unchanged.

- `app/static/src/ts/modules/enrichment.ts` (~460 LOC) — Three changes needed:
  1. `renderEnrichmentResult()` context path (line ~233): change `detailsContainer` lookup from `slot.querySelector(".enrichment-details")` to `slot.querySelector(".enrichment-section--context")`.
  2. `renderEnrichmentResult()` verdict path (line ~307): route no-data/error verdicts to `.enrichment-section--no-data`, other verdicts to `.enrichment-section--reputation`.
  3. `sortDetailRows()` (line ~43): remove the context-row-pinning block (lines 64-69) — context rows are now in their own section. The sort only targets rows inside the reputation section container passed as `detailsContainer`.

- `app/static/src/ts/modules/row-factory.ts` (~490 LOC) — `injectSectionHeadersAndNoDataSummary()` (line ~437) simplifies significantly:
  - Remove section header insertion logic (headers are now in template).
  - Keep no-data summary row creation (count is only accurate post-enrichment).
  - Retarget the no-data row query to `.enrichment-section--no-data` container.
  - The no-data collapse toggle (`no-data-expanded` class) should be scoped to the no-data section container instead of the entire `.enrichment-details`.

- `app/static/src/input.css` — Add CSS for `.enrichment-section` containers. Handle empty-section hiding. The existing `.provider-section-header`, `.provider-row--no-data`, `.no-data-summary-row`, and `.no-data-expanded` rules may need minor scope adjustments.

### Build Order

**Build atomically.** Template + JS routing + post-enrichment logic must change together. The template alone breaks current JS (rows would append outside section containers); JS alone breaks without template sections to target. The natural decomposition is:

1. **T01 — Template restructuring + JS routing (atomic):** Modify `_enrichment_slot.html` to add three section containers. Update `enrichment.ts` to route rows to correct containers. Simplify `sortDetailRows` (remove context pinning). Update `injectSectionHeadersAndNoDataSummary` in `row-factory.ts` to remove header injection and retarget no-data logic. Add CSS for section containers.

2. **T02 — Verification and cleanup:** Run full E2E suite. Check `max-height: 600px` on `.enrichment-details.is-open` is sufficient with additional section wrapper divs (S03 flagged this). Remove dead code paths. Confirm empty sections are hidden. Run `grep` for innerHTML (SEC-08 gate).

### Verification Approach

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero results
- DOM inspection confirms: `.enrichment-section--reputation` contains verdict rows, `.enrichment-section--context` contains context rows, `.enrichment-section--no-data` contains no-data/error rows
- `document.querySelectorAll('.enrichment-section').length` per enrichment slot = 3
- `document.querySelectorAll('.provider-section-header').length` per enrichment slot = 3 (now template-static, not JS-injected)
- Chevron toggle still expands/collapses `.enrichment-details` — verify `nextElementSibling` adjacency preserved
- No-data summary row still shows count and toggles collapse
- Empty sections (e.g., no context providers for hash IOCs) are hidden

## Constraints

- **Chevron adjacency:** `wireExpandToggles()` reads `toggle.nextElementSibling` and checks for `.enrichment-details` class. The `.enrichment-details` container must remain the immediate next sibling of `.chevron-toggle`. Section containers go inside it, not around it.
- **`data-*` attribute contract:** `.ioc-card` root element carries `data-ioc-value`, `data-ioc-type`, `data-verdict` — no template change touches these. `_ioc_card.html` is not modified in this slice.
- **SEC-08:** All DOM construction must use `createElement + textContent`. Template-rendered HTML is safe (Jinja autoescaping). No `innerHTML` in TypeScript.
- **No new template variables:** S04 is restructuring, not new features. The Flask route context stays unchanged.
- **`.enrichment-slot--loaded`:** This class is added by JS on first result and gates chevron visibility via CSS. The section structure must not interfere with this.
- **`max-height: 600px`** on `.enrichment-details.is-open`: S03 forward intelligence flagged this. Adding three section wrapper divs with their own headers adds ~60px of chrome. May need to increase to 700-750px, or switch to a more flexible approach.

## Common Pitfalls

- **Duplicate section headers** — If `injectSectionHeadersAndNoDataSummary()` is not updated simultaneously with the template change, it will inject JS headers on top of template headers, producing duplicates. These must be changed atomically.
- **`sortDetailRows` operates on wrong container** — Currently targets `slot.querySelector(".enrichment-details")` which would now contain section wrappers, not raw rows. Must be updated to target `.enrichment-section--reputation` specifically, or the sort will silently do nothing (no `.provider-detail-row` children at top level).
- **Empty section with visible header** — If no context providers return results (e.g., for hash IOCs), the "Infrastructure Context" header sits alone with no rows. CSS must hide sections that have no provider rows. `:has()` selector (96%+ support) is the cleanest approach: `.enrichment-section:not(:has(.provider-detail-row)) { display: none; }`.
- **No-data routing at render time vs post-enrichment** — Currently `createDetailRow` adds `.provider-row--no-data` class, and CSS hides these rows. With three sections, no-data rows route directly to `.enrichment-section--no-data` at render time. The CSS `display: none` on `.provider-row--no-data` may conflict with the section-based approach — the rows should be visible within their section, just the section itself is collapsed. Need to adjust the CSS to not hide `.provider-row--no-data` when it's inside `.enrichment-section--no-data`.
