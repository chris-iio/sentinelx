---
id: S03
parent: M007
milestone: M007
provides:
  - Shared test helper pattern (mock_adapter_session + make_*_ioc factories) available for any future adapter test files
requires:
  - slice: S01
    provides: safe_request() consolidation completed — test files stable for refactoring
affects:
  []
key_files:
  - tests/helpers.py
  - tests/test_malwarebazaar.py
  - tests/test_vt_adapter.py
  - tests/test_threatfox.py
  - tests/test_shodan.py
  - tests/test_greynoise.py
  - tests/test_hashlookup.py
  - tests/test_urlhaus.py
  - tests/test_abuseipdb.py
  - tests/test_crtsh.py
  - tests/test_otx.py
  - tests/test_ip_api.py
  - tests/test_threatminer.py
key_decisions:
  - mock_adapter_session() returns adapter for chaining and accepts method/response/side_effect kwargs
  - Used explicit domain/hash values where local factory defaults differed from shared helper defaults to preserve test semantics
patterns_established:
  - All adapter test files now use mock_adapter_session(adapter, response=resp) or mock_adapter_session(adapter, method='post', response=resp) for session mocking — no direct adapter._session manipulation
  - All adapter test files use make_*_ioc() factories for IOC construction — no inline IOC(type=IOCType...) patterns
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M007/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-28T03:03:46.968Z
blocker_discovered: false
---

# S03: Test DRY-up

**Migrated all 12 HTTP adapter test files to shared make_*_ioc() factories and mock_adapter_session() helper, eliminating all inline IOC construction and MagicMock session setup.**

## What Happened

S03 completed the final leg of M007's cleanup by standardizing test helper usage across all 12 HTTP adapter test files.

**T01** added three new IOC factory functions (`make_sha1_ioc`, `make_cve_ioc`, `make_email_ioc`) and a `mock_adapter_session()` helper to `tests/helpers.py`. The helper accepts `method`, `response`, and `side_effect` kwargs, returns the adapter for chaining, and handles both GET and POST adapters. T01 then migrated the 6 smaller adapter test files (test_malwarebazaar, test_vt_adapter, test_threatfox, test_shodan, test_greynoise, test_hashlookup) to zero inline `IOC(type=IOCType...)` construction and zero `adapter._session = MagicMock()` blocks.

**T02** tackled the 6 larger adapter test files (test_urlhaus, test_abuseipdb, test_crtsh, test_otx, test_ip_api, test_threatminer). This batch was significantly larger — test_ip_api had 37 session mocks and 39 inline IOCs, test_threatminer had 55 session mocks and 5 local factory functions. T02 used automated regex replacement for the 181 session mocks and 99 inline IOC constructions, then fixed edge cases (multiline IOC constructors, function-call response values, multiline side_effect lists). It also removed 5 local `_make_*_ioc` factory functions from test_threatminer.py and 1 from test_crtsh.py, replacing all calls with the shared helpers.

All 1057 tests pass. All 12 adapter test files have zero `adapter._session = MagicMock()` occurrences, zero `IOC(type=IOCType` inline constructions, and zero local `_make_*_ioc` factory functions.

## Verification

All slice verification checks pass:

1. `python3 -m pytest -x -q` → 1057 passed (exit 0)
2. `grep -c 'adapter._session = MagicMock()'` across all 12 files → all 0
3. `grep -c 'IOC(type=IOCType'` across all 12 files → all 0
4. `grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py` → both 0
5. `grep -c 'def mock_adapter_session' tests/helpers.py` → 1
6. `grep -c 'def make_sha1_ioc\|def make_cve_ioc\|def make_email_ioc' tests/helpers.py` → 3

Note: grep -c returns exit code 1 when all counts are 0 (standard grep behavior). The counts themselves confirm the migration is complete.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Used automated regex-based batch replacement instead of manual per-test edits for the larger files (T02). Required three fix passes for edge cases: multiline IOC constructors, function-call response values, multiline side_effect lists. No semantic deviations from the plan.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `tests/helpers.py` — Added make_sha1_ioc(), make_cve_ioc(), make_email_ioc() factories and mock_adapter_session() helper
- `tests/test_malwarebazaar.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_vt_adapter.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_threatfox.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_shodan.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_greynoise.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_hashlookup.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_urlhaus.py` — Replaced inline IOC construction and session mocking with shared helpers (POST adapter)
- `tests/test_abuseipdb.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_crtsh.py` — Replaced inline IOC construction and session mocking; removed local _make_domain_ioc factory
- `tests/test_otx.py` — Replaced inline IOC construction and session mocking with shared helpers
- `tests/test_ip_api.py` — Replaced 37 session mocks and 39 inline IOCs with shared helpers
- `tests/test_threatminer.py` — Replaced 55 session mocks and all inline IOCs; removed 5 local _make_*_ioc factory functions
