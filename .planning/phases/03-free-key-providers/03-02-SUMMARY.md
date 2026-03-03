---
phase: 03-free-key-providers
plan: "02"
subsystem: enrichment
tags: [greynoise, abuseipdb, ip-enrichment, tdd, ssrf, provider-protocol]

# Dependency graph
requires:
  - phase: 01-registry-refactor
    provides: Provider protocol, ProviderRegistry, http_safety utilities
  - phase: 02-shodan-internetdb
    provides: ShodanAdapter reference pattern (class structure, 404 handling, _parse_response)
provides:
  - GreyNoiseAdapter: IP enrichment with riot/noise/classification verdict logic
  - AbuseIPDBAdapter: IP enrichment with confidence score threshold verdict logic
  - SSRF allowlist entries for api.greynoise.io and api.abuseipdb.com
affects: [03-03-OTX, 03-04-registry-registration, 04-results-ux]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - 404-before-raise_for_status for providers where 404 means no_data (GreyNoise)
    - pre-raise_for_status 429 check for descriptive rate limit messages (AbuseIPDB)
    - lowercase auth header key for GreyNoise ('key'), capital for AbuseIPDB ('Key')
    - score threshold verdicts: malicious >= 75, suspicious >= 25, clean if reports > 0

key-files:
  created:
    - app/enrichment/adapters/greynoise.py
    - app/enrichment/adapters/abuseipdb.py
    - tests/test_greynoise.py
    - tests/test_abuseipdb.py
  modified:
    - app/config.py

key-decisions:
  - "GreyNoise 404 treated as no_data EnrichmentResult (not EnrichmentError) — same pattern as Shodan"
  - "AbuseIPDB 429 checked before raise_for_status — returns descriptive 'Rate limit exceeded (429)' message"
  - "GreyNoise auth header lowercase 'key' (API requirement), AbuseIPDB uses capital 'Key' (different API convention)"
  - "AbuseIPDB score thresholds: >=75 malicious, >=25 suspicious, >0 reports clean, else no_data"
  - "AbuseIPDB does not use 404 for unknown IPs — score=0, totalReports=0 signals no_data"

patterns-established:
  - "Verdict priority for GreyNoise: riot > malicious_classification > noise > no_data"
  - "Score-based verdict for AbuseIPDB: confidence score thresholds with report count fallback"
  - "Rate limit pre-handling (429 before raise_for_status) enables descriptive error messages"

requirements-completed: [GREY-01, ABUSE-01]

# Metrics
duration: 4min
completed: 2026-03-03
---

# Phase 03 Plan 02: GreyNoise + AbuseIPDB Adapters Summary

**GreyNoise Community adapter with riot/noise/classification verdict + AbuseIPDB adapter with confidence score thresholds, both IP-only with full SSRF safety controls**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T11:48:21Z
- **Completed:** 2026-03-03T11:53:11Z
- **Tasks:** 2 (4 commits — 2 RED + 2 GREEN per TDD cycle)
- **Files modified:** 5

## Accomplishments

- GreyNoiseAdapter: IP enrichment using `/v3/community/{ip}` with riot/noise/classification verdict priority, 404 treated as no_data, lowercase `key` auth header
- AbuseIPDBAdapter: IP enrichment using `/api/v2/check` with score threshold verdicts (>=75 malicious, >=25 suspicious), rate limit 429 special handling, capital `Key` auth header
- Both adapters satisfy Provider protocol (isinstance check passes), support IPv4 + IPv6, reject other IOC types
- Both hostnames added to SSRF allowlist: `api.greynoise.io` and `api.abuseipdb.com`
- 62 new tests (29 GreyNoise + 33 AbuseIPDB), 440 total suite passes with zero regressions

## Task Commits

Each task was committed atomically via TDD (RED then GREEN):

1. **Task 1: GreyNoise Community Adapter (TDD)**
   - RED: `4b4c465` test(03-02): add failing tests for GreyNoiseAdapter
   - GREEN: `e2096c6` feat(03-02): implement GreyNoiseAdapter — riot/noise/classification verdict

2. **Task 2: AbuseIPDB Adapter (TDD)**
   - RED: `d51cddc` test(03-02): add failing tests for AbuseIPDBAdapter
   - GREEN: `11e1349` feat(03-02): implement AbuseIPDBAdapter — score-based verdict

_TDD tasks have 2 commits each: test (RED) then implementation (GREEN)_

## Files Created/Modified

- `app/enrichment/adapters/greynoise.py` — GreyNoiseAdapter class + `_parse_response()` function
- `tests/test_greynoise.py` — 29 tests covering protocol, verdict logic, error handling, SSRF
- `app/enrichment/adapters/abuseipdb.py` — AbuseIPDBAdapter class + `_parse_response()` function
- `tests/test_abuseipdb.py` — 33 tests covering protocol, score thresholds, boundary values, rate limit, SSRF
- `app/config.py` — Added `api.greynoise.io` and `api.abuseipdb.com` to ALLOWED_API_HOSTS

## Decisions Made

- **GreyNoise 404 = no_data result**: Same pattern as Shodan — 404 means IP not in database, not an API failure. Check 404 before `raise_for_status()`.
- **AbuseIPDB never returns 404**: Fundamentally different from Shodan/GreyNoise. Unknown IPs return 200 with score=0 and totalReports=0. No 404 special handling needed.
- **Rate limit pre-handling**: AbuseIPDB 429 is checked before `raise_for_status()` to return the descriptive "Rate limit exceeded (429)" message rather than the generic "HTTP 429" format.
- **Distinct auth header conventions**: GreyNoise uses lowercase `key` (their API requirement), AbuseIPDB uses capital `Key`. Tests verify the exact casing for each.
- **Score thresholds chosen**: >=75 malicious, >=25 suspicious, <25 with reports=clean, no reports=no_data — reflects AbuseIPDB documentation guidance.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — both adapters implemented cleanly on first attempt.

## User Setup Required

None — no external service configuration required at this stage. API keys will be configured via the Settings page UI (Phase 4 work).

## Next Phase Readiness

- GreyNoiseAdapter and AbuseIPDBAdapter ready to register in `build_registry()` (Phase 03-04 or via 03-01 registration plan)
- Both adapters satisfy Provider protocol — registry registration is a 2-line addition per adapter
- 440 tests pass, codebase in clean state for Plan 03 (OTX AlienVault adapter)

## Self-Check: PASSED

- app/enrichment/adapters/greynoise.py: FOUND
- app/enrichment/adapters/abuseipdb.py: FOUND
- tests/test_greynoise.py: FOUND
- tests/test_abuseipdb.py: FOUND
- .planning/phases/03-free-key-providers/03-02-SUMMARY.md: FOUND
- Commit 4b4c465 (RED greynoise): FOUND
- Commit e2096c6 (GREEN greynoise): FOUND
- Commit d51cddc (RED abuseipdb): FOUND
- Commit 11e1349 (GREEN abuseipdb): FOUND

---
*Phase: 03-free-key-providers*
*Completed: 2026-03-03*
