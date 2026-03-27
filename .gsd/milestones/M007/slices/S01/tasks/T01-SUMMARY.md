---
id: T01
parent: S01
milestone: M007
provides: []
requires: []
affects: []
key_files: ["app/enrichment/http_safety.py", "tests/test_http_safety.py"]
key_decisions: ["getattr(session, method.lower()) dispatch to preserve existing test mocks", "Exception chain ordering SSLError → ConnectionError enforced as correctness constraint"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "python3 -m pytest tests/test_http_safety.py -v — 14/14 pass. grep -c 'def safe_request' returns 1. Full suite: 1035 pass, 9 pre-existing M006 failures (test patches on removed imports, not caused by T01)."
completed_at: 2026-03-27T12:42:36.570Z
blocker_discovered: false
---

# T01: Added safe_request() to http_safety.py with full exception chain, SSRF validation, pre_raise_hook support, and 14 unit tests

> Added safe_request() to http_safety.py with full exception chain, SSRF validation, pre_raise_hook support, and 14 unit tests

## What Happened
---
id: T01
parent: S01
milestone: M007
key_files:
  - app/enrichment/http_safety.py
  - tests/test_http_safety.py
key_decisions:
  - getattr(session, method.lower()) dispatch to preserve existing test mocks
  - Exception chain ordering SSLError → ConnectionError enforced as correctness constraint
duration: ""
verification_result: passed
completed_at: 2026-03-27T12:42:36.571Z
blocker_discovered: false
---

# T01: Added safe_request() to http_safety.py with full exception chain, SSRF validation, pre_raise_hook support, and 14 unit tests

**Added safe_request() to http_safety.py with full exception chain, SSRF validation, pre_raise_hook support, and 14 unit tests**

## What Happened

Implemented safe_request() in app/enrichment/http_safety.py with the exact D040 signature. The function wraps SSRF validation → HTTP dispatch → optional pre_raise_hook → raise_for_status → byte-limited read in a single call. Exception chain ordering (SSLError before ConnectionError) is enforced as a correctness constraint. Created tests/test_http_safety.py with 14 tests covering all paths: GET/POST success, form-data POST, stream/redirect flags, SSRF rejection, all 5 exception types, SSLError-before-ConnectionError ordering, and pre_raise_hook short-circuit + pass-through.

## Verification

python3 -m pytest tests/test_http_safety.py -v — 14/14 pass. grep -c 'def safe_request' returns 1. Full suite: 1035 pass, 9 pre-existing M006 failures (test patches on removed imports, not caused by T01).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_http_safety.py -v` | 0 | ✅ pass | 2100ms |
| 2 | `grep -c 'def safe_request' app/enrichment/http_safety.py` | 0 | ✅ pass | 100ms |
| 3 | `python3 -m pytest -q (excluding 9 pre-existing M006 failures)` | 0 | ✅ pass (1035 passed, 9 deselected) | 83900ms |


## Deviations

None.

## Known Issues

9 pre-existing test failures from unstaged M006 route refactoring — tests patch app.routes.HistoryStore and app.routes.Thread which M006 removed.

## Files Created/Modified

- `app/enrichment/http_safety.py`
- `tests/test_http_safety.py`


## Deviations
None.

## Known Issues
9 pre-existing test failures from unstaged M006 route refactoring — tests patch app.routes.HistoryStore and app.routes.Thread which M006 removed.
