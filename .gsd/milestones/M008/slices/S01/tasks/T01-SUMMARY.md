---
id: T01
parent: S01
milestone: M008
provides: []
requires: []
affects: []
key_files: ["app/routes/__init__.py", "app/routes/_helpers.py", "app/routes/analysis.py", "app/routes/enrichment.py", "app/routes/settings.py", "app/routes/history.py", "app/routes/detail.py"]
key_decisions: ["Kept single 'main' Blueprint shared across all route modules — avoids breaking url_for('main.xxx') in 15+ template references", "Route modules import shared bp from __init__.py and attach @bp.route() decorators", "_orchestrators dict shared by reference across analysis.py and enrichment.py via _helpers.py import"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Verified routes.py deleted, package exists with 7 files all under 120 LOC. 1057 tests pass."
completed_at: 2026-03-28T05:29:23.392Z
blocker_discovered: false
---

# T01: Split routes.py into app/routes/ package with 7 focused modules, all under 120 LOC.

> Split routes.py into app/routes/ package with 7 focused modules, all under 120 LOC.

## What Happened
---
id: T01
parent: S01
milestone: M008
key_files:
  - app/routes/__init__.py
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/enrichment.py
  - app/routes/settings.py
  - app/routes/history.py
  - app/routes/detail.py
key_decisions:
  - Kept single 'main' Blueprint shared across all route modules — avoids breaking url_for('main.xxx') in 15+ template references
  - Route modules import shared bp from __init__.py and attach @bp.route() decorators
  - _orchestrators dict shared by reference across analysis.py and enrichment.py via _helpers.py import
duration: ""
verification_result: passed
completed_at: 2026-03-28T05:29:23.393Z
blocker_discovered: false
---

# T01: Split routes.py into app/routes/ package with 7 focused modules, all under 120 LOC.

**Split routes.py into app/routes/ package with 7 focused modules, all under 120 LOC.**

## What Happened

Split monolithic routes.py (488 LOC) into app/routes/ package with 7 files. Key design choice: keep a single Blueprint named 'main' shared across all route modules rather than separate blueprints, because 15+ template url_for('main.xxx') references would all break. Each route module imports bp from __init__.py and attaches its handlers. Shared state (_orchestrators, _enrichment_pool, serializers) lives in _helpers.py and is imported by reference into analysis.py and enrichment.py. Deleted routes.py after verifying the package import resolves correctly.

## Verification

Verified routes.py deleted, package exists with 7 files all under 120 LOC. 1057 tests pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -x -q` | 0 | ✅ pass | 52110ms |
| 2 | `test ! -f app/routes.py` | 0 | ✅ pass | 5ms |
| 3 | `wc -l app/routes/*.py` | 0 | ✅ pass — max 119 LOC (analysis.py) | 10ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/routes/__init__.py`
- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/enrichment.py`
- `app/routes/settings.py`
- `app/routes/history.py`
- `app/routes/detail.py`


## Deviations
None.

## Known Issues
None.
