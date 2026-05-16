---
id: T01
parent: S02
milestone: M020
key_files:
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_history_routes.py
key_decisions:
  - Focused new assertions on public route/test-client responses rather than adding more private helper coupling because helper-level seam tests already existed.
duration: 
verification_result: passed
completed_at: 2026-05-16T08:40:21.623Z
blocker_discovered: false
---

# T01: Added public route regressions for grouped IOC rendering, API payload grouping, history replay safety, and diagnostic-visible route contracts.

**Added public route regressions for grouped IOC rendering, API payload grouping, history replay safety, and diagnostic-visible route contracts.**

## What Happened

Inspected the existing analysis, API, history route modules and their focused tests. The suite already contained many private helper and performance seam assertions, so I extended it with public response-level regressions: browser analysis now verifies grouped IOC card rendering and HTML escaping for raw IOC text; the API now verifies flat serialized IOC rows and grouped rows preserve mixed-type order and duplicate type grouping; history replay now verifies grouped persisted IOC cards, empty replay JSON payloads, and escaped persisted raw-match text. These tests use inline fixtures and route/test-client behavior only, avoiding .gsd or ignored planning paths.

## Verification

Ran the task verification command `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`; it passed with 130 tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py` | 0 | ✅ pass (130 passed) | 5588ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`
