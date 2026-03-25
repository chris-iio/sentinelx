# S02: WHOIS Domain Enrichment

**Goal:** Domain IOC enrichment includes WHOIS data (registrar, creation date, expiry, name servers) in a provider detail row alongside DNS Records, VirusTotal, OTX, etc.
**Demo:** Domain IOC enrichment shows WHOIS data (registrar, creation date, expiry, name servers) in a provider detail row alongside DNS Records, VirusTotal, OTX, etc.

## Must-Haves

- WhoisAdapter satisfies Provider protocol, supports DOMAIN only, requires no API key
- WhoisAdapter.lookup() returns EnrichmentResult with verdict="no_data" and raw_stats containing registrar, creation_date, expiration_date, name_servers, org
- Datetime polymorphism handled: single datetime, list of datetimes, None, str fallback
- Error handling: domain not found → no_data, quota/timeout → EnrichmentError, parse failure → graceful degrade
- Adapter registered in setup.py as 15th provider (zero-auth section)
- python-whois added to requirements.txt
- WHOIS added to CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS in row-factory.ts
- All existing tests pass plus new WhoisAdapter and registry tests
- make typecheck passes

## Proof Level

- This slice proves: contract — all behavior verified through mocked unit tests; no live WHOIS queries needed

## Integration Closure

- Upstream surfaces consumed: `app/enrichment/provider.py` (Provider protocol), `app/enrichment/models.py` (EnrichmentResult, EnrichmentError), `app/pipeline/models.py` (IOC, IOCType)
- New wiring introduced: `app/enrichment/adapters/whois_lookup.py` (new adapter), one `register()` call in `app/enrichment/setup.py`, `python-whois` dependency in `requirements.txt`, WHOIS entries in `row-factory.ts` CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS
- What remains before milestone is truly usable end-to-end: S03 (URL polish), S04 (input page redesign) — independent of this slice

## Verification

- Runtime signals: WHOIS lookup errors logged via `logger.exception()` for unexpected errors; structured `lookup_errors` key in raw_stats for partial failures
- Inspection surfaces: raw_stats in enrichment result JSON — visible on detail page as key-value pairs
- Failure visibility: EnrichmentError returned to orchestrator on timeout/command failure; lookup_errors list for parse/TLD issues
- Redaction constraints: none — WHOIS data is public registry info

## Tasks

- [x] **T01: Implement WhoisAdapter and unit tests** `est:45m`
  Create the WhoisAdapter class following the DnsAdapter pattern exactly. The adapter queries WHOIS data for domain IOCs using the python-whois library, returning registrar, creation date, expiry date, name servers, and org in raw_stats. Verdict is always 'no_data' (WHOIS is informational context). Write comprehensive unit tests mocking whois.whois() to cover all scenarios.

Key design constraints:
- WHOIS uses port 43 directly — do NOT import http_safety.py or requests
- requires_api_key = False, is_configured() always returns True
- allowed_hosts accepted for API compat but unused (no HTTP, no SSRF)
- Must handle datetime polymorphism: creation_date/expiration_date can be datetime, list[datetime], None, or str
- Must handle name_servers being None (default to empty list)
- Error handling follows research doc mapping: WhoisDomainNotFoundError → no_data, WhoisQuotaExceededError → EnrichmentError, etc.
  - Files: `app/enrichment/adapters/whois_lookup.py`, `tests/test_whois_lookup.py`
  - Verify: python -m pytest tests/test_whois_lookup.py -v && python -c "from app.enrichment.adapters.whois_lookup import WhoisAdapter; from app.enrichment.provider import Provider; assert isinstance(WhoisAdapter(allowed_hosts=[]), Provider)" && grep -c 'http_safety\|validate_endpoint\|safe_request' app/enrichment/adapters/whois_lookup.py | grep -q '^0$'

- [x] **T02: Wire WhoisAdapter into registry, add frontend context fields, update tests** `est:30m`
  Three mechanical changes to integrate the WhoisAdapter into the running system:

1. **requirements.txt**: Add `python-whois==0.9.6` dependency
2. **setup.py**: Import WhoisAdapter and register it in the zero-auth section alongside DnsAdapter. Update docstring provider count from 14 to 15.
3. **row-factory.ts**: Add 'WHOIS' to CONTEXT_PROVIDERS set (line 162). Add WHOIS entry to PROVIDER_CONTEXT_FIELDS with fields: registrar (text), creation_date as 'Created' (text), expiration_date as 'Expires' (text), name_servers as 'NS' (tags), org (text).
4. **test_registry_setup.py**: Update `test_registry_has_fourteen_providers` to assert 15. Add `test_registry_contains_whois` and `test_whois_is_always_configured` tests. The `get_provider_key` call count stays at 6 (WHOIS has no API key).

Verify with pytest on registry tests, make typecheck, and full test suite.
  - Files: `requirements.txt`, `app/enrichment/setup.py`, `app/static/src/ts/modules/row-factory.ts`, `tests/test_registry_setup.py`
  - Verify: python -m pytest tests/test_registry_setup.py -v && make typecheck && python -m pytest --tb=short -q

## Files Likely Touched

- app/enrichment/adapters/whois_lookup.py
- tests/test_whois_lookup.py
- requirements.txt
- app/enrichment/setup.py
- app/static/src/ts/modules/row-factory.ts
- tests/test_registry_setup.py
