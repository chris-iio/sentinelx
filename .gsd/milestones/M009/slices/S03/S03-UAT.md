# S03: Adapter test consolidation — UAT

**Milestone:** M009
**Written:** 2026-03-29T20:02:44.816Z

## UAT: S03 — Adapter test consolidation

### Preconditions
- Python 3.10+ with pytest available
- All project dependencies installed (`pip install -e ".[dev]"`)
- Working directory: project root

### Test 1: Contract module covers all 15 adapters
**Steps:**
1. Run: `python3 -m pytest tests/test_adapter_contract.py -v --tb=short`
2. Count unique adapter names in output: `python3 -m pytest tests/test_adapter_contract.py -v 2>&1 | grep -oP '\[.*?\]' | sort -u | wc -l`

**Expected:**
- 172 tests pass, 0 failures
- 15 unique adapter parameter IDs appear (shodan-internetdb, abuseipdb, greynoise, circl-hashlookup, ip-context, otx-alienvault, malwarebazaar, threatfox, urlhaus, cert-history, virustotal, threatminer, dns-records, asn-intel, whois)

### Test 2: Full suite passes with no regressions
**Steps:**
1. Run: `python3 -m pytest tests/ -x -q --ignore=tests/e2e`

**Expected:**
- 947 tests pass, 0 failures
- No skips, no errors

### Test 3: Per-adapter files contain no contract tests
**Steps:**
1. Run: `grep -l 'isinstance.*Provider' tests/test_shodan.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py tests/test_vt_adapter.py tests/test_threatminer.py tests/test_dns_lookup.py tests/test_asn_cymru.py tests/test_whois_lookup.py 2>/dev/null`
2. Run: `grep -l 'test_name_is_\|test_requires_api_key\|test_supported_types_is_frozenset\|TestProtocolConformance\|TestAllowedHostsIntegration' tests/test_shodan.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py tests/test_vt_adapter.py tests/test_threatminer.py tests/test_dns_lookup.py tests/test_asn_cymru.py tests/test_whois_lookup.py 2>/dev/null`

**Expected:**
- Both commands produce empty output (no matches)

### Test 4: Adding a new adapter requires only one registry entry
**Steps:**
1. Open `tests/test_adapter_contract.py`
2. Find `ADAPTER_REGISTRY` list
3. Verify each entry is an `AdapterEntry` dataclass with fields: adapter_class, constructor_kwargs, name, requires_api_key, supported_types, excluded_types, http_method, is_http, allowed_hosts_config_entry, sample_ioc_factory

**Expected:**
- 15 entries in ADAPTER_REGISTRY
- Each entry is self-contained — no additional test methods needed per adapter

### Test 5: Contract tests cover all expected dimensions
**Steps:**
1. Run: `python3 -m pytest tests/test_adapter_contract.py --collect-only -q 2>&1 | grep '::' | sed 's/::test.*//' | sort -u`

**Expected:**
- 12 test classes: TestProtocolConformance, TestAdapterName, TestRequiresApiKey, TestIsConfigured, TestSupportedTypesContains, TestSupportedTypesExcludes, TestUnsupportedTypeRejection, TestTimeoutHandling, TestHTTP500Error, TestSSRFValidation, TestResponseSizeLimit, TestAllowedHostsConfig

### Edge Case 1: Non-HTTP adapters excluded from HTTP-only tests
**Steps:**
1. Run: `python3 -m pytest tests/test_adapter_contract.py -v -k "Timeout" 2>&1 | grep -c "PASSED"`
2. Run: `python3 -m pytest tests/test_adapter_contract.py -v -k "SSRF" 2>&1 | grep -c "PASSED"`

**Expected:**
- Timeout: 12 passed (HTTP adapters only, not dns-records/asn-intel/whois)
- SSRF: 12 passed (HTTP adapters only)

### Edge Case 2: is_configured negative tests only for key-required adapters
**Steps:**
1. Run: `python3 -m pytest tests/test_adapter_contract.py -v -k "not_configured" 2>&1 | grep -c "PASSED"`

**Expected:**
- 7 passed (only adapters with requires_api_key=True: abuseipdb, greynoise, otx, malwarebazaar, threatfox, urlhaus, virustotal)
