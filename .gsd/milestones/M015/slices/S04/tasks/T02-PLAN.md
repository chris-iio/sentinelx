---
estimated_steps: 8
estimated_files: 7
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
  - verify-before-complete
---

# T02: Add final browser assembly proof and responsive polish

Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's route contract by proving the assembled workbench in a live browser at desktop and mobile sizes, including seeded history resume and the real Offline paste-to-results path. Prefer test/page-object additions first; touch CSS or generated assets only for concrete responsive/polish regressions exposed by the browser assertions.

Quality gates — Failure Modes: if seeded history cannot be created, fix the E2E fixture seam rather than relying on a developer-local `~/.sentinelx/history.db`; if history lookup is unavailable, the browser must still see the form and enabled Extract after text entry; if a recent row link is broken, the click must fail before slice close; if generated assets are stale after CSS/TS fixes, regenerate with `make build` rather than hand-editing `app/static/dist/*`. Load Profile: browser proof should use one or a few deterministic seeded rows, no client polling/fetch/storage, no external provider calls for Offline mode, and no extra runtime beyond existing live-server fixtures. Negative Tests: E2E must cover desktop secondary hierarchy, mobile stacking without horizontal overflow, empty/unavailable recent states, stable mode state, history resume link navigation, and real Offline extraction results.

Steps:
1. Extend `tests/e2e/pages/index_page.py` with any missing high-level helper(s) needed to assert the integrated workbench is ready: command card visible, mode state synchronized, recent rail visible/secondary, row href present, mobile rail below the command card, and no preview surfaces.
2. Add final assembly tests in `tests/e2e/test_homepage.py` that seed deterministic history, assert desktop command-card dominance with the recent rail present, assert mobile stacking/no overflow with the same assembled UI, click a recent row to prove `/history/<id>` resume, and re-prove Offline paste-to-results from the final layout.
3. Preserve or strengthen existing empty/unavailable recent-history tests so they prove the form remains usable and `#submit-btn` enables after IOC text even when history is absent or failing.
4. If assertions reveal composition polish issues, adjust `app/static/src/input.css` only as needed to keep the command card dominant, the rail compact/secondary, focus states visible, and mobile layout overflow-free; then run `make build` to refresh `app/static/dist/style.css` and `app/static/dist/main.js`.
5. Run the focused browser command, then the full browser lane; fix selector, fixture, CSS, or generated-asset regressions without weakening T01's route contract.

## Inputs

- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`
- `tests/e2e/test_extraction.py`
- `tests/e2e/test_ui_controls.py`
- `tests/e2e/conftest.py`
- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`

## Expected Output

- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`
- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`

## Verification

python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_ui_controls.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline && make verify-fast && python3 -m pytest -q tests/e2e

## Observability Impact

Signals added/changed: Playwright assertions become the final diagnostic surface for desktop/mobile layout, form readiness, mode synchronization, recent-history states, history resume, and Offline extraction.
How a future agent inspects this: run `python3 -m pytest -q tests/e2e/test_homepage.py` for focused homepage assembly failures, or `python3 -m pytest -q tests/e2e` for the full browser lane.
Failure state exposed: command-card crowding, mobile overflow, missing/incorrect recent hrefs, unusable form after history failure, stale generated assets, and broken paste-to-results navigation fail explicit browser assertions.
