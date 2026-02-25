---
phase: 07-filtering-search
plan: 02
subsystem: testing
tags: [playwright, e2e, alpine.js, csp, vanilla-js, filtering]

# Dependency graph
requires:
  - phase: 07-filtering-search
    plan: 01
    provides: Filter bar HTML and CSS in results.html, data-verdict/data-ioc-type/data-ioc-value attributes on cards

provides:
  - E2E tests for all 4 FILTER requirements covering verdict/type/search/sticky
  - Fixed Alpine CSP incompatibility: replaced Alpine directives with vanilla JS initFilterBar()
  - ResultsPage POM with filter bar selectors and actions
  - Vanilla JS filter bar that works in strict CSP environment (no unsafe-inline, no unsafe-eval)

affects: [08, 09, 10, e2e-tests, results-page, main-js]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Vanilla JS filter state machine with applyFilter() on each state change
    - data-filter-verdict/data-filter-type attributes on buttons drive JS click handlers
    - filter-btn--active/filter-pill--active CSS classes toggled by JS (not Alpine :class)
    - Alpine CSP build limitation: does not support $el, $event, or function call args in templates

key-files:
  created:
    - tests/e2e/test_results_page.py
  modified:
    - tests/e2e/pages/results_page.py
    - app/templates/results.html
    - app/static/main.js
    - app/templates/base.html

key-decisions:
  - "Alpine CSP build (alpine.csp.min.js) cannot evaluate inline JS expressions — x-data inline objects, $el, $event, and function call args are all unsupported; replaced entire filter with vanilla JS"
  - "Vanilla JS initFilterBar() reads data-filter-verdict/data-filter-type attributes from buttons; toggles filter-btn--active class; sets card.style.display via DOM property (not blocked by CSP)"
  - "script loading order matters: main.js must load before alpine.csp.min.js so alpine:init listener fires before Alpine processes DOM"

patterns-established:
  - "When Alpine CSP build is in use, only zero-arg method calls and simple property access work in templates — use vanilla JS or data attributes for anything more complex"
  - "filter-btn--active and filter-pill--active are CSS class names toggled by initFilterBar() — not by Alpine :class bindings"

requirements-completed: [FILTER-01, FILTER-02, FILTER-03, FILTER-04]

# Metrics
duration: 16min
completed: 2026-02-25
---

# Phase 7 Plan 02: E2E Filter Tests and Alpine CSP Fix Summary

**13 E2E tests covering all 4 FILTER requirements, plus auto-fixed Alpine CSP incompatibility by replacing Alpine reactive filtering with pure vanilla JS initFilterBar()**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-02-25T07:44:18Z
- **Completed:** 2026-02-25T07:59:58Z
- **Tasks:** 1 complete (Task 2 awaiting human verification)
- **Files modified:** 5

## Accomplishments
- Added `initFilterBar()` to `main.js`: pure vanilla JS filter state machine that reads `data-filter-verdict` / `data-filter-type` attributes from buttons and toggles `filter-btn--active` / `filter-pill--active` classes
- Updated `results.html` to remove Alpine directives (x-data, x-show, x-model, :class, @click with args) and use plain HTML attributes consumed by vanilla JS
- Added 11 properties/methods to the `ResultsPage` POM for filter bar interaction
- Created `tests/e2e/test_results_page.py` with 13 tests covering: filter bar rendering, verdict filtering, type pill filtering, text search, combined filters, and sticky positioning
- All 13 filter tests pass; 279/281 total tests pass (2 pre-existing VT API key failures)

## Task Commits

1. **Task 1: Add E2E tests for filter bar + fix Alpine CSP incompatibility** - `533b4b8` (feat)

## Files Created/Modified
- `tests/e2e/test_results_page.py` - New file: 13 E2E filter tests using ResultsPage POM
- `tests/e2e/pages/results_page.py` - Added filter_bar, filter_verdict_buttons, filter_by_verdict, filter_type_pills, filter_by_type, search_input, search, visible_cards, hidden_cards, dashboard_badges, click_dashboard_badge
- `app/templates/results.html` - Replaced Alpine directives with data-filter-verdict/data-filter-type attributes, removed x-data/x-show/x-model, added id=filter-search-input
- `app/static/main.js` - Added ~90-line initFilterBar() function, removed Alpine.data() registration code, updated feature comment block
- `app/templates/base.html` - Changed script order: main.js before alpine.csp.min.js

## Decisions Made
- Replaced Alpine-based filtering with pure vanilla JS because the Alpine CSP build doesn't support any of the expression types needed: `x-data` inline objects fail, `:class` with function calls fail, `@click` with args fails, `$el` and `$event` magic properties are not supported
- `card.style.display = "none"` via JavaScript DOM is NOT blocked by CSP `style-src 'self'` (CSP only blocks inline `style=""` HTML attributes and `<style>` blocks, not JS DOM property writes)
- Kept Alpine loaded in base.html for potential future CSP-safe uses, but it's dormant on results page

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Alpine CSP incompatibility — filter bar non-functional as shipped**
- **Found during:** Task 1 (E2E test execution — all cards showed `display:none`)
- **Issue:** The Alpine CSP build (`alpine.csp.min.js`) cannot evaluate inline JavaScript in `x-data` attribute expressions, function calls with string arguments in `:class`/`@click`, or magic properties `$el`/`$event`. The filter bar shipped in Phase 7 Plan 01 used inline `x-data="{...}"` with a `cardVisible(card)` function — none of this works in CSP mode. All 5 cards were permanently hidden (`display:none`) and the filter buttons had no effect.
- **Fix:** Replaced the entire Alpine-based filter interaction with `initFilterBar()` in `main.js` — a pure vanilla JS function that attaches click listeners to buttons via `data-filter-verdict`/`data-filter-type` attributes, and toggles card visibility via `element.style.display`. Updated `results.html` to use plain HTML attributes (no Alpine directives). Changed script loading order in `base.html` so `main.js` loads before Alpine.
- **Files modified:** `app/templates/results.html`, `app/static/main.js`, `app/templates/base.html`
- **Verification:** 13 E2E tests pass; verified via Playwright that clicking filter buttons correctly shows/hides cards in real browser
- **Committed in:** 533b4b8 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** The filter bar would have appeared to work in development (plain `alpine.min.js` supports eval) but was completely non-functional with the CSP build. The fix was necessary for correctness. No scope creep — the E2E tests were the planned deliverable, and fixing the underlying bug was required to make the tests pass.

## Issues Encountered
- Test assertion had wrong assumption: `test_combined_type_and_search_filters` initially searched "8" expecting 2 results (8.8.8.8 and 1.1.1.1), but 1.1.1.1 contains no "8". Fixed test to search "1.1" and "8.8" instead.
- `test_filter_bar_has_sticky_position` was flaky in full test suite (passed in isolation). Added explicit `expect(results.filter_bar).to_be_visible()` before the CSS check to ensure the test is on the right page.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Filter bar is fully functional in both online and offline modes
- All 4 FILTER requirements verified by E2E tests
- Vanilla JS approach is CSP-compatible and doesn't require Alpine for filtering
- Alpine is still loaded but dormant — available for future CSP-safe directive use
- Awaiting human visual verification (Task 2 checkpoint)

---
*Phase: 07-filtering-search*
*Completed: 2026-02-25*

## Self-Check: PASSED

All created/modified files verified present. Commit verified in git log.

- `tests/e2e/test_results_page.py` — FOUND
- `tests/e2e/pages/results_page.py` — FOUND
- `app/templates/results.html` — FOUND
- `app/static/main.js` — FOUND
- `app/templates/base.html` — FOUND
- `.planning/phases/07-filtering-search/07-02-SUMMARY.md` — FOUND
- `533b4b8` (Task 1 commit) — FOUND
