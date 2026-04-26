---
estimated_steps: 9
estimated_files: 6
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
  - verify-before-complete
---

# T02: Style the compact rail and prove browser resume links without crowding intake

Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's server-rendered contract to make the Recent Analyses surface compact, secondary, keyboard/link accessible, and responsive, then seed deterministic live-server history in E2E so browser tests prove row visibility, `/history/<id>` linking, failure-free intake rendering, and unchanged offline extraction.

Quality gates — Failure Modes: if E2E cannot seed a live-server history row, fix the test fixture seam rather than relying on a developer's real `~/.sentinelx/history.db`; if generated CSS/JS are stale, regenerate through `make build` and do not hand-edit `app/static/dist/*`; if the rail reduces the command card below a dominant width or appears above the paste form on mobile, browser geometry assertions must fail. Load Profile: the rail renders at most the bounded rows T01 supplies, uses no client polling/fetch/storage, and adds only constant-time DOM/CSS work in the browser; 10x history volume should not increase index render beyond the route limit. Negative Tests: browser proof must cover seeded history row link href, no recent rows when empty/unavailable state is present, desktop secondary hierarchy, mobile stacking below the command card, submit enablement after IOC input, and offline paste-to-results navigation.

Steps:
1. Update `app/static/src/input.css` so `.intake-workbench` becomes a desktop command-card-plus-rail layout with the command card dominant, `.recent-analyses-rail` visually secondary, compact recent rows reusing or extending existing history row classes, and mobile stacking that places history below the paste command card without horizontal overflow.
2. Run `make build` after CSS changes so `app/static/dist/style.css` (and any generated bundle if the build touches it) reflects source changes.
3. Extend `tests/e2e/pages/index_page.py` with locators/helpers for `.recent-analyses-rail`, `.recent-analysis-row`, recent empty/unavailable states, and a helper that asserts the command card remains before/dominant over the recent rail.
4. Update `tests/e2e/conftest.py` to isolate the live server's `HistoryStore` to a temp database and expose a deterministic seeding helper for homepage E2E tests; keep existing config-store isolation and mocked-online behavior intact.
5. Extend `tests/e2e/test_homepage.py`: replace the stale “no recent rail” assertion with tests proving seeded recent analyses render as links to `/history/<id>`, desktop rail is secondary to the command card, mobile history stacks below the command card, empty/unavailable states do not block form visibility, and the existing offline submit E2E still reaches results.
6. Run the focused build/typecheck/browser command set and fix layout, fixture, or selector regressions without weakening T01's route contract.

## Inputs

- `app/routes/analysis.py`
- `app/templates/index.html`
- `app/static/src/input.css`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_homepage.py`
- `tests/e2e/test_extraction.py`

## Expected Output

- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_homepage.py`

## Verification

make build
npx tsc --noEmit
python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline

## Observability Impact

- Signals added/changed: browser-visible recent rail, row, empty, and unavailable selectors plus Playwright geometry/link assertions that identify whether layout or data seeding failed.
- How a future agent inspects this: run focused homepage E2E tests or inspect the seeded row/link locators in `tests/e2e/pages/index_page.py`.
- Failure state exposed: layout crowding, missing history links, stale generated CSS, real-history fixture leakage, and offline-submit regressions fail with localized browser test names.
