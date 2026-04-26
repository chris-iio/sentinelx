---
estimated_steps: 8
estimated_files: 5
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
  - verify-before-complete
---

# T02: Style and prove the responsive command-card fast path

Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's stable DOM to make the command card visually dominant, update browser tests/POM locators for the new workbench shape, and prove the live offline extraction path still works.

Quality gates — Failure Modes: if the Tailwind/CSS build tool is missing or fails, stop with the build error and do not hand-edit `app/static/dist/style.css`; if Playwright cannot find the command card or form controls, treat it as a DOM/regression failure rather than weakening selectors; if submit enablement or extraction navigation breaks, diagnose `form.ts` selector compatibility before changing route logic. Load Profile: style-only runtime cost should remain static CSS plus the existing `form.ts` event listeners; no new fetches, timers beyond existing paste feedback, DB reads, or history-store calls are allowed. Negative Tests: cover empty initial submit-disabled state, enabled Extract after synthetic paste/fill, desktop and mobile command-card visibility, and a real offline submit reaching results with no provider dependency.

Steps:
1. Update `app/static/src/input.css` so `.page-index`, `.intake-workbench`, `.command-card`, command-card header/copy, textarea area, and form actions create a clear primary command surface with responsive stacking at mobile widths; keep existing component-class ownership conventions and avoid Tailwind utility conflicts on existing component classes.
2. Run `make build` after CSS changes so `app/static/dist/style.css` reflects the source stylesheet; do not edit generated CSS manually except through the build.
3. Update `tests/e2e/pages/index_page.py` with command-card/workbench locators while keeping existing form-control locators unchanged for downstream tests.
4. Extend `tests/e2e/test_homepage.py` with browser assertions for command-card visibility, desktop/mobile responsive hierarchy, default disabled Extract, Extract enabling after text entry, and absence of pre-submit preview/recent rail content in S01.
5. Re-run the focused E2E home/extraction proof plus TypeScript/build checks, fixing only S01 regressions and leaving S02/S03 scope untouched.

## Inputs

- `app/templates/index.html`
- `app/static/src/input.css`
- `app/static/src/ts/modules/form.ts`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`
- `tests/e2e/test_extraction.py`

## Expected Output

- `app/static/src/input.css`
- `app/static/dist/style.css`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`

## Verification

make build
npx tsc --noEmit
python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline

## Observability Impact

- Signals added/changed: Playwright assertions for desktop/mobile command-card visibility, submit state transitions, no preview/recent content, and offline results navigation.
- How a future agent inspects this: run `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline`; failures identify whether the break is layout, form state, or extraction navigation.
- Failure state exposed: responsive or selector regressions surface as targeted Playwright expectation failures against `.intake-workbench`, `.command-card`, and existing form IDs.
