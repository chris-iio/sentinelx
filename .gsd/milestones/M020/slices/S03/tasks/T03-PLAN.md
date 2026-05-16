---
estimated_steps: 7
estimated_files: 3
skills_used: []
---

# T03: Refresh S03 audit outcome and fast proof

skills_used: [write-docs, verify-before-complete]
Why: M020 uses the generated audit as the durable documentation surface for shipped/rejected rewrite outcomes, so S03 must update the runner and regenerated artifact rather than leaving evidence only in tests.
Do: Update `tools/optimization_audit.py` and `tests/test_optimization_audit.py` so the generated M020 audit records the S03 diagnostics policy extraction as shipped, or records an explicit rejection if T02 finds evidence against the refactor. The audit row must name the diagnostic modules, focused pytest lane, failure-visibility guarantees, redaction guardrails, and the reason for any leave-alone/rejection decision. Run `make audit-m020` to regenerate `.gsd/milestones/M020/M020-AUDIT.md`. Then run focused audit tests and `make verify-fast`.
Done when: The generated audit artifact includes the S03 outcome with synchronized rerun lanes and guardrails, focused optimization-audit tests pass, and `make verify-fast` passes.
Failure Modes (Q5): Audit capture-command failures must remain visible as failed rows rather than hidden; stale audit prose must be caught by tests.
Load Profile (Q6): No runtime load impact; generated audit work remains a local developer command.
Negative Tests (Q7): Audit tests should fail if S03 outcome language, proof command, failure visibility, or redaction guardrails disappear.

## Inputs

- `app/diagnostics/policy.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/diagnostics/sources.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `Makefile`

## Expected Output

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

make verify-fast

## Observability Impact

Updates the generated audit as the durable inspection surface for S03, including focused proof commands, failure-state visibility, and redaction constraints.
