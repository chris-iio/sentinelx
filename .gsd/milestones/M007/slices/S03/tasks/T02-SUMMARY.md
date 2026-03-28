---
id: T02
parent: S03
milestone: M007
provides: []
requires: []
affects: []
key_files: ["tests/test_urlhaus.py", "tests/test_abuseipdb.py", "tests/test_crtsh.py", "tests/test_otx.py", "tests/test_ip_api.py", "tests/test_threatminer.py"]
key_decisions: ["Used explicit domain/hash values where local factory defaults differed from shared helper defaults to preserve test semantics"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "All 1057 tests pass. Zero adapter._session = MagicMock() occurrences across all 12 adapter test files. Zero IOC(type=IOCType inline constructions. Zero local _make_*_ioc factory functions in test_threatminer.py and test_crtsh.py."
completed_at: 2026-03-28T02:58:35.362Z
blocker_discovered: false
---

# T02: Migrated all 6 larger adapter test files to shared helpers; removed 6 local factories from test_threatminer and test_crtsh; all 1057 tests pass

> Migrated all 6 larger adapter test files to shared helpers; removed 6 local factories from test_threatminer and test_crtsh; all 1057 tests pass

## What Happened
---
id: T02
parent: S03
milestone: M007
key_files:
  - tests/test_urlhaus.py
  - tests/test_abuseipdb.py
  - tests/test_crtsh.py
  - tests/test_otx.py
  - tests/test_ip_api.py
  - tests/test_threatminer.py
key_decisions:
  - Used explicit domain/hash values where local factory defaults differed from shared helper defaults to preserve test semantics
duration: ""
verification_result: passed
completed_at: 2026-03-28T02:58:35.362Z
blocker_discovered: false
---

# T02: Migrated all 6 larger adapter test files to shared helpers; removed 6 local factories from test_threatminer and test_crtsh; all 1057 tests pass

**Migrated all 6 larger adapter test files to shared helpers; removed 6 local factories from test_threatminer and test_crtsh; all 1057 tests pass**

## What Happened

Migrated test_urlhaus, test_abuseipdb, test_crtsh, test_otx, test_ip_api, and test_threatminer to use mock_adapter_session() and make_*_ioc() factories from tests/helpers.py. Used automated regex replacement for 181 session mocks and 99 inline IOC constructions, then fixed edge cases (multiline IOC constructors, function-call response values, multiline side_effect lists). Removed 5 local factory functions from test_threatminer.py and 1 from test_crtsh.py. Updated imports in all 6 files.

## Verification

All 1057 tests pass. Zero adapter._session = MagicMock() occurrences across all 12 adapter test files. Zero IOC(type=IOCType inline constructions. Zero local _make_*_ioc factory functions in test_threatminer.py and test_crtsh.py.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -x -q` | 0 | ✅ pass | 52440ms |
| 2 | `grep -c 'adapter._session = MagicMock()' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py` | 1 | ✅ pass (all 0) | 100ms |
| 3 | `grep -c 'IOC(type=IOCType' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py` | 1 | ✅ pass (all 0) | 100ms |
| 4 | `grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py` | 1 | ✅ pass (both 0) | 100ms |


## Deviations

Used automated regex migration instead of manual per-file editing due to volume; required three fix passes for edge cases.

## Known Issues

None.

## Files Created/Modified

- `tests/test_urlhaus.py`
- `tests/test_abuseipdb.py`
- `tests/test_crtsh.py`
- `tests/test_otx.py`
- `tests/test_ip_api.py`
- `tests/test_threatminer.py`


## Deviations
Used automated regex migration instead of manual per-file editing due to volume; required three fix passes for edge cases.

## Known Issues
None.
