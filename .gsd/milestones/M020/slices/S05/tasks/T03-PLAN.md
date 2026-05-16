---
estimated_steps: 1
estimated_files: 10
skills_used: []
---

# T03: Run final verify and assemble closeout evidence

Why: The milestone success criteria require the real final verification entrypoint, not only focused tests, and S05 owns validating R097-R100 for closeout. Expected executor skills: verify-before-complete, write-docs. Do: run `npx vitest run app/static/src/ts/modules/result-application.test.ts` if it was not already run during T02 execution diagnostics, then run the final `make verify` target; preserve the fresh command evidence for task/slice completion; summarize in the task completion evidence how intake/extraction/enrichment/results/history/detail/diagnostics/filtering/copy/export are covered by focused lanes plus `make verify`, and call out the S04 virtualization deferment as intentionally left alone. Failure Modes (Q5): if `make verify` fails, do not mark complete; use the failing target output to route remediation to backend tests, frontend tests/build, browser lane, or audit generation. Load Profile (Q6): `make verify` is the all-up local verification load and may rebuild assets and run browser-facing checks; no production traffic or live secrets should be required. Negative Tests (Q7): final evidence must include failure-path/redaction coverage from diagnostics and route tests, and should not claim live-provider behavior beyond what the project's verification lane actually exercises. Done when `make verify` exits 0 and completion evidence is ready for `gsd_task_complete`/`gsd_slice_complete` without inventing manual UAT.

## Inputs

- `.gsd/milestones/M020/M020-AUDIT.md`
- `Makefile`
- `app/static/src/ts/modules/result-application.test.ts`
- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
- `tests/test_optimization_audit.py`

## Expected Output

- Update the implementation and proof artifacts needed for this task.

## Verification

make verify

## Observability Impact

Uses the real all-up Makefile entrypoint as the final inspection surface and preserves failure localization through the failing subtarget output.
