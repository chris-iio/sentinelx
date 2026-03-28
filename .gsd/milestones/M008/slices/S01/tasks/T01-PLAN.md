---
estimated_steps: 12
estimated_files: 9
skills_used: []
---

# T01: Create routes package and _helpers.py

1. Create app/routes/ directory with __init__.py.
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

## Inputs

- `app/routes.py`

## Expected Output

- `app/routes/__init__.py`
- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/enrichment.py`
- `app/routes/settings.py`
- `app/routes/history.py`
- `app/routes/detail.py`

## Verification

python3 -m pytest -x -q && wc -l app/routes/*.py | sort -n && test ! -f app/routes.py
