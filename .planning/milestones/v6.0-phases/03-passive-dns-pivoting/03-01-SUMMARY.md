---
phase: 03-passive-dns-pivoting
plan: 01
subsystem: enrichment
tags: [threatminer, passive-dns, adapter, tdd, python]

# Dependency graph
requires:
  - phase: 02-domain-intelligence
    provides: Provider Protocol, http_safety controls, CrtShAdapter pattern, EnrichmentResult/EnrichmentError models
provides:
  - ThreatMinerAdapter class in app/enrichment/adapters/threatminer.py
  - 69 unit tests covering all IOC types, no_data handling, HTTP errors, safety controls
  - Multi-type routing via IOC-type dispatch (IP/domain/hash)
affects:
  - 03-02 (registry wiring, config update, frontend rendering)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-type adapter routing: single adapter dispatches to different endpoints per IOCType"
    - "Two-call domain lookup: sequential rt=2 + rt=4 calls merged into one EnrichmentResult"
    - "Defensive sample extraction: _extract_samples() handles both plain string and dict results"
    - "Body-status-based no_data: check body['status_code'] == '404' (string), not HTTP status"

key-files:
  created:
    - app/enrichment/adapters/threatminer.py
    - tests/test_threatminer.py
  modified: []

key-decisions:
  - "ThreatMiner body status_code '404' (string, not int) is no_data, not an error — HTTP is always 200"
  - "Domain lookup makes two sequential API calls (rt=2 + rt=4), merged into one raw_stats dict"
  - "If first domain call hits 429, second call is skipped immediately and error returned"
  - "Body status_code '404' on one of two domain calls: include the other call's data only"
  - "IOCType.EMAIL does not exist in codebase — test used IOCType.CVE instead"
  - "verdict=no_data always — ThreatMiner data is analyst context, not a threat detection signal"

patterns-established:
  - "Pattern: _call() helper encapsulates single API call with all HTTP safety controls"
  - "Pattern: _extract_samples() defensive helper for string/dict mixed results"

requirements-completed: [DINT-03]

# Metrics
duration: 13min
completed: 2026-03-12
---

# Phase 03 Plan 01: ThreatMinerAdapter Summary

**Zero-auth ThreatMiner API v2 adapter with multi-IOC-type passive DNS (IP/domain) and related samples (domain/hash) routing, 69 tests, all green**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-12T18:17:43Z
- **Completed:** 2026-03-12T18:30:45Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Implemented ThreatMinerAdapter satisfying Provider protocol with 6 supported IOC types (IPV4, IPV6, DOMAIN, MD5, SHA1, SHA256)
- IP lookup: queries host.php rt=2, extracts domains that resolved to the IP, capped at 25
- Domain lookup: two sequential calls (domain.php rt=2 + rt=4), merged into single raw_stats with passive_dns IPs + sample hashes; 429 on first call skips second
- Hash lookup: queries sample.php rt=4, extracts related sample hashes, capped at 20; defensive dict/string handling via _extract_samples()
- Body status_code "404" (string, not HTTP 404) correctly returns no_data not error
- All HTTP safety controls enforced: timeout=TIMEOUT, allow_redirects=False, stream=True, validate_endpoint per call, params dict not f-string URL
- 69 unit tests written TDD-style (RED commit then GREEN commit)

## Task Commits

1. **RED: Failing tests for ThreatMinerAdapter** - `5fa7fa2` (test)
2. **GREEN: ThreatMinerAdapter implementation** - `60eb97d` (feat)

## Files Created/Modified

- `app/enrichment/adapters/threatminer.py` - ThreatMinerAdapter with multi-type routing, _call() helper, _lookup_ip/domain/hash methods, _extract_samples() helper
- `tests/test_threatminer.py` - 69 unit tests: TestProviderProtocol, TestIPLookup, TestDomainLookup, TestHashLookup, TestNoDataHandling, TestHTTPErrors, TestHTTPSafetyControls

## Decisions Made

- ThreatMiner body status_code "404" (a string, not int) means no data — HTTP response is always 200. Check body field, not raise_for_status(), as the primary no_data gate.
- Domain lookup uses two sequential API calls (rt=2 passive DNS + rt=4 related samples) merged into one EnrichmentResult. This keeps the adapter's output consistent with other providers (one result per IOC).
- If first domain call returns EnrichmentError (e.g., HTTP 429), second call is immediately skipped and error returned — no partial results on hard failures.
- If one domain call returns body status_code "404", only the other call's data is included in raw_stats. Both "404" -> raw_stats={}.
- verdict=no_data always — passive DNS history is analyst context, not a threat verdict.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IOCType.EMAIL does not exist in codebase**
- **Found during:** GREEN phase (running tests)
- **Issue:** Plan's interface docs listed EMAIL as an IOCType, but the actual `app/pipeline/models.py` IOCType enum only has: IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256, CVE. No EMAIL type exists.
- **Fix:** Replaced `IOCType.EMAIL` test with `IOCType.CVE` in `test_unsupported_type_email_returns_error` (renamed to `test_unsupported_type_cve_returns_error`). Also added `test_supported_types_has_six_types` to verify exact count.
- **Files modified:** tests/test_threatminer.py
- **Verification:** All 69 tests pass
- **Committed in:** 60eb97d (GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test referencing nonexistent enum value)
**Impact on plan:** Minimal — only a test fixture fix. No change to adapter logic or scope.

## Issues Encountered

None — adapter implementation matched the plan specification closely. The ThreatMiner body-404 vs HTTP-404 distinction was handled correctly from the start using the research doc's guidance.

## User Setup Required

None - ThreatMiner is zero-auth. No API keys or environment variables required.

## Next Phase Readiness

- ThreatMinerAdapter is complete and tested (69 tests, all passing)
- Plan 02 can wire ThreatMinerAdapter into the registry (`build_registry()`), add `api.threatminer.org` to ALLOWED_API_HOSTS in config.py, and update the frontend PROVIDER_CONTEXT_FIELDS and CONTEXT_PROVIDERS
- No blockers

---
*Phase: 03-passive-dns-pivoting*
*Completed: 2026-03-12*
