---
estimated_steps: 10
estimated_files: 2
skills_used: []
---

# T02: Update tests for /history route and stripped-down home page

Rewrite TestIndexWithHistory in test_history_routes.py to test the new /history route instead of GET /. Add tests for the history list page (populated, empty, error). Verify index still returns 200 without recent analyses.

Steps:
1. In tests/test_history_routes.py, rename TestIndexWithHistory to TestHistoryList (or similar). Rewrite the 4 tests:
   - test_index_shows_recent_analyses → test_history_list_shows_analyses: GET /history with seeded store, assert 200, assert b'Recent Analyses' or analysis text in response, assert link to /history/abc123deadbeef
   - test_index_no_history → test_history_list_empty: GET /history with empty store, assert 200, assert empty-state message present
   - test_index_history_error_graceful → test_history_list_error_graceful: GET /history with store that raises Exception, assert 500 (or handle gracefully if the route has try/except — check T01's implementation)
   - test_index_shows_verdict_badge → test_history_list_shows_verdict_badge: GET /history with seeded store, assert verdict badge text present
2. In tests/test_routes.py, verify test_index_returns_200 still passes. The index route no longer passes recent_analyses, so mock_store may no longer be needed for that test — check and simplify if applicable.
3. Run pytest --tb=short -q to confirm all tests pass.
4. Run pytest tests/test_history_routes.py -v to confirm the rewritten tests specifically pass.

## Inputs

- ``app/routes/history.py` — T01 added history_list() route`
- ``app/routes/analysis.py` — T01 simplified index()`
- ``app/templates/history.html` — T01 created this template`
- ``tests/test_history_routes.py` — existing TestIndexWithHistory to rewrite`
- ``tests/test_routes.py` — test_index_returns_200 may need mock update`

## Expected Output

- ``tests/test_history_routes.py` — TestIndexWithHistory rewritten as TestHistoryList testing /history`
- ``tests/test_routes.py` — test_index_returns_200 updated if needed`

## Verification

pytest tests/test_history_routes.py tests/test_routes.py --tb=short -q && pytest --tb=short -q
