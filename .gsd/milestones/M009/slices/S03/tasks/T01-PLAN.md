---
estimated_steps: 28
estimated_files: 2
skills_used: []
---

# T01: Create shared parametrized adapter contract test module

Create `tests/test_adapter_contract.py` with pytest parametrize covering the shared contract behavior for all 15 adapters.

The module defines an ADAPTER_REGISTRY — a list of dataclass/namedtuple entries, one per adapter, containing:
- adapter_class: the class to instantiate
- constructor_kwargs: dict (api_key, allowed_hosts)
- name: expected .name value
- requires_api_key: expected bool
- supported_types: frozenset of expected supported IOCType members
- excluded_types: list of IOCType members known to be unsupported (for rejection tests)
- http_method: 'get' or 'post' (for mock_adapter_session; None for non-HTTP)
- is_http: bool (True for BaseHTTPAdapter subclasses)
- allowed_hosts_config_entry: the hostname string expected in Config.ALLOWED_API_HOSTS (None for non-HTTP and adapters without a config entry)
- sample_ioc_factory: function returning an IOC of a supported type for error path tests

Parametrized test classes:
1. **TestProtocolConformance** (all 15): isinstance(adapter, Provider)
2. **TestAdapterName** (all 15): adapter.name == expected
3. **TestRequiresApiKey** (all 15): adapter.requires_api_key == expected
4. **TestIsConfigured** (all 15): True when key provided (or no key needed), False when key-required but missing/empty
5. **TestSupportedTypesContains** (all 15): each type in supported_types is present
6. **TestSupportedTypesExcludes** (all 15): each type in excluded_types is absent
7. **TestUnsupportedTypeRejection** (all 15): lookup(unsupported_ioc) → EnrichmentError with 'Unsupported'
8. **TestTimeoutHandling** (12 HTTP only): mock Timeout side_effect → EnrichmentError with 'Timeout'
9. **TestHTTP500Error** (12 HTTP only): mock 500 response → EnrichmentError with 'HTTP 500'
10. **TestSSRFValidation** (12 HTTP only): allowed_hosts=[] → EnrichmentError mentioning SSRF/allowed
11. **TestResponseSizeLimit** (12 HTTP only): oversized iter_content → EnrichmentError
12. **TestAllowedHostsConfig** (adapters with config entries): hostname in Config.ALLOWED_API_HOSTS

For ThreatMiner timeout test: ThreatMiner overrides lookup() entirely and makes multi-call dispatches. The timeout test works the same way — mock_adapter_session with Timeout side_effect still triggers in the first self._session.get() call.

For CrtSh/VT/ThreatMiner: These override lookup() but still use self._session internally, so timeout/SSRF/HTTP 500 tests work identically via mock_adapter_session.

Run `python3 -m pytest tests/test_adapter_contract.py -v` to verify all parametrized tests pass.

## Inputs

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter class`
- ``app/enrichment/adapters/shodan.py` — representative simple HTTP adapter`
- ``app/enrichment/adapters/malwarebazaar.py` — representative POST adapter`
- ``app/enrichment/adapters/virustotal.py` — representative complex override adapter`
- ``app/enrichment/adapters/dns_lookup.py` — representative non-HTTP adapter`
- ``app/enrichment/adapters/asn_cymru.py` — non-HTTP adapter`
- ``app/enrichment/adapters/whois_lookup.py` — non-HTTP adapter`
- ``app/enrichment/provider.py` — Provider protocol`
- ``app/config.py` — Config.ALLOWED_API_HOSTS`
- ``app/enrichment/http_safety.py` — MAX_RESPONSE_BYTES`
- ``tests/helpers.py` — make_mock_response, make_*_ioc, mock_adapter_session`

## Expected Output

- ``tests/test_adapter_contract.py` — shared parametrized contract test module`

## Verification

python3 -m pytest tests/test_adapter_contract.py -v && python3 -m pytest tests/ -x -q --ignore=tests/e2e
