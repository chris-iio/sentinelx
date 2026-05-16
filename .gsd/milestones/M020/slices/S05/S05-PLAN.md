# S05: Final Integration and Closeout Proof

**Goal:** Close M020 by refreshing the generated audit with all shipped/rejected outcomes, running the real final verification entrypoint, and producing evidence that SentinelX's analyst loop and failure/redaction guardrails survived S02-S04.
**Demo:** The M020 audit reflects shipped/rejected outcomes, final make verify passes, and closeout proof confirms SentinelX’s analyst loop still works end-to-end.

## Must-Haves

- Generated M020 audit records S02, S03, and S04 outcomes plus S05 closeout language for final verification and remaining deferred work.
- Focused regression lanes for route/API/history, diagnostics, frontend result rendering, and audit generation remain executable and green before the final all-up command.
- `make verify` passes as the final milestone verification entrypoint.
- Closeout evidence covers R097-R100: analyst loop continuity, strict lanes, failure visibility/redaction, and durable shipped/rejected outcome documentation.

## Proof Level

- This slice proves: final-assembly: this slice proves milestone integration and operational closeout through generated audit inspection, focused boundary tests, and the real `make verify` entrypoint. Real runtime: yes through the project's verification/browser lanes. Human/UAT required: no.

## Integration Closure

Upstream surfaces consumed: S02 route/API/history helper outcome, S03 diagnostics policy outcome, S04 frontend virtualization deferment, tools/optimization_audit.py, tests/test_optimization_audit.py, and Makefile verification targets. New wiring introduced: none unless audit source/tests need final closeout text. What remains before the milestone is usable end-to-end: nothing if final `make verify` passes and the generated audit/closeout summary records the result.

## Verification

- No new runtime observability surface is planned. S05 must preserve and prove existing inspection surfaces: route/API responses for missing-provider/empty paths, diagnostic bundle manifest status/error/omitted/truncated metadata, redaction metadata without secrets, generated audit command-capture rows, and browser-visible result DOM behavior.

## Tasks

- [x] **T01: Lock final audit closeout contract** `est:45m`
  Why: S05 must make the M020 outcome durable before running final verification, and the generated audit source is the canonical documentation surface rather than hand-edited prose. Expected executor skills: verify-before-complete, write-docs, test. Do: inspect the current generated M020 audit source and tests; add or tighten tests in `tests/test_optimization_audit.py` so they require S02 shipped route helper centralization, S03 shipped diagnostics policy centralization, S04 virtualization deferment, and S05 final closeout language including final `make verify`, failure-visibility/redaction guardrails, and what remains deferred; then update `tools/optimization_audit.py` only as needed to satisfy those generated-content tests. Failure Modes (Q5): if the generator omits a slice outcome, downstream closeout becomes stale; fail the audit test instead of hand-editing `.gsd` output. Load Profile (Q6): trivial generator/test workload; no shared runtime resources. Negative Tests (Q7): assert absence of misleading final-shipped language for the deferred virtualization rewrite and presence of redaction/failure-state guardrails. Done when the focused audit test lane passes and no `.gsd/` artifact has been manually edited in this task.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`
  - Verify: python3 -m pytest -q tests/test_optimization_audit.py

- [x] **T02: Regenerate audit and rerun focused continuity lanes** `est:1h`
  Why: Final closeout should consume the real generated audit artifact and focused regressions from S02-S04 before the slower all-up verification command. Expected executor skills: verify-before-complete, test. Do: run `make audit-m020` to regenerate `.gsd/milestones/M020/M020-AUDIT.md` from `tools/optimization_audit.py`; inspect only if needed to diagnose failures; run focused backend route/API/history tests, diagnostics tests, frontend result-application Vitest, and audit tests. Failure Modes (Q5): if a focused lane fails, do not proceed to final closeout; localize to the owning seam from S02, S03, or S04 and fix/regenerate before continuing. Load Profile (Q6): focused test lanes exercise large-result frontend behavior and backend helper/diagnostics seams without live provider load; browser/live load is deferred to T03's Makefile lane. Negative Tests (Q7): these lanes include missing-provider redirects, empty paths, diagnostics error/omitted states, secret redaction, and same-severity large-result no-op behavior. Done when the generated audit is refreshed from source and all focused continuity lanes pass.
  - Files: `.gsd/milestones/M020/M020-AUDIT.md`
  - Verify: python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py tests/test_optimization_audit.py

- [x] **T03: Run final verify and assemble closeout evidence** `est:1h`
  Why: The milestone success criteria require the real final verification entrypoint, not only focused tests, and S05 owns validating R097-R100 for closeout. Expected executor skills: verify-before-complete, write-docs. Do: run `npx vitest run app/static/src/ts/modules/result-application.test.ts` if it was not already run during T02 execution diagnostics, then run the final `make verify` target; preserve the fresh command evidence for task/slice completion; summarize in the task completion evidence how intake/extraction/enrichment/results/history/detail/diagnostics/filtering/copy/export are covered by focused lanes plus `make verify`, and call out the S04 virtualization deferment as intentionally left alone. Failure Modes (Q5): if `make verify` fails, do not mark complete; use the failing target output to route remediation to backend tests, frontend tests/build, browser lane, or audit generation. Load Profile (Q6): `make verify` is the all-up local verification load and may rebuild assets and run browser-facing checks; no production traffic or live secrets should be required. Negative Tests (Q7): final evidence must include failure-path/redaction coverage from diagnostics and route tests, and should not claim live-provider behavior beyond what the project's verification lane actually exercises. Done when `make verify` exits 0 and completion evidence is ready for `gsd_task_complete`/`gsd_slice_complete` without inventing manual UAT.
  - Verify: make verify

## Files Likely Touched

- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M020/M020-AUDIT.md
