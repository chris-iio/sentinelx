---
phase: 02-core-enrichment
plan: 03
subsystem: ui
tags: [flask, jinja2, configstore, virustotal, threading, polling, background-thread]

# Dependency graph
requires:
  - phase: 02-01
    provides: VTAdapter for IOC enrichment
  - phase: 02-02
    provides: EnrichmentOrchestrator with parallel execution and job tracking

provides:
  - Settings page (GET/POST /settings) for VT API key management via ConfigStore
  - Online-mode /analyze with background enrichment and non-blocking job_id response
  - GET /enrichment/status/<job_id> polling endpoint returning JSON with provider, verdict, scan_date
  - Navigation link to /settings in base.html header

affects: [03-additional-enrichment-providers, 04-ui-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level _orchestrators dict as job registry (job_id -> orchestrator)
    - Flask flash() + get_flashed_messages() for success/error feedback
    - daemon=True thread prevents blocking Flask on enrichment (Pitfall 4)
    - _mask_key() reveals only last 4 chars of stored API key for display

key-files:
  created:
    - app/templates/settings.html
    - tests/test_settings.py
  modified:
    - app/routes.py
    - app/templates/base.html
    - app/templates/index.html
    - tests/test_routes.py

key-decisions:
  - "Module-level _orchestrators dict stores job_id -> orchestrator — allows polling endpoint to look up running jobs without Flask app context"
  - "daemon=True on enrichment thread — prevents orphaned threads blocking process exit (Pitfall 4)"
  - "API key masking reveals only last 4 chars — confirms key is saved without exposing full value"
  - "Empty/whitespace-only API key rejected at POST /settings before reaching ConfigStore"

patterns-established:
  - "Flash messages for route-level user feedback (success/error on form submit)"
  - "Redirect-after-POST pattern for all settings form submissions"
  - "JSON polling endpoint with 404 for unknown jobs"

requirements-completed: [UI-03, ENRC-05]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 2 Plan 03: Flask Routes Wiring Summary

**Settings page with VT API key management, online-mode /analyze launching background enrichment via daemon Thread, and /enrichment/status polling endpoint returning provider/verdict/scan_date JSON**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T09:55:21Z
- **Completed:** 2026-02-21T09:58:31Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Settings page (GET/POST /settings) saves and retrieves VT API key via ConfigStore with masking
- Online-mode POST /analyze checks for configured API key, runs pipeline, launches enrich_all in daemon thread, returns job_id immediately
- GET /enrichment/status/<job_id> returns JSON with total, done, complete, and serialized results (provider name, verdict, scan_date per ENRC-05)
- Navigation Settings link added to base.html header
- 11 new settings tests + 8 new route tests; full suite at 187 tests, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Settings page and API key management routes** - `9ff3f22` (feat)
2. **Task 2: Online-mode /analyze with background enrichment and polling endpoint** - `cfa2a5e` (feat)

## Files Created/Modified

- `app/routes.py` - Added settings routes (GET/POST /settings), online-mode /analyze with background Thread, /enrichment/status polling endpoint, _mask_key() helper, _orchestrators registry
- `app/templates/settings.html` - Settings page with VT API key form, show/hide toggle, storage location info
- `app/templates/base.html` - Settings nav link added to header
- `app/templates/index.html` - Added data-settings-url attribute to analyze form
- `tests/test_settings.py` - 11 integration tests for settings page and API key management
- `tests/test_routes.py` - 8 new online-mode, polling, and serialization tests added

## Decisions Made

- Module-level `_orchestrators` dict stores job_id -> orchestrator so the polling endpoint can look up running jobs without needing Flask app context — simpler than storing on `g` or `current_app` which don't persist across requests
- `daemon=True` on the enrichment Thread prevents orphaned threads from blocking process exit (Pitfall 4 from Phase 02-01 research)
- `_mask_key()` reveals only last 4 chars of stored key — confirms a key is configured without exposing the full secret in the UI
- Empty and whitespace-only API keys are rejected at the route level before ConfigStore is called

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all tests passed on first run.

## Next Phase Readiness

- Browser can now submit in online mode, receive a job_id, and poll /enrichment/status for incremental results
- VTAdapter + orchestrator are wired into Flask routes and ready for Phase 3 (additional providers)
- No blockers — settings, online-mode /analyze, and polling endpoint are all operational

---
*Phase: 02-core-enrichment*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: app/routes.py
- FOUND: app/templates/settings.html
- FOUND: tests/test_settings.py
- FOUND: 02-03-SUMMARY.md
- FOUND commit 9ff3f22 (Task 1)
- FOUND commit cfa2a5e (Task 2)
