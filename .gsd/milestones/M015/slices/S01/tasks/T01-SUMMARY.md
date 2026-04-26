---
id: T01
parent: S01
milestone: M015
key_files:
  - app/templates/index.html
  - tests/test_index_intake_contract.py
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-26T08:40:49.222Z
blocker_discovered: false
---

# T01: Added a tested command-card DOM contract for the index IOC intake form.

**Added a tested command-card DOM contract for the index IOC intake form.**

## What Happened

Created `tests/test_index_intake_contract.py` first and confirmed it failed against the existing sparse index template because `.intake-workbench` was missing. Restructured `app/templates/index.html` around `.page-index`, `.intake-workbench`, and `.command-card` wrappers with analyst-oriented heading/help text while preserving the existing POST `/analyze` form, CSRF hidden input, `#ioc-text`, `#submit-btn`, `#clear-btn`, hidden offline `#mode-input`, mode toggle widget/button, paste feedback span, disabled initial Extract button, and error alert behavior. The new contract test also asserts that S01 has not introduced Recent Analyses or pre-submit preview surfaces.

## Verification

Verified the new Flask-client contract, existing empty/whitespace error behavior, offline no-HTTP route behavior, and security headers with pytest. Ran `npx tsc --noEmit` and `make build` for slice-level inspection/build consistency. Exercised the real local browser flow at `http://127.0.0.1:5000/`: command-card selectors were visible, initial submit was disabled, hidden mode remained `offline`, no Recent Analyses/preview markup was present, synthetic IOC text enabled submit, and submitting reached `/analyze` with `.page-results`, Offline Mode, and a found IOC count. Browser network diagnostics showed no failed requests; console diagnostics showed existing CSP inline-style warnings from inline style attributes, which did not block the verified flow.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_analyze_empty_input tests/test_routes.py::test_analyze_whitespace_only_input tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present` | 0 | ✅ pass | 200ms |
| 2 | `npx tsc --noEmit` | 0 | ✅ pass | 1000ms |
| 3 | `make build` | 0 | ✅ pass | 1000ms |
| 4 | `browser: GET / command-card selector assertions, offline paste-to-results flow, and no_failed_requests assertion` | 0 | ✅ pass | 18000ms |

## Deviations

None. Extra verification included the whitespace negative route test, TypeScript/build checks, and a live browser smoke flow because this task touches user-visible intake behavior.

## Known Issues

Browser console diagnostics showed CSP inline-style warnings for existing inline style attributes such as `style="display:none;"`; functional route and browser checks passed, and removing inline style behavior is outside T01's conservative DOM contract scope.

## Files Created/Modified

- `app/templates/index.html`
- `tests/test_index_intake_contract.py`
