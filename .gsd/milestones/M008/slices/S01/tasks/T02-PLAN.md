---
estimated_steps: 7
estimated_files: 3
skills_used: []
---

# T02: Fix test imports

1. Update all test files that reference app.routes to use the new module paths:
   - tests/test_routes.py imports of app.routes → app.routes._helpers or app.routes.analysis etc.
   - tests/test_history_routes.py imports of app.routes._run_enrichment_and_save → app.routes._helpers._run_enrichment_and_save
   - tests/test_ioc_detail_routes.py — check for any app.routes references
   - Any E2E test files that patch app.routes
2. Verify url_for('main.xxx') calls still work (blueprint name may need updating if using multiple blueprints with different names).
3. Run full test suite.

## Inputs

- `tests/test_routes.py`
- `tests/test_history_routes.py`
- `tests/test_ioc_detail_routes.py`

## Expected Output

- `tests/test_routes.py`
- `tests/test_history_routes.py`
- `tests/test_ioc_detail_routes.py`

## Verification

python3 -m pytest -x -q — 1057 passed, 0 failed
