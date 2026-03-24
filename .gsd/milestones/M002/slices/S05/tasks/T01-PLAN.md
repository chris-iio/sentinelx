---
estimated_steps: 5
estimated_files: 1
---

# T01: Add enrichment surface locators and helpers to ResultsPage page object

**Slice:** S05 — E2E test suite update
**Milestone:** M002

## Description

The `ResultsPage` page object (`tests/e2e/pages/results_page.py`) currently has locators only for the pre-S01 DOM — IOC cards, filter bar, verdict dashboard, and provider coverage. It has zero locators for any of the new S01–S04 enrichment surface elements: `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.detail-link-footer`, `.ioc-summary-attribution`, `.enrichment-slot`, `.enrichment-slot--loaded`, `.is-open` expand state, or `.enrichment-section`.

This task adds all missing locators and helper methods to the page object so T02 can write new tests that exercise these elements. No test files are modified — this is a pure page-object expansion.

**Skill:** `test` skill is relevant for matching existing test patterns.

## Steps

1. Read `tests/e2e/pages/results_page.py` (the executor already has the slice plan context, but should confirm current state).
2. Update the module docstring from `"Page Object Model for the SentinelX results page (card layout)."` to reflect the new single-column layout with enrichment surface.
3. Add the following locators to `__init__`:
   - None needed — all new locators are scoped to individual cards, so they work better as methods/properties below.
4. Add the following properties and methods to `ResultsPage`:

   **Enrichment slot locators (scoped to page):**
   - `enrichment_slots` → `page.locator(".enrichment-slot")` — all enrichment slots
   - `loaded_enrichment_slots` → `page.locator(".enrichment-slot--loaded")` — slots that have received data
   - `enrichment_details` → `page.locator(".enrichment-details")` — all detail panels

   **Summary row locators (scoped to page):**
   - `summary_rows` → `page.locator(".ioc-summary-row")` — all JS-created summary rows
   - `expanded_summary_rows` → `page.locator(".ioc-summary-row.is-open")` — expanded summary rows

   **Enrichment element locators (scoped to page):**
   - `chevron_wrappers` → `page.locator(".chevron-icon-wrapper")` — all chevron icons
   - `micro_bars` → `page.locator(".verdict-micro-bar")` — all verdict micro-bars
   - `staleness_badges` → `page.locator(".staleness-badge")` — all staleness badges
   - `attribution_spans` → `page.locator(".ioc-summary-attribution")` — all attribution spans
   - `detail_link_footers` → `page.locator(".detail-link-footer")` — all detail link footers
   - `detail_links` → `page.locator(".detail-link")` — all "View full detail →" links
   - `context_lines` → `page.locator(".ioc-context-line")` — all context lines

   **Section containers:**
   - `enrichment_sections` → `page.locator(".enrichment-section")` — all section containers
   - `section_context` → `page.locator(".enrichment-section--context")` — infrastructure context sections
   - `section_reputation` → `page.locator(".enrichment-section--reputation")` — reputation sections
   - `section_no_data` → `page.locator(".enrichment-section--no-data")` — no-data sections

   **Card-scoped helpers:**
   - `summary_row_for_card(ioc_value: str)` → `page.locator(f'.ioc-card[data-ioc-value="{ioc_value}"] .ioc-summary-row')` — summary row within a specific card
   - `enrichment_details_for_card(ioc_value: str)` → `page.locator(f'.ioc-card[data-ioc-value="{ioc_value}"] .enrichment-details')` — details panel for a specific card

   **Expand/collapse helpers:**
   - `expand_row(ioc_value: str)` → clicks the `.ioc-summary-row` within the card matching `ioc_value`, then asserts `.is-open` class is present on both the summary row and its sibling `.enrichment-details`
   - `collapse_row(ioc_value: str)` → clicks the `.ioc-summary-row` again, then asserts `.is-open` class is removed
   - `is_row_expanded(ioc_value: str) -> bool` → evaluates whether the `.ioc-summary-row` for the given card has the `.is-open` class

5. Run `python3 -m pytest tests/e2e/ -q` to confirm all 91 existing tests still pass. The new locators are additive — no existing code is modified.

## Must-Haves

- [ ] All 18+ new locators/properties added to `ResultsPage`
- [ ] `expand_row()`, `collapse_row()`, `is_row_expanded()` helpers added
- [ ] Module docstring updated
- [ ] All 91 existing tests still pass (zero regressions)
- [ ] No existing locator or method modified or removed

## Verification

- `python3 -m pytest tests/e2e/ -q` → 91 passed, 0 failed
- Visual inspection: `results_page.py` has all new locators listed in steps above

## Inputs

- `tests/e2e/pages/results_page.py` — current page object (118 lines). All existing locators and methods must remain intact.
- DOM source of truth for selectors:
  - `.ioc-summary-row`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.ioc-summary-attribution` → created by JS in `row-factory.ts`
  - `.enrichment-slot`, `.enrichment-details`, `.enrichment-section`, `.enrichment-section--context/--reputation/--no-data` → server-rendered in `_enrichment_slot.html`
  - `.enrichment-slot--loaded`, `.is-open` → added dynamically by `enrichment.ts`
  - `.detail-link-footer`, `.detail-link` → injected by `enrichment.ts` `injectDetailLink()`
  - `.ioc-context-line` → server-rendered in `_ioc_card.html`

## Observability Impact

This task makes zero runtime changes — it is a pure page-object expansion with no application code touched. Observable effects are limited to the test layer:

**What changes are visible:**
- `results_page.py` gains 18+ new `@property` methods. Running `python3 -c "from tests.e2e.pages.results_page import ResultsPage; print([m for m in dir(ResultsPage) if not m.startswith('_')])"` shows the new locator names.
- Any test that previously accessed these selectors manually now has a canonical method to call.

**How a future agent inspects this task:**
- `wc -l tests/e2e/pages/results_page.py` — should be ~200 lines after this task (was ~118 before).
- `grep -c "def \|property" tests/e2e/pages/results_page.py` — count includes all property/method definitions.
- `python3 -m pytest tests/e2e/ -q` — 91 tests pass confirms no regression.

**Failure state visibility:**
- If a new property has a typo in the CSS selector, no test will fail yet (T02 exercises these). The failure surfaces in T02 as a Playwright timeout with element-not-found context.
- If an existing property was accidentally deleted, one or more of the 91 existing tests will fail immediately and name the missing locator.

## Expected Output

- `tests/e2e/pages/results_page.py` — expanded from ~118 lines to ~200 lines with all new locators and helpers

