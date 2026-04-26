---
id: T02
parent: S02
milestone: M015
key_files:
  - app/static/src/ts/modules/form.ts
  - app/static/src/ts/modules/form.test.ts
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_ui_controls.py
  - tests/e2e/test_homepage.py
key_decisions:
  - Centralized mode-state rendering in `form.ts` so all observable mode surfaces update from one normalized offline/online state path.
  - Preserved native button keyboard semantics and `aria-pressed` instead of introducing a custom switch role, while synchronizing optional `aria-checked` defensively if future markup includes it.
duration: 
verification_result: mixed
completed_at: 2026-04-26T08:58:06.383Z
blocker_discovered: false
---

# T02: Synchronized the index mode toggle across TypeScript state, minimalist styling, generated assets, and browser/E2E proof.

**Synchronized the index mode toggle across TypeScript state, minimalist styling, generated assets, and browser/E2E proof.**

## What Happened

Added focused Vitest coverage for the index form mode toggle, including initial offline default, click toggle online/back offline, hidden input synchronization, widget `data-mode`, `aria-pressed`, optional `aria-checked` synchronization, status copy, submit button class preservation, invalid-mode normalization, fail-fast missing-markup behavior, and submit enablement independence. Updated `form.ts` to centralize mode rendering through a single normalized state path so initial load and every native button activation update the hidden `mode` input, `#mode-toggle-widget[data-mode]`, `#mode-toggle-btn` ARIA state, `#mode-status`, and the `Extract` button mode class without changing the submit label. Polished the mode control in `input.css` with restrained/minimal command-card styling, readable help/status copy, active/inactive affordances, tactile press state, and visible keyboard focus. Regenerated `app/static/dist/style.css` and `app/static/dist/main.js` via `make build`. Extended the index page object with stable mode copy/status locators and strengthened Playwright checks for click, keyboard Space/Enter, accessible descriptions, hidden input/widget/ARIA/status sync, unchanged Extract enablement, offline extraction, and online results indication. A managed dev server was restarted for a real browser smoke check after detecting a stale process serving old assets; the smoke flow passed and the server was stopped afterward. The user additionally requested a minimalist/simple homepage direction and asked about Next.js; I captured that as future product/architecture context rather than changing this Flask/static slice contract.

## Verification

Fresh verification passed after final code and asset changes: `npx vitest run app/static/src/ts/modules/form.test.ts` passed 6/6 tests; `npx tsc --noEmit` exited 0; `make build` regenerated CSS/JS successfully; Flask index contract tests passed 2/2; focused Playwright/E2E checks passed 16/16 across mode UI controls, homepage mode defaults/labels, offline extraction, and online mode indication. A real browser smoke flow on `http://127.0.0.1:5000/` also completed 10 steps: verified default offline DOM/ARIA/status/button class, toggled online and verified synchronized DOM/ARIA/status/button class, toggled back offline, submitted synthetic `192.0.2.44`, and verified the results page `.mode-indicator.mode-offline`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run app/static/src/ts/modules/form.test.ts` | 0 | ✅ pass | 973ms |
| 2 | `npx tsc --noEmit` | 0 | ✅ pass | 476ms |
| 3 | `make build` | 0 | ✅ pass | 1382ms |
| 4 | `python3 -m pytest -q tests/test_index_intake_contract.py` | 0 | ✅ pass | 473ms |
| 5 | `python3 -m pytest -q tests/e2e/test_ui_controls.py tests/e2e/test_homepage.py::test_mode_toggle_labels tests/e2e/test_homepage.py::test_offline_mode_by_default tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline tests/e2e/test_extraction.py::test_online_mode_indicator` | 0 | ✅ pass | 4945ms |
| 6 | `Browser smoke via browser_batch completed 10 steps against restarted local dev server: offline DOM/ARIA/status/button class, online toggle DOM/ARIA/status/button class, offline submit, and results `.mode-indicator.mode-offline` all verified.` | -1 | unknown (coerced from string) | 0ms |

## Deviations

Used the existing native button keyboard activation instead of adding custom keydown handlers; this preserves T01's native button + `aria-pressed` decision while still proving Space/Enter behavior in Playwright. Recorded the user's minimalist homepage/Next.js request as future context rather than changing the active Flask/static slice contract.

## Known Issues

The browser diagnostics still surface the pre-existing CSP warning for inline style application on page load; this was already noted in T01 and was not introduced by the mode synchronization work. A stale managed dev-server process initially served old assets during browser smoke verification; restarting it resolved the issue and the server was stopped after the smoke check.

## Files Created/Modified

- `app/static/src/ts/modules/form.ts`
- `app/static/src/ts/modules/form.test.ts`
- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_ui_controls.py`
- `tests/e2e/test_homepage.py`
