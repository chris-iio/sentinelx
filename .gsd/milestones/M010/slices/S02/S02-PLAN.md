# S02: Recent Analyses → Dedicated /history Page

**Goal:** Home page shows only the paste form; /history lists recent analyses with links to detail pages; nav bar includes a History link.
**Demo:** After this: After this: home page shows only the paste form; /history lists recent analyses with links to detail pages.

## Tasks
- [x] **T01: Added /history list route, history.html template, clock nav icon, and removed Recent Analyses from the home page** — Create the /history list route in history.py, create history.html template, add a clock icon to icons.html, add a History nav link to base.html, remove the Recent Analyses HTML block from index.html, remove the list_recent() call from analysis.py index(), and remove initRecentAnalysesToggle() from ui.ts.

Steps:
1. Add a 'clock' Heroicons v2 solid SVG path to app/templates/macros/icons.html (new elif branch).
2. Add a History nav link to base.html inside <nav class="floating-settings">, before the Settings link. Use: <a href="{{ url_for('main.history_list') }}" class="nav-link nav-link--icon" aria-label="History">{{ icon("clock", class="nav-icon nav-icon--lg") }}</a>
3. Add history_list() route to app/routes/history.py:
   @bp.route("/history")
   @limiter.limit("30 per minute")
   def history_list():
       analyses = current_app.history_store.list_recent(limit=50)
       return render_template("history.html", analyses=analyses)
4. Create app/templates/history.html extending base.html. Reuse the .recent-analyses-list / .recent-analysis-row HTML structure from index.html but without the collapse toggle — the list is always visible. Include a heading. Show an empty-state message when analyses is empty.
5. In app/templates/index.html, delete the entire {% if recent_analyses %} ... {% endif %} block (the .recent-analyses section, approximately lines 62-82).
6. In app/routes/analysis.py index(), remove the try/except block that calls history_store.list_recent() and stop passing recent_analyses to render_template. The index() function should just return render_template("index.html").
7. In app/static/src/ts/modules/ui.ts, delete the initRecentAnalysesToggle() function (lines 45-58) and remove its call from init() (line 64). Run make js to rebuild.
8. Run make typecheck to confirm TS compiles. Run python -c "from app import create_app; create_app()" to confirm Flask boots.
  - Estimate: 30m
  - Files: app/routes/history.py, app/routes/analysis.py, app/templates/history.html, app/templates/index.html, app/templates/base.html, app/templates/macros/icons.html, app/static/src/ts/modules/ui.ts
  - Verify: python -c "from app import create_app; app=create_app(); c=app.test_client(); r1=c.get('/'); r2=c.get('/history'); assert r1.status_code==200; assert b'Recent Analyses' not in r1.data; assert r2.status_code==200; print('OK')" && make typecheck && make js
- [ ] **T02: Update tests for /history route and stripped-down home page** — Rewrite TestIndexWithHistory in test_history_routes.py to test the new /history route instead of GET /. Add tests for the history list page (populated, empty, error). Verify index still returns 200 without recent analyses.

Steps:
1. In tests/test_history_routes.py, rename TestIndexWithHistory to TestHistoryList (or similar). Rewrite the 4 tests:
   - test_index_shows_recent_analyses → test_history_list_shows_analyses: GET /history with seeded store, assert 200, assert b'Recent Analyses' or analysis text in response, assert link to /history/abc123deadbeef
   - test_index_no_history → test_history_list_empty: GET /history with empty store, assert 200, assert empty-state message present
   - test_index_history_error_graceful → test_history_list_error_graceful: GET /history with store that raises Exception, assert 500 (or handle gracefully if the route has try/except — check T01's implementation)
   - test_index_shows_verdict_badge → test_history_list_shows_verdict_badge: GET /history with seeded store, assert verdict badge text present
2. In tests/test_routes.py, verify test_index_returns_200 still passes. The index route no longer passes recent_analyses, so mock_store may no longer be needed for that test — check and simplify if applicable.
3. Run pytest --tb=short -q to confirm all tests pass.
4. Run pytest tests/test_history_routes.py -v to confirm the rewritten tests specifically pass.
  - Estimate: 20m
  - Files: tests/test_history_routes.py, tests/test_routes.py
  - Verify: pytest tests/test_history_routes.py tests/test_routes.py --tb=short -q && pytest --tb=short -q
