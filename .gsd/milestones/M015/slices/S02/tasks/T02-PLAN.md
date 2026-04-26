---
estimated_steps: 8
estimated_files: 9
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
  - verify-before-complete
---

# T02: Synchronize mode state across TypeScript, styling, and browser proof

Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's additive mode markup so click and keyboard interactions keep the hidden input, widget `data-mode`, ARIA state, visible status copy, and Extract button styling in sync, then regenerate assets and prove both offline and online submit behavior still use the current route semantics.

Quality gates — Failure Modes: if `form.ts` cannot find T01's markup, fail fast with a Vitest or Playwright selector/state assertion rather than weakening IDs; if `make build` fails, do not hand-edit `app/static/dist/style.css` or `app/static/dist/main.js`; if online submit behavior redirects because providers are unconfigured, preserve the existing route behavior and use the repository's existing mocked/provider E2E fixtures rather than changing production routes. Load Profile: S02 may add constant-time DOM text/attribute updates to the existing toggle listener only; it must add no network calls, storage, intervals, history reads, or provider initialization on `/`. Negative Tests: cover initial offline default, click toggle to online/back offline, keyboard Space/Enter toggle behavior, hidden-input value synchronization, ARIA/status synchronization, disabled/enabled Extract behavior, offline no-HTTP behavior, and online mode result indication through existing E2E fixtures.

Steps:
1. Add `app/static/src/ts/modules/form.test.ts` with jsdom/Vitest coverage for `init()` on the index form: initial offline state, click toggling to online/back offline, hidden `#mode-input` value updates, `#mode-toggle-widget[data-mode]`, `aria-pressed`, `aria-checked` if present, status/descriptive text updates, and submit button mode class preservation.
2. Update `app/static/src/ts/modules/form.ts` to centralize mode-state rendering so initial load and every toggle update hidden input value, widget data attribute, ARIA attributes/label, visible status text, and submit button class without changing the submit label text (`Extract`).
3. Update `app/static/src/input.css` to make the clarified mode area readable in the command card on desktop and mobile, with clear active/inactive affordances and a visible focus ring; regenerate `app/static/dist/style.css` and `app/static/dist/main.js` via `make build`.
4. Extend `tests/e2e/pages/index_page.py` with stable locators for the mode title/help/status and any active mode notes added in T01.
5. Extend `tests/e2e/test_ui_controls.py` and, if needed, `tests/e2e/test_homepage.py` with browser assertions for keyboard mode toggling, screen-reader-visible state attributes, hidden input synchronization, clarified copy, and unchanged Extract enablement; re-run focused offline and online extraction proofs.

## Inputs

- `app/templates/index.html`
- `app/static/src/ts/modules/form.ts`
- `app/static/src/input.css`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_ui_controls.py`
- `tests/e2e/test_homepage.py`
- `tests/e2e/test_extraction.py`

## Expected Output

- `app/static/src/ts/modules/form.ts`
- `app/static/src/ts/modules/form.test.ts`
- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_ui_controls.py`
- `tests/e2e/test_homepage.py`

## Verification

npx vitest run app/static/src/ts/modules/form.test.ts
npx tsc --noEmit
make build
python3 -m pytest -q tests/e2e/test_ui_controls.py tests/e2e/test_homepage.py::test_mode_toggle_labels tests/e2e/test_homepage.py::test_offline_mode_by_default tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline tests/e2e/test_extraction.py::test_online_mode_indicator

## Observability Impact

- Signals added/changed: synchronized DOM state across hidden input value, widget `data-mode`, toggle ARIA attributes, visible status text, and submit button mode class.
- How a future agent inspects this: run `npx vitest run app/static/src/ts/modules/form.test.ts` for state-sync failures, then `python3 -m pytest -q tests/e2e/test_ui_controls.py` for browser/keyboard failures.
- Failure state exposed: desynchronized mode state, lost keyboard accessibility, or broken generated assets fail with targeted unit/build/E2E output before S04's broader integration lane.
