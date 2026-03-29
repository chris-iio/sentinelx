---
estimated_steps: 18
estimated_files: 3
skills_used: []
---

# T03: Remove duplicated contract tests from 3 non-HTTP adapter test files and verify final state

Remove contract test functions from the 3 non-HTTP adapter test files. These adapters (DnsAdapter, CymruASNAdapter, WhoisAdapter) have a simpler contract surface — no timeout/SSRF/HTTP error tests to remove, only:
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

## Inputs

- ``tests/test_adapter_contract.py` — the shared contract module from T01`
- ``tests/test_dns_lookup.py` — non-HTTP adapter test file`
- ``tests/test_asn_cymru.py` — non-HTTP adapter test file`
- ``tests/test_whois_lookup.py` — non-HTTP adapter test file`

## Expected Output

- ``tests/test_dns_lookup.py` — DNS-specific tests only`
- ``tests/test_asn_cymru.py` — ASN-specific tests only`
- ``tests/test_whois_lookup.py` — WHOIS-specific tests only`

## Verification

python3 -m pytest tests/ -x -q --ignore=tests/e2e && python3 -m pytest tests/test_adapter_contract.py -v --tb=short
