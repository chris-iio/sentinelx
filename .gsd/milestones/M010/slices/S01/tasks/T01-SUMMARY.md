---
id: T01
parent: S01
milestone: M010
provides: []
requires: []
affects: []
key_files: ["app/routes/_helpers.py", "app/routes/analysis.py", "app/routes/api.py", "app/routes/enrichment.py", "tests/test_routes.py", "tests/test_api.py"]
key_decisions: ["_setup_orchestrator returns (job_id, orchestrator, registry) tuple so callers can use registry for template_extras without a second lookup"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 1060 tests pass. grep confirms zero inline EnrichmentOrchestrator( constructors in analysis.py and api.py. Both status endpoints are single-line delegations."
completed_at: 2026-04-04T05:03:59.123Z
blocker_discovered: false
---

# T01: Extract _setup_orchestrator() and _get_enrichment_status() into _helpers.py, eliminating ~40 duplicated lines across route modules

> Extract _setup_orchestrator() and _get_enrichment_status() into _helpers.py, eliminating ~40 duplicated lines across route modules

## What Happened
---
id: T01
parent: S01
milestone: M010
key_files:
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/api.py
  - app/routes/enrichment.py
  - tests/test_routes.py
  - tests/test_api.py
key_decisions:
  - _setup_orchestrator returns (job_id, orchestrator, registry) tuple so callers can use registry for template_extras without a second lookup
duration: ""
verification_result: passed
completed_at: 2026-04-04T05:03:59.124Z
blocker_discovered: false
---

# T01: Extract _setup_orchestrator() and _get_enrichment_status() into _helpers.py, eliminating ~40 duplicated lines across route modules

**Extract _setup_orchestrator() and _get_enrichment_status() into _helpers.py, eliminating ~40 duplicated lines across route modules**

## What Happened

Extracted two shared helpers into app/routes/_helpers.py: _setup_orchestrator() consolidates uuid/cache/config/constructor/registry/pool-submit that was duplicated in analysis.py and api.py; _get_enrichment_status() consolidates lock/lookup/serialize/jsonify that was duplicated in enrichment.py and api.py. Updated all four route files to use the helpers. Fixed 13 broken test patch targets across test_routes.py and test_api.py by retargeting from app.routes.analysis.* and app.routes.api.* to app.routes._helpers.*.

## Verification

All 1060 tests pass. grep confirms zero inline EnrichmentOrchestrator( constructors in analysis.py and api.py. Both status endpoints are single-line delegations.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest --tb=short -q` | 0 | ✅ pass | 51300ms |
| 2 | `grep -c 'EnrichmentOrchestrator(' app/routes/analysis.py app/routes/api.py | grep -v ':0' | wc -l` | 0 | ✅ pass | 100ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/api.py`
- `app/routes/enrichment.py`
- `tests/test_routes.py`
- `tests/test_api.py`


## Deviations
None.

## Known Issues
None.
