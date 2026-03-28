# S01: Routes decomposition

**Goal:** Split monolithic routes.py into focused Blueprint modules sharing state via _helpers.py
**Demo:** After this: routes.py deleted, replaced by app/routes/ package with 7 focused modules. All 1057 tests pass. No behavior changes.

## Tasks
- [x] **T01: Split routes.py into app/routes/ package with 7 focused modules, all under 120 LOC.** — 1. Create app/routes/ directory with __init__.py.
2. Move shared state (_orchestrators, _orch_lock, _MAX_ORCHESTRATORS, _enrichment_pool, _mask_key, _serialize_result, _serialize_ioc, _run_enrichment_and_save) from routes.py into app/routes/_helpers.py.
3. Create individual Blueprint files:
   - analysis.py: bp_analysis — /, /analyze
   - enrichment.py: bp_enrichment — /enrichment/status/<job_id>
   - settings.py: bp_settings — /settings/*, /settings/cache/*
   - history.py: bp_history — /history/<analysis_id>
   - detail.py: bp_detail — /ioc/<ioc_type>/<path:ioc_value>
4. Update app/routes/__init__.py to register all blueprints.
5. Update app/__init__.py to import from app.routes instead of app.routes (should resolve automatically if the package __init__.py re-exports bp, but check).
6. Delete routes.py.
7. Run tests.
  - Estimate: 45min
  - Files: app/routes/__init__.py, app/routes/_helpers.py, app/routes/analysis.py, app/routes/enrichment.py, app/routes/settings.py, app/routes/history.py, app/routes/detail.py, app/__init__.py, app/routes.py
  - Verify: python3 -m pytest -x -q && wc -l app/routes/*.py | sort -n && test ! -f app/routes.py
- [x] **T02: Fixed 25 test import/patch paths across 3 test files for new routes package structure.** — 1. Update all test files that reference app.routes to use the new module paths:
   - tests/test_routes.py imports of app.routes → app.routes._helpers or app.routes.analysis etc.
   - tests/test_history_routes.py imports of app.routes._run_enrichment_and_save → app.routes._helpers._run_enrichment_and_save
   - tests/test_ioc_detail_routes.py — check for any app.routes references
   - Any E2E test files that patch app.routes
2. Verify url_for('main.xxx') calls still work (blueprint name may need updating if using multiple blueprints with different names).
3. Run full test suite.
  - Estimate: 30min
  - Files: tests/test_routes.py, tests/test_history_routes.py, tests/test_ioc_detail_routes.py
  - Verify: python3 -m pytest -x -q — 1057 passed, 0 failed
