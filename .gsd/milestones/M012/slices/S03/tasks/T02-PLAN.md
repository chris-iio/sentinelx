---
estimated_steps: 4
estimated_files: 3
skills_used:
  - test
  - verify-before-complete
---

# T02: Stub online E2E orchestration so the deep lane stays deterministic

**Slice:** S03 — Fast default proof loop and deterministic expensive lane
**Milestone:** M012

## Description

Patch the E2E live-server/test helper seam so online tests that already mock `/enrichment/status/**` stop launching real background enrichment jobs, then add browser assertions proving the deterministic seam is active and run the full expensive lane without shutdown-noise ambiguity. Keep the real Flask app, CSRF/security headers, results-page HTML contract, and browser interaction path intact; only the background orchestration submission should become test-deterministic.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tests/e2e/conftest.py` live server + route-mocking seam | Fail loudly in pytest; do not silently fall back to real background enrichment | Keep the same route-mock wait points so browser tests time out on missing deterministic setup instead of hanging | If mocked metadata is incomplete, make the browser assertions catch the missing job id/provider state |
| `app/routes/analysis.py` online-mode template contract | Preserve the real online page shape, CSRF behavior, and provider/progress metadata expected by the browser tests | Do not add retries or sleeps around online submission; the seam should be deterministic immediately | Match the real template fields (`job_id`, provider counts, progress text) closely enough that the UI path stays honest |
| `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` | Add explicit assertions for deterministic mocked-online behavior so future regressions fail in-browser | Keep waits bounded to the existing summary-row/detail-link selectors; avoid new indefinite sleeps | If a mocked response or fake job id drifts, assert on the wrong/missing value rather than letting the suite pass implicitly |

## Load Profile

- **Shared resources**: in-process Flask server, Playwright browser session, route mocks, and any background-thread/orchestrator state created during the E2E session.
- **Per-operation cost**: one online form submit, one mocked polling stream, and the existing browser/UI DOM assertions per test.
- **10x breakpoint**: if mocked-online tests still schedule real enrichment work, background threads and provider calls become the first source of flake/noise long before the browser assertions themselves are a problem.

## Negative Tests

- **Malformed inputs**: mocked-online setup missing a fake job id, empty provider metadata, or route mocks registered too late.
- **Error paths**: online E2E submit accidentally hits real background orchestration, deep-lane run emits interpreter-shutdown executor noise, or the mocked-online seam stops matching the rendered DOM contract.
- **Boundary conditions**: repeated online mocked submissions in one session, both IP and URL mocked-online flows, and complete mocked responses that still drive summary rows and detail-link injection.

## Steps

1. Update `tests/e2e/conftest.py` so the live E2E server can replace online-mode orchestration with a deterministic test-only seam when the browser tests are already supplying mocked `/enrichment/status/**` responses.
2. Keep the seam at the test boundary by preserving the real Flask app, security headers, CSRF behavior, and rendered results-page contract while bypassing background `ThreadPoolExecutor` submission.
3. Extend `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` with explicit assertions that the mocked-online path is active (for example via deterministic job metadata or equivalent visible contract) instead of only inferring it from passing enrichment rows.
4. Run the full browser lane through the named command and confirm the expensive proof path is deterministic, still exercises the real UI, and no longer ends with the interpreter-shutdown executor trace.

## Must-Haves

- [ ] Mocked-online E2E tests no longer schedule real background enrichment work.
- [ ] The deep lane keeps the real browser/UI path, CSRF, security headers, and results-page DOM contract intact.
- [ ] `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` assert that the deterministic mocked-online seam is active.
- [ ] `make verify-deep` is the trustworthy slower lane and no longer finishes with ambiguous shutdown-noise output.

## Verification

- `make verify-deep`
- `python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_url_e2e.py`

## Observability Impact

- Signals added/changed: deterministic mocked-online job metadata and explicit browser assertions replace implicit trust in background-thread behavior.
- How a future agent inspects this: run `make verify-deep` or the focused E2E modules and inspect the failing assertion/pytest output rather than chasing shutdown logs.
- Failure state exposed: accidental real orchestration, missing fake job metadata, or deep-lane nondeterminism becomes a direct test failure.

## Inputs

- `tests/e2e/conftest.py` — current live-server fixture and `/enrichment/status/**` route-mocking helper.
- `tests/e2e/test_results_page.py` — online mocked enrichment surface coverage for IP/standard result cards.
- `tests/e2e/test_url_e2e.py` — online mocked enrichment surface coverage for URL results.
- `app/routes/analysis.py` — online-mode route contract the E2E seam must preserve.
- `app/routes/_helpers.py` — current real orchestrator setup path that the test seam must avoid triggering.
- `app/templates/results.html` — rendered results-page attributes and progress/export contract the browser lane still needs to exercise.

## Expected Output

- `tests/e2e/conftest.py` — deterministic test-only online orchestration seam for mocked browser runs.
- `tests/e2e/test_results_page.py` — browser assertions proving the mocked-online seam is active for the standard online flow.
- `tests/e2e/test_url_e2e.py` — browser assertions proving the mocked-online seam is active for URL online flow.
