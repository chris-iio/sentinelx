---
id: T01
parent: S02
milestone: M006
key_files:
  - app/enrichment/adapters/whois_lookup.py
  - tests/test_whois_lookup.py
key_decisions:
  - WhoisAdapter handles FailedParsingWhoisOutputError and UnknownTldError from whois.whois() as graceful degrades (EnrichmentResult with lookup_errors) rather than hard failures (EnrichmentError), matching the error mapping from the research doc
  - Datetime normalization extracts first element from list (python-whois sometimes returns multiple dates for the same field)
  - Docstrings avoid literal http_safety/validate_endpoint/safe_request strings to satisfy the no-HTTP-safety grep verification, using descriptive phrases instead
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:36:37.471Z
blocker_discovered: false
---

# T01: Implement WhoisAdapter with full error handling, datetime normalization, and 56 unit tests

**Implement WhoisAdapter with full error handling, datetime normalization, and 56 unit tests**

## What Happened

Created the WhoisAdapter class in `app/enrichment/adapters/whois_lookup.py` following the DnsAdapter pattern exactly. The adapter queries WHOIS data for domain IOCs using the python-whois library, returning registrar, creation_date, expiration_date, name_servers, and org in raw_stats.

Key implementation details:
- **Protocol compliance**: name="WHOIS", supported_types=frozenset({IOCType.DOMAIN}), requires_api_key=False, is_configured() always returns True
- **No HTTP safety**: WHOIS uses port 43 directly — no http_safety.py imports, no requests, no SSRF surface. Docstrings were carefully worded to avoid literal "http_safety"/"validate_endpoint"/"safe_request" strings that would trip the verification grep.
- **Datetime polymorphism**: `_normalise_datetime()` helper handles all python-whois return shapes — single datetime → isoformat, list of datetimes → first element isoformat, empty list → None, None → None, string → pass-through
- **name_servers None handling**: Defaults to empty list when python-whois returns None
- **Error handling mapping**: WhoisDomainNotFoundError → EnrichmentResult(verdict='no_data'); FailedParsingWhoisOutputError/UnknownTldError → EnrichmentResult with lookup_errors (graceful degrade); WhoisQuotaExceededError → EnrichmentError; WhoisCommandFailedError → EnrichmentError; unexpected exceptions → EnrichmentError + logger.exception()

Wrote comprehensive unit tests in `tests/test_whois_lookup.py` with 56 tests organized into 12 test classes covering: class metadata, protocol conformance, unsupported IOC type, successful lookups, raw_stats field extraction, datetime polymorphism (7 cases), domain not found, quota exceeded, command failed, graceful degrade (parse/TLD errors), unexpected exceptions with logging verification, no-HTTP-safety invariant, and _normalise_datetime unit tests.

## Verification

All three verification checks from the task plan pass:
1. `python3 -m pytest tests/test_whois_lookup.py -v` — 56 passed in 0.07s
2. `python3 -c "...isinstance(WhoisAdapter(allowed_hosts=[]), Provider)"` — Protocol check PASS
3. `grep -c 'http_safety|validate_endpoint|safe_request' ... | grep -q '^0$'` — No HTTP safety imports PASS

Full test suite: 1033 passed in 49.32s (no regressions)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_whois_lookup.py -v` | 0 | ✅ pass | 70ms |
| 2 | `python3 -c "from app.enrichment.adapters.whois_lookup import WhoisAdapter; from app.enrichment.provider import Provider; assert isinstance(WhoisAdapter(allowed_hosts=[]), Provider)"` | 0 | ✅ pass | 200ms |
| 3 | `grep -c 'http_safety|validate_endpoint|safe_request' app/enrichment/adapters/whois_lookup.py | grep -q '^0$'` | 0 | ✅ pass | 10ms |
| 4 | `python3 -m pytest --tb=short -q` | 0 | ✅ pass | 49320ms |


## Deviations

Docstrings in whois_lookup.py were reworded to avoid literal "http_safety", "validate_endpoint", and "safe_request" strings that the verification grep checks for. The DnsAdapter reference has the same issue (its docstrings mention http_safety 3 times), but since the verification command is specified for whois_lookup.py only, the rewording was necessary to pass the grep -q '^0$' check. The semantic meaning is identical — just phrased as "HTTP safety module" / "endpoint validation" instead.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/whois_lookup.py`
- `tests/test_whois_lookup.py`
