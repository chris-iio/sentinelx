# S04: Analyst Flow Regression + Secondary Optimization

**Goal:** Ship or explicitly reject the remaining high-confidence frontend/render optimization after S03, preserving analyst IOC intake, live enrichment polling, results/history/detail continuity, diagnostics, and security/redaction behavior with focused frontend proof and mocked-online browser regression.
**Demo:** Any remaining high-confidence optimization tied to intake/results/history/diagnostics is shipped or explicitly rejected, with browser-visible analyst flow proof if touched.

## Must-Haves

- The S04 plan evaluates the M017 do-next browser result rendering churn target from `tools/optimization_audit.py` against the actual result-application path.
- If the optimization is justified, frontend result application avoids unnecessary flush-wide verdict dashboard recount/reorder work when incoming polling/history deltas do not change severity/order-relevant state; if not justified, the rejection is encoded in the audit generator with evidence.
- Focused Vitest coverage exercises live/history result application, no-op or provider-only deltas, severity/order changes, copy/export/detail-link continuity, and textContent-safe rendering assumptions.
- Focused Python audit tests prove the S04 shipped/rejected outcome is durable and not hand-patched.
- Integrated verification passes `make verify-fast` and `make verify-deep`; browser-visible analyst-flow proof is included because S04 touches or evaluates frontend render behavior.

## Proof Level

- This slice proves: Integration proof with browser-visible mocked-online regression. Real runtime required: yes, via existing local Flask/Playwright e2e harness in `make verify-deep`. Human/UAT required: no.

## Integration Closure

Upstream surfaces consumed: S03 incremental polling route proof, M017 audit generator, result application modules under `app/static/src/ts/modules`, templates under `app/templates`, and e2e fixtures under `tests/e2e`. New wiring introduced: either a narrow frontend render optimization in the shared result application path plus audit proof, or an explicit audit-generator rejection of that optimization with focused evidence. Remaining before S05: final full milestone assembly, requirements coverage confirmation, and final `make verify-fast`/`make verify-deep` closeout.

## Verification

- S04 must preserve existing analyst inspection surfaces: visible enrichment progress/results state, browser-accessible history/detail pages, `/diagnostics` redacted provider/config/cache diagnostics, status route fields (`status`, `terminal`, `terminal_reason`, `error`, `next_since`), and generated M017 audit proof. Any new frontend test hook or render instrumentation must remain test-only or non-sensitive and must not expose API keys, tokens, raw secrets, or unsafe IOC HTML.

## Tasks

- [x] **T01: Lock browser result rendering churn contract with focused frontend tests** `est:1h`
  Why: S04's secondary target is the do-next frontend/render opportunity named by the M017 audit: flush-wide verdict dashboard recounts and severity reorders during polling/history replay. Before changing code, create or extend focused Vitest coverage that exposes the desired contract and protects analyst-visible behavior.
  - Files: `app/static/src/ts/modules/result-application.test.ts`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/cards.ts`, `package.json`, `vitest.config.ts`
  - Verify: npm test -- --run

- [x] **T02: Implement or reject the narrow frontend render optimization** `est:1h30m`
  Why: S04 must either ship the remaining high-confidence optimization tied to the analyst results path or explicitly reject it with evidence. The preferred implementation target is reducing unnecessary flush-wide dashboard recount/reorder work after S03's backend polling optimization.
  - Files: `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/cards.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/result-application.test.ts`
  - Verify: npm test -- --run && python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py

- [x] **T03: Encode the S04 secondary optimization outcome in the audit generator** `est:45m`
  Why: M017 requires optimization decisions to be durable and evidence-backed. S04 must update the generated audit source so future agents see whether the frontend/render follow-up shipped or was rejected, and why.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M017/M017-AUDIT.md`
  - Verify: python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md && python3 -m pytest -q tests/test_optimization_audit.py

- [x] **T04: Run integrated analyst-flow regression proof for S04** `est:1h`
  Why: Because S04 touches or formally evaluates analyst-visible frontend/render behavior, closeout must prove IOC intake, enrichment, results, history/detail, diagnostics, and security/redaction behavior still hold after the secondary optimization decision.
  - Files: `Makefile`, `tests/e2e/test_results_page.py`, `tests/e2e/test_emailrep_online.py`, `tests/test_optimization_audit.py`, `app/static/src/ts/modules/result-application.test.ts`
  - Verify: npm test -- --run && python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py && make verify-fast && make verify-deep

## Files Likely Touched

- app/static/src/ts/modules/result-application.test.ts
- app/static/src/ts/modules/result-application.ts
- app/static/src/ts/modules/cards.ts
- package.json
- vitest.config.ts
- app/static/src/ts/modules/enrichment.ts
- app/static/src/ts/modules/row-factory.ts
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M017/M017-AUDIT.md
- Makefile
- tests/e2e/test_results_page.py
- tests/e2e/test_emailrep_online.py
