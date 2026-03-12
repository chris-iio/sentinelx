---
phase: 02-domain-intelligence
plan: "02"
subsystem: enrichment
tags: [crt.sh, certificate-transparency, domain, http-safety, tdd, mocked-tests]

# Dependency graph
requires:
  - phase: 02-domain-intelligence
    provides: HTTP safety controls (validate_endpoint, TIMEOUT, read_limited) from http_safety.py

provides:
  - CrtShAdapter class at app/enrichment/adapters/crtsh.py
  - cert_count, earliest, latest, subdomains fields in raw_stats for domain IOCs
  - 37 unit tests covering cert extraction, normalization, error handling, HTTP safety

affects:
  - 02-03 (registration plan adds CrtShAdapter to ALLOWED_API_HOSTS and provider registry)
  - Phase 04 frontend will need to render CT history fields from raw_stats

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zero-auth HTTP adapter pattern: validate_endpoint + TIMEOUT + stream=True + allow_redirects=False + read_limited"
    - "Subdomain normalization pipeline: split name_value on newline, lstrip wildcard, lowercase, dedupe via set, sort, cap"
    - "read_limited() returns parsed JSON list for array endpoints — annotation says dict but runtime is list (Python json.loads handles both)"

key-files:
  created:
    - app/enrichment/adapters/crtsh.py
    - tests/test_crtsh.py
  modified: []

key-decisions:
  - "CrtShAdapter verdict is always no_data — CT history is informational context for analysts, not a threat signal"
  - "read_limited() patched directly in tests (app.enrichment.adapters.crtsh.read_limited) to control list return value without needing iter_content mock complexity"
  - "Subdomain cap set at 50 — balances analyst utility vs response size for domains with extensive CT history"

patterns-established:
  - "TDD for HTTP adapters: write tests first patching both requests.get and read_limited, then implement"
  - "All crt.sh tests use double patch context manager (requests.get + read_limited) for clean list injection"

requirements-completed: [DINT-02]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 02 Plan 02: CrtSh Adapter Summary

**CrtShAdapter querying crt.sh CT API via mocked HTTP, returning cert_count/date-range/deduplicated-subdomain-list with full SEC-04/05/06/16 safety controls**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-12T15:42:24Z
- **Completed:** 2026-03-13T00:46:24Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- CrtShAdapter queries `https://crt.sh/?q={domain}&output=json` with all HTTP safety controls
- Extracts cert_count, earliest/latest dates (YYYY-MM-DD), and a normalized subdomain list from SANs
- Subdomain normalization: wildcard `*.` prefix stripped, lowercased, deduplicated, sorted alphabetically, capped at 50
- Empty `[]` response returns `EnrichmentResult(verdict="no_data", raw_stats={})` cleanly
- 37 unit tests — all mocked (no real network calls), covering every behavior in the plan spec

## Task Commits

1. **Task 1 RED: Failing tests** - `f94d19d` (test)
2. **Task 1 GREEN: CrtShAdapter implementation** - `907b2a4` (feat)

## Files Created/Modified

- `app/enrichment/adapters/crtsh.py` - CrtShAdapter with `_parse_response()` helper, full HTTP safety
- `tests/test_crtsh.py` - 37 unit tests organized in 5 test classes

## Decisions Made

- `verdict="no_data"` always — CT history doesn't indicate malicious/clean, it's analyst context
- Patching `app.enrichment.adapters.crtsh.read_limited` directly in tests avoids needing `iter_content` mock setup, since `read_limited()` returns a parsed list for crt.sh responses
- Subdomain cap of 50 chosen to match the plan spec

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. crt.sh is zero-auth.

## Next Phase Readiness

- CrtShAdapter is complete and tested; Plan 02-03 registers it in the provider registry and adds `crt.sh` to `ALLOWED_API_HOSTS`
- Both `DnsAdapter` (Plan 02-01) and `CrtShAdapter` (Plan 02-02) are ready for registration

---
*Phase: 02-domain-intelligence*
*Completed: 2026-03-13*
