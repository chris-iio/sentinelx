---
phase: 13-results-page-redesign
plan: "01"
subsystem: ui
tags: [jinja2, templates, partials, e2e, playwright]

# Dependency graph
requires:
  - phase: 12-shared-component-elevation
    provides: "Base CSS component classes (.ioc-card, .filter-bar-wrapper, .verdict-dashboard) used in extracted partials"
provides:
  - "5 Jinja2 partial templates in app/templates/partials/ for independent editability"
  - "Slim results.html orchestrator using {% include %} for each section"
  - "test_header_branding E2E test fixed to match Phase 12 tagline change"
affects: [13-02-PLAN, 13-03-PLAN, 13-04-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 partial include pattern — conditional logic stays in parent, unconditional content in partial"
    - "Nested include: _ioc_card.html includes _enrichment_slot.html for inner card content"

key-files:
  created:
    - app/templates/partials/_empty_state.html
    - app/templates/partials/_verdict_dashboard.html
    - app/templates/partials/_filter_bar.html
    - app/templates/partials/_enrichment_slot.html
    - app/templates/partials/_ioc_card.html
  modified:
    - app/templates/results.html
    - tests/e2e/test_homepage.py

key-decisions:
  - "All {% if %} guards stay in results.html — partials contain unconditional content only"
  - "Nested include: _ioc_card.html uses {% include 'partials/_enrichment_slot.html' %} for the spinner div"
  - "JS contracts preserved exactly: all IDs, data-attributes, class names unchanged character-for-character"

patterns-established:
  - "Jinja2 include inheritance: partials automatically receive all render_template() context variables"
  - "Partial file naming convention: _snake_case.html with leading underscore in app/templates/partials/"

requirements-completed: [RESULTS-01]

# Metrics
duration: 2min
completed: "2026-02-28"
---

# Phase 13 Plan 01: Extract results.html into Jinja2 Partials Summary

**results.html split into 5 independently-editable Jinja2 partials with all JS contracts preserved and test_header_branding fixed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T06:25:44Z
- **Completed:** 2026-02-28T06:27:59Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Extracted monolithic results.html (162 lines) into 5 partial template files in app/templates/partials/
- results.html is now a slim 70-line orchestrator using {% include %} for all major sections
- All JS contracts preserved exactly — IDs, data-attributes, and class names unchanged
- Fixed pre-existing test_header_branding E2E failure from Phase 12 tagline change
- 57 E2E tests pass; only 2 known pre-existing VT API key failures remain

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract Jinja2 template partials from results.html** - `3182de4` (refactor)
2. **Task 2: Fix pre-existing test_header_branding test failure** - `05b7281` (fix)

## Files Created/Modified
- `app/templates/partials/_empty_state.html` — No-results div with hint text
- `app/templates/partials/_verdict_dashboard.html` — Verdict dashboard with data-verdict-count spans for JS updates
- `app/templates/partials/_filter_bar.html` — Sticky filter bar with verdict buttons, type pills, and search input
- `app/templates/partials/_enrichment_slot.html` — Spinner-wrapper div for pending enrichment (JS removes .spinner-wrapper class)
- `app/templates/partials/_ioc_card.html` — Full IOC card with nested {% include 'partials/_enrichment_slot.html' %}
- `app/templates/results.html` — Slimmed orchestrator: conditional logic + {% include %} calls
- `tests/e2e/test_homepage.py` — Updated tagline expectation from "Offline IOC Extractor" to "IOC Triage Tool"

## Decisions Made
- All `{% if %}` guards (mode checks, no_results check) remain in results.html — partials contain unconditional content. This keeps the conditional logic centralized and partials reusable.
- _ioc_card.html uses a nested `{% include "partials/_enrichment_slot.html" %}` wrapped in the existing `{% if mode == "online" and job_id %}` guard (which stays in results.html context, inherited by the partial).
- The enrichment slot `{% if %}` guard stays in the card partial itself (not results.html) because the card is the natural owner of its own conditional inner content.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — extraction was straightforward. Jinja2 include inherits the full render context automatically, so no variable passing was needed.

## Next Phase Readiness
- All 5 partials in place and independently editable — Plans 02 and 03 can now modify individual partials without touching results.html
- test_header_branding fixed — full E2E baseline is clean (57 passing, 2 known VT skips)
- No blockers

---
*Phase: 13-results-page-redesign*
*Completed: 2026-02-28*
