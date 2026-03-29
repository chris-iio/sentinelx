---
estimated_steps: 28
estimated_files: 12
skills_used: []
---

# T02: Remove duplicated contract tests from 12 HTTP adapter test files

Remove contract test functions from each HTTP adapter test file that are now covered by `tests/test_adapter_contract.py`. The contract tests to remove are those testing:
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

## Inputs

- ``tests/test_adapter_contract.py` — the shared contract module from T01 (defines what's now covered centrally)`
- ``tests/test_shodan.py` — HTTP adapter test file`
- ``tests/test_abuseipdb.py` — HTTP adapter test file`
- ``tests/test_greynoise.py` — HTTP adapter test file`
- ``tests/test_hashlookup.py` — HTTP adapter test file`
- ``tests/test_ip_api.py` — HTTP adapter test file`
- ``tests/test_otx.py` — HTTP adapter test file`
- ``tests/test_malwarebazaar.py` — HTTP adapter test file`
- ``tests/test_threatfox.py` — HTTP adapter test file`
- ``tests/test_urlhaus.py` — HTTP adapter test file`
- ``tests/test_crtsh.py` — HTTP adapter test file`
- ``tests/test_vt_adapter.py` — HTTP adapter test file`
- ``tests/test_threatminer.py` — HTTP adapter test file`

## Expected Output

- ``tests/test_shodan.py` — verdict-only tests`
- ``tests/test_abuseipdb.py` — verdict-only tests`
- ``tests/test_greynoise.py` — verdict-only tests`
- ``tests/test_hashlookup.py` — verdict-only tests`
- ``tests/test_ip_api.py` — verdict-only tests`
- ``tests/test_otx.py` — verdict-only tests`
- ``tests/test_malwarebazaar.py` — verdict-only tests`
- ``tests/test_threatfox.py` — verdict-only tests`
- ``tests/test_urlhaus.py` — verdict-only tests`
- ``tests/test_crtsh.py` — verdict-only tests`
- ``tests/test_vt_adapter.py` — verdict-only tests`
- ``tests/test_threatminer.py` — verdict-only tests`

## Verification

python3 -m pytest tests/ -x -q --ignore=tests/e2e
