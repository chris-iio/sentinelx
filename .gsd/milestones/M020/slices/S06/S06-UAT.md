# S06: Validation remediation for deferred scope coverage — UAT

**Milestone:** M020
**Written:** 2026-05-16T09:27:08.045Z

## UAT Type

Artifact and verification closeout UAT; no live external providers required.

## Preconditions

1. Worktree contains the completed S06 changes.
2. Local Python/test dependencies are available.
3. No external provider credentials are required; verification uses local audit generation and local test lanes.

## Steps

1. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
2. Confirm the suite passes and includes expectations for R101, R102, R103, deferred-scope/non-claim language, and S02-S04 analyst-visible handoff language.
3. Run `make verify`.
4. Inspect `.gsd/milestones/M020/M020-AUDIT.md` and confirm it is regenerated from `tools/optimization_audit.py` and explicitly states that no new storage redesign, broad UI/product redesign, or external provider integration shipped.
5. Inspect `.gsd/REQUIREMENTS.md` entries for R101-R103 and confirm they remain deferred constraints with validation-backed closeout notes rather than shipped capability claims.

## Expected Outcomes

- Focused audit tests pass with 29 tests.
- `make verify` passes, including the E2E lane.
- The generated audit names R101, R102, R103, the deferred-scope boundaries, and the S02 route/API/history, S03 diagnostics/redaction, and S04 browser-visible deferment contracts.
- Requirements R101-R103 are closed as validation-backed deferred constraints, not as implemented storage/UI/provider rewrites.

## Edge Cases

- If generated audit text is hand-edited but the generator is not updated, focused tests or regeneration will expose the drift.
- If future work accidentally claims a storage redesign, broad UI redesign, or new provider integration under M020, the audit expectations should fail until supported by executable evidence.
- If E2E behavior regresses, `make verify` blocks the milestone closeout even when audit text passes.

## Not Proven By This UAT

- Live external provider behavior or credentials.
- A new storage architecture, major product/UI redesign, or additional external provider integration.
- Production monitoring behavior beyond existing diagnostics/redaction and local verification surfaces.
