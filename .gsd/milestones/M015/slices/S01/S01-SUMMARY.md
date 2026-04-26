---
id: S01
parent: M015
milestone: M015
provides:
  - Stable command-card intake layout and selector contract for S02 mode clarification.
  - Primary command-card/future-secondary layout foundation for S03 Recent Analyses.
  - Fresh proof that the default offline paste-to-results path still works.
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - app/templates/index.html
  - tests/test_index_intake_contract.py
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_homepage.py
  - .gsd/PROJECT.md
key_decisions:
  - Preserved all stable form-control selectors and POST `/analyze` route behavior while layering command-card redesign through wrapper markup and CSS.
  - Kept S01 scope free of pre-submit preview, history reads, provider calls, client-side persistence, and mode semantic redesign.
patterns_established:
  - Use `.page-index`, `.intake-workbench`, and `.command-card` as the stable M015 intake layout shell.
  - Pin server-rendered form contracts with focused Flask tests before layering Playwright/browser style proof.
  - Regenerate `app/static/dist/*` through `make build`; do not hand-edit generated assets.
observability_surfaces:
  - No new runtime observability surface was introduced; health/failure visibility is via focused route tests, Playwright checks, TypeScript/build checks, and existing app errors.
drill_down_paths:
  - .gsd/milestones/M015/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-26T08:45:59.331Z
blocker_discovered: false
---

# S01: Fast intake command surface

**Redesigned `/` into a dominant command-card intake surface while preserving the stable paste → offline Extract → results contract.**

## What Happened

S01 established the Intake Workbench foundation without changing extraction behavior. T01 first pinned the index route with a Flask-client HTML contract test, then restructured `app/templates/index.html` around `.page-index`, `.intake-workbench`, and `.command-card` wrappers. The template keeps the existing POST `/analyze` form, CSRF token, `#ioc-text`, disabled initial `#submit-btn`, `#clear-btn`, hidden offline `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, paste feedback span, textarea naming, and error alert behavior intact. The contract also explicitly prevents S01 scope creep by asserting that no Recent Analyses rail or pre-submit preview UI appears yet.

T02 turned that stable DOM into the visible command surface: `app/static/src/input.css` now gives the intake page a centered workbench, elevated command card, stronger heading/copy hierarchy, larger textarea well, tactile actions, and responsive mobile stacking. Generated frontend assets were refreshed through `make build` rather than manual edits. The Playwright page object now exposes the new workbench/card locators while preserving the form-control locators downstream slices depend on, and homepage E2E coverage now checks command-card visibility, desktop/mobile hierarchy, disabled/enabled Extract behavior, absence of preview/recent surfaces, and real offline extraction navigation.

No new history reads, provider calls, client-side IOC parsing, persistence, or network dependencies were introduced. The slice advances the M015 front-door redesign while leaving S02's mode clarity, S03's recent-analysis rail, and S04's integrated proof as separate follow-on work.

## Verification

Fresh slice-close verification passed after implementation:

- `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_analyze_empty_input tests/test_routes.py::test_analyze_whitespace_only_input tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present` → 6 passed in 0.23s.
- `make build` → Tailwind rebuilt `app/static/dist/style.css` and esbuild rebuilt `app/static/dist/main.js` successfully.
- `npx tsc --noEmit` → exit code 0.
- `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` → 18 passed in 2.39s.

Together these checks prove the GET `/` command-card DOM contract, CSRF/form action preservation, empty-input error handling, offline no-HTTP behavior, security headers, generated asset consistency, TypeScript validity, desktop/mobile command-card visibility, submit enablement after IOC input, and a real browser offline paste-to-results path.

## Requirements Advanced

- R070 — The home page now has a dominant command-card paste-and-submit surface with browser proof for submit enablement and offline extraction.
- R071 — The stable paste → default Offline mode → Extract → results flow was preserved and re-proven through route and Playwright tests.
- R075 — The command-card responsive foundation now exists on desktop/mobile; the compact recent rail portion remains for S03/S04.
- R076 — S01 re-proved CSRF/security headers, offline no-HTTP behavior, TypeScript, generated assets, and focused E2E behavior for the touched surfaces.

## Requirements Validated

- R013 — The input/home page now matches the M015 command-card design direction and passed focused contract, build, TypeScript, and Playwright verification.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None. The slice stayed within the planned command-card DOM/CSS/test scope and did not add history, preview, provider, persistence, or route behavior.

## Known Limitations

S02 still needs to clarify the Offline/Online mode presentation and keyboard/accessibility polish. S03 still needs to add the compact Recent Analyses rail/list and prove history listing failures do not block intake. S04 still needs to verify the assembled workbench across desktop/mobile, history resume, and full regression lanes. Existing CSP console warnings for inline style attributes were observed during T01 browser diagnostics but did not block S01 and were outside this conservative redesign scope.

## Follow-ups

Proceed with S02 using the stable command-card shell and preserved hidden `mode` input contract. Proceed with S03 by adding Recent Analyses only as a secondary, failure-tolerant surface that cannot block the command card.

## Files Created/Modified

- `app/templates/index.html` — Added the command-card/workbench structure while preserving the existing IOC form contract.
- `tests/test_index_intake_contract.py` — Added focused Flask HTML contract tests for the redesigned index form and S01 scope boundaries.
- `app/static/src/input.css` — Styled the command-card intake surface and responsive workbench hierarchy.
- `app/static/dist/style.css` — Regenerated built CSS from Tailwind source.
- `app/static/dist/main.js` — Regenerated browser bundle via the standard build pipeline.
- `tests/e2e/pages/index_page.py` — Added command-card/workbench locators while preserving stable form-control locators.
- `tests/e2e/test_homepage.py` — Added Playwright coverage for command-card visibility, responsive hierarchy, submit state, S01 scope boundaries, and offline extraction navigation.
- `.gsd/PROJECT.md` — Refreshed project state to record that M015/S01 is complete and identify remaining M015 work.
