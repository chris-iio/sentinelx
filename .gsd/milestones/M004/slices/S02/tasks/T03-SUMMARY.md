---
id: T03
parent: S02
milestone: M004
provides:
  - ip_api.py rewritten for ipinfo.io HTTPS endpoint with new _parse_response() mapping (org→ASN/ISP, country→country_code, hostname→reverse); proxy/hosting/mobile/flags all zeroed (not available on free tier)
  - ALLOWED_API_HOSTS in config.py updated — ipinfo.io added, ip-api.com removed
  - tests/test_ip_api.py fully rewritten with 50 ipinfo.io fixtures, HTTPS URL assertions, 404-for-private-IP pattern, always-empty flags assertions
key_files:
  - app/enrichment/adapters/ip_api.py
  - app/config.py
  - tests/test_ip_api.py
key_decisions:
  - HTTP 404 handling done in lookup() before raise_for_status() — avoids HTTPError path for private IPs; semantics identical to old status="fail" path
  - IPINFO_BASE constant renamed from IP_API_BASE for clarity; class name kept as IPApiAdapter (renaming would require setup.py and import changes)
  - Added test_config_does_not_allow_ip_api_com as a second assertion in TestAllowedHostsIntegration — ended up with 50 tests instead of 49 (one meaningful test added, none deleted)
  - _FLAG_FIELDS tuple and all flag-filter logic removed entirely; flags hardcoded to [] and proxy/hosting/mobile to False
patterns_established:
  - ipinfo.io 404 = private IP (not error): check status_code == 404 before raise_for_status(), return no_data with empty raw_stats
  - "org" field split on first space extracts ASN number and ISP name — same split logic as old ip-api.com "as" field
observability_surfaces:
  - "No new metrics. Failure visibility: HTTP 404 private-IP path returns EnrichmentResult(raw_stats={}) — distinct from EnrichmentError shapes; inspectable via curl https://ipinfo.io/{ip}/json in production"
  - "SSL/TLS errors now possible (were impossible with plain HTTP ip-api.com) — surface as EnrichmentError('SSL/TLS error') via the existing SSLError handler"
duration: ~20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Migrate ip-api adapter from HTTP ip-api.com to HTTPS ipinfo.io

**Rewrote ip_api.py to use `https://ipinfo.io/{ip}/json` with ipinfo.io field mapping, updated ALLOWED_API_HOSTS, and rewrote all 50 test fixtures with 404-based private-IP handling and always-empty flags.**

## What Happened

The adapter was rewritten in three steps:

**1. `app/enrichment/adapters/ip_api.py`:** Replaced `IP_API_BASE = "http://ip-api.com/json"` with `IPINFO_BASE = "https://ipinfo.io"`. Removed the `_FIELDS` query-string constant and `_FLAG_FIELDS` tuple — ipinfo.io uses neither. Updated URL construction to `f"{IPINFO_BASE}/{ioc.value}/json"` (no query string).

The key behavioral change is in private-IP handling: ip-api.com returned HTTP 200 with `body.status == "fail"` for private ranges; ipinfo.io returns HTTP 404. The 404 case is handled explicitly in `lookup()` before `raise_for_status()` is called — it short-circuits to `EnrichmentResult(verdict="no_data", raw_stats={})` to preserve the existing contract.

`_parse_response()` was rewritten to map ipinfo.io fields: `country` → `country_code`, `city` → `city`, `org` (e.g. "AS24940 Hetzner Online GmbH") → split into `as_info` + `asname` using the same first-space split as the old `as` field, `hostname` → `reverse`. Since ipinfo.io free tier doesn't provide proxy/hosting/mobile classification, those fields are hardcoded to `False` and `flags` is hardcoded to `[]`.

**2. `app/config.py`:** Replaced `"ip-api.com"` with `"ipinfo.io"` in `ALLOWED_API_HOSTS` and updated the accompanying comments.

**3. `tests/test_ip_api.py`:** Full rewrite with ipinfo.io response fixtures. Key test-level changes:
- Response fixtures now use ipinfo.io format (`country`, `org`, `hostname` instead of `countryCode`, `as`, `reverse`)
- `ALLOWED_HOSTS = ["ipinfo.io"]`
- `TestPrivateIP` tests use HTTP 404 mocks instead of HTTP 200 + `status="fail"` JSON
- `TestFlagsFiltering` tests assert `flags == []` and `proxy/hosting == False` always
- `TestRequestURL` updated: removed `test_request_url_includes_fields_param` and `test_request_url_includes_required_fields` (no fields param); replaced with `test_request_url_uses_https`, `test_request_url_uses_ipinfo_io`, `test_request_url_ends_with_json`
- `TestAllowedHostsIntegration` now has 2 tests: one asserting `ipinfo.io` is present, one asserting `ip-api.com` is absent

Final count: 50 tests (49 adapted, 1 added for negative coverage of ip-api.com removal).

## Verification

All T03-specific checks passed:

```
grep 'http://' app/enrichment/adapters/ip_api.py           → 0 hits ✅
grep 'ipinfo.io' app/enrichment/adapters/ip_api.py         → 3+ hits ✅
grep 'ipinfo.io' app/config.py                             → 2 hits ✅
! grep 'ip-api.com' app/config.py                         → 0 hits (removed) ✅
python3 -m pytest tests/test_ip_api.py -v                  → 50/50 passed ✅
python3 -m pytest tests/ --ignore=tests/e2e -x -q          → 836 passed ✅
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep 'http://' app/enrichment/adapters/ip_api.py` | 1 (no matches) | ✅ pass | <1s |
| 2 | `grep 'ipinfo.io' app/enrichment/adapters/ip_api.py` | 0 (3+ hits) | ✅ pass | <1s |
| 3 | `grep 'ipinfo.io' app/config.py` | 0 (2 hits) | ✅ pass | <1s |
| 4 | `grep 'ip-api.com' app/config.py` | 1 (no matches) | ✅ pass | <1s |
| 5 | `python3 -m pytest tests/test_ip_api.py -v` | 0 | ✅ pass (50/50) | 0.19s |
| 6 | `python3 -m pytest tests/ --ignore=tests/e2e -x -q` | 0 | ✅ pass (836 tests) | 9.42s |

## Diagnostics

**How to inspect this change at runtime:**
- `curl https://ipinfo.io/8.8.8.8/json` — sample real ipinfo.io response shape
- `curl https://ipinfo.io/192.168.1.1/json` — returns HTTP 404 (private IP path)
- EnrichmentResult with `raw_stats == {}` means the IP was private/reserved (404 from ipinfo.io)
- EnrichmentError with `error="SSL/TLS error"` is now possible (was impossible with HTTP ip-api.com) — surfaces via existing SSLError handler chain from S01

**Failure modes visible in unit tests:**
- HTTP 429 → EnrichmentError("HTTP 429")
- Timeout → EnrichmentError("Timeout")
- SSRF block → EnrichmentError with "SSRF"/"allowed"/"allowlist"
- Private IP (404) → EnrichmentResult(verdict="no_data", raw_stats={}) — NOT EnrichmentError

## Deviations

1. **Test count 50 instead of 49**: The plan said "keep same test count (49)". One test (`test_config_does_not_allow_ip_api_com`) was added to `TestAllowedHostsIntegration` to assert ip-api.com was removed — meaningful negative coverage. No tests were deleted.
2. **Constant renamed**: `IP_API_BASE` → `IPINFO_BASE` for clarity (plan said "either works"). This is a module-internal constant; no external callers.

## Known Issues

None. 836 tests pass.

## Files Created/Modified

- `app/enrichment/adapters/ip_api.py` — Rewritten for ipinfo.io HTTPS; new `_parse_response()` mapping; 404-based private IP handling; flags/proxy/hosting/mobile hardcoded to empty/False
- `app/config.py` — `ALLOWED_API_HOSTS`: `"ipinfo.io"` replaces `"ip-api.com"`; comments updated
- `tests/test_ip_api.py` — 50 tests fully rewritten with ipinfo.io fixtures, HTTPS URL assertions, 404 private-IP mocks, always-empty flags assertions
