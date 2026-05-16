---
id: T01
parent: S06
milestone: M020
key_files:
  - tests/test_optimization_audit.py
key_decisions:
  - Kept remediation coverage locked in generator-output tests using pytest temporary output paths, avoiding dependency on `.gsd/` planning artifacts.
duration: 
verification_result: passed
completed_at: 2026-05-16T09:17:24.208Z
blocker_discovered: false
---

# T01: Added generator-output audit assertions that lock M020 remediation coverage for deferred R101/R102/R103 scope and the S02-S04 analyst-visible handoff contracts.

**Added generator-output audit assertions that lock M020 remediation coverage for deferred R101/R102/R103 scope and the S02-S04 analyst-visible handoff contracts.**

## What Happened

Updated `tests/test_optimization_audit.py` in the existing M020 baseline audit test. The new assertions require generated audit output to mention R101, R102, and R103, identify them as deferred-scope constraints rather than shipped optimizations, explicitly state that no new storage redesign, broad UI/product redesign, or external provider integration shipped, and name the S02 route/API/history, S03 diagnostics/redaction, and S04 browser-visible deferment handoff contracts. The assertions remain pointed at `tools/optimization_audit.py` output written to a pytest temporary path, not at `.gsd/` artifacts.

## Verification

Ran `python3 -m pytest -q tests/test_optimization_audit.py`. The focused suite entered the intended red state for this TDD task: 28 tests passed and `test_m020_baseline_uses_aggressive_rewrite_contract` failed on the first new missing generated-audit expectation, proving the added expectations currently require a generator update in T02.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_optimization_audit.py` | 1 | ✅ expected fail (red state for T01); 28 passed, 1 failed on new M020 generated-audit assertion | 3109ms |

## Deviations

None.

## Known Issues

The focused audit suite is intentionally failing until T02 updates `tools/optimization_audit.py` generated prose to satisfy the new assertions.

## Files Created/Modified

- `tests/test_optimization_audit.py`
