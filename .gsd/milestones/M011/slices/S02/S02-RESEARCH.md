# S02 Research: Per-Adapter Test Consolidation

## Summary

Straightforward deduplication work. D049 (human decision) is clear: remove per-adapter tests that re-assert fields already covered by the parametrized contract suite (`test_adapter_contract.py`, 13 tests × 15 adapters). Per-adapter files keep only verdict-logic and response-parsing tests. ~54 tests removed, ~540 lines cut, 9 files modified, 1 file deleted.

## Requirement Coverage

- **R057** (Per-adapter test consolidation) — this slice's primary requirement
- **R060** (All tests pass, zero behavior changes) — verification gate

## Recommendation

Three tasks, ordered by risk:

1. **Delete `test_provider_protocol.py`; relocate 2 negative tests** — highest confidence, zero risk of coverage loss. All 15 positive tests (isinstance, name, requires_api_key, is_configured) are parametrically covered by `test_adapter_contract.py`. The 2 negative tests (`test_non_conforming_class_fails_isinstance`, `test_non_conforming_class_missing_lookup_fails`) test the Protocol itself and should move to `test_adapter_contract.py`.

2. **Consolidate per-field tests across 7 adapter test files** — bulk of the work. Pattern: delete 3-11 single-assertion tests per file, fold their assertions into an existing test that already uses the same fixture + setup. Every assertion is preserved — only the redundant test scaffolding (function def, docstring, fixture setup, isinstance guard) is removed.

3. **Final verification pass** — run full test suite, confirm count dropped by ~54, confirm zero failures.

## Implementation Landscape

### Files to Modify (8 files + 1 deletion)

| File | Tests to Remove | Lines Cut | Folding Target |
|------|----------------|-----------|----------------|
| `tests/test_provider_protocol.py` | 15 (delete file) | ~132 | 2 negative tests → `test_adapter_contract.py` |
| `tests/test_ip_api.py` | 11 | ~110 | Fold into `test_geo_format_cc_city_asn_isp`, `test_raw_stats_contains_required_fields`, new `test_public_ip_response_shape` |
| `tests/test_asn_cymru.py` | 9 | ~100 | Fold `has_*_key` assertions into existing `test_raw_stats_asn_value` etc.; fold detection/scan_date into `test_returns_enrichment_result` |
| `tests/test_crtsh.py` | 4 | ~44 | Fold into `test_verdict_is_no_data` + `test_empty_array_returns_no_data` |
| `tests/test_dns_lookup.py` | 3 | ~33 | Fold into existing response test |
| `tests/test_threatminer.py` | 3 | ~33 | Fold into existing IP lookup test |
| `tests/test_abuseipdb.py` | 3 | ~33 | Fold into `test_high_score_returns_malicious` |
| `tests/test_greynoise.py` | 3 | ~33 | Fold into verdict tests |
| `tests/test_whois_lookup.py` | 3 | ~22 | Fold into existing domain lookup test |
| **Total** | **54** | **~540** | |

### What Stays (per D049)

Per-adapter files keep:
- **Verdict logic** — tests with different fixtures proving verdict thresholds (e.g., pulse_count=5 → malicious, pulse_count=4 → suspicious)
- **Response parsing** — tests proving specific field mapping from provider API shape to EnrichmentResult (e.g., ipinfo.io `org` → `as_info`)
- **Edge cases** — 404 handling, empty arrays, malformed responses, multi-call fallback (ThreatMiner)
- **Auth header format** — per-adapter header case/key name tests
- **URL construction** — endpoint path tests

### What Gets Removed

1. **detection_count / total_engines / scan_date triplets** — 7 files have 3 tests each asserting these are 0/0/None for informational adapters. These are pure protocol conformance already covered by the contract suite's response-shape tests. For adapters where these are parsed from the response (AbuseIPDB, GreyNoise), fold the assertion into the verdict test that already uses the same fixture.

2. **raw_stats key-existence tests** — `test_raw_stats_has_asn_key`, `test_raw_stats_has_prefix_key`, etc. These are subsumed by the value-assertion tests that follow (asserting `result.raw_stats["asn"] == "23028"` implicitly asserts the key exists).

3. **Protocol conformance tests** — `test_provider_protocol.py` is entirely subsumed by `test_adapter_contract.py` which covers all 15 adapters parametrically.

### Consolidation Pattern

Before (3 tests, ~33 lines):
```python
def test_detection_count_always_zero(self):
    # 11 lines: setup + 1 assert

def test_total_engines_always_zero(self):
    # 11 lines: same setup + 1 assert

def test_scan_date_always_none(self):
    # 11 lines: same setup + 1 assert
```

After (0 tests removed, assertions folded into existing test, ~0 new lines):
```python
def test_returns_enrichment_result(self):
    # existing test, add 3 lines:
    assert result.detection_count == 0
    assert result.total_engines == 0
    assert result.scan_date is None
```

### Baseline Metrics

- **Current test count:** 1,061 tests (948 unit, 113 E2E)
- **Current unit test time:** ~9.6s
- **Expected test count after:** ~1,009 (1,061 - 54 + 2 relocated)
- **Expected unit test time:** ~9.5s (marginal — S03 handles the real speedup)

### Constraints

- Every assertion removed from a standalone test MUST appear in the folding-target test. Coverage must not decrease.
- Use descriptive assert messages (`assert result.detection_count == 0, "informational adapter — detection_count must be 0"`) since multi-assert test failure messages need context.
- The 2 negative Protocol tests (`test_non_conforming_class_*`) test the Protocol runtime check, not any adapter — they belong in the contract test file near the protocol conformance section.
- `test_adapter_contract.py` itself is not modified beyond receiving the 2 relocated negative tests.

### Verification

```bash
# Full unit test suite passes
python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short

# Test count decreased by ~52 (54 removed, 2 relocated)
python3 -m pytest --co -q 2>&1 | tail -1  # expect ~1009

# No stale imports from deleted file
python3 -c "import tests.test_provider_protocol" 2>&1  # should fail (file deleted)

# All assertion coverage preserved (spot-check)
python3 -m pytest tests/test_ip_api.py -v --tb=short
python3 -m pytest tests/test_asn_cymru.py -v --tb=short
```
