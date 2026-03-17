---
estimated_steps: 7
estimated_files: 5
---

# T01: Convert grid layout to single-column rows — restructure templates + structural CSS

**Slice:** S01 — Layout skeleton + quiet precision design system
**Milestone:** M002

## Description

This task performs the structural migration from 2-column card grid to single-column full-width row layout. It restructures all four template files (results.html, _ioc_card.html, _verdict_dashboard.html, _filter_bar.html) and updates the corresponding layout/structural CSS in input.css. This is the highest-risk task in S01 because it changes DOM structure that TS modules and E2E tests depend on.

The critical constraint is **contract preservation**: every selector and data attribute that TS, filters, export, or E2E depend on must remain in place with the same names and relationships. The research doc identified the exact contract surface — follow it strictly.

**Skill note:** The `frontend-design` skill is available but T01 focuses on structure, not visual polish. Save the `frontend-design` skill for T02.

## Steps

1. **Read current templates** to understand exact DOM structure before modifying:
   - `app/templates/results.html`
   - `app/templates/partials/_ioc_card.html`
   - `app/templates/partials/_verdict_dashboard.html`
   - `app/templates/partials/_filter_bar.html`
   - `app/templates/partials/_enrichment_slot.html` (read-only — do NOT modify)

2. **Read current input.css** to understand existing layout rules:
   - `app/static/src/input.css`
   - Focus on: `.ioc-cards-grid`, `.ioc-card`, `.ioc-card-header`, `#verdict-dashboard`, `.verdict-kpi-card`, `.filter-bar-wrapper`, and any media query breakpoints

3. **Read contract reference** to confirm locked selectors:
   - `cat .planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — verify which selectors are locked

4. **Restructure `_ioc_card.html`** — convert card layout to horizontal row:
   - Keep `.ioc-card` as the root element with `data-ioc-value`, `data-ioc-type`, `data-verdict` attributes unchanged
   - Reorganize internals into a horizontal row composition: left section (verdict + type + value), right section (actions: copy button, detail link)
   - Keep ALL child hooks in place: `.ioc-value`, `.ioc-type-badge`, `.verdict-label`, `.copy-btn`, detail link, `.ioc-original`, `.ioc-context-line`
   - Keep the `{% include 'partials/_enrichment_slot.html' %}` include exactly where it is (or at the end of the card, below the main row content)
   - Do NOT touch any Jinja2 logic — only restructure the HTML wrapper elements

5. **Compress `_verdict_dashboard.html`** — convert large KPI boxes to compact inline bar:
   - Keep `#verdict-dashboard` as root container
   - Keep each `.verdict-kpi-card` with its `data-verdict` attribute and child `[data-verdict-count]` span
   - Restructure layout internals to be a compact horizontal bar (inline-flex or flexbox row) instead of 5 separate large card boxes
   - Keep the click targets working (the `.verdict-kpi-card[data-verdict]` elements must remain clickable)

6. **Compact `_filter_bar.html`** — consolidate into single row:
   - Keep `.filter-bar-wrapper` as root
   - Keep `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input` with exact attributes
   - Reorganize internal layout so verdict pills, type pills, and search input sit in a single horizontal row instead of stacked rows

7. **Update structural CSS in `input.css`**:
   - Remove the 2-column media query breakpoint on `#ioc-cards-grid` (the `@media (min-width: 768px)` that sets `grid-template-columns: repeat(2, 1fr)` or similar)
   - Update `.ioc-card` styles: remove card-like appearance (rounded corners, shadow, padding), add row-like styling (full-width, subtle bottom border, horizontal padding, tighter vertical padding)
   - Update `.ioc-card` internal layout to use flexbox for horizontal arrangement
   - Compress `#verdict-dashboard` and `.verdict-kpi-card` styles to render as compact inline bar
   - Compact `.filter-bar-wrapper` styles for single-row layout
   - Keep all existing enrichment-related styles unchanged (`.enrichment-slot`, `.enrichment-details`, `.ioc-summary-row`, `.chevron-toggle`)

8. **Verify all three build commands pass**:
   - `make css` — Tailwind compiles
   - `make typecheck` — TypeScript has no errors
   - `make js-dev` — Bundle builds

## Must-Haves

- [ ] `.ioc-card` root element retains `data-ioc-value`, `data-ioc-type`, `data-verdict` attributes
- [ ] `#ioc-cards-grid` renders as single column at ALL viewport widths (no 2-column breakpoint)
- [ ] `.ioc-card` renders as a full-width horizontal row, not a card box
- [ ] `#verdict-dashboard` renders as compressed inline bar, not 5 large KPI boxes
- [ ] `.filter-bar-wrapper` renders as a single compact row
- [ ] All contract selectors present in DOM: `.ioc-card`, `#ioc-cards-grid`, `#verdict-dashboard`, `.filter-bar-wrapper`, `.enrichment-slot`, `.ioc-context-line`, `.verdict-label`, `.ioc-type-badge`, `.copy-btn`, `[data-verdict-count]`, `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input`
- [ ] `.enrichment-slot` subtree is NOT modified — only repositioned/restyled around
- [ ] `make css`, `make typecheck`, and `make js-dev` all pass

## Observability Impact

**Signals that change after T01:**
- `make css` — Tailwind will now process new utility classes added to templates (flexbox layout classes on `.ioc-card`, `.verdict-dashboard`, `.filter-bar-wrapper`). Unused old grid classes may appear as warnings if they remain in input.css without DOM references.
- `make typecheck` — Zero new TS signals expected. Any breakage here means a contract selector was accidentally renamed.
- Flask 500 in browser — Template syntax errors (broken Jinja2 blocks from restructuring) show as 500 with traceback in `flask run` output.

**How a future agent inspects this task:**
- Run `grep -n 'data-ioc-value\|data-ioc-type\|data-verdict' app/templates/partials/_ioc_card.html` — must return the root `.ioc-card` element line
- Run `grep -n 'ioc-cards-grid\|grid-cols-2\|repeat(2' app/static/src/input.css` — must return 0 lines matching `grid-cols-2` or `repeat(2`
- Run `grep -n 'flex' app/static/src/input.css | grep ioc-card` — should show flexbox on `.ioc-card`

**Failure state visibility:**
- 2-column layout still present: `grep 'grid-cols-2\|repeat(2' app/static/src/input.css` returns a hit
- TS build fails with selector reference: error message names the exact class/attribute that is missing
- Template partial error: Flask log shows `jinja2.exceptions.UndefinedError` with partial file name and line number

## Verification

- `make css` exits 0
- `make typecheck` exits 0
- `make js-dev` exits 0
- Grep the modified template files to confirm all contract selectors are still present

## Inputs

- `app/templates/results.html` — current page orchestration template
- `app/templates/partials/_ioc_card.html` — current IOC card partial
- `app/templates/partials/_verdict_dashboard.html` — current dashboard partial
- `app/templates/partials/_filter_bar.html` — current filter bar partial
- `app/templates/partials/_enrichment_slot.html` — read-only reference for enrichment subtree
- `app/static/src/input.css` — current stylesheet
- `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — selector lockfile

## Expected Output

- `app/templates/results.html` — simplified page composition
- `app/templates/partials/_ioc_card.html` — horizontal row layout internals
- `app/templates/partials/_verdict_dashboard.html` — compact inline bar layout
- `app/templates/partials/_filter_bar.html` — single-row compact layout
- `app/static/src/input.css` — structural CSS updated (single-column grid, row styling, compressed dashboard, compact filter bar)
