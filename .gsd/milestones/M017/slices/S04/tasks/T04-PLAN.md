---
estimated_steps: 13
estimated_files: 5
skills_used: []
---

# T04: Run integrated analyst-flow regression proof for S04

Why: Because S04 touches or formally evaluates analyst-visible frontend/render behavior, closeout must prove IOC intake, enrichment, results, history/detail, diagnostics, and security/redaction behavior still hold after the secondary optimization decision.

Skills used: `verify-before-complete`, `test`.

Do:
1. Run focused frontend and audit checks after all code/audit updates.
2. Run `make verify-fast` for the repo-wide fast lane.
3. Run `make verify-deep` for deterministic mocked-online browser proof. This is required for any shipped frontend/render change and still valuable for an explicit rejection because S04's purpose is analyst-flow regression.
4. If failures appear, fix the source behavior rather than weakening tests, unless a test is demonstrably stale; document any legitimate test correction in the task summary.
5. Ensure diagnostics/redaction behavior remains covered by existing suites and no new browser-visible output exposes API keys, tokens, or raw secrets.

Threat surface (Q3): confirms browser-visible user input, copy/export, result/detail navigation, and diagnostics remain safe after render-path work.
Requirement impact (Q4): re-verifies R086, R087, R088 and supports S05 final proof.
Failure modes (Q5): passing focused tests while full analyst flow regresses; generated audit out of sync with source; diagnostics/redaction regression.
Load profile (Q6): full local fast/deep verification including mocked-online e2e suite; no external provider calls required.
Negative tests (Q7): existing CSRF/redaction/security and browser e2e checks must remain green; focused no-op/severity-change frontend tests must remain green.

## Inputs

- ``app/static/src/ts/modules/result-application.test.ts``
- ``tests/test_optimization_audit.py``
- ``tests/e2e/test_results_page.py``
- ``tests/e2e/test_emailrep_online.py``
- ``Makefile``
- ``tools/optimization_audit.py``

## Expected Output

- `Makefile`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_emailrep_online.py`
- `tests/test_optimization_audit.py`
- `app/static/src/ts/modules/result-application.test.ts`

## Verification

npm test -- --run && python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py && make verify-fast && make verify-deep

## Observability Impact

Produces command evidence that the existing observable analyst surfaces and diagnostics/redaction contracts remain intact.
