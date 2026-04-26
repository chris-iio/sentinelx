---
estimated_steps: 7
estimated_files: 5
skills_used:
  - tdd
  - security-review
  - verify-before-complete
---

# T01: Add final assembled route and security contract proof

Load the `tdd`, `security-review`, and `verify-before-complete` skills before editing. Start with route/HTML contract coverage that treats the final `/` page as one assembled Intake Workbench, not three independent slice fragments. The task should avoid production behavior changes unless the new contract exposes a real regression; preserve the S01/S02/S03 selectors and fail-open recent-history behavior.

Quality gates — Failure Modes: if `current_app.history_store.list_recent(limit=4)` raises, GET `/` and no-input POST `/analyze` must still render status 200 with `#analyze-form`, `#ioc-text`, `#submit-btn`, `#mode-input`, `#mode-toggle-widget`, CSRF, and a quiet unavailable recent-history state; malformed or missing optional row fields must render safe fallback text; unknown `/history/<id>` behavior remains owned by the existing history route. Load Profile: GET `/` must still do at most one bounded history summary read and no provider calls, background work, polling, or per-row detail loads. Negative Tests: contract tests must cover stored text escaping, no pre-submit preview rail, absent raw results/provider secrets, no-HTTP Offline behavior, Online-without-provider redirect, CSRF/security headers, and sanitized recent-history failure logging.

Steps:
1. Extend `tests/test_index_intake_contract.py` with an integrated workbench contract test that seeds recent rows through a mocked store and asserts command-card selectors, clarified mode copy/status, hidden `mode=offline`, recent row `/history/<id>` links, no preview surfaces, bounded `list_recent(limit=4)`, and escaped stored input text in the same GET `/` response.
2. Add or tighten a fail-open no-input POST contract in `tests/test_index_intake_contract.py` so validation errors that re-render `index.html` still include the recent-history unavailable/empty context plus the full paste form and CSRF contract.
3. If the tests expose a real route/template bug, make the smallest fix in `app/routes/analysis.py` or `app/templates/index.html`; do not introduce a new API, client fetch, preview extraction, provider call, or dashboard surface.
4. Run the focused route/security command and fix failures without weakening the assertions.

## Inputs

- `tests/test_index_intake_contract.py`
- `app/routes/analysis.py`
- `app/templates/index.html`
- `tests/test_routes.py`
- `tests/test_history_routes.py`

## Expected Output

- `tests/test_index_intake_contract.py`
- `app/routes/analysis.py`
- `app/templates/index.html`

## Verification

python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings tests/test_routes.py::test_security_headers_present tests/test_routes.py::test_csrf_token_required tests/test_history_routes.py

## Observability Impact

Signals added/changed: focused route tests become the first diagnostic surface for final workbench contract, fail-open recent-history behavior, sanitized logging, and CSRF/security preservation.
How a future agent inspects this: run the focused `python3 -m pytest -q tests/test_index_intake_contract.py ...` command to isolate route/template/security failures without opening a browser.
Failure state exposed: missing selectors, unsafe stored text rendering, raw exception leakage, unbounded or blocking history reads, offline network attempts, and security-header/CSRF regressions fail explicit tests.
