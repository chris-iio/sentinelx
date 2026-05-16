---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T03: Run focused frontend and mocked-online browser proof

Expected executor skills: verify-before-complete, test.

Why: S04 is explicitly analyst-visible/browser-visible, so focused Vitest proof alone is not enough. The slice must show that mocked-online browser workflows still pass after the S04 decision and audit refresh.

Do: Run the focused frontend measurement test, regenerate the audit, run the optimization-audit tests, then run `make verify-deep`. If T02 touched production TypeScript, also run `make verify-fast` to cover typecheck/build and non-E2E regressions. Investigate any browser failure as a real continuity regression unless evidence shows test infrastructure failure. Do not mask provider/status/diagnostics failures or add secret-bearing logs.

Done when: all required commands pass and the executor has fresh evidence for focused frontend behavior, generated audit correctness, and mocked-online browser continuity.

## Inputs

- `app/static/src/ts/modules/result-application.test.ts`
- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`
- `Makefile`
- `tests/e2e`

## Expected Output

- `app/static/src/ts/modules/result-application.test.ts`
- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

make verify-deep

## Observability Impact

Verifies the existing browser-observable inspection surfaces: mocked-online E2E status/result DOM, frontend Vitest spies, and generated audit proof language. Failure should remain visible in test output rather than hidden by retries or broad assertions.
