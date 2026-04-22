---
id: T02
parent: S03
milestone: M012
key_files:
  - tests/e2e/conftest.py
  - tests/e2e/test_results_page.py
  - tests/e2e/test_url_e2e.py
key_decisions:
  - Implemented the deterministic mocked-online seam by patching `app.routes.analysis._setup_orchestrator` only inside the E2E live-server fixture, leaving production orchestration untouched.
  - Made the seam observable through deterministic `data-job-id` assertions in the shared online navigation helpers so future regressions fail in-browser instead of surfacing as background-thread noise.
duration: 
verification_result: passed
completed_at: 2026-04-22T07:31:29.404Z
blocker_discovered: false
---

# T02: Stubbed mocked-online E2E submissions with deterministic fake job ids so the deep browser lane stays explicit without launching real enrichment work.

**Stubbed mocked-online E2E submissions with deterministic fake job ids so the deep browser lane stays explicit without launching real enrichment work.**

## What Happened

I kept the fix at the E2E boundary in `tests/e2e/conftest.py` instead of changing production routes. The live-server fixture now patches `app.routes.analysis._setup_orchestrator` for the E2E session only, consuming queued deterministic fake job ids when a browser test has armed the mocked-online seam. `setup_enrichment_route_mock()` now both registers the Playwright `/enrichment/status/**` intercept and queues that fake job id, so the real Flask form submit, CSRF handling, security headers, and rendered results-page contract stay in play while background enrichment submission is skipped. I then updated the shared online navigation helpers in `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` to assert that the rendered `.page-results` DOM exposes the deterministic `data-job-id` and `data-results-owner="live"` contract before waiting for enrichment rows, turning regressions in the seam into direct browser-test failures.

## Verification

Ran the task’s focused E2E command and the named deep lane after the final code change. `python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_url_e2e.py` passed with 39 tests in 15.83s. `make verify-deep` passed with 113 E2E tests in 36.12s, and its output completed cleanly without the interpreter-shutdown executor trace this task was meant to eliminate or disambiguate.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_url_e2e.py` | 0 | ✅ pass | 15830ms |
| 2 | `make verify-deep` | 0 | ✅ pass | 36120ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/e2e/conftest.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_url_e2e.py`
