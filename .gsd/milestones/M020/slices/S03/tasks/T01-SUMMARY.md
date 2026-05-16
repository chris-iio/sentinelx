---
id: T01
parent: S03
milestone: M020
key_files:
  - tests/test_diagnostic_export_assembler.py
  - tests/test_diagnostic_redaction.py
  - tests/test_diagnostic_export_sources.py
key_decisions:
  - Kept this task test-only because the existing production diagnostics modules already centralize the relevant caps through DIAGNOSTIC_SANITIZATION_POLICY.
duration: 
verification_result: passed
completed_at: 2026-05-16T08:48:52.166Z
blocker_discovered: false
---

# T01: Added focused diagnostics policy-boundary regression tests across archive assembly, redaction metadata, and runtime source sanitization.

**Added focused diagnostics policy-boundary regression tests across archive assembly, redaction metadata, and runtime source sanitization.**

## What Happened

Inspected the diagnostics policy, assembler, redaction, sources, and existing focused pytest coverage. The existing suite already covered forbidden archive paths, source error records, redaction behavior, and source sanitization caps, so I tightened remaining cross-seam regression boundaries with additional tests: default archive source max bytes tied to the shared policy, generated filename length tied to policy, config read failure metadata remaining secret-free and label-bounded, runtime source descriptors using the shared runtime cap, and nested runtime payloads stopping at the shared max-depth sentinel. During verification, two initial test expectations were corrected: default runtime source sanitization can shrink oversized job payloads before archive truncation, so the truncation boundary is asserted through an explicit runtime DiagnosticSource using the descriptor cap; depth limiting can produce multiple '<max-depth>' sentinel values for sibling fields at the cutoff, so the test now asserts sentinel presence and that deeper values are not exposed.

## Verification

Ran the focused diagnostics pytest lane before edits and after edits. Pre-edit baseline passed with 69 tests. Post-edit verification passed with 74 tests: python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py` | 0 | ✅ pass (baseline before edits, 69 passed) | 483ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py` | 1 | ❌ fail (intermediate test expectation mismatch, 72 passed/2 failed) | 631ms |
| 3 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py` | 0 | ✅ pass (final, 74 passed) | 509ms |

## Deviations

No production code changes were needed; the task was satisfied by tightening tests because the intended shared policy behavior was already implemented.

## Known Issues

None.

## Files Created/Modified

- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
