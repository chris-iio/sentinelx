# S01: Fast intake command surface

**Goal:** Redesign the `/` page into a dominant analyst command-card intake surface while preserving the existing paste → Offline mode → Extract → results behavior and the stable form-control contract consumed by later slices.
**Demo:** The home page has a redesigned command-card layout where the analyst can paste IOC text, see Extract enable, and submit offline exactly as before.

## Must-Haves

- `R013`: The input/home page adopts the milestone design language with a visible command-card structure instead of the current sparse textarea-only composition.
- `R070`: The paste textarea and Extract action are the dominant surface on first load; any supporting copy or containers reinforce fast intake rather than adding a preview or dashboard.
- `R071`: The existing form contract remains intact: `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, and `#mode-toggle-btn` still submit to `/analyze` with `mode=offline` by default.
- `R075`: The command-card layout has a responsive foundation for desktop and mobile, with the command surface staying primary and a future secondary rail area not crowding the form.
- **Threat surface:** user-supplied IOC text still enters only through the existing POST form with CSRF protection and server-side empty-input checks; S01 must not add pre-submit parsing, client-side persistence, history reads, new network calls, or provider/enrichment behavior.
- **Data exposure:** no new storage or logging of pasted IOC text; test fixtures may contain sample IOCs, but runtime UI must not expose secrets, tokens, provider keys, or history data on `/` in this slice.
- **Input trust:** `#ioc-text` remains untrusted input handled by the existing `/analyze` route; whitespace/empty submissions continue to show `.alert-error`, and offline submissions continue to make zero outbound HTTP calls.
- **Requirement impact:** touches `R013`, `R070`, `R071`, and `R075`; supports the later `R076` integrated proof by re-verifying CSRF/security headers, offline no-HTTP behavior, and a real browser offline extraction path.
- **Re-verify:** GET `/` HTML contract, CSRF token presence, submit enabled/disabled behavior, default offline hidden mode, empty-input error rendering, offline no-HTTP route behavior, desktop/mobile command-card visibility, and Playwright paste-to-results.
- **Decisions revisited:** keep `D071` command-card + compact rail direction, preserve `D072` hidden mode contract, and honor `D073` by excluding pre-submit preview/provider/history redesign from this slice.

## Proof Level

- This slice proves: contract + browser integration for the redesigned index command surface and offline submission fast path.
- Real runtime required: yes — Playwright must exercise the live Flask app from `/` through an offline extraction result.
- Human/UAT required: no — objective HTML, CSS build, TypeScript, and browser assertions are sufficient for S01.

## Integration Closure

- Upstream surfaces consumed: `app/routes/analysis.py`, `app/templates/base.html`, `app/templates/index.html`, `app/static/src/ts/modules/form.ts`, `app/static/src/input.css`, `app/static/dist/style.css`, `tests/e2e/pages/index_page.py`, and the existing route/E2E proof surface.
- New wiring introduced in this slice: command-card and workbench wrapper markup in `index.html`, responsive CSS classes for the command surface/future secondary region, and focused tests that pin the form-control selectors for S02/S03/S04.
- What remains before the milestone is truly usable end-to-end: S02 still clarifies mode presentation, S03 still wires compact Recent Analyses data/links/failure handling, and S04 still proves the assembled workbench across desktop/mobile and full regression lanes.

## Verification

- Runtime signals: stable DOM selectors/classes (`#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, `.page-index`, `.intake-workbench`, `.command-card`), submit disabled/enabled state, `.alert-error`, and results-page mode/count assertions.
- Inspection surfaces: Flask client HTML contract tests, Playwright index/extraction tests, `npx tsc --noEmit`, and `make build` for generated asset consistency.
- Failure visibility: missing selector, broken CSRF/form action, submit-state regression, responsive layout regression, or failed offline extraction is localized by focused test names before the broader milestone proof.
- Redaction constraints: do not log real IOC paste contents, provider keys, tokens, or analyst history; browser and route tests should use synthetic fixture IOCs only.

## Tasks

- [x] **T01: Restructure the index template into a tested command card** `est:0.5d`
  Load the `tdd`, `frontend-design`, `accessibility`, and `verify-before-complete` skills before editing. Convert the existing index template into the S01 command-card DOM while writing a focused HTML contract test first so later slices can rely on stable selectors without inheriting the full roadmap context.

Quality gates — Failure Modes: if Flask/Jinja rendering fails, GET `/` must fail the focused contract test rather than being masked by browser-only checks; if the CSRF macro or form action changes, the test must catch the missing hidden token or wrong `/analyze` target; if selector churn breaks `form.ts`, the test must fail on the missing IDs before E2E runs. Load Profile: this task adds no database/API calls and keeps GET `/` a single server-rendered page; 10x traffic should not introduce a new shared resource because no history/provider dependency is added in S01. Negative Tests: preserve empty/whitespace server-side error behavior via existing route tests, preserve offline no-HTTP behavior, assert that `/` still does not render Recent Analyses or pre-submit preview UI in this slice.

Steps:
1. Add `tests/test_index_intake_contract.py` with Flask client assertions for GET `/`: `.page-index`, `.intake-workbench`, `.command-card`, `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input` defaulting to `offline`, `#mode-toggle-widget`, `#mode-toggle-btn`, and hidden `csrf_token` are present, while pre-submit preview/recent-analysis markup is absent.
2. Update `app/templates/index.html` to wrap the existing form in a command-card/workbench structure with concise analyst-oriented heading/help text, keeping all existing IDs, `name="text"`, `name="mode"`, form method/action, textarea `rows="5"`, `aria-label`, paste feedback span, disabled Extract button, and error alert behavior intact.
3. Keep the Offline/Online toggle semantics visually and structurally conservative for S01: no hidden mode contract change, no keyboard/ARIA redesign beyond preserving current `aria-pressed`, and no data dependency for history.
4. Run the focused route/contract tests and fix any mismatch before handing T02 a stable DOM to style.
  - Files: `app/templates/index.html`, `tests/test_index_intake_contract.py`, `tests/test_routes.py`
  - Verify: python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_analyze_empty_input tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present

- [ ] **T02: Style and prove the responsive command-card fast path** `est:0.75d`
  Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's stable DOM to make the command card visually dominant, update browser tests/POM locators for the new workbench shape, and prove the live offline extraction path still works.

Quality gates — Failure Modes: if the Tailwind/CSS build tool is missing or fails, stop with the build error and do not hand-edit `app/static/dist/style.css`; if Playwright cannot find the command card or form controls, treat it as a DOM/regression failure rather than weakening selectors; if submit enablement or extraction navigation breaks, diagnose `form.ts` selector compatibility before changing route logic. Load Profile: style-only runtime cost should remain static CSS plus the existing `form.ts` event listeners; no new fetches, timers beyond existing paste feedback, DB reads, or history-store calls are allowed. Negative Tests: cover empty initial submit-disabled state, enabled Extract after synthetic paste/fill, desktop and mobile command-card visibility, and a real offline submit reaching results with no provider dependency.

Steps:
1. Update `app/static/src/input.css` so `.page-index`, `.intake-workbench`, `.command-card`, command-card header/copy, textarea area, and form actions create a clear primary command surface with responsive stacking at mobile widths; keep existing component-class ownership conventions and avoid Tailwind utility conflicts on existing component classes.
2. Run `make build` after CSS changes so `app/static/dist/style.css` reflects the source stylesheet; do not edit generated CSS manually except through the build.
3. Update `tests/e2e/pages/index_page.py` with command-card/workbench locators while keeping existing form-control locators unchanged for downstream tests.
4. Extend `tests/e2e/test_homepage.py` with browser assertions for command-card visibility, desktop/mobile responsive hierarchy, default disabled Extract, Extract enabling after text entry, and absence of pre-submit preview/recent rail content in S01.
5. Re-run the focused E2E home/extraction proof plus TypeScript/build checks, fixing only S01 regressions and leaving S02/S03 scope untouched.
  - Files: `app/static/src/input.css`, `app/static/dist/style.css`, `tests/e2e/pages/index_page.py`, `tests/e2e/test_homepage.py`, `tests/e2e/test_extraction.py`
  - Verify: make build
npx tsc --noEmit
python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline

## Files Likely Touched

- app/templates/index.html
- tests/test_index_intake_contract.py
- tests/test_routes.py
- app/static/src/input.css
- app/static/dist/style.css
- tests/e2e/pages/index_page.py
- tests/e2e/test_homepage.py
- tests/e2e/test_extraction.py
