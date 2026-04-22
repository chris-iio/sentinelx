# S03: Fast default proof loop and deterministic expensive lane — UAT

**Milestone:** M012
**Written:** 2026-04-22T07:37:07.695Z

# UAT — S03 Fast/default and deep verification lanes

## Preconditions
- Worktree is at the completed M012/S03 state.
- Python dependencies, Node dependencies, Playwright browsers, and the standalone build tools in `tools/` are installed.
- Run from the repo root: `/home/chris/projects/sentinelx`.

## Test Case 1 — Routine contributor proof uses the fast lane
1. Run `make verify-fast`.
2. Confirm the command runs four stages in order: non-E2E pytest, Vitest, TypeScript typecheck, and the production build.
3. Expected outcome:
   - The command exits 0.
   - Backend output reports the non-E2E suite only (`952 passed, 113 deselected` on the current slice baseline).
   - Vitest passes all frontend unit tests.
   - TypeScript exits cleanly.
   - Tailwind and esbuild complete the production asset build.
4. Edge check: no browser/E2E suite should start from this command.

## Test Case 2 — Live/results-surface work escalates to the deep lane
1. Run `make verify-deep`.
2. Expected outcome:
   - The command exits 0.
   - `tests/e2e` runs and passes (`113 passed` on the current slice baseline).
   - The output is direct pytest/browser evidence only, with no late interpreter-shutdown or `ThreadPoolExecutor` noise.
3. Edge check: failures in mocked-online flows should point to a browser assertion or route/fixture contract break, not to uncontrolled background enrichment teardown.

## Test Case 3 — Mocked-online browser flows stay deterministic
1. Run `python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_url_e2e.py`.
2. Expected outcome:
   - The focused online/offline results-surface suite passes.
   - The online helpers assert `.page-results[data-results-owner="live"]` and the deterministic `data-job-id` before waiting for `.ioc-summary-row`.
   - No real background enrichment job is required for the mocked-online tests to pass.
3. Edge check: if the E2E fixture seam regresses, the failure should surface immediately as a missing/incorrect `data-job-id` or ownership assertion instead of as shutdown noise after the test body finishes.

## Test Case 4 — Contributor guidance matches the command surface
1. Open `README.md` and inspect the "Verification lanes" section.
2. Open `Makefile` and inspect the `verify-fast`, `verify-deep`, and `verify` targets.
3. Expected outcome:
   - README names the same literal targets that exist in `Makefile`.
   - README tells contributors to stop at `make verify-fast` for routine work and escalate to `make verify-deep`/`make verify` for live enrichment, results rendering, polling/status, or mocked-online browser changes.
   - `make verify` composes the fast and deep lanes in that order.

## Pass/Fail Rule
- Pass if all four test cases succeed.
- Fail if the default lane is ambiguous, the deep lane launches uncontrolled background enrichment, or README/Makefile drift from the documented proof split.
