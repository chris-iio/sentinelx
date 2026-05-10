---
estimated_steps: 17
estimated_files: 2
skills_used: []
---

# T01: Add an EmailRep-specific mocked Online E2E fixture

Why: S04 needs a deterministic browser-level EmailRep status response that can be armed before Online submit, matches the submitted email IOC, and keeps existing mocked-IP tests unchanged.

Files: `tests/e2e/conftest.py`, `tests/e2e/pages/results_page.py`.

Do:
1. In `tests/e2e/conftest.py`, add a canned `MOCK_ENRICHMENT_RESPONSE_EMAILREP` (or factory helper) for a single email IOC such as `analyst@example.com` with one `EmailRep` result, `complete: true`, `total: 1`, `done: 1`, `next_since: 1`, `verdict: suspicious`, scalar detection fields, and flattened `raw_stats` covering reputation, references, risk_flags, domain_reputation, profiles, first_seen, last_seen, deliverable, valid_mx, spoofable, spf_strict, and dmarc_enforced.
2. Include deliberate malformed/safety payload values in the fixture: a script-like string inside an allowed scalar/list field and an unsupported nested object under an unknown key. This gives T02 a real browser negative assertion without adding unsafe production behavior.
3. Add a helper such as `setup_emailrep_enrichment_route_mock(page, email: str = EMAILREP_E2E_EMAIL) -> str` that calls the existing fake-job arm path and installs `page.route("**/enrichment/status/**", ...)` before submit, mirroring `setup_enrichment_route_mock` so route ordering remains correct.
4. Keep the existing `setup_enrichment_route_mock` and `mocked_enrichment` behavior unchanged for IP tests.
5. Optionally add small `ResultsPage` helper locators for card-scoped provider detail rows and provider context fields if they make T02 assertions clearer; avoid broad selector rewrites.

Must-haves:
- The EmailRep mock payload's `ioc_value` must match the email used by the planned browser test.
- The helper must return the deterministic fake job id so T02 can assert `.page-results[data-job-id]`.
- No live EmailRep key, EmailRep URL, or third-party request should be introduced.
- Existing mocked enrichment route helper semantics must remain backward-compatible.

Verify:
- `python3 -m pytest tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling -q`
- `python3 -m pytest tests/e2e/test_settings.py::test_save_key_shows_success_flash -q`

Done when: EmailRep-specific E2E mocking can be imported by a browser test, returns a fake job id, uses a complete mocked status payload, and existing mocked Online IP/settings tests still pass.

## Inputs

- `tests/e2e/conftest.py`
- `tests/e2e/pages/results_page.py`
- `app/static/src/ts/modules/result-application.test.ts`
- `app/static/src/ts/modules/row-factory.test.ts`

## Expected Output

- `tests/e2e/conftest.py`
- `tests/e2e/pages/results_page.py`

## Verification

python3 -m pytest tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q

## Observability Impact

Adds a deterministic test-only status payload and fake-job helper that future agents can inspect in `tests/e2e/conftest.py` when browser EmailRep proof fails. Failure state is visible through the returned fake job id and mocked JSON body rather than external provider logs.
