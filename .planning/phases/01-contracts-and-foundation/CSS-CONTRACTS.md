# CSS Contracts — v1.1 Results Page Redesign

> DO NOT RENAME any class, ID, or data-attribute listed in this file without updating
> every consumer listed in its row AND re-running the full E2E suite (`pytest tests/ -m e2e --tb=short`).
>
> This catalog is the single source of truth for what is locked. Inline comments in source files
> reference this file. Created during Phase 1; enforced from Phase 2 onward.

---

## E2E-Locked Selectors (DO NOT RENAME)

All selectors in this table are directly queried by Playwright in `tests/e2e/pages/results_page.py`
or in inline locator calls in individual test files. Renaming any of these breaks E2E tests
immediately (Playwright reports "locator not found" rather than a compile-time error).

| Selector | results_page.py Method | Source File | Notes |
|----------|------------------------|-------------|-------|
| `.mode-indicator` | `mode_indicator` | `results.html:7` | Top-level locator |
| `.results-summary .ioc-count` | `ioc_count` | `results.html:16,20` | Top-level locator |
| `a.back-link` | `back_link` | `results.html:35` | Top-level locator |
| `.empty-state` | `no_results_box` | `_empty_state.html` | Top-level locator |
| `.empty-state-body` | `no_results_hint` | `_empty_state.html` | Top-level locator |
| `.ioc-card` | `ioc_cards`, `cards_for_type` | `_ioc_card.html:1` | Root card element |
| `.ioc-card[data-ioc-type="..."]` | `cards_for_type()` | `_ioc_card.html:1` | Compound selector |
| `.ioc-type-badge` | `type_badge()` | `_ioc_card.html:4` | Type badge in card header |
| `.ioc-value` | `ioc_values()` | `_ioc_card.html:3` | IOC value display |
| `.ioc-original` | `ioc_originals()` | `_ioc_card.html:23` | Original (pre-normalization) value |
| `.copy-btn` | `copy_buttons()` | `_ioc_card.html:8` | Copy button |
| `.verdict-label` | `verdict_labels()` | `_ioc_card.html:5` | Verdict label in card header |
| `#verdict-dashboard` | `verdict_dashboard` | `_verdict_dashboard.html:1` | ID selector |
| `.filter-bar-wrapper` | `filter_bar` | `_filter_bar.html:2` | Filter bar container |
| `.filter-verdict-buttons .filter-btn` | `filter_verdict_buttons` | `_filter_bar.html:6-11` | Verdict filter buttons |
| `.filter-btn` | `filter_by_verdict()` | `_filter_bar.html:6-11` | Individual filter button |
| `.filter-type-pills .filter-pill` | `filter_type_pills` | `_filter_bar.html:17-20` | Type pill container |
| `.filter-pill` | `filter_by_type()` | `_filter_bar.html:17-20` | Individual type pill |
| `.filter-search-input` | `search_input` | `_filter_bar.html:27` | Search text input |
| `.ioc-card:visible` | `visible_cards` | `_ioc_card.html:1` | Visibility pseudo-selector |
| `.ioc-card:not(:visible)` | `hidden_cards` | `_ioc_card.html:1` | Hidden pseudo-selector |
| `.provider-coverage-row` | `provider_coverage` | `_verdict_dashboard.html:29` | Coverage row |
| `.enrichment-slot` | inline in `test_results_page.py:283` | `_enrichment_slot.html:1` | Not in POM |
| `#ioc-cards-grid` | inline in `test_extraction.py:282` | `results.html:67` | Not in POM |

**Inline test selectors (not routed through results_page.py POM):**
- `test_extraction.py:282` — `page.locator("#ioc-cards-grid")`
- `test_results_page.py:283` — `results.page.locator(".enrichment-slot")`

---

## Data-Attribute Contracts on `.ioc-card`

### Data-Attribute Triple-Consumer Contract

The three `data-*` attributes below are read by four independent consumers simultaneously.
They MUST remain on the `.ioc-card` root `<div>` at all times.

| Attribute | Value Domain | Consumer 1 (CSS) | Consumer 2 (TypeScript) | Consumer 3 (Filter JS) | Consumer 4 (E2E) |
|-----------|-------------|-------------------|-------------------------|-------------------------|-------------------|
| `data-ioc-value` | normalized IOC string | — | — | `filter.ts` text search | `results_page.py: ioc_values()`, `cards_for_type()` |
| `data-ioc-type` | `ipv4\|ipv6\|domain\|url\|md5\|sha1\|sha256\|cve` | — | — | `filter.ts` type pills | `results_page.py: cards_for_type()` |
| `data-verdict` | `no_data\|malicious\|suspicious\|clean\|known_good\|error` | `input.css` border-left color selectors | `enrichment.ts: updateCardVerdict()` | `filter.ts` verdict buttons | `results_page.py`, `test_extraction.py` |

**Rule:** All three attributes MUST remain on the `.ioc-card` root `<div>`. Moving them to a
child element silently breaks all four consumers. This is the most fragile contract in the codebase.

---

## JS-Created Runtime Classes (DO NOT RENAME)

These classes are assigned via `element.className = "..."` or `classList.add()` in TypeScript
(`enrichment.ts`), then exist in the DOM after enrichment runs. E2E tests in `test_extraction.py`
and `test_results_page.py` may query them after enrichment completes. Renaming any of these
breaks E2E tests silently.

| Class | Created By | CSS Definition | Purpose |
|-------|-----------|----------------|---------|
| `.ioc-summary-row` | `getOrCreateSummaryRow()` line 170 | `input.css:1146` | Summary row container inside enrichment slot |
| `.verdict-badge` | `updateSummaryRow()` line 207 | `input.css:1125` | Verdict badge |
| `.verdict-{verdict}` | `updateSummaryRow()` line 207 | `input.css:1137-1142` | Verdict color modifier |
| `.ioc-summary-attribution` | `updateSummaryRow()` line 213 | `input.css:1154` | Attribution text |
| `.consensus-badge` | `updateSummaryRow()` line 219 | `input.css:1165` | Consensus badge |
| `.consensus-badge--{green/yellow/red}` | `updateSummaryRow()` line 219 | `input.css:1174-1190` | Consensus color modifier |
| `.provider-detail-row` | `createDetailRow()` line 424 | `input.css:1236` | Per-provider result row |
| `.provider-context-row` | `createContextRow()` line 386 | `input.css:1276` | Context provider row |
| `.provider-detail-name` | both row creators lines 390,428 | `input.css:1249` | Provider name cell |
| `.provider-detail-stat` | `createDetailRow()` line 436 | `input.css:1256` | Provider stat cell |
| `.provider-context` | `createContextRow()` line 346 | `input.css:1284` | Context fields container |
| `.provider-context-field` | `createContextRow()` line 323 | `input.css:1295` | Individual context field |
| `.provider-context-label` | `createContextRow()` line 326 | `input.css:1302` | Context field label |
| `.context-tag` | `createContextRow()` line 359 | `input.css:1307` | Tag chip |
| `.cache-badge` | both row creators lines 405,446 | `input.css:1357` | Cache hit indicator |
| `.enrichment-slot--loaded` | `handleResult()` lines 666,690 | `input.css:1218` | Loaded state class |
| `.enrichment-waiting-text` | `showWaitingCard()` line 597 | implicit | Waiting state text |
| `.is-open` | toggle logic | `input.css:1213,1230` | Open state for chevron/details |

All line numbers above reference `enrichment.ts` and were verified against the codebase on
2026-03-17. If the file is significantly modified, re-verify line numbers but do NOT change
class names without a full E2E run.

---

## Information Density Acceptance Criteria

These criteria define the minimum visible information on the results page without hover or expansion.
They apply before AND after every phase of v1.1.

| Element | Requirement | Rationale |
|---------|-------------|-----------|
| `.ioc-value` (code element) | Always visible in card header | IOC value is the primary identity — analyst must see it at a glance |
| `.verdict-label` | Always visible in card header | Worst verdict must be at-a-glance without any interaction |
| `.ioc-type-badge` | Always visible in card header | Type context (IP vs domain vs hash) without expansion |
| `.consensus-badge` | Visible without hover | Must not be tooltip-only or hover-only — analyst needs consensus count at a glance |
| Provider detail rows | Collapsed by default, expansion is opt-in | Reduce cognitive load; 14 providers x N IOCs would overwhelm |

---

## CSS Layer Ownership Rule

Effective from Phase 1 onward. Governs all CSS changes in Phases 2-5.

**Component classes** (`.ioc-card`, `.verdict-label`, `.filter-btn`, `.provider-detail-row`, etc.):
own ALL visual properties for existing elements. Never add Tailwind utilities alongside these
on existing elements. Component classes are defined inside `@layer components` in `input.css`.

**Tailwind utilities**: reserved for NEW layout structures introduced in v1.1+.
Do not back-apply utilities to elements that already have component class styles.
Adding Tailwind utilities alongside component classes causes specificity conflicts because
`@layer components` has lower specificity than unbounded utilities.

**Violation example (DO NOT):**
```html
<!-- WRONG: .ioc-card already has display/gap in @layer components -->
<div class="ioc-card flex gap-4">
```

**Correct approach:**
```html
<!-- RIGHT: new wrapper element uses Tailwind; existing element untouched -->
<div class="flex gap-4">
  <div class="ioc-card">
```

See `app/static/src/input.css` header comment for the full rule text.

---

## Internal CSS-Only Classes (Not E2E-Locked)

These classes exist for visual structure but are NOT referenced in E2E tests or TypeScript.
They MAY be renamed in future phases, but renaming should be deliberate and documented.

Key examples: `.results-header`, `.ioc-card-header`, `.ioc-card-actions`, `.enrich-warning`,
`.enrich-progress`, `.shimmer-wrapper`, `.shimmer-line`, `.verdict-dashboard` (class, NOT the
`#verdict-dashboard` ID which IS locked), `.verdict-kpi-card`, `.verdict-kpi-count`,
`.verdict-kpi-label`, `.filter-bar`, `.filter-verdict-buttons`, `.filter-type-pills`,
`.filter-search`, `.filter-search-wrapper`, `.filter-search-icon`.

Note: `.verdict-dashboard` (class) is not E2E-locked, but `#verdict-dashboard` (ID) IS.
The ID is the contract — the class is internal styling.

---

*Last updated: Phase 1 (2026-03-17). Maintained by the phase executor for each v1.1 phase.*
*Before any CSS/HTML rename, check this file. After any rename, update the relevant rows.*
