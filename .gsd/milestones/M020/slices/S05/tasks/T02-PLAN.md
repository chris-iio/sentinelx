---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T02: Regenerate audit and rerun focused continuity lanes

Why: Final closeout should consume the real generated audit artifact and focused regressions from S02-S04 before the slower all-up verification command. Expected executor skills: verify-before-complete, test. Do: run `make audit-m020` to regenerate `.gsd/milestones/M020/M020-AUDIT.md` from `tools/optimization_audit.py`; inspect only if needed to diagnose failures; run focused backend route/API/history tests, diagnostics tests, frontend result-application Vitest, and audit tests. Failure Modes (Q5): if a focused lane fails, do not proceed to final closeout; localize to the owning seam from S02, S03, or S04 and fix/regenerate before continuing. Load Profile (Q6): focused test lanes exercise large-result frontend behavior and backend helper/diagnostics seams without live provider load; browser/live load is deferred to T03's Makefile lane. Negative Tests (Q7): these lanes include missing-provider redirects, empty paths, diagnostics error/omitted states, secret redaction, and same-severity large-result no-op behavior. Done when the generated audit is refreshed from source and all focused continuity lanes pass.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
- `app/static/src/ts/modules/result-application.test.ts`

## Expected Output

- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py tests/test_optimization_audit.py

## Observability Impact

Confirms existing failure visibility through focused route, diagnostics, redaction, generated-audit, and frontend assertions before full integration verification.
