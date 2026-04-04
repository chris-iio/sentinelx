---
estimated_steps: 65
estimated_files: 8
skills_used: []
---

# T02: Consolidate per-field tests across 7 adapter test files into response-shape tests

## Description

Across 7 adapter test files, ~37 tests repeat identical fixture setup to assert a single field (detection_count, total_engines, scan_date, raw_stats key existence, provider name). Per D049, these are removed and their assertions folded into existing tests that already use the same fixture.

The consolidation pattern per file:
- Identify tests that duplicate fixture setup for a single assertion
- Find the existing "folding target" test that already does the same setup
- Add the assertion(s) to the folding target with descriptive assert messages
- Delete the standalone test function entirely

**File-by-file consolidation map:**

1. **`tests/test_ip_api.py`** (~3 tests, ~39 lines):
   - Delete: `test_public_ip_provider_name`, `test_public_ip_detection_counts_always_zero`, `test_public_ip_scan_date_is_none`
   - Fold into: `test_public_ip_returns_enrichment_result` — add `assert result.provider == "IP Context"`, `assert result.detection_count == 0`, `assert result.total_engines == 0`, `assert result.scan_date is None`

2. **`tests/test_asn_cymru.py`** (~9 tests, ~100 lines):
   - Delete: `test_successful_lookup_provider_name`, `test_detection_count_always_zero`, `test_total_engines_always_zero`, `test_scan_date_always_none`, `test_raw_stats_has_asn_key`, `test_raw_stats_has_prefix_key`, `test_raw_stats_has_rir_key`, `test_raw_stats_has_allocated_key`, `test_nxdomain_detection_count_zero`
   - Fold provider/detection/scan assertions into `test_successful_lookup_returns_enrichment_result`
   - Fold raw_stats key assertions into `test_raw_stats_asn_value` (key existence is implied by value assertion)
   - Fold nxdomain detection into `test_nxdomain_returns_enrichment_result`
   - Also delete `test_nxdomain_scan_date_none` — fold into `test_nxdomain_returns_enrichment_result`

3. **`tests/test_crtsh.py`** (~4 tests, ~44 lines):
   - Delete: `test_detection_count_always_zero`, `test_total_engines_always_zero`, `test_scan_date_always_none`, `test_empty_array_detection_count_zero`
   - Fold first 3 into the test that returns EnrichmentResult for certificates found
   - Fold `test_empty_array_detection_count_zero` into `test_empty_array_returns_no_data`

4. **`tests/test_dns_lookup.py`** (~4 tests, ~44 lines):
   - Delete: `test_successful_lookup_provider_name`, `test_detection_count_always_zero`, `test_total_engines_always_zero`, `test_scan_date_always_none`
   - Fold into `test_successful_lookup_returns_enrichment_result` (or equivalent test that does the A-record mock)

5. **`tests/test_threatminer.py`** (~3 tests, ~33 lines):
   - Delete: `test_ip_lookup_detection_count_always_zero`, `test_ip_lookup_total_engines_always_zero`, `test_ip_lookup_scan_date_always_none`
   - Fold into the existing IP lookup success test

6. **`tests/test_abuseipdb.py`** (~3 tests, ~33 lines):
   - Delete: `test_detection_count_equals_total_reports`, `test_total_engines_equals_num_distinct_users`, `test_scan_date_is_last_reported_at`
   - Fold into `test_high_score_returns_malicious` — these assert parsed values, not zero-constants

7. **`tests/test_greynoise.py`** (~3 tests, ~33 lines):
   - Delete: `test_detection_count_malicious_is_one`, `test_detection_count_clean_is_zero`, `test_scan_date_is_last_seen`
   - Fold detection_count assertions into existing malicious/clean verdict tests
   - Fold scan_date into the malicious verdict test

8. **`tests/test_whois_lookup.py`** (~3 tests, ~33 lines):
   - Delete: `test_successful_lookup_provider_name`, `test_detection_count_always_zero`, `test_total_engines_always_zero`, `test_scan_date_always_none`
   - Fold into `test_successful_domain_lookup_returns_result` (or equivalent)

Use descriptive assert messages for all folded assertions, e.g.:
`assert result.detection_count == 0, "informational adapter — detection_count must be 0"`

## Steps

1. For each of the 7 files listed above:
   a. Read the file to confirm the test names and folding targets match the map
   b. Add assertions to the folding-target test (with descriptive messages)
   c. Delete the standalone test functions
2. After all 7 files are edited, run the full unit test suite: `python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short`
3. Count tests: `python3 -m pytest --co -q 2>&1 | tail -1` — expect ~1,009 (1,061 baseline - 15 from T01 - ~37 from T02 + 2 relocated in T01)
4. Spot-check individual files to confirm all assertions present:
   - `python3 -m pytest tests/test_ip_api.py -v --tb=short`
   - `python3 -m pytest tests/test_asn_cymru.py -v --tb=short`
   - `python3 -m pytest tests/test_crtsh.py -v --tb=short`
   - `python3 -m pytest tests/test_dns_lookup.py -v --tb=short`
   - `python3 -m pytest tests/test_threatminer.py -v --tb=short`
   - `python3 -m pytest tests/test_abuseipdb.py -v --tb=short`
   - `python3 -m pytest tests/test_greynoise.py -v --tb=short`
   - `python3 -m pytest tests/test_whois_lookup.py -v --tb=short`

## Must-Haves

- [ ] Every assertion from a deleted test appears in its folding-target test
- [ ] All 7 adapter test files edited
- [ ] Full unit test suite passes with 0 failures
- [ ] Test count decreased by ~37 from T01 baseline (total ~52 from original 1,061)
- [ ] No test file has a standalone test that only asserts detection_count, total_engines, or scan_date when the adapter is informational

## Verification

- `python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short` — 0 failures
- `python3 -m pytest --co -q 2>&1 | tail -1` — count ~1,009
- All 7 individual file test runs pass with -v flag

## Inputs

- ``tests/test_ip_api.py` — adapter test file to consolidate`
- ``tests/test_asn_cymru.py` — adapter test file to consolidate`
- ``tests/test_crtsh.py` — adapter test file to consolidate`
- ``tests/test_dns_lookup.py` — adapter test file to consolidate`
- ``tests/test_threatminer.py` — adapter test file to consolidate`
- ``tests/test_abuseipdb.py` — adapter test file to consolidate`
- ``tests/test_greynoise.py` — adapter test file to consolidate`
- ``tests/test_whois_lookup.py` — adapter test file to consolidate`

## Expected Output

- ``tests/test_ip_api.py` — 3 tests removed, assertions folded`
- ``tests/test_asn_cymru.py` — 9-10 tests removed, assertions folded`
- ``tests/test_crtsh.py` — 4 tests removed, assertions folded`
- ``tests/test_dns_lookup.py` — 4 tests removed, assertions folded`
- ``tests/test_threatminer.py` — 3 tests removed, assertions folded`
- ``tests/test_abuseipdb.py` — 3 tests removed, assertions folded`
- ``tests/test_greynoise.py` — 3 tests removed, assertions folded`
- ``tests/test_whois_lookup.py` — 3-4 tests removed, assertions folded`

## Verification

python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short && python3 -m pytest --co -q 2>&1 | tail -1
