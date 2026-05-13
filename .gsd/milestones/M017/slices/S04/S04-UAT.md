# S04: Analyst Flow Regression + Secondary Optimization — UAT

**Milestone:** M017
**Written:** 2026-05-13T17:55:06.175Z

# UAT: S04 Analyst Flow Regression + Secondary Optimization

## UAT Type
Automated, mocked-online analyst-flow regression with focused frontend contract tests and generated audit proof.

## Preconditions
1. Work from `/home/chris/projects/sentinelx`.
2. Dependencies are installed for the existing Node/Vitest and Python/pytest/Playwright harnesses.
3. External provider calls remain mocked by the existing e2e fixtures; no real API keys are required.
4. The S04 code and audit changes are present.

## Steps
1. Run the focused frontend contract suite with `npm test -- --run`.
2. Run the focused generated-audit and analyst browser regression suites with `python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`.
3. Run the integrated fast lane with `make verify-fast`.
4. Run the integrated deep lane with `make verify-deep`.
5. Inspect the generated M017 audit artifact for S04 shipped frontend/render severity-gate language and absence of stale unresolved browser-render target wording.

## Expected Outcomes
1. Provider-only or no-op result deltas preserve rendered cards, copy/export/detail affordances, and safe textContent rendering without forcing global dashboard recount/reorder work.
2. Severity/order-relevant result deltas still update verdict dashboard counts and card ordering correctly.
3. IOC intake, live enrichment polling, results display, history/detail navigation, diagnostics, status fields, and redaction/security behavior remain browser-visible and passing under mocked-online e2e coverage.
4. The generated audit durably records S04 as shipped with evidence, not as a pending do-next item.
5. `make verify-fast` and `make verify-deep` both pass.

## Edge Cases Covered
- Provider-only polling/history deltas that should not change severity or ordering.
- Severity-changing deltas that must refresh counts and order.
- History replay/finalized result affordances.
- Copy/export/detail-link continuity.
- TextContent-safe provider rendering to avoid unsafe IOC/provider HTML injection.
- Diagnostics and redaction behavior under the full e2e lane.

## Not Proven By This UAT
- Real third-party provider availability or latency, because browser proof intentionally uses mocked-online fixtures.
- Browser performance timing metrics in production; S04 uses code-path reasoning and regression proof rather than timing instrumentation.
- Final milestone-level requirements assembly and closeout, which is reserved for S05.
