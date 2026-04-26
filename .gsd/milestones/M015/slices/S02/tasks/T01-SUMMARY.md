---
id: T01
parent: S02
milestone: M015
key_files:
  - app/templates/index.html
  - tests/test_index_intake_contract.py
key_decisions:
  - Preserved the native button + `aria-pressed` toggle semantics and added descriptive `aria-describedby`/live status copy instead of adding unsynchronized `role="switch"`/`aria-checked`.
duration: 
verification_result: passed
completed_at: 2026-04-26T08:53:08.639Z
blocker_discovered: false
---

# T01: Pinned the index mode-toggle contract with visible Offline/Online guidance, live status copy, and route-level selector/ARIA assertions.

**Pinned the index mode-toggle contract with visible Offline/Online guidance, live status copy, and route-level selector/ARIA assertions.**

## What Happened

Extended the index intake contract test first to require explicit mode-title/help/status markup, visible Offline and Online labels, default offline safety copy, an online configured-provider cue, preserved hidden `mode=offline`, preserved `#mode-toggle-widget[data-mode="offline"]`, and `#mode-toggle-btn` as a button with `aria-pressed="false"` plus valid `aria-describedby` references. The new test failed against the existing template on missing `#mode-title`, then the index template was updated additively inside `.mode-toggle` without changing `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, CSRF output, hidden `#mode-input`, or `/analyze` submission behavior. I kept the accessibility semantics on the existing native button + `aria-pressed` toggle contract rather than adding `role="switch"`/`aria-checked`, because this task does not update TypeScript state synchronization and stale ARIA checked state would be worse than additive descriptive wiring. A local browser smoke check confirmed the visible copy, default offline widget state, disabled submit state, and an offline submit to `/analyze` rendering `192.168.1.1`.

## Verification

Fresh verification passed after the final code changes: focused Flask contract/negative route checks passed, focused Playwright UI controls passed, available Vitest tests passed, a focused extraction E2E passed, TypeScript typecheck passed, and `make build` passed. Browser smoke verification also passed: visible `Analysis mode`, offline safety/status copy, `#mode-toggle-widget[data-mode="offline"]`, `#mode-toggle-btn[aria-pressed="false"]` with describedby wiring, disabled submit before input, and offline submit to `/analyze` with extracted result text.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings` | 0 | ✅ pass | 465ms |
| 2 | `python3 -m pytest -q tests/e2e/test_ui_controls.py::test_mode_toggle_to_online tests/e2e/test_ui_controls.py::test_submit_enabled_when_text_entered` | 0 | ✅ pass | 1347ms |
| 3 | `npx vitest run` | 0 | ✅ pass | 1332ms |
| 4 | `python3 -m pytest -q tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` | 0 | ✅ pass | 1301ms |
| 5 | `npx tsc --noEmit` | 0 | ✅ pass | 415ms |
| 6 | `make build` | 0 | ✅ pass | 1310ms |

## Deviations

The slice plan references `app/static/src/ts/modules/form.test.ts`, but no tracked `form.test.ts` exists in this checkout. I ran the full available Vitest suite plus focused Playwright UI/extraction checks instead. I also avoided adding `role="switch"`/`aria-checked` in T01 to prevent introducing an ARIA state that current TypeScript does not yet synchronize.

## Known Issues

Browser navigation logged an existing CSP warning about inline style application on page load; it was not introduced by this server-rendered markup change and no failed requests were observed in the DOM smoke check. No blocker discovered.

## Files Created/Modified

- `app/templates/index.html`
- `tests/test_index_intake_contract.py`
