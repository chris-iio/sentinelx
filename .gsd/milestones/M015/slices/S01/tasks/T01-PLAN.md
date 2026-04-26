---
estimated_steps: 7
estimated_files: 3
skills_used:
  - tdd
  - frontend-design
  - accessibility
  - verify-before-complete
---

# T01: Restructure the index template into a tested command card

Load the `tdd`, `frontend-design`, `accessibility`, and `verify-before-complete` skills before editing. Convert the existing index template into the S01 command-card DOM while writing a focused HTML contract test first so later slices can rely on stable selectors without inheriting the full roadmap context.

Quality gates — Failure Modes: if Flask/Jinja rendering fails, GET `/` must fail the focused contract test rather than being masked by browser-only checks; if the CSRF macro or form action changes, the test must catch the missing hidden token or wrong `/analyze` target; if selector churn breaks `form.ts`, the test must fail on the missing IDs before E2E runs. Load Profile: this task adds no database/API calls and keeps GET `/` a single server-rendered page; 10x traffic should not introduce a new shared resource because no history/provider dependency is added in S01. Negative Tests: preserve empty/whitespace server-side error behavior via existing route tests, preserve offline no-HTTP behavior, assert that `/` still does not render Recent Analyses or pre-submit preview UI in this slice.

Steps:
1. Add `tests/test_index_intake_contract.py` with Flask client assertions for GET `/`: `.page-index`, `.intake-workbench`, `.command-card`, `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input` defaulting to `offline`, `#mode-toggle-widget`, `#mode-toggle-btn`, and hidden `csrf_token` are present, while pre-submit preview/recent-analysis markup is absent.
2. Update `app/templates/index.html` to wrap the existing form in a command-card/workbench structure with concise analyst-oriented heading/help text, keeping all existing IDs, `name="text"`, `name="mode"`, form method/action, textarea `rows="5"`, `aria-label`, paste feedback span, disabled Extract button, and error alert behavior intact.
3. Keep the Offline/Online toggle semantics visually and structurally conservative for S01: no hidden mode contract change, no keyboard/ARIA redesign beyond preserving current `aria-pressed`, and no data dependency for history.
4. Run the focused route/contract tests and fix any mismatch before handing T02 a stable DOM to style.

## Inputs

- `app/templates/index.html`
- `app/routes/analysis.py`
- `app/static/src/ts/modules/form.ts`
- `tests/test_routes.py`

## Expected Output

- `app/templates/index.html`
- `tests/test_index_intake_contract.py`

## Verification

python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_analyze_empty_input tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present

## Observability Impact

- Signals added/changed: focused route-level assertions for command-card selectors, CSRF/form action, default hidden mode, and no unintended recent/preview surface.
- How a future agent inspects this: run `python3 -m pytest -q tests/test_index_intake_contract.py` and read assertion names before opening the browser.
- Failure state exposed: missing or renamed S01 boundary selectors fail fast with a route-test assertion instead of surfacing later as ambiguous JavaScript or Playwright failures.
