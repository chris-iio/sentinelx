---
id: S03
parent: M012
milestone: M012
provides:
  - An explicit fast/default verification lane future optimization slices can use without paying the browser-test cost every time.
  - A deterministic mocked-online browser seam future UI/enrichment work can reuse for real Flask + browser proof without launching uncontrolled background jobs.
  - Contributor documentation that explains when deeper proof is mandatory for live enrichment and results-surface changes.
requires:
  - slice: S01
    provides: stable live status semantics and `.page-results[data-results-owner]` ownership contract that browser helpers can assert.
  - slice: S02
    provides: shared live/history result-application path whose browser-visible contract remains worth protecting with the deep lane.
affects:
  - S04
key_files:
  - Makefile
  - README.md
  - tests/e2e/conftest.py
  - tests/e2e/test_results_page.py
  - tests/e2e/test_url_e2e.py
key_decisions:
  - Preserve the repo-native Makefile verification surface and README wording instead of introducing wrapper scripts or alternate command names.
  - Patch `app.routes.analysis._setup_orchestrator` only inside the E2E live-server fixture so production orchestration remains untouched while mocked-online tests stay deterministic.
  - Make the mocked-online seam browser-visible by asserting `.page-results[data-results-owner]` and deterministic `data-job-id` values in the shared online navigation helpers.
patterns_established:
  - Use `make verify-fast` for routine work, `make verify-deep` for browser/live enrichment/results-surface changes, and `make verify` for the combined handoff proof command.
  - Keep mocked-online E2E determinism at the fixture boundary: arm the Playwright route mock before submit, queue a deterministic fake job id, and bypass background submission only in the E2E live-server seam.
  - Assert the rendered server/browser contract (`data-results-owner`, `data-job-id`) before waiting on JS-driven enrichment rows so regressions fail where the seam breaks.
observability_surfaces:
  - `make verify-fast` and `make verify-deep` are now the explicit contributor-facing health checks for this seam.
  - The `.page-results[data-results-owner][data-job-id]` DOM contract gives browser tests a direct observable signal that the deterministic mocked-online seam is active.
  - Deep-lane failures now resolve to direct pytest/Playwright assertion output instead of ambiguous interpreter-shutdown executor traces.
drill_down_paths:
  - .gsd/milestones/M012/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-22T07:37:07.695Z
blocker_discovered: false
---

# S03: Fast default proof loop and deterministic expensive lane

**Verified the repo-native fast/deep proof lanes and made mocked-online browser tests deterministic so contributors can escalate from `make verify-fast` to `make verify-deep` without launching real enrichment work.**

## What Happened

S03 closed the developer-verification seam by making the expected proof lanes explicit and trustworthy. On the fast/default side, the slice confirmed that the existing repo-native command surface already matched the plan: `make verify-fast` runs non-E2E pytest, Vitest, TypeScript typecheck, and the production build, while `README.md` explains when contributors can stop there versus when they must escalate. No Makefile/README rewrite was needed; the slice outcome was to validate and preserve that literal command surface instead of introducing wrapper scripts or alternate names.

On the deep/browser side, the slice hardened the mocked-online E2E seam in `tests/e2e/conftest.py` by patching `app.routes.analysis._setup_orchestrator` only inside the live-server fixture. When a test arms `setup_enrichment_route_mock()`, the fixture now consumes a deterministic fake job id, keeps the real Flask form POST + CSRF + security-header path intact, and prevents the app from launching uncontrolled background enrichment work. The shared online navigation helpers in `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` now assert `.page-results[data-results-owner="live"]` plus the expected deterministic `data-job-id` before waiting for enrichment rows, so regressions fail as direct browser assertions instead of surfacing later as interpreter-shutdown executor noise.

The net result is a slice that did not optimize production runtime behavior directly, but materially improved decision-quality for future optimization work: contributors now have an explicit fast lane for routine changes, a distinct deeper browser lane for live/results-surface work, and deterministic mocked-online coverage that keeps expensive-lane failures attributable to the browser contract under test.

## Verification

Fresh slice verification was run after reviewing the assembled work:

- `make verify-fast` ✅ passed in 6.7s
  - `python3 -m pytest -q -m 'not e2e'` → `952 passed, 113 deselected in 3.11s`
  - `npx vitest run` → `6 passed files, 78 passed tests`
  - `npx tsc --noEmit` → exit 0
  - `make build` → Tailwind + esbuild production bundle completed successfully
- `make verify-deep` ✅ passed in 36.5s
  - `python3 -m pytest -q tests/e2e` → `113 passed in 36.72s`

The deep lane completed cleanly with direct pytest output only; no interpreter-shutdown / background-executor noise appeared, which is the behavioral failure mode this slice was meant to eliminate from mocked-online browser coverage.

## Requirements Advanced

None.

## Requirements Validated

- R040 — Fresh slice verification passed: `make verify-fast` completed with 952 non-E2E backend tests, 78 Vitest tests, clean TypeScript, and a successful production build; `make verify-deep` then passed 113 E2E tests with deterministic mocked-online coverage.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

T01 required no source edits because the repo already had the planned `make verify-fast` / `make verify-deep` / `make verify` surface and matching README guidance. The slice therefore delivered verification and seam hardening, not a command-surface rewrite.

## Known Limitations

The deep lane still depends on the local Playwright/browser toolchain being installed, and deterministic behavior is guaranteed only for tests that arm the mocked-online seam through `setup_enrichment_route_mock()`. The slice does not add timing dashboards or persistent metrics beyond command output and browser-test assertions.

## Follow-ups

S04 can rely on `make verify-fast` as the default optimization proof loop and only escalate to `make verify-deep` when touching browser/live results behavior. If future work adds new mocked-online E2E helpers, keep them on the same deterministic fake-job-id seam instead of reintroducing production-route changes or uncontrolled background work.

## Files Created/Modified

- `tests/e2e/conftest.py` — Added the E2E-only `_setup_orchestrator` patch and deterministic fake job-id queue used by mocked-online browser tests.
- `tests/e2e/test_results_page.py` — Shared online navigation helper now asserts `data-results-owner` and deterministic `data-job-id` before waiting for enrichment rows.
- `tests/e2e/test_url_e2e.py` — URL mocked-online helper now asserts the same rendered job ownership/job-id contract for deterministic browser verification.
