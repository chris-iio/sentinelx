---
id: S01
parent: M008
milestone: M008
provides:
  - app/routes/ package with shared _helpers.py for S02 API blueprint to consume
requires:
  []
affects:
  - S02
key_files:
  - app/routes/__init__.py
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/enrichment.py
  - app/routes/settings.py
  - app/routes/history.py
  - app/routes/detail.py
key_decisions:
  - Single shared Blueprint 'main' across all route modules — preserves all template url_for() references
  - Shared mutable state in _helpers.py imported by reference
patterns_established:
  - Route modules attach handlers to shared bp imported from __init__.py
  - Shared route state lives in _helpers.py, imported by reference into consuming modules
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M008/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-28T05:29:52.761Z
blocker_discovered: false
---

# S01: Routes decomposition

**Split routes.py (488 LOC) into 7-file app/routes/ package — all modules under 120 LOC, 1057 tests passing.**

## What Happened

Decomposed monolithic routes.py (488 LOC) into 7-file app/routes/ package. Largest file is analysis.py at 119 LOC. Single shared Blueprint named 'main' preserves all template url_for() references. Shared state (_orchestrators, _enrichment_pool, serializers) in _helpers.py is imported by reference into analysis.py and enrichment.py. Updated 25 test import/patch paths across 3 test files. All 1057 tests pass.

## Verification

routes.py deleted. 7 package files, max 119 LOC. 1057 tests pass.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01 and T02 completed in a single pass since test fixes were straightforward.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/routes/__init__.py` — New package init — shared Blueprint 'main', imports all route modules
- `app/routes/_helpers.py` — Shared state: _orchestrators, _enrichment_pool, serializers, _run_enrichment_and_save
- `app/routes/analysis.py` — Home page and /analyze routes
- `app/routes/enrichment.py` — Enrichment polling route
- `app/routes/settings.py` — Settings and cache management routes
- `app/routes/history.py` — History reload route
- `app/routes/detail.py` — IOC detail page route
- `app/routes.py` — Deleted — replaced by app/routes/ package
- `tests/test_routes.py` — Updated 9 patch paths from app.routes to app.routes.analysis
- `tests/test_history_routes.py` — Updated 4 imports from app.routes to app.routes._helpers
- `tests/test_settings.py` — Updated 12 patch paths from app.routes.ConfigStore to app.routes.settings.ConfigStore
