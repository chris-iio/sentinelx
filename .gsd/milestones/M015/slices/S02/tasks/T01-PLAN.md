---
estimated_steps: 7
estimated_files: 3
skills_used:
  - tdd
  - accessibility
  - verify-before-complete
---

# T01: Pin clarified mode contract and copy in the index template

Load the `tdd`, `accessibility`, and `verify-before-complete` skills before editing. Start from S01's command-card shell and make the Offline/Online choice clearer at the server-rendered contract level before touching client behavior: add explicit visible mode heading/help/status copy and ARIA wiring while preserving the hidden `mode` input, existing IDs, form action, CSRF token, and default `offline` value.

Quality gates — Failure Modes: if Jinja rendering, CSRF output, or selector preservation regresses, `tests/test_index_intake_contract.py` must fail before browser tests; if the clarified copy removes or renames `#mode-input`, `#mode-toggle-widget`, or `#mode-toggle-btn`, downstream TypeScript and Playwright selectors are considered broken and should not be worked around. Load Profile: GET `/` remains a single server-rendered page with no DB, history, provider, fetch, or polling dependency; 10x traffic should see no new shared resource from S02 markup. Negative Tests: route proof must keep offline no-HTTP behavior and online no-provider redirect behavior intact, and the index contract must continue excluding Recent Analyses and pre-submit preview UI.

Steps:
1. Extend `tests/test_index_intake_contract.py` first so GET `/` asserts the clarified mode contract: visible Offline/Online labels, explicit default/offline safety copy, an online enrichment/provider cue, `#mode-input` as hidden `name="mode" value="offline"`, `#mode-toggle-widget[data-mode="offline"]`, and `#mode-toggle-btn` as `type="button"` with preserved `aria-pressed="false"` plus descriptive ARIA wiring.
2. Update `app/templates/index.html` to add concise mode-title/help/status markup inside `.mode-toggle` without changing `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, hidden CSRF, hidden `#mode-input`, or POST `/analyze` behavior.
3. Keep the mode UI semantically additive: adding `role="switch"`, `aria-checked`, `aria-describedby`, or live status text is allowed, but removing the existing button/hidden-input contract is not.
4. Run the focused route tests and fix only contract/markup issues before handing T02 the stable markup to style and synchronize from TypeScript.

## Inputs

- `app/templates/index.html`
- `app/routes/analysis.py`
- `app/static/src/ts/modules/form.ts`
- `tests/test_index_intake_contract.py`
- `tests/test_routes.py`

## Expected Output

- `app/templates/index.html`
- `tests/test_index_intake_contract.py`

## Verification

python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings

## Observability Impact

- Signals added/changed: route-level assertions for mode help/status markup, ARIA wiring, default hidden `mode=offline`, and absence of out-of-scope recent/preview surfaces.
- How a future agent inspects this: run `python3 -m pytest -q tests/test_index_intake_contract.py` before opening a browser.
- Failure state exposed: missing mode copy, broken hidden-input contract, or selector churn is localized to focused HTML assertion failures.
