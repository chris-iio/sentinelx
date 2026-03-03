---
phase: 03-free-key-providers
plan: "01"
subsystem: enrichment
tags: [urlhaus, otx, alienvault, abuse.ch, threat-intelligence, tdd, adapters]

requires:
  - phase: 02-shodan-internetdb
    provides: ShodanAdapter TDD pattern, http_safety module, Provider protocol

provides:
  - URLhausAdapter: POST-based multi-endpoint adapter for URL/IP/domain/hash IOCs
  - OTXAdapter: GET-based adapter supporting all 8 IOC types including CVE
  - SSRF allowlist entries for urlhaus-api.abuse.ch and otx.alienvault.com

affects:
  - 03-02-free-key-providers (GreyNoise/AbuseIPDB adapters, follows same patterns)
  - 03-03-free-key-providers (registry registration of all 4 free-key adapters)

tech-stack:
  added: []
  patterns:
    - "POST form-encoded adapter pattern (URLhaus): data= not json=, Auth-Key header"
    - "_ENDPOINT_MAP dict routing IOCType to (url_path, body_key) tuple"
    - "_OTX_TYPE_MAP dict routing IOCType to URL path string (MD5/SHA1/SHA256 -> file)"
    - "Pulse count verdict thresholds: >=5 malicious, 1-4 suspicious, 0 no_data"
    - "frozenset(IOCType) for 'all types supported' declaration"

key-files:
  created:
    - app/enrichment/adapters/urlhaus.py
    - app/enrichment/adapters/otx.py
    - tests/test_urlhaus.py
    - tests/test_otx.py
  modified:
    - app/config.py

key-decisions:
  - "URLhausAdapter.supported_types excludes SHA1 and CVE — URLhaus API does not accept SHA1 hashes"
  - "OTXAdapter uses frozenset(IOCType) for all-8-types support — simplest declaration, auto-includes future types"
  - "All three hash types (MD5/SHA1/SHA256) map to OTX 'file' path segment — OTX has no per-hash-type endpoints"
  - "URLhaus verdict for query_status='ok'+urls_count=0 is no_data — IP seen but no active malicious URLs"
  - "OTX pulse count thresholds set at 5 (malicious) and 1 (suspicious) — empirically reasonable for community threat feeds"

patterns-established:
  - "POST adapter pattern: ENDPOINT_MAP dict, data= form-encoded, custom header for auth"
  - "GET adapter pattern with type map: _OTX_TYPE_MAP[ioc.type] -> path segment, 404-before-raise_for_status"
  - "All free-key adapters follow same constructor signature: __init__(api_key, allowed_hosts)"
  - "Module-level _parse_response() function: stateless, takes (ioc, body, provider_name)"

requirements-completed: [URL-01, OTX-01]

duration: 8min
completed: "2026-03-03"
---

# Phase 03 Plan 01: URLhaus and OTX AlienVault Adapters Summary

**URLhausAdapter (POST multi-endpoint abuse.ch) and OTXAdapter (GET all-8-IOC-types including CVE), both TDD with 75 tests green**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-03T00:00:00Z
- **Completed:** 2026-03-03T00:08:00Z
- **Tasks:** 2 (4 commits: 2x RED + 2x GREEN)
- **Files modified:** 5

## Accomplishments

- URLhausAdapter: POST form-encoded requests to /v1/url/, /v1/host/, /v1/payload/ with Auth-Key header; multi-endpoint routing via _ENDPOINT_MAP; 33 tests
- OTXAdapter: GET requests to /api/v1/indicators/{type}/{value}/general with X-OTX-API-KEY header; first CVE-capable provider; pulse count verdict thresholds; 42 tests
- Both adapters added to SSRF allowlist (urlhaus-api.abuse.ch, otx.alienvault.com) in app/config.py
- Full test suite: 440 tests passing, zero regressions

## Task Commits

Each task committed atomically via TDD (RED then GREEN):

1. **Task 1 RED: URLhausAdapter tests** - `29f314d` (test)
2. **Task 1 GREEN: URLhausAdapter implementation** - `94d7396` (feat)
3. **Task 2 RED: OTXAdapter tests** - `1acb9f9` (test) *(includes config.py with otx host)*
4. **Task 2 GREEN: OTXAdapter implementation** - `b342c74` (feat)

*TDD tasks have separate test (RED) and implementation (GREEN) commits.*

## Files Created/Modified

- `/home/chris/projects/sentinelx/app/enrichment/adapters/urlhaus.py` - URLhausAdapter with POST multi-endpoint routing, Auth-Key auth, form-encoded bodies
- `/home/chris/projects/sentinelx/app/enrichment/adapters/otx.py` - OTXAdapter with GET all-8-IOC-type routing, X-OTX-API-KEY auth, pulse-count verdict
- `/home/chris/projects/sentinelx/tests/test_urlhaus.py` - 33 tests covering protocol, lookup, errors, SSRF, allowed hosts
- `/home/chris/projects/sentinelx/tests/test_otx.py` - 42 tests covering protocol, lookup (incl. CVE), errors, type mapping, allowed hosts
- `/home/chris/projects/sentinelx/app/config.py` - Added urlhaus-api.abuse.ch and otx.alienvault.com to ALLOWED_API_HOSTS

## Decisions Made

- URLhausAdapter excludes SHA1 and CVE from supported_types — URLhaus API has no SHA1 or CVE endpoints
- OTXAdapter uses `frozenset(IOCType)` (all enum members) — simplest way to declare full coverage, automatically includes any future IOCType additions
- All hash types (MD5/SHA1/SHA256) map to OTX "file" path — OTX does not have per-hash-type endpoints
- URLhaus query_status="ok" + urls_count=0 returns no_data verdict — IP was submitted to URLhaus but has no active malicious URLs associated
- OTX pulse count thresholds: >=5 = malicious, 1-4 = suspicious, 0 = no_data — balances sensitivity vs. noise for community threat feed

## Deviations from Plan

None - plan executed exactly as written.

Note: During the OTX RED commit, app/config.py also received GreyNoise and AbuseIPDB host entries from an automated hook (pre-empting Plan 02 needs). These entries were already in the file when the GREEN phase ran; `otx.alienvault.com` was added as planned.

## Issues Encountered

None - both adapters implemented cleanly on first attempt.

## Self-Check

- [x] `app/enrichment/adapters/urlhaus.py` exists and contains `class URLhausAdapter`
- [x] `app/enrichment/adapters/otx.py` exists and contains `class OTXAdapter`
- [x] `tests/test_urlhaus.py` exists with 33 passing tests
- [x] `tests/test_otx.py` exists with 42 passing tests
- [x] `urlhaus-api.abuse.ch` in Config.ALLOWED_API_HOSTS
- [x] `otx.alienvault.com` in Config.ALLOWED_API_HOSTS
- [x] All 440 tests passing (zero regressions)
- [x] Commits: 29f314d, 94d7396, 1acb9f9, b342c74

## Self-Check: PASSED

## User Setup Required

None - no external service configuration required at this stage. API keys for URLhaus and OTX will be configured via the Settings page (Phase 03-05).

## Next Phase Readiness

- URLhausAdapter and OTXAdapter are ready to be registered in build_registry() (Plan 03-03)
- Plan 03-02 (GreyNoise + AbuseIPDB adapters) is independent and can proceed in parallel
- Free-key adapter pattern established: constructor takes (api_key, allowed_hosts), is_configured() checks bool(api_key)

---
*Phase: 03-free-key-providers*
*Completed: 2026-03-03*
