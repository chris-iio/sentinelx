---
id: T01
parent: S03
milestone: M015
key_files:
  - app/routes/analysis.py
  - app/templates/index.html
  - tests/test_index_intake_contract.py
  - tests/test_history_routes.py
key_decisions:
  - Kept recent analysis retrieval server-rendered and fail-open using `HistoryStore.list_recent(limit=4)`; no client fetch, provider calls, background work, or per-row detail loads were added.
duration: 
verification_result: passed
completed_at: 2026-04-26T10:50:45.502Z
blocker_discovered: false
---

# T01: Wired the intake page to fail-open recent-analysis summaries with bounded history lookup and safe template states.

**Wired the intake page to fail-open recent-analysis summaries with bounded history lookup and safe template states.**

## What Happened

Updated GET `/` to call `current_app.history_store.list_recent(limit=4)` through a narrow helper that catches storage failures, logs only the exception class, and renders the intake form regardless of history availability. Added a compact server-rendered Recent Analyses rail inside `.intake-workbench` with deterministic row, empty, and unavailable DOM states, safe Jinja autoescaping, fallback copy for missing optional fields, and `/history/<id>` links for resumable analyses. Replaced the old index-contract expectation that forbade recent history with S03 coverage for seeded rows, bounded reads, empty history, fail-open exceptions, preserved form/CSRF selectors, and markup-like stored text.

## Verification

Ran the focused index contract after implementation: `python3 -m pytest -q tests/test_index_intake_contract.py` passed 6 tests. Ran the task verification command with timing: `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_history_routes.py::TestHistoryListRoute tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present` passed 13 tests. The tests verify bounded history reads, sanitized warning logging on failures, deterministic recent-analysis DOM states, preserved intake form selectors/CSRF, offline no-HTTP behavior, and security headers.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_index_intake_contract.py` | 0 | ✅ pass | 300ms |
| 2 | `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_history_routes.py::TestHistoryListRoute tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present` | 0 | ✅ pass | 590ms |

## Deviations

Also passed recent-analysis context to the no-input POST error render so the shared index template receives the same fail-open state when re-rendered after validation errors.

## Known Issues

Browser/styling proof is intentionally left to the downstream T02 task per this task plan.

## Files Created/Modified

- `app/routes/analysis.py`
- `app/templates/index.html`
- `tests/test_index_intake_contract.py`
- `tests/test_history_routes.py`
