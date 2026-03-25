---
estimated_steps: 8
estimated_files: 2
skills_used: []
---

# T01: Implement WhoisAdapter and unit tests

Create the WhoisAdapter class following the DnsAdapter pattern exactly. The adapter queries WHOIS data for domain IOCs using the python-whois library, returning registrar, creation date, expiry date, name servers, and org in raw_stats. Verdict is always 'no_data' (WHOIS is informational context). Write comprehensive unit tests mocking whois.whois() to cover all scenarios.

Key design constraints:
- WHOIS uses port 43 directly — do NOT import http_safety.py or requests
- requires_api_key = False, is_configured() always returns True
- allowed_hosts accepted for API compat but unused (no HTTP, no SSRF)
- Must handle datetime polymorphism: creation_date/expiration_date can be datetime, list[datetime], None, or str
- Must handle name_servers being None (default to empty list)
- Error handling follows research doc mapping: WhoisDomainNotFoundError → no_data, WhoisQuotaExceededError → EnrichmentError, etc.

## Inputs

- ``app/enrichment/adapters/dns_lookup.py` — reference pattern for non-HTTP adapter structure`
- ``app/enrichment/provider.py` — Provider protocol the adapter must satisfy`
- ``app/enrichment/models.py` — EnrichmentResult and EnrichmentError dataclasses`
- ``app/pipeline/models.py` — IOC and IOCType used for type checking and test fixtures`
- ``tests/test_dns_lookup.py` — reference pattern for comprehensive adapter unit tests`

## Expected Output

- ``app/enrichment/adapters/whois_lookup.py` — WhoisAdapter class satisfying Provider protocol`
- ``tests/test_whois_lookup.py` — comprehensive unit tests covering metadata, protocol conformance, successful lookup, error handling, datetime normalization, no-HTTP-safety invariant`

## Verification

python -m pytest tests/test_whois_lookup.py -v && python -c "from app.enrichment.adapters.whois_lookup import WhoisAdapter; from app.enrichment.provider import Provider; assert isinstance(WhoisAdapter(allowed_hosts=[]), Provider)" && grep -c 'http_safety\|validate_endpoint\|safe_request' app/enrichment/adapters/whois_lookup.py | grep -q '^0$'
