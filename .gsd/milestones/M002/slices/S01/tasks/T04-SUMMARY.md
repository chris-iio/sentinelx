---
id: T04
parent: S01
milestone: M002
provides:
  - MalwareBazaar adapter converted to safe_request() with _parse_response as module-level function
  - URLhaus adapter converted to safe_request()
  - ThreatMiner _call() converted to safe_request() with body-level 404 check preserved
  - SEC-XX references removed from all 12 HTTP adapter files
key_files:
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/threatminer.py
  - tests/test_malwarebazaar.py
  - tests/test_urlhaus.py
  - tests/test_threatminer.py
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/otx.py
key_decisions:
  - URLhaus test updated to check `not call_kwargs.get("json")` instead of `"json" not in call_kwargs` because safe_request always passes json=None explicitly
patterns_established:
  - POST adapters follow same safe_request() pattern as GET — method arg is first positional param
  - Test mocks for all adapters now uniformly use patch("requests.request") since safe_request() uses requests.request() internally
  - ThreatMiner test mocks use patch("app.enrichment.http_safety.read_limited") not adapter-level — since read_limited is no longer imported by the adapter
observability_surfaces:
  - Each adapter retains logger.exception() for unexpected-error logging
  - SSRF violations surface via ValueError with "SSRF" and "allowlist" in message
  - Response size violations surface via ValueError with "exceeded size limit"
  - grep -rn 'safe_request' app/enrichment/adapters/*.py confirms all 12 adapters converted
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Convert POST adapters, ThreatMiner, and trim SEC-XX docstrings

**Converted MalwareBazaar, URLhaus, and ThreatMiner to safe_request(), removed SEC-XX references from all 12 HTTP adapters, migrated all test mocks — 924/924 tests pass, slice S01 complete**

## What Happened

Converted the final three HTTP adapters (MalwareBazaar, URLhaus, ThreatMiner) from inline HTTP plumbing to the shared `safe_request()` helper, completing the S01 slice goal of unified HTTP handling.

**MalwareBazaar:** Replaced `validate_endpoint()` + `requests.post()` + `raise_for_status()` + `read_limited()` with a single `safe_request("POST", ...)` call. Moved `_parse_response` from an instance method to a module-level function. Added `ValueError` catch for SSRF/size-cap errors from `safe_request()`.

**URLhaus:** Same pattern as MalwareBazaar — replaced inline HTTP block with `safe_request("POST", ...)`. Added `ValueError` catch. The separate `validate_endpoint()` call was absorbed into `safe_request()`.

**ThreatMiner:** Replaced the `_call()` method's `validate_endpoint()` + `requests.get()` + `raise_for_status()` + `read_limited()` block with `safe_request("GET", ...)`. Critically, did NOT use `no_data_on_404=True` — ThreatMiner always returns HTTP 200 and uses body-level `status_code == "404"` which is checked in `_lookup_ip`/`_lookup_domain`/`_lookup_hash` after `_call()` returns.

**Test mocks:** Updated all test files to use `patch("requests.request")` instead of `patch("requests.post")` or `patch("requests.get")`. For ThreatMiner, changed `read_limited` patch target from adapter-level to `app.enrichment.http_safety.read_limited`. Updated URL index assertions from `[0]` to `[1]` to account for `requests.request(method, url, ...)` positional args. Fixed URLhaus test that checked `"json" not in call_kwargs` to use `not call_kwargs.get("json")` since `safe_request` always passes `json=None`.

**SEC-XX cleanup:** Removed all SEC-04/05/06/07/16 references from module docstrings in all 12 HTTP adapter files. Replaced with standardized text pointing to `safe_request()` as the centralized control point. Left `http_safety.py`'s own SEC references intact.

## Verification

All slice-level verification checks pass:

1. **924/924 tests pass:** `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/ -q --tb=short` → 924 passed in 42.17s
2. **SEC-XX count = 0:** `grep -c 'SEC-'` for all 12 HTTP adapter files → 0 for every file
3. **No HTTP plumbing remnants:** `grep -c 'validate_endpoint|stream=True|allow_redirects=False'` → 0 for all HTTP adapters (empty after grep -v)
4. **safe_request import count = 12:** All HTTP adapters import safe_request
5. **requests.Session count = 0:** No Session usage anywhere
6. **Failure-path logging preserved:** `grep -c 'logger.exception'` → 1 for each of the 6 adapters checked

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/ -q --tb=short` | 0 | ✅ pass | 42.17s |
| 2 | `grep -c 'SEC-' app/enrichment/adapters/{12 files}` | 1 (grep no match) | ✅ pass | <1s |
| 3 | `grep -c 'validate_endpoint\|stream=True\|allow_redirects=False' ...` | 1 (grep no match) | ✅ pass | <1s |
| 4 | `grep -rn ... \| grep -c 'safe_request'` → 12 | 0 | ✅ pass | <1s |
| 5 | `grep -c 'requests.Session' app/enrichment/adapters/*.py` → all 0 | 1 (grep no match) | ✅ pass | <1s |
| 6 | `grep -c 'logger.exception' ...` → 1 for each | 0 | ✅ pass | <1s |

## Diagnostics

- `grep -rn 'safe_request' app/enrichment/adapters/*.py` — confirms all 12 HTTP adapters use the shared helper
- `grep -c 'validate_endpoint\|stream=True' app/enrichment/adapters/*.py` — detects any unconverted remnants (should be 0 for HTTP adapters)
- `grep -c 'SEC-' app/enrichment/adapters/*.py` — verifies SEC references removed from adapters (should be 0, except dns_lookup/asn_cymru)
- Each adapter's try/except logs unexpected errors via `logger.exception()` with provider name
- SSRF violations produce errors containing "SSRF" and "allowlist"
- Size-cap violations produce errors containing "exceeded size limit"

## Deviations

- URLhaus test assertion changed from `"json" not in call_kwargs` to `not call_kwargs.get("json")` because `safe_request()` always passes `json=None` to `requests.request()`. This is behaviorally equivalent — the adapter still uses form-encoded `data=`, not JSON body.
- Added `ValueError` catch blocks in all three adapters for SSRF/size-cap errors from `safe_request()`. The plan didn't mention this explicitly, but it's required since `safe_request()` raises `ValueError` for these cases rather than returning an error.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/malwarebazaar.py` — Converted to safe_request(), _parse_response moved to module-level, SEC-XX removed
- `app/enrichment/adapters/urlhaus.py` — Converted to safe_request(), SEC-XX removed
- `app/enrichment/adapters/threatminer.py` — _call() converted to safe_request(), SEC-XX removed
- `app/enrichment/adapters/abuseipdb.py` — SEC-XX docstring references removed
- `app/enrichment/adapters/crtsh.py` — SEC-XX docstring references removed
- `app/enrichment/adapters/greynoise.py` — SEC-XX docstring references removed
- `app/enrichment/adapters/hashlookup.py` — SEC-XX docstring references removed
- `app/enrichment/adapters/ip_api.py` — SEC-XX docstring references removed
- `app/enrichment/adapters/otx.py` — SEC-XX docstring references removed
- `tests/test_malwarebazaar.py` — Test mocks migrated from requests.post to requests.request
- `tests/test_urlhaus.py` — Test mocks migrated from requests.post to requests.request, URL index fixed, json assertion updated
- `tests/test_threatminer.py` — Test mocks migrated from requests.get to requests.request, read_limited patch target updated, URL indices fixed
