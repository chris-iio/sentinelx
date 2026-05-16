---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T03: Close requirements and rerun final verification ladder

Why: The remediation is only complete if requirements and final proof are aligned with the regenerated audit and strict verification ladder. This task records validation-backed closeout for R101-R103 and reruns focused plus all-up checks. Skills used: verify-before-complete.

Do: Use DB-backed requirement updates for R101, R102, and R103 to record validation notes that they remain deferred constraints covered by generated audit evidence and final local verification; do not mark them as shipped capabilities. Rerun `make audit-m020`, `python3 -m pytest -q tests/test_optimization_audit.py`, and final `make verify`. If final verification fails, fix only issues directly caused by this remediation or document blockers before completion. Preserve S05's claim boundaries: local verification lanes, no live-provider expansion, no storage/product redesign.

Done when: R101-R103 validation notes are regenerated into `.gsd/REQUIREMENTS.md`, the audit artifact is current, focused audit tests pass, and a fresh final `make verify` exits 0.

## Inputs

- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M020/M020-AUDIT.md`
- `tests/test_optimization_audit.py`
- `Makefile`

## Expected Output

- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

make verify

## Observability Impact

Keeps validation evidence inspectable in the requirements ledger and generated audit closeout; no runtime observability changes.
