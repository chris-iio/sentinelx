---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T02: Regenerate audit remediation language from source

Why: M020 audit artifacts are generated, so deferred-scope remediation must be encoded in `tools/optimization_audit.py` and regenerated rather than hand-edited in `.gsd/milestones/M020/M020-AUDIT.md`. Skills used: write-docs, verify-before-complete.

Do: Update `tools/optimization_audit.py` so `make audit-m020` emits final remediation language for R101-R103 and the S02-S04 analyst-visible handoff. The language should cite evidence classes already proven by S02-S05, keep S04 virtualization explicitly deferred, and avoid claiming a storage rewrite, product redesign, provider expansion, live-provider validation, or behavior outside local verification lanes. Run `python3 -m pytest -q tests/test_optimization_audit.py` and `make audit-m020` to regenerate `.gsd/milestones/M020/M020-AUDIT.md` from source.

Done when: The generator tests pass and the regenerated audit artifact contains the same evidence-backed deferred-scope coverage required by T01.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M020/M020-AUDIT.md`
- `.gsd/milestones/M020/slices/S05/S05-SUMMARY.md`

## Expected Output

- `tools/optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

No runtime signals change; generated audit text becomes the inspection surface for deferred-scope validation decisions.
