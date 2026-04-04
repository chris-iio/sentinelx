# S02: Per-Adapter Test Consolidation — UAT

**Milestone:** M011
**Written:** 2026-04-04T12:08:14.356Z

## UAT: Per-Adapter Test Consolidation

### Preconditions
- Working directory: `/home/chris/projects/sentinelx`
- Python 3.x with pytest available
- All project dependencies installed

### Test Cases

#### TC-01: Deleted file is gone
```bash
python3 -c "import tests.test_provider_protocol" 2>&1 | grep -q ModuleNotFoundError && echo PASS || echo FAIL
```
**Expected:** PASS — file no longer exists.

#### TC-02: Negative Protocol tests relocated and passing
```bash
python3 -m pytest tests/test_adapter_contract.py::TestProtocolNegative -v --tb=short
```
**Expected:** 2 tests pass — `test_non_conforming_class_fails_isinstance` and `test_non_conforming_class_missing_lookup_fails`.

#### TC-03: Full contract test suite green
```bash
python3 -m pytest tests/test_adapter_contract.py -v --tb=short
```
**Expected:** 174 tests pass, 0 failures.

#### TC-04: No standalone per-field tests on informational adapters
```bash
grep -c 'def test_.*detection_count\|def test_.*total_engines\|def test_.*scan_date' tests/test_ip_api.py tests/test_crtsh.py tests/test_dns_lookup.py tests/test_threatminer.py tests/test_greynoise.py
```
**Expected:** All counts are 0. No standalone single-field tests remain for informational adapters.

#### TC-05: Folded assertions present with descriptive messages
```bash
grep -c 'informational adapter' tests/test_ip_api.py tests/test_asn_cymru.py tests/test_crtsh.py tests/test_dns_lookup.py tests/test_threatminer.py tests/test_whois_lookup.py
```
**Expected:** Each file shows ≥1 match — descriptive assert messages confirm assertions were folded, not dropped.

#### TC-06: All 8 adapter test files pass individually
```bash
python3 -m pytest tests/test_ip_api.py tests/test_asn_cymru.py tests/test_crtsh.py tests/test_dns_lookup.py tests/test_threatminer.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_whois_lookup.py -v --tb=short
```
**Expected:** 227 tests pass across 8 files, 0 failures.

#### TC-07: Full unit test suite green at reduced count
```bash
python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short
```
**Expected:** 899 passed, 0 failures.

#### TC-08: Test count reduced from baseline
```bash
python3 -m pytest tests/ --ignore=tests/e2e --co -q 2>&1 | tail -1
```
**Expected:** 899 tests collected (down from 948 pre-M011 baseline; -49 net).

### Edge Cases

#### EC-01: Error-path provider_name tests preserved
```bash
python3 -m pytest tests/test_asn_cymru.py::TestASNCymruAdapter::test_generic_exception_provider_name_correct tests/test_whois_lookup.py::TestWhoisAdapter::test_quota_exceeded_provider_name -v --tb=short
```
**Expected:** Both pass. These are error-path tests, not redundant per-field tests — they must be preserved.

#### EC-02: No import errors from deleted file references
```bash
grep -r 'test_provider_protocol' tests/ 2>/dev/null | grep -v __pycache__
```
**Expected:** No matches — no remaining references to the deleted module.
