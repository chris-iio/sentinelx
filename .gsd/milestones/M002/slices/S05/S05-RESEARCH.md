# S05 — Research

**Date:** 2026-03-18

## Summary

S05 is a light, mechanical slice: update the `ResultsPage` page object to expose new S01–S04 DOM elements, update any tests whose assertions no longer match the new layout, and confirm 91/91 pass. The page object pattern already isolates all selectors — test logic should survive with minimal changes.

The current 91/91 pass (from S04) proves that existing selectors still work because D015 preserved all original class names. The gap is **coverage**, not breakage: the page object has no locators for `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.detail-link-footer`, `.ioc-summary-attribution`, or the `.is-open` expand state. No existing tests exercise inline expand or at-a-glance enrichment surface features. S05 should add page object methods for these new surfaces and write tests that exercise them. One existing test (`test_responsive_grid_layout`) references "responsive grid layout" in its name/docstring but only asserts `#ioc-cards-grid` visibility — the docstring should be updated to match the new single-column layout, but the assertion is still valid since the `#ioc-cards-grid` element persists.

No selector renames, no file restructuring, no technology changes. This is adding locators and tests using established Playwright patterns already in the codebase.

## Recommendation

**Two-task approach:**

1. **T01: Update `results_page.py` page object** — Add locators and helper methods for new enrichment surface elements. Update the module docstring. This is a pure page-object edit with no test changes.

2. **T02: Add new tests + update existing tests** — Write new E2E tests for the inline expand, enrichment summary row, and detail link features (requires online mode stub or offline-mode absence checks). Update `test_responsive_grid_layout` docstring. Run full 91+ suite.

## Implementation Landscape

### Key Files

- `tests/e2e/pages/results_page.py` — Page object (118 lines). Needs new locators for: `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge`, `.detail-link-footer`, `.ioc-summary-attribution`, `.is-open` state, `.enrichment-slot`, `.enrichment-slot--loaded`. Needs helper methods for expand/collapse interaction.
- `tests/e2e/test_results_page.py` (284 lines) — Filter/UX tests. `test_responsive_grid_layout` docstring needs update ("single-column layout" not "responsive grid"). Add structural tests for enrichment slot absence in offline mode (already exists), and new tests for enrichment surface elements in online mode or offline-mode absence guards.
- `tests/e2e/test_extraction.py` (283 lines) — IOC extraction tests. Uses `ResultsPage` heavily. `test_responsive_grid_layout` lives here (line 275). No selector changes needed — all used selectors (`.ioc-card`, `.ioc-value`, `.verdict-label`, `.ioc-type-badge`, `.ioc-original`, `#verdict-dashboard`) are stable per D015.
- `tests/e2e/test_copy_buttons.py` (78 lines) — Uses `results.copy_buttons()`. No changes needed — `.copy-btn[data-value]` is stable.
- `tests/e2e/test_navigation.py` (61 lines) — Uses `results.back_link`, `results.go_back()`, `results.expect_no_results()`, `results.expect_total_count()`. No changes needed.
- `tests/e2e/conftest.py` — Fixtures. May need review for online-mode test fixtures if new tests require enrichment data. Check if an online-mode fixture exists.
- `app/templates/partials/_ioc_card.html` — Source of truth for server-rendered DOM structure.
- `app/templates/partials/_enrichment_slot.html` — Source of truth for enrichment container structure (`.enrichment-slot`, `.enrichment-details`, section containers).
- `app/static/src/ts/modules/row-factory.ts` — Source of truth for JS-created DOM (`.ioc-summary-row`, `.verdict-micro-bar`, `.chevron-icon-wrapper`, `.staleness-badge`, provider detail rows).
- `app/static/src/ts/modules/enrichment.ts` — Source of truth for `.detail-link-footer`, `.enrichment-slot--loaded`, `.is-open` toggle, `wireExpandToggles()`.

### Build Order

1. **T01 first** — Update the page object with all new locators. This unblocks T02 because tests import from `results_page.py`.
2. **T02 second** — Add new tests + update existing tests. Run full suite at the end.

### Verification Approach

- `python3 -m pytest tests/e2e/ -q` → must be ≥ 91 tests, all passing. The count will increase if new tests are added.
- `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` — count tests collected before running.
- No `make typecheck` needed (Python only, no TS changes).
- No `make css` or `make js` needed (no source changes outside tests/).

## Constraints

- **Online-mode tests require API keys** — tests that need enrichment data flowing in (to verify `.ioc-summary-row`, `.enrichment-details` expansion) require either a real API key or a mock server. The codebase currently skips online enrichment tests by default. New tests for enrichment surface elements should either: (a) test their **absence** in offline mode (cheap, no API needed), or (b) use Playwright route mocking to intercept enrichment API calls if testing presence/interaction.
- **`python3` not `python`** — the system PATH does not have `python` aliased (per S04 forward intelligence).
- **All 91 tests must keep passing** — no coverage reduction. Test count should go up (new tests), never down.
- **The page title is `"sentinelx"` (all-lowercase)** — per D021. Any new test asserting the title must use lowercase.

## Common Pitfalls

- **Testing enrichment surface in offline mode** — In offline mode, `_enrichment_slot.html` is not rendered at all (conditional `{% if mode == "online" and job_id %}`). New tests must not assert `.enrichment-slot` presence in offline mode — the existing `test_offline_mode_cards_have_no_enrichment_slot` already covers this correctly. Any enrichment surface test needs online mode + either a real API key or route mocking.
- **`.ioc-summary-row` is JS-created, not server-rendered** — It only exists after `enrichment.ts` creates it during polling. Tests that check for this element need to wait for enrichment to produce at least one result. The element does not exist in the initial DOM.
- **Expand/collapse state is CSS class `.is-open`** — Testing expand requires clicking `.ioc-summary-row` and then asserting `.is-open` class presence on both the summary row and its sibling `.enrichment-details`.
