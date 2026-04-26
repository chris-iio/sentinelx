---
id: S02
parent: M015
milestone: M015
provides:
  - Clarified Offline/Online mode UI for the intake command card.
  - Preserved hidden `mode` form contract and existing `/analyze` submit behavior.
  - Keyboard-accessible and screen-reader-inspectable mode state with synchronized visible status copy.
  - Focused automated proof for route contract, TypeScript form behavior, generated assets, and browser offline/online flows.
requires:
  - slice: S01
    provides: Command-card shell and stable intake form controls (`#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`).
affects:
  - S04
key_files:
  - app/templates/index.html
  - tests/test_index_intake_contract.py
  - app/static/src/ts/modules/form.ts
  - app/static/src/ts/modules/form.test.ts
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_ui_controls.py
  - tests/e2e/test_homepage.py
key_decisions:
  - Preserved the native button + `aria-pressed` mode-toggle contract instead of replacing it with a custom switch role.
  - Centralized mode-state rendering in `form.ts` so hidden input, widget data, ARIA state, visible status, and submit-button mode class update from one normalized state path.
  - Kept S02 as a static markup/CSS/DOM synchronization slice with no pre-submit parsing, provider calls, history reads, storage, polling, or new API surface.
patterns_established:
  - Mode UI improvements must be additive around the stable hidden-input form contract.
  - Use focused contract tests for server-rendered IDs/ARIA, Vitest for DOM state synchronization, and Playwright for click/keyboard/live submit proof.
  - Regenerate generated static assets via `make build`; do not hand-edit `app/static/dist` outputs.
observability_surfaces:
  - Focused Flask contract tests fail on selector/ARIA/form-contract regressions.
  - Focused Vitest form-module tests fail on hidden-input/widget/ARIA/status synchronization regressions.
  - Focused Playwright tests fail on keyboard accessibility, visible copy, submit enablement, and offline/online route behavior regressions.
  - No runtime observability surface was added because S02 has no new backend process, network call, storage path, or API.
drill_down_paths:
  - .gsd/milestones/M015/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-26T09:00:21.127Z
blocker_discovered: false
---

# S02: Mode clarity without semantic churn

**Clarified the Offline/Online mode control in the intake command card while preserving the hidden `mode` input contract and existing paste-to-results route behavior.**

## What Happened

S02 delivered a semantic and visual clarification of the intake page's Offline/Online mode choice without changing the analyst flow or introducing a new data dependency. The index template now exposes visible mode heading/help/status copy that explains the default offline safety path and the online provider/enrichment intent before submit, while preserving the S01 controls and form contract: `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, hidden `#mode-input name="mode" value="offline"`, `#mode-toggle-widget`, and `#mode-toggle-btn`.

The client behavior was centralized in `app/static/src/ts/modules/form.ts`. Initial load and every click/native keyboard activation now render from one normalized offline/online state path so the hidden input value, widget `data-mode`, button ARIA state, visible `#mode-status`, and submit-button mode class remain synchronized. The button remains a real native button using `aria-pressed`; optional `aria-checked` synchronization is defensive only if future markup adds it. The `Extract` label and `/analyze` route semantics remain unchanged.

Styling in `app/static/src/input.css` makes the mode area clearer but intentionally secondary to the paste command card: offline/online labels, mode notes, live status, active/inactive affordances, and keyboard focus rings are readable on desktop and mobile without adding preview parsing, provider calls, history reads, storage, polling, or a new API surface on `/`. Generated `app/static/dist/style.css` and `app/static/dist/main.js` were rebuilt via `make build`.

Operational readiness / diagnostics: the health signal for this slice is the focused contract + browser suite covering default offline state, state synchronization, keyboard accessibility, offline extraction, and online mode indication. Failure signals are localized: missing/renamed form selectors fail `tests/test_index_intake_contract.py`, state-sync regressions fail `app/static/src/ts/modules/form.test.ts`, build/type regressions fail `npx tsc --noEmit` or `make build`, and live UI/submit regressions fail focused Playwright tests. Recovery is to preserve the stable IDs, rerun `make build` after source changes, restart any stale dev server before browser smoke checks, and rerun the focused verification lane. No runtime monitoring surface was added because S02 is static markup/CSS/DOM state only.

## Verification

Fresh slice-level verification passed in this closeout attempt after the final code state. Evidence:

- `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings` → exit 0, `4 passed in 0.34s`.
- `npx vitest run app/static/src/ts/modules/form.test.ts` → exit 0, `6 tests` / `1 file` passed.
- `npx tsc --noEmit` → exit 0.
- `make build` → exit 0; Tailwind rebuilt `app/static/dist/style.css` and esbuild produced `app/static/dist/main.js`.
- `python3 -m pytest -q tests/e2e/test_ui_controls.py tests/e2e/test_homepage.py::test_mode_toggle_labels tests/e2e/test_homepage.py::test_offline_mode_by_default tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline tests/e2e/test_extraction.py::test_online_mode_indicator` → exit 0, `16 passed in 3.12s`.

These checks cover the hidden `mode` input contract, default offline semantics, no-HTTP offline route behavior, online no-provider route behavior, TypeScript validity, generated asset consistency, click and keyboard toggle behavior, ARIA/status synchronization, submit enablement after IOC input, offline extraction results, and online mode result indication.

## Requirements Advanced

- R071 — Re-proved the primary paste → default Offline → Extract → results path and the online mode selection path through focused Playwright extraction checks.
- R076 — Preserved CSRF/form submission, offline no-HTTP behavior, online no-provider behavior, TypeScript/build validity, and existing focused E2E behavior while changing the intake UI.

## Requirements Validated

- R072 — S02 route, Vitest, TypeScript/build, and Playwright verification proved clearer Offline/Online copy and synchronized mode state while preserving the hidden `mode` contract and submit behavior.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None from the S02 scope. The implementation intentionally kept native button + `aria-pressed` semantics rather than introducing a custom switch role, matching the task-level decision to avoid unsynchronized ARIA state.

## Known Limitations

S02 does not add Recent Analyses, history loading, pre-submit IOC preview, provider initialization, polling, storage, or any new API surface. A pre-existing CSP warning about inline style application may still appear in browser diagnostics; it was not introduced by S02.

## Follow-ups

S03 should add the compact Recent Analyses rail/list orthogonally to the command card and must not make history availability a prerequisite for paste/extract. S04 should run integrated desktop/mobile/full-regression proof across S01, S02, and S03.

## Files Created/Modified

- `app/templates/index.html` — Added visible mode title/help/status copy and ARIA descriptions without changing form action or stable IDs.
- `tests/test_index_intake_contract.py` — Pinned the clarified mode contract and preserved hidden input/default offline semantics.
- `app/static/src/ts/modules/form.ts` — Centralized mode-state rendering across hidden input, widget data, ARIA, status copy, and submit button class.
- `app/static/src/ts/modules/form.test.ts` — Added focused Vitest coverage for initial/toggled/invalid/missing-markup mode state behavior.
- `app/static/src/input.css` — Styled the clarified mode area, active/inactive affordances, status copy, and focus treatment.
- `app/static/dist/style.css` — Regenerated built CSS via `make build`.
- `app/static/dist/main.js` — Regenerated bundled/minified browser JavaScript via `make build`.
- `tests/e2e/pages/index_page.py` — Exposed stable locators for mode copy/status and synchronized state assertions.
- `tests/e2e/test_ui_controls.py` — Expanded browser coverage for click/keyboard mode toggling and synchronized state.
- `tests/e2e/test_homepage.py` — Strengthened homepage checks for mode labels/default offline state.
- `.gsd/PROJECT.md` — Refreshed project state to note M015/S02 completion and the clarified mode-toggle pattern.
