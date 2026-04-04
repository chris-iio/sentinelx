---
id: S02
parent: M010
milestone: M010
provides:
  - Dedicated /history page listing recent analyses with links to detail pages
  - Clock nav icon in base.html nav bar
  - Clean home page showing only the paste form
requires:
  - slice: S01
    provides: Clean route layer (no duplication)
affects:
  []
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
  - D048: Recent Analyses relocated to dedicated /history route (supersedes D044 which kept it on home page)
patterns_established:
  - Reuse existing CSS classes (.recent-analyses-list, .recent-analysis-row) when relocating UI blocks to new pages — avoids duplicating styling
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M010/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T05:25:43.780Z
blocker_discovered: false
---

# S02: Recent Analyses → Dedicated /history Page

**Relocated Recent Analyses from the home page to a dedicated /history route with clock nav icon; home page now shows only the paste form.**

## What Happened

The home page's collapsible Recent Analyses block was moved to a dedicated `/history` route served by `history_list()` in `history.py`. A new `history.html` template reuses the existing `.recent-analyses-list` / `.recent-analysis-row` CSS classes for visual consistency. A clock Heroicon was added to `icons.html` and a History nav link placed in `base.html` before the Settings link.

On the removal side: the `{% if recent_analyses %}` block was deleted from `index.html`, the `index()` function in `analysis.py` was simplified to a bare `render_template("index.html")` (no more `history_store.list_recent()` call), and `initRecentAnalysesToggle()` was removed from `ui.ts` along with its call from `init()`.

Tests were updated: `TestIndexWithHistory` was renamed to `TestHistoryListRoute` with tests targeting GET `/history` (populated list, empty state, verdict badge, no-recent-analyses-on-index). A new `test_history_list_error_propagates` test was added to confirm exception propagation when `list_recent()` raises under Flask TESTING mode. All 1061 tests pass.

## Verification

All slice-level verification checks pass independently:
1. Flask boot + test client: GET / returns 200 with no 'Recent Analyses' text; GET /history returns 200.
2. `make typecheck` — TypeScript compiles clean.
3. `make js` — esbuild produces 28.7kb bundle.
4. `pytest tests/test_history_routes.py tests/test_routes.py --tb=short -q` — 43 passed.
5. `pytest --tb=short -q` — 1061 passed, 0 failures.
6. File-level checks: history_list route exists in history.py, clock icon in icons.html, History nav link in base.html, no 'Recent Analyses' in index.html, no list_recent in analysis.py, no initRecentAnalysesToggle in ui.ts.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01 completed most of the T02-planned test rewrites ahead of schedule. T02 only needed to add the error-propagation test. The graceful-error test was replaced with an exception-propagation test (Flask TESTING=True propagates exceptions rather than returning 500).

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/routes/history.py` — Added history_list() route serving /history with 50 most recent analyses
- `app/templates/history.html` — New template listing recent analyses with verdict badges, IOC counts, timestamps
- `app/templates/index.html` — Removed collapsible Recent Analyses block
- `app/routes/analysis.py` — Simplified index() to bare render_template (no more history_store query)
- `app/templates/base.html` — Added History nav link with clock icon before Settings link
- `app/templates/macros/icons.html` — Added clock Heroicon SVG path
- `app/static/src/ts/modules/ui.ts` — Removed initRecentAnalysesToggle() and its call from init()
- `tests/test_history_routes.py` — Rewrote TestIndexWithHistory → TestHistoryListRoute; added error-propagation test
