---
id: T02
parent: S03
milestone: M009
provides: []
requires: []
affects: []
key_files: ["tests/test_shodan.py", "tests/test_abuseipdb.py", "tests/test_greynoise.py", "tests/test_hashlookup.py", "tests/test_ip_api.py", "tests/test_otx.py", "tests/test_malwarebazaar.py", "tests/test_threatfox.py", "tests/test_urlhaus.py", "tests/test_crtsh.py", "tests/test_vt_adapter.py", "tests/test_threatminer.py"]
key_decisions: ["Kept adapter-specific error tests (429/403/400/502) while removing generic contract tests that are now centralized"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "python3 -m pytest tests/ -x -q --ignore=tests/e2e → 980 passed in 9.03s"
completed_at: 2026-03-29T19:55:36.302Z
blocker_discovered: false
---

# T02: Removed 175 duplicated contract tests from 12 adapter test files, leaving only verdict/parsing tests; full suite passes at 980 tests

> Removed 175 duplicated contract tests from 12 adapter test files, leaving only verdict/parsing tests; full suite passes at 980 tests

## What Happened
---
id: T02
parent: S03
milestone: M009
key_files:
  - tests/test_shodan.py
  - tests/test_abuseipdb.py
  - tests/test_greynoise.py
  - tests/test_hashlookup.py
  - tests/test_ip_api.py
  - tests/test_otx.py
  - tests/test_malwarebazaar.py
  - tests/test_threatfox.py
  - tests/test_urlhaus.py
  - tests/test_crtsh.py
  - tests/test_vt_adapter.py
  - tests/test_threatminer.py
key_decisions:
  - Kept adapter-specific error tests (429/403/400/502) while removing generic contract tests that are now centralized
duration: ""
verification_result: passed
completed_at: 2026-03-29T19:55:36.303Z
blocker_discovered: false
---

# T02: Removed 175 duplicated contract tests from 12 adapter test files, leaving only verdict/parsing tests; full suite passes at 980 tests

**Removed 175 duplicated contract tests from 12 adapter test files, leaving only verdict/parsing tests; full suite passes at 980 tests**

## What Happened

Systematically edited all 12 HTTP adapter test files to remove test classes and methods now covered by the shared test_adapter_contract.py from T01. Removed: protocol conformance, adapter name, requires_api_key, is_configured, supported_types, unsupported type rejection, timeout, HTTP 500, SSRF, response size limit, and Config.ALLOWED_API_HOSTS tests. Preserved adapter-specific tests (rate-limit 429, auth 401/403, malformed hash 400, crt.sh 502, VT-specific timeout tuple, geo formatting, multi-call routing, boundary conditions). Cleaned up unused imports. Test count: 1155 → 980 (175 removed, 0 failures).

## Verification

python3 -m pytest tests/ -x -q --ignore=tests/e2e → 980 passed in 9.03s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/ -x -q --ignore=tests/e2e` | 0 | ✅ pass | 9030ms |


## Deviations

GreyNoise had no adapter-specific error tests remaining, so TestGreyNoiseErrors was removed entirely. Kept VT's TestHTTPSafetyControls with adapter-specific timeout tuple tests.

## Known Issues

None.

## Files Created/Modified

- `tests/test_shodan.py`
- `tests/test_abuseipdb.py`
- `tests/test_greynoise.py`
- `tests/test_hashlookup.py`
- `tests/test_ip_api.py`
- `tests/test_otx.py`
- `tests/test_malwarebazaar.py`
- `tests/test_threatfox.py`
- `tests/test_urlhaus.py`
- `tests/test_crtsh.py`
- `tests/test_vt_adapter.py`
- `tests/test_threatminer.py`


## Deviations
GreyNoise had no adapter-specific error tests remaining, so TestGreyNoiseErrors was removed entirely. Kept VT's TestHTTPSafetyControls with adapter-specific timeout tuple tests.

## Known Issues
None.
