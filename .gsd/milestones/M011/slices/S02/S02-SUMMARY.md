---
id: S02
parent: M011
milestone: M011
provides:
  - 49 fewer tests to maintain across adapter test suite
  - Descriptive assert messages on all folded assertions for clear failure diagnosis
requires:
  []
affects:
  []
key_files:
  - tests/test_adapter_contract.py
  - tests/test_ip_api.py
  - tests/test_asn_cymru.py
  - tests/test_crtsh.py
  - tests/test_dns_lookup.py
  - tests/test_threatminer.py
  - tests/test_abuseipdb.py
  - tests/test_greynoise.py
  - tests/test_whois_lookup.py
key_decisions:
  - Placed relocated negative Protocol tests in TestProtocolNegative class after TestProtocolConformance for logical grouping
  - Folded all per-field assertions into existing response-shape tests with descriptive messages rather than creating new combined tests
  - Kept error-path provider_name tests (exception/quota scenarios) since they test distinct code paths
patterns_established:
  - Test consolidation pattern: fold single-field assertions into existing response-shape tests with descriptive assert messages rather than creating new aggregate tests
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M011/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T12:08:14.356Z
blocker_discovered: false
---

# S02: Per-Adapter Test Consolidation

**Removed 49 redundant per-field tests (17 from test_provider_protocol.py, 34 from 8 adapter test files), relocated 2 unique negative Protocol tests, and folded all assertions into existing response-shape tests — net -431 lines, 899 unit tests passing.**

## What Happened

Two tasks executed the D049 dedup strategy against adapter test files.

T01 deleted `tests/test_provider_protocol.py` entirely (17 tests). 15 of those were positive protocol/attribute tests already parametrically covered by `test_adapter_contract.py` across all 15 adapters. The 2 unique negative tests (verifying Protocol rejection of non-conforming classes) were relocated into a new `TestProtocolNegative` class in `test_adapter_contract.py`. Net: -15 tests.

T02 consolidated 34 standalone per-field tests across 8 adapter test files. Each deleted test had duplicated the same fixture setup just to assert a single field (detection_count, total_engines, scan_date, provider_name). Those assertions were folded into existing response-shape tests that already used the same fixture, with descriptive assert messages. Breakdown: test_ip_api (-3), test_asn_cymru (-10), test_crtsh (-4), test_dns_lookup (-4), test_threatminer (-3), test_abuseipdb (-3), test_greynoise (-3), test_whois_lookup (-4). Net: -34 tests.

Total: 49 tests removed, 431 lines deleted, zero assertion coverage lost. Full suite green at 899.

## Verification

Independent closer verification:
1. `test -f tests/test_provider_protocol.py` → DELETED (confirmed absent)
2. `grep -n TestProtocolNegative tests/test_adapter_contract.py` → class exists at L364 with 2 negative tests
3. `python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short` → 899 passed, 0 failures
4. `python3 -m pytest tests/ --ignore=tests/e2e --co -q` → 899 tests collected
5. All 8 individual adapter test files pass: ip_api(29), asn_cymru(34), crtsh(22), dns_lookup(37), threatminer(41), abuseipdb(13), greynoise(9), whois_lookup(42)
6. `grep 'def test_.*detection_count\|def test_.*total_engines\|def test_.*scan_date\|def test_.*provider_name' tests/test_{ip_api,crtsh,dns_lookup,threatminer,greynoise}.py` → 0 matches (standalone per-field tests eliminated from informational adapters)
7. `git diff --stat HEAD~2 -- tests/` → 10 files changed, 93 insertions, 524 deletions (net -431 lines)

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Plan estimated ~37 tests removed in T02; actual was 34 (asn_cymru had 10 removals including 4 has_key and nxdomain tests, slightly different grouping than planned). Plan estimated 400-600 lines removed; actual was 431 — within range.

## Known Limitations

Error-path provider_name tests (e.g. test_generic_exception_provider_name_correct in asn_cymru, test_quota_exceeded_provider_name in whois_lookup) were intentionally kept — they test distinct error-handling code paths, not redundant field assertions on success responses.

## Follow-ups

None.

## Files Created/Modified

- `tests/test_adapter_contract.py` — Added TestProtocolNegative class with 2 relocated negative Protocol tests (+39 lines)
- `tests/test_provider_protocol.py` — Deleted entirely — 17 tests, 132 lines removed
- `tests/test_ip_api.py` — Removed 3 standalone tests, folded assertions into test_public_ip_returns_enrichment_result (-43 lines net)
- `tests/test_asn_cymru.py` — Removed 10 standalone tests, folded assertions into response-shape tests (-120 lines net)
- `tests/test_crtsh.py` — Removed 4 standalone tests, folded assertions into existing tests (-52 lines net)
- `tests/test_dns_lookup.py` — Removed 4 standalone tests, folded assertions into test_successful_lookup_returns_enrichment_result (-50 lines net)
- `tests/test_threatminer.py` — Removed 3 standalone tests, folded assertions into IP lookup success test (-38 lines net)
- `tests/test_abuseipdb.py` — Removed 3 standalone tests, folded assertions into test_high_score_returns_malicious (-52 lines net)
- `tests/test_greynoise.py` — Removed 3 standalone tests, folded assertions into malicious/clean verdict tests (-49 lines net)
- `tests/test_whois_lookup.py` — Removed 4 standalone tests, folded assertions into test_successful_domain_lookup_returns_result (-42 lines net)
