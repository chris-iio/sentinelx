---
estimated_steps: 32
estimated_files: 1
skills_used: []
---

# T02: Prove Online email submission renders EmailRep verdict and context in Playwright

Why: This is the slice demo and final assembly proof: the browser must exercise the real settings page, real analyze form, CSRF-enabled Flask routes, provider-count HTML contract, frontend polling, shared result application, row expansion, and safe EmailRep context rendering.

Files: `tests/e2e/test_emailrep_online.py`.

Do:
1. Create `tests/e2e/test_emailrep_online.py` with a focused Playwright test, for example `test_online_email_ioc_renders_mocked_emailrep_context`.
2. Use `SettingsPage` against `live_server` to save a fake EmailRep key such as `emailrep-e2e-fake-key-1234567890`; assert the success flash/configured status and assert the raw fake key is not visible in page text after save/reload.
3. Call `setup_emailrep_enrichment_route_mock(page, email=...)` from T01 before submitting the Online form. This ordering is mandatory to avoid the existing 750ms polling race.
4. Use `IndexPage` to submit text containing only the matching email IOC in Online mode through the real form.
5. Assert `.page-results` has `data-results-owner="live"`, `data-job-id` equal to the helper return value, and a parseable `data-provider-counts` JSON object where `email == 1`.
6. Assert the email card exists with `data-ioc-type="email"` and the expected `data-ioc-value`; wait for `.ioc-summary-row`; assert summary/verdict surfaces include the EmailRep verdict/attribution (for the planned fixture, `SUSPICIOUS` and `EmailRep: Suspicious`).
7. Expand the row and assert one EmailRep provider detail row appears under `.enrichment-section--reputation`, not context/no-data sections, with compact context fields from the fixture.
8. Add negative DOM assertions: no `<script>` under the EmailRep row/card, script-like raw value appears only as text if included in an allowed field, unknown nested payload key/value does not appear, and `[object Object]`/raw JSON dumping does not appear.
9. Keep the test deterministic: no live EmailRep HTTP request, no waiting on background provider threads, no dependency on pre-existing provider keys.

Must-haves:
- The test must fail if provider-count wiring regresses to `email: 0`.
- The test must fail if EmailRep is rendered in the wrong section, not rendered at all, or stops updating the summary/worst-verdict surface.
- The test must fail if unsafe nested/raw values are dumped into the DOM.
- The test must use existing page objects/route mocks rather than adding production-only hooks.

Threat Surface (Q3): The test sends user-controlled email text through `/analyze`, stores a fake provider secret through `/settings`, and renders remote-provider-controlled `raw_stats`; assertions must preserve CSRF path, key redaction, provider-count gating, and textContent-based DOM safety.

Requirement Impact (Q4): Re-verifies R078 (configured Online EmailRep coverage), R016 (email IOC display compatibility), R008 (Online progress/result application wiring), and R009 (secret redaction and safe DOM rendering). Decision D074 remains locked: use shared row-factory provider-context rendering, not provider-specific nested rendering.

Failure Modes (Q5):
| Dependency | On error | On timeout | On malformed response |
|------------|----------|------------|-----------------------|
| `/settings` save | Test fails before Online submit; no fallback key injection | Playwright action/assertion timeout localizes to settings UI | Status/config assertions reject missing or echoed key |
| `/analyze` Online submit | Test fails on missing `.page-results`/redirect | Playwright timeout localizes to form/route | Provider-count JSON parse/assertion fails |
| `/enrichment/status/**` route mock | Test fails on missing summary row/fake job id | Poll wait times out; confirms route was not armed or frontend did not poll | DOM safety/section assertions fail without live network fallback |

Load Profile (Q6): One browser test, one fake key save, one email IOC, one mocked status response, and one provider result. Shared resources are the session-scoped temp ConfigStore/history DB and Playwright route table; 10x cost is linear in test count and should not stress provider rate limits because no external requests occur.

Negative Tests (Q7): Malformed provider payload includes script-like text and an unknown nested object. Boundary conditions include exactly one email provider in `data-provider-counts`, a single email IOC input to avoid unrelated provider-count noise, and absence of raw key text after settings save.

Verify:
- `python3 -m pytest tests/e2e/test_emailrep_online.py -q`
- `python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py tests/e2e/test_settings.py -q`
- `npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit`

Done when: The new Playwright proof passes in isolation and with the supporting EmailRep/settings/results regression targets, proving the full mocked Online email enrichment demo without any live EmailRep key or network call.

## Inputs

- `tests/e2e/conftest.py`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/pages/results_page.py`
- `tests/e2e/pages/settings_page.py`
- `tests/test_emailrep_online_coverage.py`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- `app/routes/analysis.py`

## Expected Output

- `tests/e2e/test_emailrep_online.py`

## Verification

python3 -m pytest tests/e2e/test_emailrep_online.py -q && python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py tests/e2e/test_settings.py -q && npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

## Observability Impact

Adds the final browser assertion surface for M016. Future failures identify the broken seam by assertion: settings/configured status for key gating, `data-provider-counts` for registry coverage, fake `data-job-id` for E2E route-mock ordering, summary/verdict selectors for result application, and provider context fields for row-factory safety.
