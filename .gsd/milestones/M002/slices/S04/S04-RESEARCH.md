# S04: Functionality integration + polish — Research

**Date:** 2026-03-18

## Summary

S04 is primarily a verification and polish slice, not a construction slice. S01–S03 preserved all functional wiring (D015: no selector renames) — export, filter, dashboard, sorting, progress bar, and warning banners all work against the current DOM structure without code changes. The 36 E2E tests pass as of S03 completion.

The work divides into three streams: (1) integration verification — methodically prove each R008 sub-feature works end-to-end, (2) security audit — verify R009 contracts (CSP, CSRF, SEC-08 textContent-only), and (3) visual polish — consistent spacing, transitions, hover states, and a pass through the S03 UAT script. No new TypeScript functions, no new template partials, no architectural decisions.

## Recommendation

Run integration verification first (T01) to confirm the functional pipeline is intact, then security audit (T02) to verify compliance contracts, then visual polish pass (T03) for CSS refinement and any spacing/transition adjustments discovered during manual review. The first two tasks are purely diagnostic — they produce evidence, not code changes. The third task may produce CSS edits if polish issues are found.

## Implementation Landscape

### Key Files

- `app/static/src/ts/modules/export.ts` — JSON/CSV export reads from `allResults[]` in enrichment.ts (DOM-independent); `copyAllIOCs()` queries `.ioc-card[data-ioc-value]` (preserved by D015). **No changes expected.**
- `app/static/src/ts/modules/filter.ts` — Reads `data-verdict`, `data-ioc-type`, `data-ioc-value` from `.ioc-card` elements; dashboard badge click reads `.verdict-kpi-card[data-verdict]`. **No changes expected.**
- `app/static/src/ts/modules/cards.ts` — `updateDashboardCounts()` queries `.ioc-card` + `[data-verdict-count]`; `sortCardsBySeverity()` reorders `.ioc-card` children in `#ioc-cards-grid`. **No changes expected.**
- `app/static/src/ts/modules/enrichment.ts` — Owns polling loop, progress bar updates (`#enrich-progress-fill`, `#enrich-progress-text`), warning banner (`#enrich-warning`), export button wiring (`#export-btn`, `#export-dropdown`), `markEnrichmentComplete()`. **No changes expected.**
- `app/static/src/ts/modules/clipboard.ts` — Binds `.copy-btn` with `data-value` at init. **No changes expected.**
- `app/static/src/ts/modules/row-factory.ts` — All DOM builders; `injectSectionHeadersAndNoDataSummary()` and `injectDetailLink()` (via enrichment.ts). **No changes expected.**
- `app/templates/results.html` — Orchestrates all partials; contains progress bar, export group, warning banner. **No changes expected.**
- `app/templates/partials/_verdict_dashboard.html` — 5 KPI cards with `data-verdict` + `data-verdict-count`; provider coverage row. Dashboard-click-to-filter wired by `filter.ts`. **No changes expected.**
- `app/templates/partials/_filter_bar.html` — Verdict buttons (`data-filter-verdict`), type pills (`data-filter-type`), search input (`#filter-search-input`). **No changes expected.**
- `app/templates/partials/_ioc_card.html` — `.ioc-card` root with contract attributes; copy button, detail link. **No changes expected.**
- `app/__init__.py` — CSP header (line 71), CSRF protection (CSRFProtect). **Read-only for security audit.**
- `app/templates/base.html` — `<meta name="csrf-token">` (line 8). **Read-only for security audit.**
- `app/static/src/input.css` — Design tokens, all component styles. **May receive minor CSS adjustments during visual polish.**
- `.gsd/milestones/M002/slices/S03/S03-UAT.md` — UAT script for S03; S04 should execute during visual polish pass.

### Build Order

1. **T01 — Integration verification (R008):** Verify every sub-feature of R008 works against the current DOM. This is diagnostic — it either confirms the pipeline is intact or surfaces specific breakages that need code fixes before proceeding. Covers: export (JSON/CSV/clipboard), dashboard-click-to-filter, verdict sorting, progress bar, warning banners, copy buttons, detail links. Evidence: documented verification matrix with commands/checks.

2. **T02 — Security audit (R009):** Verify CSP headers present, CSRF protection active, no innerHTML in any TS module, all DOM construction uses createElement+textContent+setAttribute. Verify `.style.xxx` assignments (enrichment.ts, filter.ts) are DOM property access not inline `<style>` injection. Evidence: grep-based audit results documented.

3. **T03 — Visual polish + build verification (R010):** Run S03 UAT script items. CSS consistency pass — verify spacing, transitions, hover states. Verify `--bg-hover` token is defined and wired (already confirmed: line 53 of input.css). Check production build size (currently 26.6KB minified — well under concern threshold). Rebuild CSS+JS and run full E2E suite as final gate.

### Verification Approach

**Integration (T01):**
- `make typecheck` — 0 errors
- `make css && make js-dev` — successful build
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36/36 pass
- Export: verify `allResults` accumulation path in enrichment.ts → export.ts wiring (code review, no runtime test needed since export reads from array not DOM)
- Dashboard click-to-filter: verify `filter.ts` init() binds `.verdict-kpi-card[data-verdict]` click → `applyFilter()` — DOM elements present in `_verdict_dashboard.html`
- Sort: verify `cards.ts` `sortCardsBySeverity()` reads `data-verdict` from `.ioc-card` children of `#ioc-cards-grid`
- Progress bar: verify `#enrich-progress-fill` and `#enrich-progress-text` elements present in `results.html`
- Warning banner: verify `#enrich-warning` element present in `results.html`
- Copy: verify `.copy-btn` with `data-value` present in `_ioc_card.html`

**Security (T02):**
- `grep -c 'innerHTML' app/static/src/ts/modules/*.ts` — 0 in code (comments only)
- `grep -n 'Content-Security-Policy' app/__init__.py` — header present
- `grep -n 'csrf' app/__init__.py app/templates/base.html` — CSRF protection active
- `grep -rn 'document\.write\|eval(' app/static/src/ts/` — 0 matches
- Review all `.style.xxx` assignments — DOM property access, not inline style element injection

**Polish (T03):**
- Visual review of key states: empty state, pre-enrichment, enriching, enriched, expanded panel, filtered view
- `make js` production build — verify size ≤ 30KB
- `make css` + `make js-dev` rebuild
- `pytest tests/e2e/ -q` — full E2E suite passes
- S03 UAT items: hover state visible, chevron rotation smooth, detail link present after completion

## Constraints

- All DOM construction must use `createElement` + `textContent` (SEC-08) — no innerHTML
- CSP `script-src 'self'` prohibits inline scripts; `.style.xxx` property access is fine
- Production build target: ≤ ~30KB minified JS (currently 26.6KB)
- No selector renames in S04 (D015) — preserve all existing class names and data attributes

## Common Pitfalls

- **Assuming functionality is broken** — S01–S03 were careful to preserve all wiring. The default assumption should be "this works" with verification proving it, not "this needs fixing." Don't refactor working code during a verification slice.
- **CSS polish breaking existing layout** — Any input.css changes in T03 must be followed by full CSS rebuild + visual check. Small CSS tweaks can cascade into unintended layout shifts.
- **Forgetting to rebuild dist files** — Final verification must run against freshly built `dist/style.css` and `dist/main.js`, not stale artifacts.
