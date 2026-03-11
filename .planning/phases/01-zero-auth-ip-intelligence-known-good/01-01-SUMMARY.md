---
phase: 01-zero-auth-ip-intelligence-known-good
plan: "01"
subsystem: enrichment-adapters
tags: [adapter, zero-auth, hashlookup, ip-api, geoip, nsrl, known-good]
dependency_graph:
  requires: []
  provides:
    - HashlookupAdapter (CIRCL NSRL hash lookups)
    - IPApiAdapter (ip-api.com GeoIP/rDNS/proxy)
  affects:
    - app/enrichment/setup.py (registry now 10 providers)
    - app/config.py (ALLOWED_API_HOSTS expanded)
tech_stack:
  added: []
  patterns:
    - ShodanAdapter pattern extended to MD5/SHA1/SHA256 hash types
    - ip-api.com body.status field check (HTTP 200 for both success and fail)
    - Pre-formatted geo string with middle dot (U+00B7) separator
    - Pre-filtered flags list for true-flag names only
key_files:
  created:
    - app/enrichment/adapters/hashlookup.py
    - app/enrichment/adapters/ip_api.py
    - tests/test_hashlookup.py
    - tests/test_ip_api.py
  modified:
    - app/enrichment/setup.py
    - app/config.py
    - tests/test_registry_setup.py
decisions:
  - "HashlookupAdapter: 404 maps to verdict=no_data (not error) — absence from NSRL does not imply maliciousness"
  - "IPApiAdapter name is 'IP Context' — matches frontend identifier for special context row rendering"
  - "ip-api.com uses HTTP (not HTTPS) — free tier does not support HTTPS; this is intentional"
  - "geo string pre-formatted in Python as 'CC · City · ASN (ISP)' — frontend renders directly without parsing"
  - "flags pre-filtered to list of true-flag names — trivial frontend rendering"
metrics:
  duration: "8m 9s"
  completed_date: "2026-03-11"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 3
  tests_added: 105
---

# Phase 01 Plan 01: Zero-Auth Adapters (Hashlookup + IP Context) Summary

**One-liner:** CIRCL Hashlookup NSRL adapter (MD5/SHA1/SHA256 -> known_good/no_data) and ip-api.com IP Context adapter (IPv4/IPv6 -> geo/rDNS/flags), wired into 10-provider registry with SSRF allowlist updates.

## What Was Built

Two new zero-auth enrichment adapters following the established ShodanAdapter pattern:

**HashlookupAdapter** (`app/enrichment/adapters/hashlookup.py`):
- Queries `https://hashlookup.circl.lu/lookup/{type}/{hash}` for MD5, SHA1, SHA256 hashes
- 200 response (hash in NSRL) -> `verdict=known_good`, `raw_stats={file_name, source, db}`
- 404 response (hash not in NSRL) -> `verdict=no_data` with empty stats (not an error)
- Full HTTP safety: validate_endpoint, TIMEOUT=(5,30), allow_redirects=False, stream=True

**IPApiAdapter** (`app/enrichment/adapters/ip_api.py`):
- Queries `http://ip-api.com/json/{ip}?fields=...` for IPv4 and IPv6
- body.status="success" -> `verdict=no_data` with geo/rDNS/ASN/flags in raw_stats
- body.status="fail" (private/reserved IP) -> `verdict=no_data` with empty raw_stats
- Pre-formats `geo` as "CC · City · AS12345 (ISP)" using U+00B7 middle dot
- Pre-filters `flags` to only include names of true flags (e.g., `["proxy", "hosting"]`)
- Always `verdict=no_data` — IP context is informational, never a threat verdict

**Registry and SSRF updates** (`app/enrichment/setup.py`, `app/config.py`):
- Both adapters registered in `build_registry()` — total provider count 8 -> 10
- `ALLOWED_API_HOSTS` expanded with `"ip-api.com"` and `"hashlookup.circl.lu"`

## Tests

All tests written using TDD (RED -> GREEN):

| File | Tests Added | Coverage |
|------|-------------|----------|
| tests/test_hashlookup.py | 35 | HashlookupAdapter: URL patterns, verdicts, safety controls, protocol conformance |
| tests/test_ip_api.py | 50 | IPApiAdapter: geo formatting, flags filtering, private IP, safety controls |
| tests/test_registry_setup.py | +5 (modified) | Registry count 8->10, new provider presence, zero-auth configuration |

Total new tests: 85 new + 5 updated registry tests.

Full suite: 650/652 pass (2 pre-existing E2E title case failures unrelated to this plan).

## Deviations from Plan

None — plan executed exactly as written.

The one nuance: the `test_config_allows_hashlookup` and `test_config_allows_ip_api` tests were written in Tasks 1 and 2 respectively (as part of the AllowedHostsIntegration test class), and they failed until Task 3 added the entries to `ALLOWED_API_HOSTS`. This is correct TDD behavior — the tests crossed the task boundary intentionally to verify the complete integration.

## Deferred Items

**Pre-existing E2E failures (out of scope):**
- `tests/e2e/test_homepage.py::test_page_title` — expects "SentinelX" but page title is "sentinelx" (case mismatch in `<title>` tag)
- `tests/e2e/test_settings.py::test_settings_page_title_tag` — same issue
- These failures existed before this plan and are unrelated to the adapter work.

## Self-Check: PASSED

Files created:
- app/enrichment/adapters/hashlookup.py: FOUND
- app/enrichment/adapters/ip_api.py: FOUND
- tests/test_hashlookup.py: FOUND
- tests/test_ip_api.py: FOUND

Commits:
- 042a966: test(01-01): add failing tests for HashlookupAdapter — FOUND
- 4c57734: feat(01-01): implement HashlookupAdapter for CIRCL NSRL hash lookups — FOUND
- 2c2c99f: test(01-01): add failing tests for IPApiAdapter — FOUND
- 894ddec: feat(01-01): implement IPApiAdapter for GeoIP, rDNS, and proxy flags — FOUND
- 55c6b91: feat(01-01): register HashlookupAdapter and IPApiAdapter, update SSRF allowlist — FOUND
