# S03: Adapter test consolidation

**Goal:** Shared parametrized test module covers protocol/error/type-guard contract once for all 15 adapters. Per-adapter test files contain only verdict+parsing tests. Full test suite passes.
**Demo:** After this: After this: Shared parametrized test module covers protocol/error/type-guard contract once for all 15 adapters. Per-adapter test files contain only verdict+parsing tests. Test suite passes.

## Tasks
- [x] **T01: Created tests/test_adapter_contract.py with 172 parametrized tests covering protocol/error/type-guard/safety contracts for all 15 adapters** — Create `tests/test_adapter_contract.py` with pytest parametrize covering the shared contract behavior for all 15 adapters.

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
  - Estimate: 45m
  - Files: tests/test_adapter_contract.py, tests/helpers.py
  - Verify: python3 -m pytest tests/test_adapter_contract.py -v && python3 -m pytest tests/ -x -q --ignore=tests/e2e
- [x] **T02: Removed 175 duplicated contract tests from 12 adapter test files, leaving only verdict/parsing tests; full suite passes at 980 tests** — Remove contract test functions from each HTTP adapter test file that are now covered by `tests/test_adapter_contract.py`. The contract tests to remove are those testing:
- Protocol conformance (isinstance Provider)
- Adapter name
- requires_api_key
- is_configured (true/false)
- supported_types contains/excludes
- Unsupported type rejection
- Timeout handling
- HTTP 500/422 error handling
- SSRF validation (allowed_hosts=[])
- Response size limit
- Config.ALLOWED_API_HOSTS membership

For each file, remove entire test classes if all methods are contract tests. Remove individual methods if the class mixes contract and verdict tests. Remove unused imports after deletions.

Files to edit (12 HTTP adapters):
1. `tests/test_shodan.py` — remove TestLookupErrors (unsupported+timeout+http errors), TestHTTPSafetyControls (ssrf+size), TestSupportedTypes, TestProtocolConformance, TestAllowedHostsIntegration. Keep TestLookupFound, TestLookupNotFound.
2. `tests/test_abuseipdb.py` — remove contract methods from TestAbuseIPDBProtocol and TestAbuseIPDBErrors, remove TestAllowedHosts. Keep verdict/parsing tests in TestAbuseIPDBLookup and non-contract error tests.
3. `tests/test_greynoise.py` — same pattern as abuseipdb.
4. `tests/test_hashlookup.py` — remove TestSupportedTypes, TestProtocolConformance, TestAllowedHostsIntegration, contract methods from TestLookupErrors, TestHTTPSafetyControls.
5. `tests/test_ip_api.py` — remove TestSupportedTypes, TestProtocolConformance, TestAllowedHostsIntegration, contract methods from TestLookupErrors, TestHTTPSafetyControls.
6. `tests/test_otx.py` — remove contract methods from TestOTXProtocol, TestOTXErrors, TestAllowedHosts.
7. `tests/test_malwarebazaar.py` — remove contract methods (unsupported type, timeout, ssrf, http_500, response_size_limit).
8. `tests/test_threatfox.py` — remove contract methods (unsupported type, timeout, ssrf, response_size_limit).
9. `tests/test_urlhaus.py` — remove contract methods from TestURLhausErrors, TestHTTPSafetyControls, TestSupportedTypes, TestProtocolConformance, TestAllowedHostsIntegration.
10. `tests/test_crtsh.py` — remove contract methods from error/safety/protocol/supported_types classes.
11. `tests/test_vt_adapter.py` — remove test_lookup_cve_returns_error (unsupported type), test_timeout_returns_error, test_allowed_hosts_enforced, test_response_size_limit, and HTTP safety control tests that overlap with contract.
12. `tests/test_threatminer.py` — remove contract methods (unsupported type, timeout, ssrf, response_size, protocol, supported_types, is_configured). Keep all verdict/multi-call/rate-limit tests.

After each file: remove now-unused imports (Provider, MAX_RESPONSE_BYTES, requests.exceptions if no longer used). Delete empty test classes.

Run `python3 -m pytest tests/ -x -q --ignore=tests/e2e` after all edits. Total test count should be lower than 983 baseline but 0 failures.
  - Estimate: 1h
  - Files: tests/test_shodan.py, tests/test_abuseipdb.py, tests/test_greynoise.py, tests/test_hashlookup.py, tests/test_ip_api.py, tests/test_otx.py, tests/test_malwarebazaar.py, tests/test_threatfox.py, tests/test_urlhaus.py, tests/test_crtsh.py, tests/test_vt_adapter.py, tests/test_threatminer.py
  - Verify: python3 -m pytest tests/ -x -q --ignore=tests/e2e
- [x] **T03: Removed 33 duplicated contract tests from 3 non-HTTP adapter test files; suite passes at 947 tests with 172 parametrized contract tests green** — Remove contract test functions from the 3 non-HTTP adapter test files. These adapters (DnsAdapter, CymruASNAdapter, WhoisAdapter) have a simpler contract surface — no timeout/SSRF/HTTP error tests to remove, only:
- Protocol conformance (isinstance Provider)
- Adapter name
- requires_api_key
- is_configured
- supported_types contains/excludes/is_frozenset
- Unsupported type rejection (e.g., test_ipv4_returns_enrichment_error in dns_lookup)

Files to edit:
1. `tests/test_dns_lookup.py` — remove: test_name_is_dns_records, test_supported_types_is_frozenset, test_supported_types_contains_domain, test_supported_types_excludes_ipv4, test_supported_types_excludes_ipv6, test_supported_types_excludes_url, test_requires_api_key_false, test_is_configured_returns_true, test_is_configured_returns_true_with_empty_hosts, test_dns_adapter_satisfies_provider_protocol, test_ipv4_returns_enrichment_error. Keep all DNS resolution tests, lookup_errors, partial failure, NXDOMAIN, etc.
2. `tests/test_asn_cymru.py` — remove: test_name_is_asn_intel, test_supported_types_is_frozenset, test_supported_types_contains_ipv4, test_supported_types_contains_ipv6, test_supported_types_is_ipv4_and_ipv6_only, test_requires_api_key_false, test_is_configured_returns_true, test_is_configured_returns_true_with_empty_hosts, test_is_configured_returns_true_with_populated_hosts, test_cymru_adapter_satisfies_provider_protocol, test_domain_ioc_returns_enrichment_error, test_domain_ioc_error_provider_name. Keep all ASN resolution tests, timeout tests (DNS-level, not HTTP), invalid IP, etc.
3. `tests/test_whois_lookup.py` — remove: test_name_is_whois, test_supported_types_is_frozenset, test_supported_types_contains_domain, test_supported_types_excludes_ipv4, test_supported_types_excludes_url, test_requires_api_key_false, test_is_configured_returns_true, test_is_configured_returns_true_with_empty_hosts, test_whois_adapter_satisfies_provider_protocol, test_ipv4_returns_enrichment_error (and variants). Keep all WHOIS parsing tests, quota/error tests, datetime normalization, etc.

After all 3 files are cleaned up:
- Remove now-unused imports (Provider if no longer referenced).
- Delete empty test classes if all methods were removed.
- Run full test suite: `python3 -m pytest tests/ -x -q --ignore=tests/e2e`
- Verify 0 failures and total count is lower than 983.
- Run `python3 -m pytest tests/test_adapter_contract.py -v --tb=short` to confirm parametrized coverage.
- Count lines: `wc -l tests/test_adapter_contract.py` + total across all 15 adapter files to quantify reduction.
  - Estimate: 30m
  - Files: tests/test_dns_lookup.py, tests/test_asn_cymru.py, tests/test_whois_lookup.py
  - Verify: python3 -m pytest tests/ -x -q --ignore=tests/e2e && python3 -m pytest tests/test_adapter_contract.py -v --tb=short
