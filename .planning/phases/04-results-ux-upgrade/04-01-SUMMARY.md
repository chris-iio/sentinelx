---
phase: 04-results-ux-upgrade
plan: "01"
subsystem: ui
tags: [html-templates, css, playwright, e2e, jinja2, flask]

# Dependency graph
requires:
  - phase: 03-free-key-providers
    provides: registry.all() and registry.configured() methods used for provider_coverage
provides:
  - Enrichment slot template with chevron toggle button and .enrichment-details collapse container
  - Provider coverage row in verdict dashboard (registered/configured/needs_key counts)
  - CSS components for summary row, consensus badge, chevron animation, slide transition, detail rows, coverage row
  - ResultsPage POM extended with Phase 4 methods (summary_row, consensus_badge, chevron_toggle, detail_rows, enrichment_details, provider_coverage)
  - Structural E2E tests verifying offline mode has no enrichment slots and no provider coverage row
affects:
  - 04-02 (TypeScript enrichment.ts refactor targets the DOM structure created here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - enrichment-slot--loaded CSS class guard pattern — JS adds class, CSS reveals elements
    - max-height transition for collapse/expand (0 → 600px with ease-out-quart)
    - provider_coverage dict passed from routes.py to Jinja2 template via template_extras
    - Jinja2 {% if provider_coverage %} conditional renders coverage row only in online mode

key-files:
  created: []
  modified:
    - app/templates/partials/_enrichment_slot.html
    - app/templates/partials/_verdict_dashboard.html
    - app/routes.py
    - app/static/src/input.css
    - app/static/dist/style.css
    - tests/e2e/pages/results_page.py
    - tests/e2e/test_results_page.py

key-decisions:
  - "Shimmer skeleton preserved in enrichment slot — removed by JS on first result (existing behavior unchanged)"
  - "Chevron/details hidden via .enrichment-slot:not(.enrichment-slot--loaded) selector — JS toggles class when results arrive"
  - "provider_coverage computed inline in routes.py analyze() using len(registry.all()) and len(registry.configured())"
  - "Provider coverage row outside #verdict-dashboard div — avoids affecting KPI card layout"
  - "E2E tests verify absence (count=0) of new elements in offline mode — positive structural tests deferred to Plan 02 when JS populates them"

patterns-established:
  - "CSS guard pattern: hide element until parent has --loaded class (.parent:not(.parent--loaded) .child { display:none })"
  - "Template conditional: {% if provider_coverage %} — provider_coverage absent in offline mode, prevents stale zeros"

requirements-completed:
  - UX-04
  - UX-05

# Metrics
duration: 3min
completed: 2026-03-03
---

# Phase 4 Plan 01: Results UX Upgrade Summary

**HTML scaffolding and CSS components for the unified results UX — enrichment slot has chevron toggle and expandable .enrichment-details container, verdict dashboard has provider coverage row, and 9 new CSS component classes power the Phase 4 interaction design**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T13:19:49Z
- **Completed:** 2026-03-03T13:22:41Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Restructured `_enrichment_slot.html` to include chevron toggle button (with inline SVG) and `.enrichment-details` collapse container alongside the existing shimmer skeleton
- Added provider coverage row to `_verdict_dashboard.html` showing registered/configured/needs-key counts from the Flask route
- Extended `routes.py` `analyze()` to compute and pass `provider_coverage` dict in online mode using `registry.all()` and `registry.configured()`
- Added 9 new CSS component classes in `input.css`: `.ioc-summary-row`, `.ioc-summary-attribution`, `.consensus-badge` (3 variants), `.chevron-toggle`, `.chevron-icon`, `.enrichment-details`, `.provider-detail-row`, `.provider-detail-name`, `.provider-detail-stat`, `.provider-coverage-row`, `.coverage-sep`, `.coverage-stat--needs-key`
- Extended `ResultsPage` POM with 6 new methods: `summary_row()`, `consensus_badge()`, `chevron_toggle()`, `detail_rows()`, `enrichment_details()`, `provider_coverage`
- Added 2 Phase 4 structural E2E tests verifying offline mode has no enrichment slots and no provider coverage row

## Task Commits

Each task was committed atomically:

1. **Task 1: Restructure HTML templates and add provider coverage to backend** - `e6f0dd8` (feat)
2. **Task 2: Add CSS components and E2E POM methods for new results structure** - `d5f2f91` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/templates/partials/_enrichment_slot.html` - Added chevron toggle SVG button and .enrichment-details container
- `app/templates/partials/_verdict_dashboard.html` - Added provider coverage row below KPI cards
- `app/routes.py` - Added provider_coverage dict to template_extras in online mode
- `app/static/src/input.css` - Added all Phase 4 CSS components (summary row, consensus badge, chevron, slide, detail rows, coverage row)
- `app/static/dist/style.css` - Rebuilt minified output
- `tests/e2e/pages/results_page.py` - Extended ResultsPage POM with Phase 4 methods
- `tests/e2e/test_results_page.py` - Added Phase 4 structural offline-mode E2E tests

## Decisions Made
- Shimmer skeleton preserved in enrichment slot — removed by JS on first result (existing behavior unchanged). This keeps loading state working while Plan 02 adds the JS that populates the new structure.
- Chevron and details hidden via CSS guard pattern (`.enrichment-slot:not(.enrichment-slot--loaded) .chevron-toggle { display: none }`) rather than inline `style` attributes — keeps behavior in CSS where it belongs.
- `provider_coverage` computed inline in `analyze()` using `len(registry.all())` and `len(registry.configured())` — no new registry methods needed.
- Provider coverage row placed outside `#verdict-dashboard` div to avoid affecting KPI card grid layout.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

3 pre-existing E2E test failures confirmed unrelated to this plan's changes:
- `test_page_title` (test_homepage.py) — page title is `sentinelx` but test expects `SentinelX — IOC Extractor`
- `test_back_link_returns_to_index` (test_navigation.py) — selector `h1.input-title` not found
- `test_results_page_has_back_link_on_no_results` (test_navigation.py) — same selector issue

All 3 failures confirmed pre-existing via `git stash` verification. Logged to deferred items. All 542 - 3 = 539 tests pass (17/17 new E2E tests in test_results_page.py pass, 25/25 route tests pass).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- DOM targets for Plan 02's TypeScript refactor are in place: `.enrichment-slot`, `.chevron-toggle`, `.enrichment-details`, `.ioc-summary-row`
- CSS is compiled and all classes are defined — Plan 02's TS can immediately use them
- ResultsPage POM methods are ready for Plan 02's E2E interaction tests (chevron click, expand/collapse, summary row content)
- `provider_coverage` template variable is live — coverage row renders in online mode

---
*Phase: 04-results-ux-upgrade*
*Completed: 2026-03-03*

## Self-Check: PASSED

- FOUND: `app/templates/partials/_enrichment_slot.html`
- FOUND: `app/templates/partials/_verdict_dashboard.html`
- FOUND: `app/routes.py`
- FOUND: `app/static/src/input.css`
- FOUND: `tests/e2e/pages/results_page.py`
- FOUND: `tests/e2e/test_results_page.py`
- FOUND: `.planning/phases/04-results-ux-upgrade/04-01-SUMMARY.md`
- FOUND commit: `e6f0dd8` (Task 1)
- FOUND commit: `d5f2f91` (Task 2)
