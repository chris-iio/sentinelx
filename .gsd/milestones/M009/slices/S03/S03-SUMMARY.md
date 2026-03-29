---
id: S03
parent: M009
milestone: M009
provides:
  - Shared parametrized contract test module covering all 15 adapters
  - Clean per-adapter test files with only verdict/parsing tests
requires:
  []
affects:
  []
key_files:
  - tests/test_adapter_contract.py
  - tests/test_shodan.py
  - tests/test_abuseipdb.py
  - tests/test_greynoise.py
  - tests/test_hashlookup.py
  - tests/test_ip_api.py
  - tests/test_otx.py
  - tests/test_malwarebazaar.py
  - tests/test_threatfox.py
  - tests/test_urlhaus.py
  - tests/test_crtsh.py
  - tests/test_vt_adapter.py
  - tests/test_threatminer.py
  - tests/test_dns_lookup.py
  - tests/test_asn_cymru.py
  - tests/test_whois_lookup.py
key_decisions:
  - Used dataclass AdapterEntry registry pattern for test parametrization — each adapter is a single registry entry, test classes iterate via @pytest.mark.parametrize
  - Kept adapter-specific error tests (429/403/400/502) in per-adapter files — only generic contract behavior was centralized
  - Kept DNS-specific does_not_call_dns/whois tests in per-adapter files — they verify adapter-specific behavior not covered by the generic contract
patterns_established:
  - AdapterEntry dataclass registry pattern for parametrized adapter testing — add one entry to ADAPTER_REGISTRY to get 12 contract test classes for free
  - Contract vs provider-specific test boundary: protocol conformance, type guards, error handling, safety controls → contract module; verdict classification, response parsing, provider-specific HTTP status codes → per-adapter file
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M009/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T20:02:44.816Z
blocker_discovered: false
---

# S03: Adapter test consolidation

**Consolidated 208 duplicated contract tests from 15 adapter test files into a single 172-test parametrized module; suite passes at 947 tests.**

## What Happened

Created `tests/test_adapter_contract.py` with an ADAPTER_REGISTRY — 15 `AdapterEntry` dataclass instances describing each adapter's constructor kwargs, expected name, API key requirement, supported/excluded types, HTTP method, and config entry. 12 parametrized test classes exercise the shared contract: protocol conformance, adapter name, requires_api_key, is_configured (positive and negative), supported types inclusion/exclusion, unsupported type rejection, timeout handling, HTTP 500 errors, SSRF validation (empty allowed_hosts), response size limits, and Config.ALLOWED_API_HOSTS membership.

After the contract module was proven (172 tests, all green), systematically removed duplicated contract tests from all 15 per-adapter files. T02 cleaned 12 HTTP adapter test files (175 tests removed), T03 cleaned 3 non-HTTP adapter files (33 tests removed). Each file was left with only verdict classification, response parsing, and provider-specific edge case tests (e.g., VT's 429 rate limiting, AbuseIPDB's 429 handling, crt.sh 502, ThreatMiner multi-call routing).

Net result: test count went from 1155 (pre-slice, with contract module overlapping) to 947. The 172 contract tests replace 208 removed duplicates — a write-once-test-all pattern that eliminates per-adapter contract maintenance.

## Verification

All slice verification commands pass independently:

1. `python3 -m pytest tests/test_adapter_contract.py -v` — 172 passed in 0.24s
2. `python3 -m pytest tests/ -x -q --ignore=tests/e2e` — 947 passed in 9.05s, 0 failures
3. grep audit of all 15 per-adapter files: 0 contract test patterns remaining
4. Per-adapter test collection confirms only verdict/parsing/provider-specific tests remain (verified on shodan, greynoise, dns_lookup)

## Requirements Advanced

- R044 — 172 parametrized contract tests cover all 15 adapters across 12 contract dimensions
- R045 — All 15 per-adapter files now contain only verdict/parsing/provider-specific tests; 208 duplicates removed

## Requirements Validated

- R044 — python3 -m pytest tests/test_adapter_contract.py -v → 172 passed
- R045 — grep audit shows 0 contract test patterns in any per-adapter file; collection confirms only verdict/parsing tests remain

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

GreyNoise TestGreyNoiseErrors was removed entirely (no adapter-specific error tests remained after contract removal). VT's TestHTTPSafetyControls retained — it contains VT-specific timeout tuple tests not covered by the generic contract. T03 had a class-merging issue in test_asn_cymru.py where an edit accidentally merged two classes; fixed during the task.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `tests/test_adapter_contract.py` — New: 588-line parametrized contract test module with ADAPTER_REGISTRY of 15 entries and 12 test classes (172 tests)
- `tests/test_shodan.py` — Removed contract test classes; 9 verdict/parsing tests remain
- `tests/test_abuseipdb.py` — Removed contract methods; verdict/parsing/rate-limit tests remain
- `tests/test_greynoise.py` — Removed contract classes including TestGreyNoiseErrors; 12 verdict tests remain
- `tests/test_hashlookup.py` — Removed contract classes; verdict/parsing tests remain
- `tests/test_ip_api.py` — Removed contract classes; geo formatting/verdict/404 tests remain
- `tests/test_otx.py` — Removed contract methods; verdict/multi-type routing tests remain
- `tests/test_malwarebazaar.py` — Removed contract methods; verdict/parsing tests remain
- `tests/test_threatfox.py` — Removed contract methods; verdict/parsing tests remain
- `tests/test_urlhaus.py` — Removed contract classes; verdict/parsing tests remain
- `tests/test_crtsh.py` — Removed contract classes; certificate parsing/verdict tests remain
- `tests/test_vt_adapter.py` — Removed generic contract tests; VT-specific timeout tuple and verdict tests remain
- `tests/test_threatminer.py` — Removed contract methods; multi-call routing/rate-limit/verdict tests remain
- `tests/test_dns_lookup.py` — Removed 11 contract tests; DNS resolution/NXDOMAIN/record parsing tests remain
- `tests/test_asn_cymru.py` — Removed 12 contract tests; ASN resolution/query construction tests remain
- `tests/test_whois_lookup.py` — Removed 10 contract tests; WHOIS parsing/datetime normalization tests remain
