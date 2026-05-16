# S05: Final Integration and Closeout Proof — UAT

**Milestone:** M020
**Written:** 2026-05-16T09:12:55.712Z

## UAT Type
Automated closeout UAT based on generated audit inspection and local verification lanes; no human exploratory session or live provider secrets required.

## Preconditions
1. Repository is checked out at the S05 completed state.
2. Local Python and Node dependencies are installed as expected by the project Makefile.
3. No live provider credentials are required for this UAT; claims are limited to project verification lanes.

## Steps
1. Run `make audit-m020`.
   - Expected: command exits 0 and regenerates `.gsd/milestones/M020/M020-AUDIT.md` from `tools/optimization_audit.py`.
2. Inspect or test the generated audit contract with `python3 -m pytest -q tests/test_optimization_audit.py`.
   - Expected: tests pass and require S02 shipped route helper centralization, S03 shipped diagnostics policy centralization, S04 virtualization deferment, final `make verify` closeout language, remaining deferred-work wording, and failure/redaction guardrails.
3. Run the focused continuity lane: `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py tests/test_optimization_audit.py`.
   - Expected: tests pass, covering route/API/history behavior, diagnostics status/error/omitted/truncated states, secret redaction, export-source behavior, and audit generation.
4. Run the focused frontend lane: `npm test -- app/static/src/ts/modules/result-application.test.ts --run`.
   - Expected: tests pass, including result-application rendering and large-result same-severity no-op behavior.
5. Run final all-up verification: `make verify`.
   - Expected: command exits 0; the e2e lane completes successfully.

## Expected End-to-End Outcomes
- The generated M020 audit documents what shipped, what was rejected or deferred, and why.
- The analyst loop remains covered across intake, extraction, enrichment, results, history/detail, diagnostics, filtering, copy, and export through focused and all-up lanes.
- Failure-path behavior remains explicit for missing-provider/empty paths and diagnostics error/omitted/truncated states.
- Redaction tests preserve the no-secrets boundary.
- S04 frontend virtualization is not falsely claimed as shipped; it remains intentionally deferred.

## Edge Cases
- Missing-provider and empty-input/API paths should continue to surface explicit route/API states rather than hiding failures.
- Diagnostic export edge cases should preserve status/error/omitted/truncated metadata.
- Redaction metadata should be present without exposing secret values.
- Large same-severity result updates should not create misleading frontend churn.

## Not Proven By This UAT
- Live provider enrichment quality or production traffic behavior.
- Manual browser exploratory usability beyond the automated browser/e2e lanes included in `make verify`.
- Performance wins from the deferred S04 virtualization rewrite, which was explicitly left alone.
