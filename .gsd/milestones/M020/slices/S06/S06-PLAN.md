# S06: Validation remediation for deferred scope coverage

**Goal:** Remediate milestone-validation coverage gaps by making generated M020 audit and closeout evidence explicitly account for deferred constraints R101 major storage redesign, R102 major UI/product redesign, R103 new external provider integrations, and the S02-S04 analyst-visible contract handoff, then rerun the audit and final verification ladder.
**Demo:** After this: Generated audit and closeout evidence explicitly cover deferred storage redesign R101, major UI/product redesign R102, external provider integration R103, and the S02 to S04 analyst-visible contract handoff, with audit tests and final verification rerun.

## Must-Haves

- Generated audit source and its tests explicitly cover R101, R102, R103, and the S02-to-S04 analyst-visible contract handoff without hand-editing the audit artifact.
- `.gsd/milestones/M020/M020-AUDIT.md` is regenerated from `tools/optimization_audit.py` and includes the remediation closeout language.
- Requirements R101-R103 are advanced from deferred/unmapped to validation-backed closeout notes only if executable evidence supports the constraint boundaries; no new storage redesign, UI redesign, or provider integration is claimed.
- Focused audit tests and all-up `make verify` pass after regeneration.

## Proof Level

- This slice proves: final-assembly. Real runtime required: no live external providers; local verification lanes only. Human/UAT required: no.

## Integration Closure

Upstream surfaces consumed: S02 route/API/history helper centralization proof, S03 diagnostics policy proof, S04 browser-visible virtualization deferment proof, S05 generated closeout pattern, R101-R103 deferred constraint rows, and Makefile audit/verify targets. New wiring introduced: none at runtime; this is a generated audit and validation-evidence closure slice. What remains after this slice: milestone validation can be rerun to produce `.gsd/milestones/M020/M020-VALIDATION.md` if the recorded proof is accepted.

## Verification

- No runtime observability surface changes are planned. The slice preserves diagnostics/redaction proof surfaces and improves future-agent inspection by making generated audit text and tests name deferred-scope boundaries and handoff evidence explicitly.

## Tasks

- [x] **T01: Lock remediation coverage in generated audit tests** `est:45m`
  Why: Milestone validation failed because final evidence did not explicitly cover deferred storage redesign R101, major UI/product redesign R102, new external provider integrations R103, and the S02-S04 analyst-visible contract handoff. This task turns those gaps into executable audit-generation expectations before changing generated prose. Skills used: tdd, verify-before-complete.
  - Files: `tests/test_optimization_audit.py`
  - Verify: python3 -m pytest -q tests/test_optimization_audit.py

- [x] **T02: Regenerate audit remediation language from source** `est:1h`
  Why: M020 audit artifacts are generated, so deferred-scope remediation must be encoded in `tools/optimization_audit.py` and regenerated rather than hand-edited in `.gsd/milestones/M020/M020-AUDIT.md`. Skills used: write-docs, verify-before-complete.
  - Files: `tools/optimization_audit.py`, `.gsd/milestones/M020/M020-AUDIT.md`
  - Verify: python3 -m pytest -q tests/test_optimization_audit.py

- [x] **T03: Close requirements and rerun final verification ladder** `est:1h`
  Why: The remediation is only complete if requirements and final proof are aligned with the regenerated audit and strict verification ladder. This task records validation-backed closeout for R101-R103 and reruns focused plus all-up checks. Skills used: verify-before-complete.
  - Files: `.gsd/REQUIREMENTS.md`, `.gsd/milestones/M020/M020-AUDIT.md`
  - Verify: make verify

## Files Likely Touched

- tests/test_optimization_audit.py
- tools/optimization_audit.py
- .gsd/milestones/M020/M020-AUDIT.md
- .gsd/REQUIREMENTS.md
