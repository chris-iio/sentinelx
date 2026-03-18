---
id: S05
parent: M002
milestone: M002
provides:
  - Updated ResultsPage page object (266 lines) with 18+ new locators and 5 helpers for S01–S04 enrichment surface
  - 8 new E2E tests exercising inline expand/collapse, enrichment summary rows, verdict micro-bar, detail link injection, enrichment-slot loaded state, and offline-mode guard
  - Playwright route-mocking infrastructure (MOCK_ENRICHMENT_RESPONSE_8888, setup_enrichment_route_mock, mocked_enrichment fixture) in conftest.py
  - 99 total passing E2E tests (up from 91 baseline, +8.8% coverage increase)
requires:
  - slice: S04
    provides: Final DOM structure and selector contract — .ioc-summary-row, .enrichment-details, .enrichment-slot, .enrichment-slot--loaded, .chevron-icon-wrapper, .verdict-micro-bar, .staleness-badge, .detail-link-footer, .detail-link, .is-open, .enrichment-section
affects:
  - downstream (milestone complete)
key_files:
  - tests/e2e/pages/results_page.py
  - tests/e2e/test_results_page.py
  - tests/e2e/conftest.py
  - tests/e2e/test_extraction.py
key_decisions:
  - Used regex class-match r".*is-open.*" in expand_row/collapse_row assertions to handle co-existing CSS classes
  - Route mock registered BEFORE navigation in _navigate_online_with_mock() — critical to avoid racing against first poll tick (750ms)
  - Used **/enrichment/status/** (double glob) in page.route() to match across path segments regardless of Playwright glob handling
  - Detail link href asserts /detail/ not /ioc/ — actual Flask route is /detail/<ioc_type>/<ioc_value>
patterns_established:
  - Card-scoped locator helpers use data-ioc-value attribute selector to target specific card then chain descendant selector — robust without numeric indexing
  - setup_enrichment_route_mock(page) call-before-navigate pattern — always register Playwright route intercepts before the page action that triggers the fetch
  - _navigate_online_with_mock() waits for .ioc-summary-row before returning ResultsPage — stable DOM state for all callers
observability_surfaces:
  - "python3 -m pytest tests/e2e/ -q → 99 passed (0 failures)"
  - "python3 -m pytest tests/e2e/ -q --co | grep -c '::test_' → 99"
  - "python3 -m pytest tests/e2e/test_results_page.py -q -k 'enrichment or expand or summary_row or detail_link' → 9 passed"
  - "wc -l tests/e2e/pages/results_page.py → 266"
drill_down_paths:
  - .gsd/milestones/M002/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S05/tasks/T02-SUMMARY.md
duration: ~38 minutes (T01: 3m, T02: ~35m)
verification_result: passed
completed_at: 2026-03-18
---

# S05: E2E test suite update

**Expanded the E2E suite from 91 to 99 passing tests with a Playwright route-mocking infrastructure that covers all S01–S04 enrichment surface elements.**

## What Happened

S04 left a stable DOM contract but zero test coverage of the enrichment surface it introduced — inline expand/collapse, summary rows, micro-bar, detail links, staleness badges, and section containers had never been touched by the automated suite. S05 closed this gap in two tasks.

**T01** rewrote `results_page.py` from 118 to 266 lines, adding 18+ new locator properties and 5 helper methods covering every S01–S04 DOM element. All existing locators and methods were preserved unchanged. The additions are purely additive — no selector renaming, no behavioral changes. The card-scoped helpers (`summary_row_for_card`, `enrichment_details_for_card`) use `data-ioc-value` attribute targeting rather than numeric indexing, which makes them stable against reordering. The `expand_row`/`collapse_row` helpers use `to_have_class(r".*is-open.*")` regex to survive co-existing classes. The 91 existing tests passed without modification.

**T02** built the route-mocking infrastructure and added 8 new tests. The conftest additions give every test the ability to intercept `/enrichment/status/**` polling and return canned provider results (`VirusTotal` + `AbuseIPDB` for `8.8.8.8/ipv4`, `complete: true`) without any external API dependency. The `_navigate_online_with_mock()` helper (in `test_results_page.py`) encapsulates the full online-mode setup: register mock → navigate → submit IOC → wait for `.ioc-summary-row` — ensuring callers always receive a stable enriched DOM state. One correction was needed: the plan assumed detail links would contain `/ioc/`; the actual Flask route generates `/detail/<ioc_type>/<ioc_value>`, so the assertion was fixed to check for `/detail/`.

The 8 new tests cover:
1. Enrichment slot count equals IOC card count in online mode
2. `.ioc-summary-row` appears inside `.ioc-card` after polling
3. `.verdict-micro-bar` present after mock
4. Expand/collapse toggles `.is-open` on both row and details panel; second click removes it
5. Expanded panel contains at least one `.enrichment-section`
6. `.detail-link-footer` and `.detail-link` injected with href containing `/detail/`
7. `.enrichment-slot--loaded` count ≥ 1 after mock
8. Offline mode shows zero `.ioc-summary-row` elements (guard test)

## Verification

All three slice-level verification checks passed:

| Check | Command | Result |
|-------|---------|--------|
| Full suite pass | `python3 -m pytest tests/e2e/ -q` | ✅ 99 passed, 0 failed (31.33s) |
| Count ≥ 91 | `python3 -m pytest tests/e2e/ -q --co \| grep -c '::test_'` | ✅ 99 |
| Enrichment tests | `-k "enrichment or expand or summary_row or detail_link"` | ✅ 9 passed (8.21s) |

## Requirements Advanced

- R011 — E2E suite updated with all new S01–S04 selectors; page object expanded from 118 to 266 lines; test count increased from 91 to 99

## Requirements Validated

- R011 — `python3 -m pytest tests/e2e/ -q` → 99 passed, 0 failed; count 99 > 91 baseline; all enrichment surface elements covered; no tests removed

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

**Detail link href path** — The S05 plan stated detail link hrefs should contain `/ioc/`. The actual Flask route generates `/detail/<ioc_type>/<ioc_value>`. Test assertion corrected to check for `/detail/`. No coverage impact — the assertion still validates that `injectDetailLink()` produces a correctly formed working URL. This deviation was recorded in KNOWLEDGE.md (SentinelX detail link route entry).

## Known Limitations

None. All must-haves from the slice plan are delivered:
- ResultsPage page object has locators for all 11+ new DOM elements listed in the plan ✓
- `expand_row`, `collapse_row`, `is_row_expanded` helpers present ✓
- New tests exercise inline expand/collapse, enrichment summary row, detail link, micro-bar, offline guard ✓
- `test_responsive_grid_layout` docstring updated to reference single-column layout ✓
- All 91 original tests still pass ✓
- Test count increased to 99 (+8) ✓

## Follow-ups

- none — S05 is the final M002 slice; milestone is complete

## Files Created/Modified

- `tests/e2e/pages/results_page.py` — expanded from 118 to 266 lines; 18+ new locator properties, 5 new helper methods, updated module docstring; all existing code preserved intact
- `tests/e2e/test_results_page.py` — 8 new enrichment surface tests + `_navigate_online_with_mock()` helper + `SINGLE_IP_IOC` constant
- `tests/e2e/conftest.py` — `MOCK_ENRICHMENT_RESPONSE_8888`, `setup_enrichment_route_mock()`, and `mocked_enrichment` fixture added
- `tests/e2e/test_extraction.py` — `test_responsive_grid_layout` docstring updated from "responsive grid layout" to "single-column layout"

## Forward Intelligence

### What the next slice should know
- This is the final M002 slice. The milestone is complete. No downstream slices depend on S05.
- The Playwright route-mocking infrastructure in conftest.py (`setup_enrichment_route_mock`, `mocked_enrichment`, `MOCK_ENRICHMENT_RESPONSE_8888`) is production-quality and reusable for any future enrichment surface work without modification.
- `_navigate_online_with_mock()` in test_results_page.py is the canonical pattern for any test needing a fully enriched DOM state — it encapsulates register-before-navigate, submit, and wait-for-stable-DOM.

### What's fragile
- The `**/enrichment/status/**` route glob pattern — if the Flask URL structure for the enrichment status endpoint changes, tests will silently fail to intercept requests and enrichment slots will remain in unloaded state. Diagnostic: `loaded_enrichment_slots.count()` returns 0.
- The `expand_row()` helper depends on event delegation on `.page-results` (D018). If `wireExpandToggles()` in enrichment.ts is ever refactored away from delegation, expand/collapse tests will silently pass or fail depending on race conditions.

### Authoritative diagnostics
- `python3 -m pytest tests/e2e/ -q` — full pass/fail verdict, single command
- `page.locator('.enrichment-slot--loaded').count()` in REPL — if 0, route mock was not triggered (check glob pattern vs actual URL)
- `--tracing on` + Playwright trace inspector → network tab confirms whether `/enrichment/status/` requests were intercepted

### What assumptions changed
- `/ioc/` href in detail links → actual route is `/detail/<ioc_type>/<ioc_value>`. Always inspect actual Flask route table or live DOM before writing URL-content assertions.
