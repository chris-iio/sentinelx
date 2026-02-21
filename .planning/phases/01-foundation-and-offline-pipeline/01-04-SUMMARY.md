---
phase: 01-foundation-and-offline-pipeline
plan: 04
subsystem: ui
tags: [flask, jinja2, csrf, csp, dark-theme, accordion, clipboard, integration-tests, security]

# Dependency graph
requires:
  - phase: 01-01
    provides: Flask app factory, security scaffold (TRUSTED_HOSTS, MAX_CONTENT_LENGTH, CSP, CSRF, debug=False)
  - phase: 01-02
    provides: normalize() and classify() functions
  - phase: 01-03
    provides: run_pipeline(text) — full offline extraction pipeline
    also: group_by_type(iocs) from models
provides:
  - GET / route rendering index.html (paste form)
  - POST /analyze route wiring run_pipeline -> group_by_type -> results.html
  - Dark theme HTML/CSS/JS analyst UI
  - 14 integration tests covering all security properties and functional behavior
  - 94% total test coverage (125 tests passing)
affects:
  - Phase 2 (online enrichment will extend POST /analyze with API calls under ALLOWED_API_HOSTS guard)
  - All future UI plans (base.html layout is the design foundation)

# Tech tracking
tech-stack:
  added: []  # All libraries already in requirements.txt
  patterns:
    - Blueprint route pattern: separate blueprint registered in create_app
    - Template inheritance: base.html -> index.html / results.html
    - CSP-compliant JS: all event handlers in external main.js, no inline scripts
    - Accordion without JS: <details>/<summary> elements with open attribute
    - Clipboard copy: navigator.clipboard.writeText() with execCommand fallback

key-files:
  created:
    - app/templates/base.html (dark theme scaffold, external CSS/JS, no inline scripts)
    - app/templates/index.html (textarea, mode select, CSRF token, submit/clear buttons)
    - app/templates/results.html (mode indicator, IOC accordion groups, copy buttons, no-results state)
    - app/static/style.css (dark theme, CSS custom properties, type accent colors, 548 lines)
    - app/static/main.js (clipboard copy, submit disable on empty, clear button)
    - tests/test_routes.py (14 integration tests)
  modified:
    - app/routes.py (full implementation replacing placeholder stubs)
    - app/__init__.py (added ALLOWED_API_HOSTS to app config, SEC-16)

key-decisions:
  - "ALLOWED_API_HOSTS exposed in app config for SEC-16 SSRF prevention structure — empty list in Phase 1, Phase 2 adds entries before any outbound calls"
  - "results.html uses <details>/<summary> accordion — no JavaScript needed for expand/collapse, all sections open by default"
  - "main.js uses navigator.clipboard.writeText() with execCommand fallback for non-HTTPS contexts"

patterns-established:
  - "Template inheritance: base.html provides layout, child templates extend with {% block content %}"
  - "No | safe filter anywhere in templates — all IOC values rendered via {{ ioc.value }} with Jinja2 autoescaping"
  - "External JS only: all DOM event listeners attached from main.js, zero inline onclick/onchange attributes"
  - "IOC type accent colors defined as CSS custom properties in :root for consistency across all IOC type groups"

requirements-completed: [UI-01, UI-02, UI-04, UI-07, SEC-16]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 1 Plan 04: Routes, Templates, and Integration Tests Summary

**Flask route wiring run_pipeline to dark-theme Jinja2 UI with accordion IOC groups, CSP-compliant external JS, CSRF form protection, and 14 security integration tests proving all SEC requirements end-to-end**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T08:37:06Z
- **Completed:** 2026-02-21T08:40:54Z
- **Tasks:** 2 auto (checkpoint:human-verify pending user confirmation)
- **Files modified:** 8

## Accomplishments

- `POST /analyze` calls `run_pipeline(text)`, groups results with `group_by_type()`, renders `results.html` — full pipeline-to-UI wire-up in offline mode with zero outbound calls
- Dark theme UI: input page with defanged IOC placeholder examples, offline/online mode select, extract/clear buttons; results page with accordion sections, count badges, type-specific accent colors, copy buttons
- 14 integration tests: functional (GET/, POST/analyze, grouping, dedup), security (413, 400 bad host, CSRF, CSP, debug=False, no HTTP calls), edge cases (empty input, no IOCs)
- 94% total coverage across 125 tests, 100% on routes.py and __init__.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement routes and integration tests** - `57fe625` (feat)
2. **Task 2: Build templates and static assets** - `81f330f` (feat)

_Task 3 (checkpoint:human-verify) pending user visual confirmation_

## Files Created/Modified

- `app/routes.py` - Full implementation: GET / renders index.html; POST /analyze runs pipeline and renders results.html with grouped IOCs
- `app/__init__.py` - Added ALLOWED_API_HOSTS to app config (SEC-16 structure)
- `app/templates/base.html` - HTML5 dark theme scaffold with external CSS/JS links, no inline scripts
- `app/templates/index.html` - Paste form: textarea with defanged examples placeholder, offline/online mode select, CSRF token, Extract IOCs submit (disabled when empty), clear button
- `app/templates/results.html` - Mode indicator banner, IOC groups in `<details>/<summary>` (all open), count badges, normalized value + original + copy button table, no-results friendly message
- `app/static/style.css` - Dark theme (--bg-primary #0d1117), CSS custom properties for all accent colors, monospace IOC values, 548 lines
- `app/static/main.js` - navigator.clipboard.writeText() with execCommand fallback, submit button disable/enable on textarea input, clear button handler
- `tests/test_routes.py` - 14 integration tests

## Decisions Made

- ALLOWED_API_HOSTS exposed in app config from config.py to satisfy SEC-16 structural requirement. In Phase 1, it is an empty list (no outbound calls). Phase 2 will populate it before adding any enrichment calls.
- `<details>/<summary>` chosen for accordion — native HTML5, no JavaScript required, all sections `open` by default as specified. Avoids any CSP complexity.
- `navigator.clipboard.writeText()` with `execCommand("copy")` fallback ensures clipboard works in both HTTPS and HTTP (localhost) contexts.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The app is running on port 5000 (or can be started with `source .venv/bin/activate && python run.py`).

## Next Phase Readiness

- Full offline IOC extraction UI is functional: paste text, see grouped results, copy IOC values
- POST /analyze is ready for Phase 2 to extend with online enrichment calls (gated by ALLOWED_API_HOSTS)
- All security properties verified by integration tests and live curl checks
- Human visual verification (Task 3 checkpoint) pending

No blockers.

## Self-Check: PASSED

All created files verified present. All task commits verified in git history (57fe625, 81f330f).
