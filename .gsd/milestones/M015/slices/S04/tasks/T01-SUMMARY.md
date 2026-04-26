---
id: T01
parent: S04
milestone: M015
key_files:
  - tests/test_index_intake_contract.py
key_decisions:
  - Preserved existing route/template behavior and added tests only because the tightened contract exposed no real regression.
duration: 
verification_result: passed
completed_at: 2026-04-26T11:09:17.599Z
blocker_discovered: false
---

# T01: Added integrated intake workbench route/security contract tests for bounded recent history, safe rendering, no preview surfaces, and fail-open no-input POST behavior.

**Added integrated intake workbench route/security contract tests for bounded recent history, safe rendering, no preview surfaces, and fail-open no-input POST behavior.**

## What Happened

Extended `tests/test_index_intake_contract.py` with an assembled GET `/` workbench contract that verifies the command card, clarified Offline/Online mode copy, hidden offline mode input, recent `/history/<id>` resume links, escaped stored input text, no pre-submit preview/result surfaces, no provider registry calls, and a single bounded `list_recent(limit=4)` read. Added a no-input POST `/analyze` fail-open contract that forces `history_store.list_recent` to raise and proves validation re-render still returns 200 with the full paste form, CSRF hidden input, mode controls, unavailable recent-history state, and sanitized warning logging. No production changes were required because the existing `app/routes/analysis.py` and `app/templates/index.html` already satisfied the tightened contract.

## Verification

Fresh verification passed after the final edit. The focused route/security command passed 27 tests, the focused E2E slice command passed 34 tests, `make verify-fast` passed 1026 non-E2E pytest tests plus 87 Vitest tests, TypeScript, and asset build, and the full E2E suite passed 125 tests. Observability signals were verified through explicit assertions on `.recent-analysis-row`, `.recent-analyses-unavailable`, `#mode-status`, CSRF input presence, bounded history lookup calls, and sanitized recent-history failure logging.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings tests/test_routes.py::test_security_headers_present tests/test_routes.py::test_csrf_token_required tests/test_history_routes.py` | 0 | ✅ pass | 1000ms |
| 2 | `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_ui_controls.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` | 0 | ✅ pass | 5000ms |
| 3 | `make verify-fast` | 0 | ✅ pass | 12000ms |
| 4 | `python3 -m pytest -q tests/e2e` | 0 | ✅ pass | 42000ms |

## Deviations

No production route/template changes were needed; the task resolved as a contract-test addition after the new assertions passed against current behavior.

## Known Issues

None.

## Files Created/Modified

- `tests/test_index_intake_contract.py`
