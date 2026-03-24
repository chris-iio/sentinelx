---
id: T03
parent: S01
milestone: M002
provides:
  - VT adapter converted from requests.Session to safe_request("GET", ...)
  - ThreatFox adapter converted from requests.Session to safe_request("POST", ...)
  - All 17 VT test mocks migrated from patch("requests.Session") to patch("requests.request")
  - All 15 ThreatFox test mocks migrated from patch("requests.Session") to patch("requests.request")
key_files:
  - app/enrichment/adapters/virustotal.py
  - app/enrichment/adapters/threatfox.py
  - tests/test_vt_adapter.py
  - tests/test_threatfox.py
key_decisions:
  - VT _map_http_error() preserved as adapter-specific error mapping (not absorbed into safe_request)
patterns_established:
  - Test mocks for Session-based adapters follow the same pattern as GET adapters: patch("requests.request") since safe_request() uses requests.request() internally — NOT requests.get/requests.post
  - URL assertions use call_args[0][1] (not [0][0]) since requests.request(method, url, ...) puts URL at index 1
observability_surfaces:
  - VT adapter: SSRF errors contain "SSRF" and "allowlist", size-cap errors contain "exceeded size limit", 429 produces "Rate limit exceeded (429)", 401/403 produce "Authentication error ({code})"
  - ThreatFox adapter: SSRF/size-cap same as VT; HTTP errors produce "HTTP {code}" with status code
  - Both adapters retain logger.exception() for unexpected errors, making failures traceable per-provider in logs
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Convert VT and ThreatFox — remove Sessions, migrate test mocks

**Converted VirusTotal and ThreatFox adapters from requests.Session() to safe_request(), migrated all 32 test mocks to patch("requests.request"), 924/924 tests pass**

## What Happened

Converted the two Session-based adapters (VT and ThreatFox) to use the shared `safe_request()` helper, eliminating all `requests.Session()` usage from the adapter codebase. Each adapter's `lookup()` method was simplified to a single `safe_request()` call plus response parsing, with adapter-specific error handling preserved (VT's `_map_http_error()` for 429/401/403 mapping, ThreatFox's direct status code mapping).

The task plan recommended mocking `requests.get`/`requests.post`, but since `safe_request()` uses `requests.request()` internally (as established in T01/T02), all test mocks were migrated to `patch("requests.request")` instead. This required adjusting URL assertions from `call_args[0][0]` to `call_args[0][1]` since `requests.request(method, url)` puts the URL at position 1.

Work was done one adapter at a time with test verification between each to catch missed mocks early, as the plan recommended.

## Verification

All task-level and slice-level (partial) verification checks pass:

- **VT tests:** 17/17 passed
- **ThreatFox tests:** 15/15 passed
- **Full suite:** 924/924 passed
- **Zero `requests.Session` in adapters:** virustotal.py=0, threatfox.py=0
- **Zero `requests.Session` in tests:** test_vt_adapter.py=0, test_threatfox.py=0
- **Failure-path logging retained:** both adapters retain `logger.exception()` in their catch-all handler

Slice-level checks that will fully pass after T04:
- `safe_request` import count is 9 (needs 12 after T04 converts remaining 3 adapters)
- Some adapters still have `validate_endpoint`/`stream=True`/`SEC-` references (T04 scope)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_vt_adapter.py -v --tb=short` | 0 | ✅ pass | 0.09s |
| 2 | `pytest tests/test_threatfox.py -v --tb=short` | 0 | ✅ pass | 0.07s |
| 3 | `pytest tests/ -q --tb=short` | 0 | ✅ pass (924/924) | 42.15s |
| 4 | `grep -c 'requests.Session' adapters/virustotal.py adapters/threatfox.py` | 0 | ✅ pass (both 0) | — |
| 5 | `grep -c 'requests.Session' tests/test_vt_adapter.py tests/test_threatfox.py` | 0 | ✅ pass (both 0) | — |
| 6 | `grep -rn 'logger.exception' adapters/virustotal.py adapters/threatfox.py` | 0 | ✅ pass (both retained) | — |

## Diagnostics

- `grep -rn 'safe_request' app/enrichment/adapters/*.py` — shows 9 adapters converted (Shodan + 6 simple + VT + ThreatFox)
- `grep -c 'requests.Session' app/enrichment/adapters/*.py` — 0 for every file (Session usage fully eliminated)
- `grep -c 'requests.Session' tests/test_vt_adapter.py tests/test_threatfox.py` — 0 for both (all mocks migrated)
- VT error messages: "Rate limit exceeded (429)" for 429, "Authentication error ({code})" for 401/403, "Timeout" for timeouts

## Deviations

- **Mock target:** Task plan specified migrating to `patch("requests.get")` (VT) and `patch("requests.post")` (ThreatFox). Actually used `patch("requests.request")` because `safe_request()` uses `requests.request()` internally. This was a known pattern from T01/T02.
- **Mock count:** Task plan said 16 VT + 13 ThreatFox = 29. Actual file has 17 VT tests and 15 ThreatFox tests = 32 total. The plan's count was approximate.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/virustotal.py` — Replaced Session-based lookup with safe_request("GET", ...), removed TIMEOUT/read_limited/validate_endpoint imports
- `app/enrichment/adapters/threatfox.py` — Replaced Session-based lookup with safe_request("POST", ...), removed TIMEOUT/read_limited/validate_endpoint imports
- `tests/test_vt_adapter.py` — Migrated all 17 test mocks from patch("requests.Session") to patch("requests.request")
- `tests/test_threatfox.py` — Migrated all 15 test mocks from patch("requests.Session") to patch("requests.request")
- `.gsd/milestones/M002/slices/S01/S01-PLAN.md` — Marked T03 done, added VT/ThreatFox failure-path verification
