---
id: S02
parent: M008
milestone: M008
provides:
  - POST /api/analyze endpoint for programmatic IOC submission
  - GET /api/status/<job_id> endpoint for enrichment polling
requires:
  - slice: S01
    provides: app/routes/ package with shared _helpers.py
affects:
  []
key_files:
  - app/routes/api.py
  - tests/test_api.py
key_decisions:
  - Separate Blueprint 'api' with url_prefix='/api' — keeps API routes cleanly namespaced
  - CSRF exemption via csrf.exempt(bp_api) scoped only to API blueprint
patterns_established:
  - Separate Blueprint for API routes with url_prefix, CSRF exemption scoped to that blueprint only
observability_surfaces:
  - API error responses include structured JSON with descriptive error messages
drill_down_paths:
  - .gsd/milestones/M008/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-28T05:34:09.566Z
blocker_discovered: false
---

# S02: REST API blueprint

**Added REST API blueprint (POST /api/analyze, GET /api/status) with 18 tests, CSRF-exempt, rate-limited \u2014 1075 tests passing.**

## What Happened

Created REST API blueprint fulfilling R035. POST /api/analyze accepts JSON with text and optional mode (offline/online), runs the same extraction pipeline as the browser route, and returns structured JSON with IOCs, grouped summary, and total count. Online mode launches background enrichment and returns job_id and status_url for polling. GET /api/status/<job_id> returns the same polling JSON as the HTML endpoint. CSRF exempted via csrf.exempt(bp_api), rate-limited at 10/min for analyze and 120/min for status. 18 tests cover validation, offline/online success, status polling, and CSRF exemption verification.

## Verification

18 API tests pass. Full suite: 1075 passed, 0 failed.

## Requirements Advanced

- R035 — REST API implemented with offline and online modes, 18 tests

## Requirements Validated

- R035 — POST /api/analyze returns JSON IOCs, online mode returns job_id for polling, CSRF exempt, rate-limited. 18 tests pass.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

api.py is 155 LOC \u2014 slightly above the 150 LOC target. The 30+ lines of docstrings account for the overage; actual code is well within bounds.

## Follow-ups

None.

## Files Created/Modified

- `app/routes/api.py` — New REST API blueprint with POST /api/analyze and GET /api/status
- `app/routes/__init__.py` — Added bp_api import
- `app/__init__.py` — Registered bp_api and csrf.exempt(bp_api)
- `tests/test_api.py` — 18 API tests
