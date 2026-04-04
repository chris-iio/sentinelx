---
id: S01
parent: M010
milestone: M010
provides:
  - _setup_orchestrator() shared helper in _helpers.py
  - _get_enrichment_status() shared helper in _helpers.py
  - Clean route modules with no duplicated orchestrator setup
requires:
  []
affects:
  - S02
key_files:
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/api.py
  - app/routes/enrichment.py
  - app/static/src/ts/modules/shared-rendering.ts
  - tests/test_routes.py
  - tests/test_api.py
key_decisions:
  - _setup_orchestrator returns (job_id, orchestrator, registry) tuple so callers can use registry for template_extras without a second lookup
patterns_established:
  - Route helper extraction: when multiple route modules share identical setup logic, extract into _helpers.py and retarget test patches from app.routes.<module>.Symbol to app.routes._helpers.Symbol
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M010/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T05:09:08.487Z
blocker_discovered: false
---

# S01: Route Duplication & Dead Code Cleanup

**Extracted _setup_orchestrator() and _get_enrichment_status() into _helpers.py eliminating ~40 duplicated lines across route modules, removed unused ResultDisplay export, and updated 13 test patch targets — all 1060 tests pass.**

## What Happened

Two tasks completed this cleanup slice.

T01 extracted two shared helpers into app/routes/_helpers.py. `_setup_orchestrator()` consolidates the uuid/cache/config/constructor/registry/pool-submit block (~20 lines) that was duplicated between analysis.py and api.py. `_get_enrichment_status()` consolidates the lock/lookup/serialize/jsonify status endpoint body that was duplicated between enrichment.py and api.py. Both analysis.py and api.py now call `_setup_orchestrator()` instead of constructing EnrichmentOrchestrator inline. Both enrichment_status() and api_status() now delegate to `_get_enrichment_status()` as one-liners. 13 test patch targets across test_routes.py and test_api.py were retargeted from the old module paths (app.routes.analysis.*, app.routes.api.*) to app.routes._helpers.*.

T02 removed the unused `export` keyword from `interface ResultDisplay` in shared-rendering.ts. No consumer imports the type by name — both enrichment.ts and history.ts destructure the return value of `computeResultDisplay` inline, so the interface type is inferred structurally.

## Verification

All 1060 tests pass (pytest --tb=short -q, exit 0, 52s). grep confirms zero inline EnrichmentOrchestrator( constructors in analysis.py and api.py. grep confirms zero 'export interface ResultDisplay' in shared-rendering.ts. make typecheck passes (tsc --noEmit, exit 0).

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/routes/_helpers.py` — Added _setup_orchestrator() and _get_enrichment_status() shared helpers
- `app/routes/analysis.py` — Replaced inline orchestrator setup with _setup_orchestrator() call; removed uuid/ConfigStore/EnrichmentOrchestrator imports
- `app/routes/api.py` — Replaced inline orchestrator setup and status body with helper calls; removed json/uuid/ConfigStore/EnrichmentOrchestrator imports
- `app/routes/enrichment.py` — Replaced enrichment_status() body with _get_enrichment_status() delegation
- `app/static/src/ts/modules/shared-rendering.ts` — Removed export keyword from ResultDisplay interface
- `tests/test_routes.py` — Retargeted 12 patch paths from app.routes.analysis.* to app.routes._helpers.*
- `tests/test_api.py` — Retargeted 1 patch path from app.routes.api._enrichment_pool to app.routes._helpers._enrichment_pool
