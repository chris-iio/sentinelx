---
estimated_steps: 6
estimated_files: 4
skills_used: []
---

# T02: Wire WhoisAdapter into registry, add frontend context fields, update tests

Three mechanical changes to integrate the WhoisAdapter into the running system:

1. **requirements.txt**: Add `python-whois==0.9.6` dependency
2. **setup.py**: Import WhoisAdapter and register it in the zero-auth section alongside DnsAdapter. Update docstring provider count from 14 to 15.
3. **row-factory.ts**: Add 'WHOIS' to CONTEXT_PROVIDERS set (line 162). Add WHOIS entry to PROVIDER_CONTEXT_FIELDS with fields: registrar (text), creation_date as 'Created' (text), expiration_date as 'Expires' (text), name_servers as 'NS' (tags), org (text).
4. **test_registry_setup.py**: Update `test_registry_has_fourteen_providers` to assert 15. Add `test_registry_contains_whois` and `test_whois_is_always_configured` tests. The `get_provider_key` call count stays at 6 (WHOIS has no API key).

Verify with pytest on registry tests, make typecheck, and full test suite.

## Inputs

- ``app/enrichment/adapters/whois_lookup.py` — WhoisAdapter class created in T01`
- ``app/enrichment/setup.py` — existing registry factory to add WhoisAdapter import and register() call`
- ``requirements.txt` — existing dependencies list to add python-whois`
- ``app/static/src/ts/modules/row-factory.ts` — CONTEXT_PROVIDERS set and PROVIDER_CONTEXT_FIELDS map to extend`
- ``tests/test_registry_setup.py` — existing registry tests to update provider count and add WHOIS tests`

## Expected Output

- ``requirements.txt` — updated with python-whois==0.9.6`
- ``app/enrichment/setup.py` — WhoisAdapter imported and registered as 15th provider`
- ``app/static/src/ts/modules/row-factory.ts` — WHOIS added to CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS`
- ``tests/test_registry_setup.py` — provider count updated to 15, WHOIS containment and configuration tests added`

## Verification

python -m pytest tests/test_registry_setup.py -v && make typecheck && python -m pytest --tb=short -q
