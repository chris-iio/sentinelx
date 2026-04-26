---
estimated_steps: 8
estimated_files: 5
skills_used:
  - tdd
  - security-review
  - verify-before-complete
---

# T01: Wire fail-open recent summaries into the index route and template contract

Load the `tdd`, `security-review`, and `verify-before-complete` skills before editing. Start with failing route/HTML contract coverage, then add the smallest server-rendered integration from GET `/` to `HistoryStore.list_recent(limit=4)` and `index.html`. Preserve every S01/S02 command-card selector and form behavior while adding recent, empty, and unavailable states as secondary markup.

Quality gates — Failure Modes: if `current_app.history_store.list_recent()` raises, GET `/` must catch it, log a warning without raw IOC content, and still render the command-card form with status 200; if a returned row is missing optional display fields, the template should degrade to safe text rather than breaking the whole page; if `/history/<id>` receives an unknown ID, the existing 404 behavior remains owned by `app/routes/history.py` and must not be changed. Load Profile: GET `/` adds exactly one bounded SQLite read using a small limit and no provider calls, background work, client fetch, or per-row detail loads; 10x homepage traffic should be limited by the existing SQLite read and should fail open if storage is unhealthy. Negative Tests: route tests must cover seeded rows with links, no-history empty/degraded state, `list_recent` exception, preserved CSRF/form selectors, offline no-HTTP behavior, and safe rendering of stored text containing markup-like characters.

Steps:
1. Update `tests/test_index_intake_contract.py` first: replace the old S01 “no recent rail” expectation with S03 contract tests for seeded recent rows, `/history/<id>` hrefs, bounded `list_recent` limit, empty history, fail-open history exceptions, and preservation of `#analyze-form`, `#ioc-text`, `#submit-btn`, `#mode-input`, `#mode-toggle-widget`, and CSRF hidden input.
2. Adjust `tests/test_history_routes.py` only where it has stale expectations that GET `/` never shows recent analyses; keep dedicated `/history` behavior and `/history/<id>` reload tests intact.
3. Update `app/routes/analysis.py` so GET `/` attempts `current_app.history_store.list_recent(limit=4)` inside a narrow try/except, passes `recent_analyses` and a boolean/error-state flag to `render_template('index.html')`, and logs a sanitized warning on failure.
4. Update `app/templates/index.html` to add a compact secondary `<aside>` or section inside `.intake-workbench` for Recent Analyses, rendering linked rows when `recent_analyses` exists, a compact empty state when the list is empty, and a quiet unavailable state when the route flags a history failure; use `url_for('main.history_detail', analysis_id=entry.id)` and keep Jinja autoescaping intact.
5. Run the focused route/contract command and fix only route/template/test issues before handing styling and browser proof to T02.

## Inputs

- `app/routes/analysis.py`
- `app/templates/index.html`
- `app/enrichment/history_store.py`
- `app/routes/history.py`
- `tests/test_index_intake_contract.py`
- `tests/test_history_routes.py`
- `tests/test_routes.py`

## Expected Output

- `app/routes/analysis.py`
- `app/templates/index.html`
- `tests/test_index_intake_contract.py`
- `tests/test_history_routes.py`

## Verification

python3 -m pytest -q tests/test_index_intake_contract.py tests/test_history_routes.py::TestHistoryListRoute tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present

## Observability Impact

- Signals added/changed: a sanitized `current_app.logger.warning` on recent-history lookup failure and deterministic DOM states for recent rows, empty history, and history unavailable.
- How a future agent inspects this: run `python3 -m pytest -q tests/test_index_intake_contract.py` to localize route/template regressions without opening a browser.
- Failure state exposed: storage failures are visible as a quiet secondary-state DOM marker or omitted rail plus warning log, while the intake form remains inspectable and usable.
