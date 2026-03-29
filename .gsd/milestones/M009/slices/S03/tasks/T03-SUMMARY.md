---
id: T03
parent: S03
milestone: M009
provides: []
requires: []
affects: []
key_files: ["tests/test_dns_lookup.py", "tests/test_asn_cymru.py", "tests/test_whois_lookup.py"]
key_decisions: ["Kept DNS-specific does_not_call_dns/whois tests in per-adapter files since they verify adapter-specific behavior not covered by the generic contract"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "python3 -m pytest tests/ -x -q --ignore=tests/e2e → 947 passed, 0 failures. python3 -m pytest tests/test_adapter_contract.py -v --tb=short → 172 passed."
completed_at: 2026-03-29T20:00:00.102Z
blocker_discovered: false
---

# T03: Removed 33 duplicated contract tests from 3 non-HTTP adapter test files; suite passes at 947 tests with 172 parametrized contract tests green

> Removed 33 duplicated contract tests from 3 non-HTTP adapter test files; suite passes at 947 tests with 172 parametrized contract tests green

## What Happened
---
id: T03
parent: S03
milestone: M009
key_files:
  - tests/test_dns_lookup.py
  - tests/test_asn_cymru.py
  - tests/test_whois_lookup.py
key_decisions:
  - Kept DNS-specific does_not_call_dns/whois tests in per-adapter files since they verify adapter-specific behavior not covered by the generic contract
duration: ""
verification_result: passed
completed_at: 2026-03-29T20:00:00.104Z
blocker_discovered: false
---

# T03: Removed 33 duplicated contract tests from 3 non-HTTP adapter test files; suite passes at 947 tests with 172 parametrized contract tests green

**Removed 33 duplicated contract tests from 3 non-HTTP adapter test files; suite passes at 947 tests with 172 parametrized contract tests green**

## What Happened

Removed TestClassMetadata, TestProtocolConformance, and generic unsupported-type contract tests from test_dns_lookup.py (11 tests), test_asn_cymru.py (12 tests), and test_whois_lookup.py (10 tests). Kept DNS/WHOIS-specific behavior tests (does_not_call_dns/whois). Removed unused Provider imports from all 3 files. Fixed class-merging issue in asn_cymru test during edit.

## Verification

python3 -m pytest tests/ -x -q --ignore=tests/e2e → 947 passed, 0 failures. python3 -m pytest tests/test_adapter_contract.py -v --tb=short → 172 passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/ -x -q --ignore=tests/e2e` | 0 | ✅ pass | 9260ms |
| 2 | `python3 -m pytest tests/test_adapter_contract.py -v --tb=short` | 0 | ✅ pass | 4100ms |


## Deviations

Fixed class-merging issue in test_asn_cymru.py where edit accidentally merged TestUnsupportedType and TestQueryConstruction classes.

## Known Issues

None.

## Files Created/Modified

- `tests/test_dns_lookup.py`
- `tests/test_asn_cymru.py`
- `tests/test_whois_lookup.py`


## Deviations
Fixed class-merging issue in test_asn_cymru.py where edit accidentally merged TestUnsupportedType and TestQueryConstruction classes.

## Known Issues
None.
