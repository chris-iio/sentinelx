# S04: Mocked Online email enrichment proof

**Goal:** Prove the assembled EmailRep Online flow end-to-end in a deterministic browser test: a fake-key-configured EmailRep provider, real settings/form/CSRF/results HTML path, mocked enrichment status response, email IOC card, EmailRep verdict summary, compact context row, and safe DOM rendering all work without a live EmailRep key or third-party HTTP request.
**Demo:** After this, a deterministic browser test submits an email IOC in Online mode and sees an EmailRep verdict/context row without requiring a live EmailRep key.

## Must-Haves

- A Playwright E2E test configures EmailRep with a syntactically valid fake key through the real `/settings` UI, then submits an email IOC in Online mode through the real index form.
- The test arms the enrichment status route mock before the Online submit and verifies `.page-results` is live-owned, uses the deterministic fake job id, and exposes `data-provider-counts` with `email: 1`.
- The mocked status payload contains an `EmailRep` result for the submitted email and the browser renders a suspicious/clean mapped verdict surface through the existing shared result-application path.
- Expanding the email IOC row shows an EmailRep provider detail row under `.enrichment-section--reputation` with compact whitelisted context fields such as reputation, references, risk flags, domain reputation, profiles, MX/deliverability/spoofing/auth flags.
- Negative/safety assertions prove script-like EmailRep raw values render as text, no `<script>` nodes are created, unsupported nested payloads are omitted, and raw object/JSON dumping does not appear.
- Existing mocked enrichment E2E helpers and EmailRep registry/settings tests remain passing; no live EmailRep request or real API key is required.

## Proof Level

- This slice proves: Final-assembly browser integration proof. Real Flask live server, real CSRF-enabled settings and analyze routes, real bundled frontend, real Playwright browser. External EmailRep network is mocked at the `/enrichment/status/**` browser route boundary, and background enrichment launch is suppressed only through the existing E2E fake-job seam in `tests/e2e/conftest.py`. Human/UAT is not required.

## Integration Closure

Consumes S01 EmailRep adapter result shape and flattened `raw_stats`, S02 registry/settings/provider-count wiring, and S03 shared row-factory/result-application rendering. Introduces only test/fixture wiring for final proof; production code should change only if the browser proof exposes a real integration bug. After this slice, M016 has deterministic proof from provider configuration through Online email IOC rendering; live EmailRep smoke remains intentionally out of scope.

## Verification

- Runtime inspection surfaces are the results root attributes (`data-results-owner`, `data-job-id`, `data-provider-counts`), provider progress/count text, `.ioc-summary-row`, `.verdict-label`, `.enrichment-section--reputation .provider-detail-row`, and `.provider-context-field`. Failure localizes to settings persistence/registry count, fake-job route setup, enrichment polling, result application, or row-factory field whitelisting based on which assertion fails. Redaction constraint: fake key must never appear in page text, test logs, or mocked payload assertions.

## Tasks

- [x] **T01: Add an EmailRep-specific mocked Online E2E fixture** `est:45m`
  Why: S04 needs a deterministic browser-level EmailRep status response that can be armed before Online submit, matches the submitted email IOC, and keeps existing mocked-IP tests unchanged.
  - Files: `tests/e2e/conftest.py`, `tests/e2e/pages/results_page.py`
  - Verify: python3 -m pytest tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q

- [x] **T02: Prove Online email submission renders EmailRep verdict and context in Playwright** `est:1h`
  Why: This is the slice demo and final assembly proof: the browser must exercise the real settings page, real analyze form, CSRF-enabled Flask routes, provider-count HTML contract, frontend polling, shared result application, row expansion, and safe EmailRep context rendering.
  - Files: `tests/e2e/test_emailrep_online.py`
  - Verify: python3 -m pytest tests/e2e/test_emailrep_online.py -q && python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py tests/e2e/test_settings.py -q && npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

## Files Likely Touched

- tests/e2e/conftest.py
- tests/e2e/pages/results_page.py
- tests/e2e/test_emailrep_online.py
