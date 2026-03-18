# S05: E2E test suite update

**Goal:** Full E2E test suite passes against the new DOM structure. ResultsPage page object exposes all S01–S04 enrichment surface elements. No coverage reduction.
**Demo:** `python3 -m pytest tests/e2e/ -q` → all pass, test count ≥ 91 (increased from baseline by new enrichment surface tests).

## Must-Haves

- ResultsPage page object has locators for all new S01–S04 DOM elements: `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.detail-link-footer`, `.ioc-summary-attribution`, `.enrichment-slot--loaded`, `.is-open` state
- ResultsPage has helper methods for expand/collapse interaction (`expand_row`, `collapse_row`, row expanded state check)
- New E2E tests exercise inline expand/collapse, enrichment summary row presence, detail link injection, and enrichment section containers — using Playwright route mocking for online mode
- `test_responsive_grid_layout` docstring updated to reference single-column layout
- All 91 original tests still pass (no regressions)
- Test count increases (new tests added, none removed)

## Verification

- `python3 -m pytest tests/e2e/ -q` → all pass, 0 failures
- `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` → count ≥ 91
- No existing test removed or renamed — only additions and docstring updates

## Observability / Diagnostics

**Runtime signals:**
- Playwright test runner output (`python3 -m pytest tests/e2e/ -v`) shows per-test pass/fail including browser console errors captured by the `console_errors` fixture.
- Playwright traces (`--tracing on`) record DOM snapshots around every `expect()` call, enabling post-mortem inspection of selector failures.
- `--headed` flag runs Chromium visibly so enrichment-slot expand/collapse animations can be observed in real time.

**Inspection surfaces:**
- `results_page.py` properties return raw `Locator` objects — call `.count()`, `.all_text_contents()`, or `.evaluate("el => el.className")` in the test REPL to inspect live DOM state.
- `is_row_expanded(ioc_value)` returns a `bool` directly evaluable in a pytest debugging session.
- The `mocked_enrichment` fixture (T02) logs which route patterns were intercepted to the test's capfd output.

**Failure visibility:**
- Mismatched CSS selector → `expect(...).to_have_count(N)` timeout with Playwright's element snapshot in the error message.
- Missing `.is-open` class after expand → `expand_row()` assertion failure clearly names which card and which selector was absent.
- Route mock not triggered → enrichment slots remain in un-loaded state; `loaded_enrichment_slots.count()` returns 0, distinguishable from a selector bug.

**Redaction constraints:**
- No PII or credentials flow through E2E tests — all IOC values in fixtures are synthetic (e.g., `1.2.3.4`, `evil.example.com`).
- Route mock bodies contain no real threat intelligence data.

## Integration Closure

- Upstream surfaces consumed: Final DOM structure from S04 — `_ioc_card.html`, `_enrichment_slot.html`, `row-factory.ts`, `enrichment.ts`
- New wiring introduced in this slice: none (test-only changes)
- What remains before the milestone is truly usable end-to-end: nothing — S05 is the final slice

## Tasks

- [x] **T01: Add enrichment surface locators and helpers to ResultsPage page object** `est:20m`
  - Why: The page object has no locators for new S01–S04 DOM elements. T02's new tests need these locators to exist before they can be written. This is a pure page-object edit — no test logic changes.
  - Files: `tests/e2e/pages/results_page.py`
  - Do: Add locators for `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.detail-link-footer`, `.detail-link`, `.ioc-summary-attribution`, `.enrichment-slot`, `.enrichment-slot--loaded`, `.is-open` state, `.enrichment-section`, `.ioc-context-line`. Add helper methods for expand/collapse. Update module docstring. Ensure existing locators and methods are unchanged.
  - Verify: `python3 -m pytest tests/e2e/ -q` → 91/91 still pass (no regressions from page object additions)
  - Done when: Page object has all new locators, all 91 existing tests pass unchanged

- [ ] **T02: Add enrichment surface tests and update test_responsive_grid_layout docstring** `est:40m`
  - Why: The current 91 tests have zero coverage of inline expand, enrichment summary row, detail link, micro-bar, or staleness badge. These features were added in S01–S04 but never tested. New tests use Playwright route mocking to simulate enrichment API responses in online mode, avoiding any dependency on external API keys.
  - Files: `tests/e2e/test_results_page.py`, `tests/e2e/test_extraction.py`, `tests/e2e/conftest.py`
  - Do: (1) Update `test_responsive_grid_layout` docstring from "responsive grid layout" to "single-column layout". (2) Add a Playwright route-mocking fixture in conftest.py that intercepts the enrichment polling endpoint and returns canned provider results, triggering JS-side summary row creation. (3) Write new tests in `test_results_page.py` covering: enrichment slot present in online mode, `.ioc-summary-row` created after mocked enrichment, expand/collapse toggles `.is-open` on both summary row and details panel, `.enrichment-details` contains section containers, `.detail-link-footer` injected after enrichment complete, `.verdict-micro-bar` present, offline mode absence guards for these elements. (4) Run full suite.
  - Verify: `python3 -m pytest tests/e2e/ -q` → all pass, test count > 91
  - Done when: New tests exercise enrichment surface features, all tests pass, count is > 91

## Files Likely Touched

- `tests/e2e/pages/results_page.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_extraction.py`
- `tests/e2e/conftest.py`
