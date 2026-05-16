---
estimated_steps: 3
estimated_files: 1
skills_used: []
---

# T01: Lock remediation coverage in generated audit tests

Why: Milestone validation failed because final evidence did not explicitly cover deferred storage redesign R101, major UI/product redesign R102, new external provider integrations R103, and the S02-S04 analyst-visible contract handoff. This task turns those gaps into executable audit-generation expectations before changing generated prose. Skills used: tdd, verify-before-complete.

Do: Update `tests/test_optimization_audit.py` to assert that generated M020 audit content includes explicit R101/R102/R103 deferred-scope closeout language, distinguishes constraints from shipped optimizations, names the S02 route/API/history contract, S03 diagnostics/redaction contract, S04 browser-visible deferment, and states that no new storage redesign, broad UI/product redesign, or external provider integration was shipped. Keep tests pointed at generator output, not `.gsd/` artifacts, so the test suite does not depend on gitignored planning files.

Done when: The focused audit test suite fails before generator updates for the new assertions and passes after T02, with assertions broad enough to lock coverage but not brittle exact prose.

## Inputs

- `tests/test_optimization_audit.py`
- `tools/optimization_audit.py`
- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M020/slices/S05/S05-SUMMARY.md`

## Expected Output

- `tests/test_optimization_audit.py`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Improves failure visibility for future agents by making missing generated-audit coverage surface as focused pytest failures rather than milestone-validation prose gaps.
