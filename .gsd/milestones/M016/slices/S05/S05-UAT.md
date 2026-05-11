# S05: S05: Validation remediation — reconcile requirements/context scope and proof — UAT

**Milestone:** M016
**Written:** 2026-05-11T19:09:36.743Z

## UAT Type
Automated deterministic closeout/UAT for milestone validation remediation; no human analyst session or live EmailRep key required.

## Preconditions
1. Work from `/home/chris/projects/sentinelx`.
2. M016 slices S01-S04 are already complete.
3. No live EmailRep API key is required; tests use mocked Online-mode proof.
4. Project dependencies for pytest, Vitest, and TypeScript are installed.

## Steps
1. Inspect `.gsd/milestones/M016/M016-CONTEXT.md` and confirm the milestone title/scope names Email Reputation Depth rather than Minimal Useful Product Hardening.
2. Inspect `.gsd/REQUIREMENTS.md` and confirm R083 is still active but owned by M018/TBD with validation language for future diagnostic-log export.
3. Run the reconciliation check from S05/T01.
4. Run the focused acceptance gate: `python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q && npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit`.
5. Confirm `.gsd/milestones/M016/M016-VALIDATION.md` exists, names Email Reputation Depth, and records either `pass` or `needs-remediation`.

## Expected Outcomes
- M016 context describes EmailRep adapter/settings/registry/safe rendering/mocked Online proof as the operative milestone contract.
- R083 remains visible and traceable, but is not an M016 acceptance blocker.
- The focused Python E2E/unit proof passes with 9 pytest tests.
- The frontend safety/application proof passes with 59 Vitest tests across 2 files.
- TypeScript checking succeeds with no emitted output.
- The validation artifact records a pass verdict for Email Reputation Depth and cites R008/R009/R011 support plus R083 future ownership.

## Edge Cases
- If the T02 command fails, do not accept the slice; reopen the owning task for execution follow-up.
- If R083 appears as an M016 blocker, reject the closeout and reconcile requirement ownership again.
- If the validation artifact includes raw provider secret values or key assignments, reject the artifact and regenerate it with redacted evidence only.

## Not Proven By This UAT
- Live third-party EmailRep API behavior with a real key.
- Raw EML/header phishing triage.
- M018 diagnostic-log export implementation.
- Multiple-provider email reputation aggregation.
