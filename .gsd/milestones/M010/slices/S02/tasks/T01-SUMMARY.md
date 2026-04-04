---
id: T01
parent: S02
milestone: M010
provides: []
requires: []
affects: []
key_files: ["app/routes/history.py", "app/templates/history.html", "app/templates/index.html", "app/routes/analysis.py", "app/templates/base.html", "app/templates/macros/icons.html", "app/static/src/ts/modules/ui.ts", "tests/test_history_routes.py"]
key_decisions: ["Reused .recent-analyses-list/.recent-analysis-row CSS classes in history.html for visual consistency with the old home page block"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Flask boot + test client assertions pass (GET / has no 'Recent Analyses', GET /history returns 200). make typecheck and make js both pass. 13/13 history route tests pass."
completed_at: 2026-04-04T05:17:08.783Z
blocker_discovered: false
---

# T01: Added /history list route, history.html template, clock nav icon, and removed Recent Analyses from the home page

> Added /history list route, history.html template, clock nav icon, and removed Recent Analyses from the home page

## What Happened
---
id: T01
parent: S02
milestone: M010
key_files:
  - app/routes/history.py
  - app/templates/history.html
  - app/templates/index.html
  - app/routes/analysis.py
  - app/templates/base.html
  - app/templates/macros/icons.html
  - app/static/src/ts/modules/ui.ts
  - tests/test_history_routes.py
key_decisions:
  - Reused .recent-analyses-list/.recent-analysis-row CSS classes in history.html for visual consistency with the old home page block
duration: ""
verification_result: passed
completed_at: 2026-04-04T05:17:08.785Z
blocker_discovered: false
---

# T01: Added /history list route, history.html template, clock nav icon, and removed Recent Analyses from the home page

**Added /history list route, history.html template, clock nav icon, and removed Recent Analyses from the home page**

## What Happened

Added history_list() route to history.py serving up to 50 recent analyses via a new history.html template. Added clock Heroicon to icons.html and a History nav link in base.html. Removed the collapsible Recent Analyses block from index.html, simplified index() in analysis.py to no longer query history_store, and removed initRecentAnalysesToggle() from ui.ts. Updated test_history_routes.py to test the new /history route and confirm the home page no longer shows Recent Analyses.

## Verification

Flask boot + test client assertions pass (GET / has no 'Recent Analyses', GET /history returns 200). make typecheck and make js both pass. 13/13 history route tests pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c 'from app import create_app; ...' (flask boot + route assertions)` | 0 | ✅ pass | 2900ms |
| 2 | `make typecheck` | 0 | ✅ pass | 2900ms |
| 3 | `make js` | 0 | ✅ pass | 2900ms |
| 4 | `python3 -m pytest tests/test_history_routes.py -x -q` | 0 | ✅ pass | 2700ms |


## Deviations

Replaced TestIndexWithHistory test class with TestHistoryListRoute targeting the new /history route. Removed the graceful-error test since index() no longer queries history_store.

## Known Issues

None.

## Files Created/Modified

- `app/routes/history.py`
- `app/templates/history.html`
- `app/templates/index.html`
- `app/routes/analysis.py`
- `app/templates/base.html`
- `app/templates/macros/icons.html`
- `app/static/src/ts/modules/ui.ts`
- `tests/test_history_routes.py`


## Deviations
Replaced TestIndexWithHistory test class with TestHistoryListRoute targeting the new /history route. Removed the graceful-error test since index() no longer queries history_store.

## Known Issues
None.
