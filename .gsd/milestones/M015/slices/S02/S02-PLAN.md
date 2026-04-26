# S02: Mode clarity without semantic churn

**Goal:** Clarify the Offline/Online mode control in the S01 command-card intake surface while preserving the existing hidden `mode` input contract, `/analyze` submit behavior, and paste-to-results flow.
**Demo:** Offline/Online mode is visually clearer and keyboard-accessible while preserving the existing hidden `mode` form contract and current submit behavior.

## Must-Haves

- `R072`: Offline and Online choices are visually and textually clearer than the S01 baseline, with explicit default/offline safety copy and online enrichment/provider intent visible before submit.
- `R072`: The stable form contract remains unchanged: `#mode-input` is still a hidden `name="mode"` input defaulting to `offline`, `#mode-toggle-widget` and `#mode-toggle-btn` remain present, and POST `/analyze` still receives `mode=offline` or `mode=online` from the hidden input.
- `R072`: The mode control is keyboard-accessible and screen-reader inspectable: the toggle button remains a real `<button>`, exposes mode state through ARIA, references visible descriptive copy/status, and updates its state/copy when toggled.
- `R071`: The primary flow remains paste → default Offline mode → Extract → results, and online selection still submits through the current online path without changing route semantics.
- **Threat surface:** user-supplied IOC text and the client-controlled hidden `mode` value remain untrusted POST form inputs. S02 must not add pre-submit parsing, client-side storage, provider calls, history reads, or a new API surface on `/`.
- **Abuse:** mode tampering is still limited to the existing `offline`/`online` branch behavior in `app/routes/analysis.py`; this slice should not invent client-only security guarantees or weaken CSRF/rate-limit coverage.
- **Data exposure:** mode copy and tests may mention provider/enrichment behavior, but must not expose API keys, secrets, stored history rows, or pasted IOC text outside the existing form/results flow.
- **Input trust:** IOC textarea content remains handled only by the existing submit route; offline mode must continue making zero outbound HTTP calls, and online mode must continue requiring configured providers.
- **Requirement impact:** touches `R072` directly and supports `R071`; it also preserves the S01 proof for `R013` and sets up S04's final `R076` regression proof.
- **Re-verify:** GET `/` HTML contract, hidden mode input default/value, mode control ARIA/descriptive copy, click and keyboard toggling, submit button enablement after paste/fill, offline no-HTTP route behavior, online no-provider redirect route behavior, generated asset consistency, TypeScript validity, and browser offline/online extraction mode indicators.
- **Decisions revisited:** keep `D072` by preserving hidden-input semantics; keep `D071` command-card layout from S01; keep `D073` exclusions by avoiding pre-submit preview, provider/enrichment rewrites, heavy dashboarding, or history additions.

## Proof Level

- This slice proves: - This slice proves: contract + browser integration for clarified mode selection inside the intake command card.
- Real runtime required: yes — Playwright must exercise the live Flask app to prove keyboard/click mode toggling and offline/online submit behavior.
- Human/UAT required: no — route, Vitest, TypeScript/build, and Playwright assertions are sufficient for S02.

## Integration Closure

- Upstream surfaces consumed: S01's `app/templates/index.html` command-card shell and stable controls (`#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`), `app/static/src/ts/modules/form.ts`, `app/static/src/input.css`, `tests/test_index_intake_contract.py`, `tests/e2e/pages/index_page.py`, and existing route/E2E mode behavior.
- New wiring introduced in this slice: clearer mode-description/status markup in `index.html`, synchronized ARIA/status updates in `form.ts`, visual mode treatment in `input.css`, a focused form-module Vitest test, and Playwright checks for keyboard/click mode selection.
- What remains before the milestone is truly usable end-to-end: S03 still adds the compact Recent Analyses rail/list and failure-tolerant history loading; S04 still proves the assembled intake workbench across desktop/mobile, history resume, and full regression lanes.

## Verification

- Runtime signals: stable DOM state on `#mode-input`, `#mode-toggle-widget[data-mode]`, `#mode-toggle-btn` ARIA attributes, visible/descriptive mode status text, submit button classes, and results-page `.mode-indicator` after submit.
- Inspection surfaces: Flask HTML contract tests, `app/static/src/ts/modules/form.test.ts`, focused Playwright tests in `tests/e2e/test_ui_controls.py` and `tests/e2e/test_extraction.py`, `npx tsc --noEmit`, and `make build`.
- Failure visibility: missing/renamed mode selectors fail in route tests; state-sync regressions fail in Vitest; keyboard/accessibility and live submit regressions fail in Playwright with localized test names.
- Redaction constraints: tests must use synthetic IOC fixtures only and must not log provider keys, secrets, analyst history, or real pasted content.

## Tasks

- [x] **T01: Pin clarified mode contract and copy in the index template** `est:0.5d`
  Load the `tdd`, `accessibility`, and `verify-before-complete` skills before editing. Start from S01's command-card shell and make the Offline/Online choice clearer at the server-rendered contract level before touching client behavior: add explicit visible mode heading/help/status copy and ARIA wiring while preserving the hidden `mode` input, existing IDs, form action, CSRF token, and default `offline` value.

Quality gates — Failure Modes: if Jinja rendering, CSRF output, or selector preservation regresses, `tests/test_index_intake_contract.py` must fail before browser tests; if the clarified copy removes or renames `#mode-input`, `#mode-toggle-widget`, or `#mode-toggle-btn`, downstream TypeScript and Playwright selectors are considered broken and should not be worked around. Load Profile: GET `/` remains a single server-rendered page with no DB, history, provider, fetch, or polling dependency; 10x traffic should see no new shared resource from S02 markup. Negative Tests: route proof must keep offline no-HTTP behavior and online no-provider redirect behavior intact, and the index contract must continue excluding Recent Analyses and pre-submit preview UI.

Steps:
1. Extend `tests/test_index_intake_contract.py` first so GET `/` asserts the clarified mode contract: visible Offline/Online labels, explicit default/offline safety copy, an online enrichment/provider cue, `#mode-input` as hidden `name="mode" value="offline"`, `#mode-toggle-widget[data-mode="offline"]`, and `#mode-toggle-btn` as `type="button"` with preserved `aria-pressed="false"` plus descriptive ARIA wiring.
2. Update `app/templates/index.html` to add concise mode-title/help/status markup inside `.mode-toggle` without changing `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, hidden CSRF, hidden `#mode-input`, or POST `/analyze` behavior.
3. Keep the mode UI semantically additive: adding `role="switch"`, `aria-checked`, `aria-describedby`, or live status text is allowed, but removing the existing button/hidden-input contract is not.
4. Run the focused route tests and fix only contract/markup issues before handing T02 the stable markup to style and synchronize from TypeScript.
  - Files: `app/templates/index.html`, `tests/test_index_intake_contract.py`, `tests/test_routes.py`
  - Verify: python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings

- [ ] **T02: Synchronize mode state across TypeScript, styling, and browser proof** `est:0.75d`
  Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's additive mode markup so click and keyboard interactions keep the hidden input, widget `data-mode`, ARIA state, visible status copy, and Extract button styling in sync, then regenerate assets and prove both offline and online submit behavior still use the current route semantics.

Quality gates — Failure Modes: if `form.ts` cannot find T01's markup, fail fast with a Vitest or Playwright selector/state assertion rather than weakening IDs; if `make build` fails, do not hand-edit `app/static/dist/style.css` or `app/static/dist/main.js`; if online submit behavior redirects because providers are unconfigured, preserve the existing route behavior and use the repository's existing mocked/provider E2E fixtures rather than changing production routes. Load Profile: S02 may add constant-time DOM text/attribute updates to the existing toggle listener only; it must add no network calls, storage, intervals, history reads, or provider initialization on `/`. Negative Tests: cover initial offline default, click toggle to online/back offline, keyboard Space/Enter toggle behavior, hidden-input value synchronization, ARIA/status synchronization, disabled/enabled Extract behavior, offline no-HTTP behavior, and online mode result indication through existing E2E fixtures.

Steps:
1. Add `app/static/src/ts/modules/form.test.ts` with jsdom/Vitest coverage for `init()` on the index form: initial offline state, click toggling to online/back offline, hidden `#mode-input` value updates, `#mode-toggle-widget[data-mode]`, `aria-pressed`, `aria-checked` if present, status/descriptive text updates, and submit button mode class preservation.
2. Update `app/static/src/ts/modules/form.ts` to centralize mode-state rendering so initial load and every toggle update hidden input value, widget data attribute, ARIA attributes/label, visible status text, and submit button class without changing the submit label text (`Extract`).
3. Update `app/static/src/input.css` to make the clarified mode area readable in the command card on desktop and mobile, with clear active/inactive affordances and a visible focus ring; regenerate `app/static/dist/style.css` and `app/static/dist/main.js` via `make build`.
4. Extend `tests/e2e/pages/index_page.py` with stable locators for the mode title/help/status and any active mode notes added in T01.
5. Extend `tests/e2e/test_ui_controls.py` and, if needed, `tests/e2e/test_homepage.py` with browser assertions for keyboard mode toggling, screen-reader-visible state attributes, hidden input synchronization, clarified copy, and unchanged Extract enablement; re-run focused offline and online extraction proofs.
  - Files: `app/static/src/ts/modules/form.ts`, `app/static/src/ts/modules/form.test.ts`, `app/static/src/input.css`, `app/static/dist/style.css`, `app/static/dist/main.js`, `tests/e2e/pages/index_page.py`, `tests/e2e/test_ui_controls.py`, `tests/e2e/test_homepage.py`, `tests/e2e/test_extraction.py`
  - Verify: npx vitest run app/static/src/ts/modules/form.test.ts
npx tsc --noEmit
make build
python3 -m pytest -q tests/e2e/test_ui_controls.py tests/e2e/test_homepage.py::test_mode_toggle_labels tests/e2e/test_homepage.py::test_offline_mode_by_default tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline tests/e2e/test_extraction.py::test_online_mode_indicator

## Files Likely Touched

- app/templates/index.html
- tests/test_index_intake_contract.py
- tests/test_routes.py
- app/static/src/ts/modules/form.ts
- app/static/src/ts/modules/form.test.ts
- app/static/src/input.css
- app/static/dist/style.css
- app/static/dist/main.js
- tests/e2e/pages/index_page.py
- tests/e2e/test_ui_controls.py
- tests/e2e/test_homepage.py
- tests/e2e/test_extraction.py
