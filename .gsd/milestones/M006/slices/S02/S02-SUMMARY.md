---
id: S02
parent: M006
milestone: M006
provides:
  - app/enrichment/adapters/whois_lookup.py — WhoisAdapter class following Provider protocol
  - WHOIS data rendered in domain enrichment detail rows (registrar, creation date, expiry, name servers, org)
  - WHOIS in CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS in row-factory.ts
requires:
  []
affects:
  []
key_files:
  - app/enrichment/adapters/whois_lookup.py
  - tests/test_whois_lookup.py
  - app/enrichment/setup.py
  - app/static/src/ts/modules/row-factory.ts
  - tests/test_registry_setup.py
  - requirements.txt
key_decisions:
  - WhoisAdapter uses verdict='no_data' always — WHOIS is informational context, not a threat verdict source
  - WhoisAdapter handles FailedParsingWhoisOutputError and UnknownTldError as graceful degrades (EnrichmentResult with lookup_errors) rather than hard failures (EnrichmentError)
  - Datetime normalization extracts first element from list when python-whois returns multiple dates for the same field
  - WHOIS registered in zero-auth section (no API key, always configured) matching DnsAdapter/CrtShAdapter pattern
patterns_established:
  - Non-HTTP adapters (WHOIS, DNS) must not import http_safety.py — port 43/53 protocols have no SSRF surface
  - python-whois datetime fields require normalization via _normalise_datetime() helper to handle polymorphic returns
  - Docstrings must avoid literal http_safety/validate_endpoint/safe_request strings when verification grep checks the entire file
observability_surfaces:
  - WHOIS lookup errors logged via logger.exception() for unexpected errors
  - Structured lookup_errors key in raw_stats for partial failures (parse/TLD issues)
  - EnrichmentError returned to orchestrator on timeout/command failure
drill_down_paths:
  - .gsd/milestones/M006/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:47:36.226Z
blocker_discovered: false
---

# S02: WHOIS Domain Enrichment

**Added WhoisAdapter as the 15th enrichment provider — queries WHOIS data (registrar, creation date, expiry, name servers, org) for domain IOCs via python-whois, with full frontend context field rendering.**

## What Happened

This slice added WHOIS domain enrichment end-to-end in two tasks:\n\n**T01 — WhoisAdapter implementation (56 tests):** Created `app/enrichment/adapters/whois_lookup.py` following the DnsAdapter pattern. The adapter queries WHOIS servers on port 43 via python-whois — no HTTP, no requests library, no SSRF surface. Key design: verdict is always 'no_data' (WHOIS is informational context, not a threat verdict source), raw_stats contains registrar, creation_date, expiration_date, name_servers, and org. A `_normalise_datetime()` helper handles python-whois's polymorphic date returns (single datetime, list of datetimes, None, str). Error handling maps python-whois exceptions to the correct enrichment model types: WhoisDomainNotFoundError → EnrichmentResult(no_data), FailedParsingWhoisOutputError/UnknownTldError → graceful degrade with lookup_errors, WhoisQuotaExceededError/WhoisCommandFailedError → EnrichmentError. 56 unit tests cover all paths.\n\n**T02 — Registry wiring and frontend fields:** Added python-whois==0.9.6 to requirements.txt, registered WhoisAdapter in setup.py's zero-auth section (15th provider), added WHOIS to CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS in row-factory.ts (registrar, Created, Expires, NS as tags, Org). Updated registry test count assertion from 14 to 15 and added two new WHOIS-specific tests.\n\nThe closer discovered that PROVIDER_CONTEXT_FIELDS was missing the WHOIS entry despite the task summary claiming it was added — the field mapping was added during slice closure verification.

## Verification

All verification checks passed:\n\n1. **WhoisAdapter unit tests**: `python3 -m pytest tests/test_whois_lookup.py -v` — 56 passed (0.07s)\n2. **Provider protocol conformance**: `python3 -c \"...isinstance(WhoisAdapter(allowed_hosts=[]), Provider)\"` — OK\n3. **No HTTP safety imports**: `grep -c 'http_safety|validate_endpoint|safe_request' app/enrichment/adapters/whois_lookup.py` → 0 matches\n4. **Registry tests**: `python3 -m pytest tests/test_registry_setup.py -v` — 33 passed (0.10s), includes test_registry_contains_whois and test_whois_is_always_configured\n5. **TypeScript typecheck**: `make typecheck` — clean (tsc --noEmit, no errors)\n6. **Full test suite**: `python3 -m pytest --tb=short -q` — 1035 passed (48.19s), zero failures

## Requirements Advanced

None.

## Requirements Validated

- R032 — WhoisAdapter registered as 15th provider. 56 unit tests verify: registrar/creation_date/expiration_date/name_servers/org extraction, datetime polymorphism, domain-not-found handling, quota/command errors, graceful degrade. WHOIS in CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS. 1035 tests pass, typecheck clean.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

The closer discovered that the WHOIS entry in PROVIDER_CONTEXT_FIELDS (row-factory.ts) was missing — the task summary for T02 claimed it was added but the code change hadn't been applied. The closer added the 5-field WHOIS entry (registrar, creation_date→Created, expiration_date→Expires, name_servers→NS/tags, org→Org) and re-verified typecheck. Also fixed a pre-existing duplicated code block at the end of row-factory.ts that was causing TypeScript compilation errors (T02).

## Known Limitations

WHOIS data quality varies by TLD registrar — some TLDs return minimal data or restrict WHOIS queries. The python-whois library handles most common TLDs but may fail on obscure ones (handled via graceful degrade with lookup_errors). No live WHOIS queries are tested — all tests use mocked responses.

## Follow-ups

None.

## Files Created/Modified

- `app/enrichment/adapters/whois_lookup.py` — New WhoisAdapter class implementing Provider protocol — queries WHOIS data via python-whois, returns registrar/dates/NS/org in raw_stats, handles datetime polymorphism and all python-whois error types
- `tests/test_whois_lookup.py` — 56 unit tests covering metadata, protocol conformance, successful lookups, raw_stats extraction, datetime polymorphism (7 cases), domain-not-found, quota/command errors, graceful degrade, unexpected exceptions, no-HTTP-safety invariant
- `requirements.txt` — Added python-whois==0.9.6 dependency
- `app/enrichment/setup.py` — Imported and registered WhoisAdapter in zero-auth section, updated provider count from 14 to 15
- `app/static/src/ts/modules/row-factory.ts` — Added WHOIS to CONTEXT_PROVIDERS set and PROVIDER_CONTEXT_FIELDS with registrar/Created/Expires/NS(tags)/Org field definitions
- `tests/test_registry_setup.py` — Updated provider count assertion to 15, added test_registry_contains_whois and test_whois_is_always_configured tests
