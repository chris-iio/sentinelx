# S05: S05: Validation remediation — reconcile requirements/context scope and proof

**Goal:** Reconcile M016 closeout artifacts so Email Reputation Depth can be validated honestly: stale context/requirement scope is aligned with the completed EmailRep roadmap, R083 diagnostic-log export is explicitly descoped to M018 rather than treated as an M016 blocker, and fresh executable proof demonstrates the EmailRep Online, CSRF/safe-rendering, and E2E coverage promises behind R008, R009, and R011.
**Demo:** After this: validation round 1 has coherent requirement coverage and acceptance evidence for Email Reputation Depth, with R083/context criteria either explicitly descoped from M016 or implemented/proven if retained.

## Must-Haves

- `.gsd/milestones/M016/M016-CONTEXT.md` describes the operative Email Reputation Depth scope and no longer presents Minimal Useful Product Hardening as the current M016 acceptance contract.
- `.gsd/REQUIREMENTS.md` makes R083 ownership unambiguous as future M018 diagnostic-log-export work, not an M016 EmailRep acceptance criterion.
- Requirement coverage for M016 explicitly ties to R008, R009, and R011 continuity/security/E2E proof plus the EmailRep-specific roadmap success criteria.
- Fresh verification passes for EmailRep coverage, mocked Online E2E rendering, existing mocked enrichment/settings flows, safe DOM/TypeScript checks, and the final validation artifact path.
- Completed slices S01-S04 remain structurally unchanged; if any proof fails, S05 records a needs-remediation validation result rather than claiming pass.

## Proof Level

- This slice proves: Final-assembly validation-remediation proof. Real runtime required: yes for browser E2E. Human/UAT required: no; deterministic automated tests and GSD validation artifact are sufficient.

## Integration Closure

S05 consumes completed S01-S04 summaries and existing EmailRep tests, updates only closeout/requirement artifacts unless verification reveals a concrete product regression, and closes M016 by producing coherent validation evidence. Nothing should remain before milestone completion except normal `gsd_slice_complete`, `gsd_validate_milestone`, and `gsd_complete_milestone` orchestration after all S05 tasks pass.

## Verification

- No production observability is added. The slice improves project-level failure visibility by making requirement ownership and validation evidence inspectable through `.gsd/REQUIREMENTS.md`, `.gsd/milestones/M016/M016-CONTEXT.md`, test output, and the milestone validation artifact; redaction constraints remain that EmailRep keys must never be echoed in settings, tests, or validation text.

## Tasks

- [x] **T01: Reconcile M016 context and requirement ownership** `est:45m`
  Expected executor skills: `write-docs`, `verify-before-complete`.
  - Files: `.gsd/milestones/M016/M016-CONTEXT.md`, `.gsd/REQUIREMENTS.md`
  - Verify: python3 - <<'PY'
from pathlib import Path
ctx = Path('.gsd/milestones/M016/M016-CONTEXT.md').read_text()
req = Path('.gsd/REQUIREMENTS.md').read_text()
assert 'Email Reputation Depth' in ctx, 'M016 context must name operative Email Reputation Depth scope'
assert 'EmailRep' in ctx and 'mocked Online' in ctx, 'M016 context must include EmailRep mocked Online proof scope'
assert 'Minimal Useful Product Hardening' not in ctx.splitlines()[0], 'M016 title must no longer advertise stale minimal-product scope'
assert 'R083' in req and 'M018' in req, 'R083 must remain recorded and point at the future M018 diagnostic export scope'
print('context/requirement reconciliation checks passed')
PY

- [ ] **T02: Refresh EmailRep acceptance proof against requirement promises** `est:1h`
  Expected executor skills: `test`, `verify-before-complete`.
  - Files: `tests/test_emailrep_online_coverage.py`, `tests/e2e/test_emailrep_online.py`, `tests/e2e/test_results_page.py`, `tests/e2e/test_settings.py`, `app/static/src/ts/modules/row-factory.test.ts`, `app/static/src/ts/modules/result-application.test.ts`
  - Verify: python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q && npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

- [ ] **T03: Produce milestone validation evidence for Email Reputation Depth** `est:45m`
  Expected executor skills: `verify-before-complete`, `write-docs`.
  - Files: `.gsd/milestones/M016/M016-VALIDATION.md`
  - Verify: test -s .gsd/milestones/M016/M016-VALIDATION.md && grep -q "Email Reputation Depth" .gsd/milestones/M016/M016-VALIDATION.md && grep -Eq "pass|needs-remediation" .gsd/milestones/M016/M016-VALIDATION.md

## Files Likely Touched

- .gsd/milestones/M016/M016-CONTEXT.md
- .gsd/REQUIREMENTS.md
- tests/test_emailrep_online_coverage.py
- tests/e2e/test_emailrep_online.py
- tests/e2e/test_results_page.py
- tests/e2e/test_settings.py
- app/static/src/ts/modules/row-factory.test.ts
- app/static/src/ts/modules/result-application.test.ts
- .gsd/milestones/M016/M016-VALIDATION.md
