---
estimated_steps: 15
estimated_files: 7
skills_used: []
---

# T01: Add /history route, template, nav link; remove Recent Analyses from home page

Create the /history list route in history.py, create history.html template, add a clock icon to icons.html, add a History nav link to base.html, remove the Recent Analyses HTML block from index.html, remove the list_recent() call from analysis.py index(), and remove initRecentAnalysesToggle() from ui.ts.

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

## Inputs

- ``app/routes/history.py` — existing history_detail route, add history_list alongside it`
- ``app/routes/analysis.py` — index() currently calls list_recent and passes recent_analyses`
- ``app/templates/index.html` — contains the Recent Analyses HTML block to remove (lines 62-82)`
- ``app/templates/base.html` — nav with Settings link, needs History link added`
- ``app/templates/macros/icons.html` — icon macro, needs clock icon added`
- ``app/static/src/ts/modules/ui.ts` — initRecentAnalysesToggle() to delete`

## Expected Output

- ``app/routes/history.py` — history_list() route added`
- ``app/routes/analysis.py` — index() simplified, no more list_recent call`
- ``app/templates/history.html` — new template listing recent analyses`
- ``app/templates/index.html` — Recent Analyses block removed`
- ``app/templates/base.html` — History nav link added`
- ``app/templates/macros/icons.html` — clock icon added`
- ``app/static/src/ts/modules/ui.ts` — initRecentAnalysesToggle removed`
- ``app/static/dist/main.js` — rebuilt JS bundle`

## Verification

python -c "from app import create_app; app=create_app(); c=app.test_client(); r1=c.get('/'); r2=c.get('/history'); assert r1.status_code==200; assert b'Recent Analyses' not in r1.data; assert r2.status_code==200; print('OK')" && make typecheck && make js
