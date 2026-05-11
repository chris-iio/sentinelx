---
estimated_steps: 14
estimated_files: 6
skills_used: []
---

# T02: Refresh EmailRep acceptance proof against requirement promises

Expected executor skills: `test`, `verify-before-complete`.

Why: S05 must not merely rewrite `.gsd` text; it must refresh executable proof for the promises advanced into validation: R008 enrichment/settings continuity, R009 CSRF and safe DOM rendering, and R011 E2E coverage for the EmailRep Online DOM structure.

Do:
1. Run the listed verification command before changing tests; inspect failures rather than broadening assertions blindly.
2. If all tests already cover the requirement promises, leave source files unchanged and carry the fresh output into the task summary.
3. If a concrete gap appears, add the smallest focused assertion to the existing test file that owns that seam: registry/settings in `tests/test_emailrep_online_coverage.py`, browser DOM/safety in `tests/e2e/test_emailrep_online.py`, existing mocked enrichment continuity in `tests/e2e/test_results_page.py`, settings CSRF/key-redaction in `tests/e2e/test_settings.py`, or frontend safe row rendering in the two Vitest files.
4. Do not add tests that read `.gsd/`, `.planning/`, `.audits/`, or other ignored planning artifacts; tests must exercise product code and public test fixtures only.
5. Preserve deterministic mocked Online proof; no live EmailRep key or third-party network call is allowed.

Threat Surface (Q3): exercises settings/CSRF, provider key redaction, mocked external-provider payloads, and script-like raw values that must render through text-only DOM paths.
Requirement Impact (Q4): re-verifies R008, R009, and R011 without reducing existing coverage.
Failure Modes (Q5): settings failures point to CSRF/config persistence; route-mock failures point to fake job/status setup; row-factory failures point to context-field whitelisting or unsafe DOM construction; TypeScript failures point to broken frontend contracts.
Load Profile (Q6): per test run is bounded local pytest/Vitest work; no shared external resources or provider rate limits.
Negative Tests (Q7): keep or add assertions for no EmailRep key -> zero email providers, unknown/empty key rejection, script-like raw values rendered as text not script nodes, unsupported nested raw payloads omitted, and no raw key echo.
Done when: the full verification command exits 0 and any added assertions are requirement-facing rather than duplicative selector checks.

## Inputs

- `tests/test_emailrep_online_coverage.py`
- `tests/e2e/test_emailrep_online.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_settings.py`
- `app/static/src/ts/modules/row-factory.test.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- `app/enrichment/providers/emailrep.py`
- `app/enrichment/provider_registry.py`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/result-application.ts`

## Expected Output

- `tests/test_emailrep_online_coverage.py`
- `tests/e2e/test_emailrep_online.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_settings.py`
- `app/static/src/ts/modules/row-factory.test.ts`
- `app/static/src/ts/modules/result-application.test.ts`

## Verification

python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q && npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

## Observability Impact

Uses existing failure surfaces: pytest assertion names localize registry/settings/E2E regressions; Vitest localizes row-factory/result-application rendering regressions; TypeScript localizes broken frontend contracts. No new runtime logging is introduced.
