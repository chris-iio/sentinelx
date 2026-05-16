---
estimated_steps: 1
estimated_files: 2
skills_used: []
---

# T01: Lock final audit closeout contract

Why: S05 must make the M020 outcome durable before running final verification, and the generated audit source is the canonical documentation surface rather than hand-edited prose. Expected executor skills: verify-before-complete, write-docs, test. Do: inspect the current generated M020 audit source and tests; add or tighten tests in `tests/test_optimization_audit.py` so they require S02 shipped route helper centralization, S03 shipped diagnostics policy centralization, S04 virtualization deferment, and S05 final closeout language including final `make verify`, failure-visibility/redaction guardrails, and what remains deferred; then update `tools/optimization_audit.py` only as needed to satisfy those generated-content tests. Failure Modes (Q5): if the generator omits a slice outcome, downstream closeout becomes stale; fail the audit test instead of hand-editing `.gsd` output. Load Profile (Q6): trivial generator/test workload; no shared runtime resources. Negative Tests (Q7): assert absence of misleading final-shipped language for the deferred virtualization rewrite and presence of redaction/failure-state guardrails. Done when the focused audit test lane passes and no `.gsd/` artifact has been manually edited in this task.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Expected Output

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Strengthens generated audit observability by requiring final proof-lane, failure-state, and redaction language to remain test-protected.
