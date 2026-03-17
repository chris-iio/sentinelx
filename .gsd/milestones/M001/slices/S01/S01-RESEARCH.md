# Phase 1: Contracts and Foundation - Research

**Researched:** 2026-03-16
**Domain:** Documentation discipline, CSS contract cataloguing, data-attribute contract documentation
**Confidence:** HIGH

## Summary

Phase 1 is entirely a documentation and cataloguing phase — no production code changes, no visual
changes, no functional changes. Its sole output is a set of written contracts that future phases
cannot violate. This makes the research domain unusual: the primary questions are not "what
library do I use?" but "what currently exists and must be preserved?"

The E2E test suite is the authoritative source of truth for what constitutes a contract. The
`tests/e2e/pages/results_page.py` page object contains all CSS class selector dependencies in one
file. The CSS source at `app/static/src/input.css` contains all CSS definitions. The template
partials define the data-attribute contracts. The TypeScript enrichment module creates additional
DOM elements at runtime with their own class names. All four sources must be cross-referenced to
produce a complete catalog.

The key architectural insight is that two distinct categories of CSS classes exist: (1) template-
sourced classes that appear in Jinja2 HTML and are queryable by E2E selectors, and (2) JS-created
classes that `enrichment.ts` assigns via `element.className = "..."` at runtime. Both categories
are contractual because E2E tests can locate them after enrichment completes. Any rename of a
class in either category breaks E2E tests silently (the test fails with "locator not found" rather
than a type error).

**Primary recommendation:** Produce one `CSS-CONTRACTS.md` file with three sections — E2E-locked
selectors, data-attribute contracts, and the CSS layer ownership rule — committed to `.planning/`.
This file becomes the "do not rename" reference that every subsequent plan task cites before
touching CSS.

## Standard Stack

This phase produces documentation artifacts only. No new libraries are introduced.

### Existing Stack (informational)
| Component | Version | Relevance to Phase 1 |
|-----------|---------|----------------------|
| Playwright (E2E) | current | Source of all CSS selector contracts |
| Tailwind CSS standalone | current | CSS layer ownership rule applies to utilities vs components |
| TypeScript 5.8 + esbuild | current | enrichment.ts creates runtime CSS classes that are also contractual |
| Jinja2 templates | Flask 3.1 | Template partials define the static HTML class contracts |

**Installation:** None required for this phase.

## Architecture Patterns

### Recommended Project Structure

The catalog file produced in this phase belongs in `.planning/` as a planning artifact:

```
.planning/
├── phases/
│   └── 01-contracts-and-foundation/
│       ├── 01-RESEARCH.md           (this file)
│       ├── 01-PLAN.md               (to be created)
│       └── CSS-CONTRACTS.md         (primary deliverable)
```

The `CSS-CONTRACTS.md` file is a planning artifact and does NOT go in `app/`. The "do not rename"
comments go inline in the source files they describe (template partials, input.css, enrichment.ts).

### Pattern 1: Catalog-then-comment

**What:** First enumerate all contracts in one central catalog file, then add inline comments in
the source files pointing back to the catalog. The catalog is the single source of truth; the
inline comments are navigation aids.

**When to use:** When multiple source files share contractual relationships with an external
consumer (the E2E tests) that cannot enforce its contracts at compile time.

**Catalog structure:**
```markdown
## E2E-Locked CSS Classes (DO NOT RENAME)

| Class | Source file | Line | E2E consumer | Notes |
|-------|-------------|------|--------------|-------|
| .ioc-card | _ioc_card.html:1 | results_page.py:26 | Root card element, data-* contracts |
| ...
```

### Pattern 2: Inline annotation in templates

**What:** Add HTML comments directly above the contractual element in the Jinja2 partial:

```html
{#
  CONTRACT: data-ioc-value, data-ioc-type, data-verdict attributes on .ioc-card
  are read by:
    - E2E tests (results_page.py: cards_for_type, ioc_values, verdict_labels)
    - enrichment.ts: updateCardVerdict(), sortCardsBySeverity()
    - filter.ts: initFilterBar() (data-verdict for hide/show, data-ioc-type for type filter)
  DO NOT rename these classes or attributes without updating CSS-CONTRACTS.md.
#}
<div class="ioc-card" data-ioc-value="..." data-ioc-type="..." data-verdict="no_data">
```

### Pattern 3: CSS layer ownership comment block

**What:** Add a comment block at the top of `input.css` declaring the ownership rule:

```css
/*
  CSS LAYER OWNERSHIP RULE (v1.1+)
  - Component classes (e.g., .ioc-card, .verdict-label): own ALL visual properties
    for existing elements. Never add Tailwind utilities to these elements inline.
  - Tailwind utilities: reserved for NEW layout structures introduced in v1.1+.
    Do not back-apply utilities to elements that already have component class styles.
*/
```

### Anti-Patterns to Avoid

- **Renaming during cataloguing:** Do not "improve" any class name while writing the catalog.
  The catalog describes what exists, not what should exist.
- **Partial catalog:** Listing only E2E-visible classes and missing JS-created runtime classes
  (e.g., `.ioc-summary-row`, `.verdict-badge`, `.provider-detail-row`). These are also locked.
- **Catalog without inline comments:** A catalog file alone means developers must remember to
  check it. Inline comments in the source files make the contract visible at the point of change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding all E2E selectors | Manual grep across test files | Read results_page.py directly — it is the complete POM | The page object pattern already centralises all selectors in one file |
| Verifying contracts are enforced | Writing a custom linter | Use the existing E2E test suite as the enforcement mechanism | 91 E2E tests already validate all contracts at runtime |

**Key insight:** The existing Page Object Model (`results_page.py`) is already a contract catalog
in code form — it's just not yet mirrored as a human-readable reference document.

## Complete CSS Contract Inventory

This section documents every contractual CSS class and attribute discovered in the codebase.
This is the authoritative pre-cataloguing research used to construct CSS-CONTRACTS.md.

### Category A: E2E-Locked Selectors (in results_page.py)

These classes appear in `tests/e2e/pages/results_page.py` and are directly queried by Playwright.
Renaming any of these breaks E2E tests immediately.

| Class / Selector | results_page.py method | Source template/file |
|-----------------|------------------------|----------------------|
| `.mode-indicator` | `mode_indicator` | `results.html:7` |
| `.results-summary .ioc-count` | `ioc_count` | `results.html:16,20` |
| `a.back-link` | `back_link` | `results.html:35` |
| `.empty-state` | `no_results_box` | `_empty_state.html` |
| `.empty-state-body` | `no_results_hint` | `_empty_state.html` |
| `.ioc-card` | `ioc_cards`, `cards_for_type` | `_ioc_card.html:1` |
| `.ioc-card[data-ioc-type="..."]` | `cards_for_type()` | `_ioc_card.html:1` |
| `.ioc-type-badge` | `type_badge()` | `_ioc_card.html:4` |
| `.ioc-value` | `ioc_values()` | `_ioc_card.html:3` |
| `.ioc-original` | `ioc_originals()` | `_ioc_card.html:23` |
| `.copy-btn` | `copy_buttons()` | `_ioc_card.html:8` |
| `.verdict-label` | `verdict_labels()` | `_ioc_card.html:5` |
| `#verdict-dashboard` | `verdict_dashboard` | `_verdict_dashboard.html:1` |
| `.filter-bar-wrapper` | `filter_bar` | `_filter_bar.html:2` |
| `.filter-verdict-buttons .filter-btn` | `filter_verdict_buttons` | `_filter_bar.html:6-11` |
| `.filter-btn` | `filter_by_verdict()` | `_filter_bar.html:6-11` |
| `.filter-type-pills .filter-pill` | `filter_type_pills` | `_filter_bar.html:17-20` |
| `.filter-pill` | `filter_by_type()` | `_filter_bar.html:17-20` |
| `.filter-search-input` | `search_input` | `_filter_bar.html:27` |
| `.ioc-card:visible` | `visible_cards` | `_ioc_card.html:1` |
| `.ioc-card:not(:visible)` | `hidden_cards` | `_ioc_card.html:1` |
| `.provider-coverage-row` | `provider_coverage` | `_verdict_dashboard.html:29` |
| `.enrichment-slot` | `test_offline_mode_cards_have_no_enrichment_slot` | `_enrichment_slot.html:1` |
| `#ioc-cards-grid` | `test_responsive_grid_layout` | `results.html:67` |

### Category B: Data-Attribute Contracts on `.ioc-card`

These `data-*` attributes are read by E2E tests, TypeScript filter logic, and verdict update
functions. All three must remain on the `.ioc-card` root element.

| Attribute | Value domain | Set by | Read by |
|-----------|-------------|--------|---------|
| `data-ioc-value` | normalized IOC string | `_ioc_card.html:1` | E2E (`test_search_filters_by_value_substring`), `filter.ts` text search |
| `data-ioc-type` | `ipv4\|ipv6\|domain\|url\|md5\|sha1\|sha256\|cve` | `_ioc_card.html:1` | E2E (`cards_for_type`), `filter.ts` type pills |
| `data-verdict` | `no_data\|malicious\|suspicious\|clean\|known_good\|error` | `_ioc_card.html:1` (initial), `enrichment.ts:updateCardVerdict()` (updated) | E2E (`test_cards_have_data_verdict_attribute`), CSS attribute selectors for left-border color, `filter.ts` verdict buttons |

### Category C: JS-Created Runtime Classes (in enrichment.ts)

These classes are assigned via `element.className = "..."` in TypeScript, then exist in the DOM.
E2E tests in `test_extraction.py` and `test_results_page.py` may query them after enrichment.

| Class | Set in enrichment.ts | CSS definition | Purpose |
|-------|---------------------|----------------|---------|
| `.ioc-summary-row` | `getOrCreateSummaryRow()` line 170 | `input.css:1146` | Summary row container inside enrichment slot |
| `.verdict-badge` | `updateSummaryRow()` line 207 | `input.css:1125` | Verdict badge in summary row |
| `.verdict-{verdict}` | `updateSummaryRow()` line 207 | `input.css:1137-1142` | Verdict color modifier on badge |
| `.ioc-summary-attribution` | `updateSummaryRow()` line 213 | `input.css:1154` | Attribution text in summary row |
| `.consensus-badge` | `updateSummaryRow()` line 219 | `input.css:1165` | Consensus badge in summary row |
| `.consensus-badge--{green/yellow/red}` | `updateSummaryRow()` line 219 | `input.css:1174-1190` | Consensus badge color modifier |
| `.provider-detail-row` | `createDetailRow()` line 424 | `input.css:1236` | Per-provider result row |
| `.provider-context-row` | `createContextRow()` line 386 | `input.css:1276` | Context provider row |
| `.provider-detail-name` | both row creators lines 390,428 | `input.css:1249` | Provider name cell |
| `.provider-detail-stat` | `createDetailRow()` line 436 | `input.css:1256` | Provider stat cell |
| `.provider-context` | `createContextRow()` line 346 | `input.css:1284` | Context fields container |
| `.provider-context-field` | `createContextRow()` line 323 | `input.css:1295` | Individual context field |
| `.provider-context-label` | `createContextRow()` line 326 | `input.css:1302` | Context field label |
| `.context-tag` | `createContextRow()` line 359 | `input.css:1307` | Tag chip in context fields |
| `.cache-badge` | both row creators lines 405,446 | `input.css:1357` | Cache hit indicator |
| `.enrichment-slot--loaded` | `handleResult()` line 666,690 | `input.css:1218` | State class — reveals chevron toggle |
| `.enrichment-waiting-text` | `showWaitingCard()` line 597 | (implicitly via class) | Waiting state text |
| `.enrichment-pending-text` | `showWaitingCard()` line 597 | (modifier class) | Pending state variant |
| `.is-open` | toggle logic | `input.css:1213,1230` | Open state for chevron and details |

### Category D: CSS Classes Used Only in CSS (Internal, Not E2E-Locked)

These classes exist for visual structure but are not referenced in E2E tests or TypeScript.
They MAY be renamed in future visual redesign work, but the catalog should document them so
renaming is deliberate.

Key examples: `.results-header`, `.ioc-card-header`, `.ioc-card-actions`, `.enrich-warning`,
`.enrich-progress`, `.shimmer-wrapper`, `.shimmer-line`, `.verdict-dashboard`, `.verdict-kpi-card`,
`.verdict-kpi-count`, `.verdict-kpi-label`, `.filter-bar`, `.filter-verdict-buttons`,
`.filter-type-pills`, `.filter-search`, `.filter-search-wrapper`, `.filter-search-icon`.

Note: `.verdict-dashboard` is E2E-locked via `#verdict-dashboard` ID in results_page.py, but
the class itself is not the selector. The ID is the contract.

## Common Pitfalls

### Pitfall 1: Missing JS-Created Classes in the Catalog
**What goes wrong:** The catalog only covers template HTML classes. JS-created classes in
`enrichment.ts` (e.g., `.ioc-summary-row`, `.verdict-badge`) are missed. Phase 3 renames
`.verdict-badge` to improve visual hierarchy and the E2E suite silently starts querying nothing.
**Why it happens:** Template files are the obvious place to look for CSS classes. TypeScript
`element.className = "..."` assignments are a separate category.
**How to avoid:** Search `enrichment.ts` explicitly for `className`, `classList.add`, and
`querySelector` calls. Every class string in these expressions is contractual.
**Warning signs:** Catalog has zero entries in the "JS-created classes" category.

### Pitfall 2: Treating Phase 1 as Optional
**What goes wrong:** Team skips Phase 1 to "save time" and goes straight to visual work. First
CSS rename breaks 3-5 E2E tests. Debugging takes longer than Phase 1 would have.
**Why it happens:** Foundation work produces no visible user-facing output.
**How to avoid:** Phase 1 is non-negotiable per `STATE.md` decision: "Phase ordering is non-
negotiable — contracts before code."

### Pitfall 3: Catalog without Verification
**What goes wrong:** Catalog is written from memory or partial grep, missing some classes.
Developer in Phase 3 renames a class not in the catalog assuming it's free to rename.
**Why it happens:** Writing a catalog from reading code is error-prone.
**How to avoid:** Run the E2E suite after Phase 1 to confirm baseline. The catalog is complete
when `pytest -m e2e` passes at 91/91 (baseline confirmation, not a new test).

### Pitfall 4: Applying Tailwind Utilities to Existing Component Elements
**What goes wrong:** Phase 3 adds `class="ioc-card flex gap-4"` to .ioc-card. The component
class `.ioc-card` already has `display: flex` with different gap — specificity conflict.
**Why it happens:** Tailwind utilities feel convenient for quick adjustments.
**How to avoid:** The CSS layer ownership rule must be written as a comment in `input.css`
before any visual work begins. Component classes own all visual properties; Tailwind for new
structure only.

### Pitfall 5: The data-verdict Double-Write Pattern
**What goes wrong:** Phase 4 template restructuring moves `data-verdict` from `.ioc-card` to
a child element. `enrichment.ts` continues updating `.ioc-card[data-verdict]`. Filter bar JS
reads `.ioc-card[data-verdict]` for hide/show. Everything silently breaks.
**Why it happens:** Template changes feel independent of TypeScript logic.
**How to avoid:** Document that `data-ioc-value`, `data-ioc-type`, and `data-verdict` are
triple-consumer contracts: (1) CSS attribute selectors for border color, (2) `enrichment.ts`
`updateCardVerdict()`, (3) filter bar JS. All three must stay on `.ioc-card` root permanently.

## Code Examples

### Information Density Acceptance Criteria (to be written in CSS-CONTRACTS.md)

```markdown
## Information Density Acceptance Criteria

These criteria define the minimum visible information on results page without hover or expansion.
They apply before AND after every phase.

| Element | Requirement | Rationale |
|---------|-------------|-----------|
| `.ioc-value` (code) | Always visible in card header | IOC value is the primary identity |
| `.verdict-label` | Always visible in card header | Worst verdict must be at-a-glance |
| `.ioc-type-badge` | Always visible in card header | Type context without expansion |
| Consensus count (`.consensus-badge`) | Visible without hover | Not tooltip, not hover-only |
| Provider detail rows | Collapsed by default, expansion is optional | Reduce cognitive load |
```

### CSS Layer Ownership Comment (to be added to input.css)

```css
/*
  ================================================================
  CSS LAYER OWNERSHIP RULE — v1.1 (enforced from Phase 1 onward)
  ================================================================

  COMPONENT CLASSES own ALL visual properties for existing elements:
    - Background, border, color, font, padding, display, etc.
    - Examples: .ioc-card, .verdict-label, .filter-btn, .provider-detail-row

  TAILWIND UTILITIES are reserved for NEW layout structures introduced in v1.1+:
    - Grid wrappers, flex containers for new sections (e.g., provider group headers)
    - Never back-apply utilities to elements that already have component class styles
    - Adding Tailwind utilities alongside component classes causes specificity conflicts

  WHY: Component classes in this file are defined inside @layer components, giving them
  lower specificity than utilities. A mix causes unpredictable override behavior and
  makes the stylesheet unmaintainable.
  ================================================================
*/
```

### Template Data-Attribute Contract Comment (to be added to _ioc_card.html)

```html
{#
  ================================================================
  CONTRACT: .ioc-card root element attributes — DO NOT MOVE
  ================================================================
  The following attributes MUST remain on the .ioc-card root div.
  They are read by THREE independent consumers:

  1. CSS selectors (input.css ~line 952):
     .ioc-card[data-verdict="malicious"] { border-left-color: ... }
     Used for verdict-colored left border on the card.

  2. enrichment.ts — updateCardVerdict() function:
     Reads card via data-ioc-value, writes data-verdict as enrichment arrives.

  3. filter.ts — initFilterBar():
     data-verdict: verdict filter buttons hide/show cards
     data-ioc-type: type pill filter hides/shows cards
     data-ioc-value: text search filters cards by IOC value substring

  4. E2E tests (tests/e2e/pages/results_page.py):
     cards_for_type(), ioc_values(), verdict_labels(), etc.

  See .planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md
  ================================================================
#}
```

## State of the Art

This phase is not adopting new technology. It establishes written contracts over existing code.

| Old State | Post-Phase-1 State | Impact |
|-----------|-------------------|--------|
| No CSS contract catalog | CSS-CONTRACTS.md committed | Future phases know what is locked |
| No inline "do not rename" comments | Comments in _ioc_card.html, input.css, enrichment.ts | Visible at point of change |
| No information density acceptance criteria | Written criteria in CSS-CONTRACTS.md | Phase 3 visual work has a test oracle |
| No CSS layer ownership rule | Rule documented in input.css header comment | Prevents Tailwind/component class conflicts in Phase 3 |

## Open Questions

1. **Where exactly does CSS-CONTRACTS.md live?**
   - What we know: It is a planning artifact, not a `docs/` file, not an `app/` file
   - What's unclear: Should it be `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md`
     or `.planning/CSS-CONTRACTS.md` (milestone-level)?
   - Recommendation: `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — it is
     produced by Phase 1 and consumed by subsequent phases; milestone-level placement if the
     planner decides it should be accessible to all phases without path traversal.

2. **Should the catalog include ID selectors (e.g., `#verdict-dashboard`, `#ioc-cards-grid`)?**
   - What we know: `results_page.py` uses `#verdict-dashboard` as an ID selector. IDs are as
     locked as class selectors.
   - What's unclear: Phase 1 success criteria mention "CSS class" specifically.
   - Recommendation: Include ID contracts in the catalog under a separate section. The goal is
     completeness, and IDs are equally fragile.

3. **Are there E2E tests beyond results_page.py that reference CSS selectors directly?**
   - What we know: `test_results_page.py` uses `page.locator("#ioc-cards-grid")` and
     `page.locator(".enrichment-slot")` inline (not via the page object).
   - What's unclear: Whether all inline locators in test files are captured.
   - Recommendation: The catalog task should grep all `tests/e2e/` files for `.locator(` strings
     to catch inline selectors not routed through the page object.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + Playwright (E2E) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -m "not e2e" -x -q` (unit only) |
| Full suite command | `pytest tests/ -m e2e --tb=short` (E2E) |

### Phase Requirements → Test Map

Phase 1 has no functional requirements — it is a documentation phase. The validation for
Phase 1 is a baseline E2E run confirming 91/91 tests pass before any subsequent work begins.
No new test files are created in this phase.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BASELINE | 91 E2E tests pass after Phase 1 commits | smoke | `pytest tests/ -m e2e --tb=short` | ✅ (existing suite) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -m "not e2e" -x -q` (unit tests only, <5s)
- **Per wave merge:** `pytest tests/ -m e2e --tb=short` (full E2E suite)
- **Phase gate:** Full E2E suite green before proceeding to Phase 2

### Wave 0 Gaps
None — Phase 1 produces documentation only. No new test infrastructure is needed.
The existing E2E suite is the enforcement mechanism.

## Sources

### Primary (HIGH confidence)
- `tests/e2e/pages/results_page.py` — complete enumeration of all CSS selector contracts
- `tests/e2e/test_results_page.py` — inline locators not in the page object
- `tests/e2e/test_extraction.py` — data-attribute contract tests
- `app/templates/partials/_ioc_card.html` — data-attribute source in HTML
- `app/templates/partials/_filter_bar.html` — filter classes source
- `app/templates/partials/_enrichment_slot.html` — enrichment slot structure
- `app/templates/partials/_verdict_dashboard.html` — verdict dashboard structure
- `app/templates/results.html` — top-level results page structure
- `app/static/src/ts/modules/enrichment.ts` — all JS-created CSS class assignments
- `app/static/src/input.css` — all CSS class definitions with line numbers verified

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` — phase success criteria and ordering rationale
- `.planning/STATE.md` — locked decision: "phase ordering is non-negotiable"

### Tertiary (LOW confidence)
- None — all research is from direct code inspection.

## Metadata

**Confidence breakdown:**
- Contract catalog: HIGH — derived from direct code reading of all four source categories
- Architecture patterns: HIGH — patterns are documentation conventions, no library choices
- Pitfalls: HIGH — pitfalls derived from actual data flow analysis of the codebase

**Research date:** 2026-03-16
**Valid until:** Stable indefinitely — contracts don't change until Phase 2+ modifies enrichment.ts