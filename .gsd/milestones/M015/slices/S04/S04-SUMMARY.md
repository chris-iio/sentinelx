---
id: S04
parent: M015
milestone: M015
provides:
  - Final integrated proof that the Intake Workbench is assembled and usable across desktop/mobile with the paste command card dominant and Recent Analyses secondary.
  - Regression evidence that extraction, Offline no-HTTP behavior, Online no-provider redirect, history reload/resume, CSRF/security headers, TypeScript, generated assets, Vitest, and full E2E behavior remain intact.
  - Reusable route and Playwright assertions for future intake workbench changes.
requires:
  - slice: S01
    provides: Command-card intake structure, stable form selectors, and baseline Offline paste-to-results behavior.
  - slice: S02
    provides: Clarified Offline/Online mode UI, hidden `mode` contract, synchronized ARIA/status behavior, and mode tests.
  - slice: S03
    provides: Bounded server-rendered Recent Analyses rail/list, fail-open history lookup, safe row rendering, and `/history/<id>` resume links.
affects:
  - M015 milestone validation can now evaluate all Intake Workbench success criteria with S04 final integrated proof.
key_files:
  - tests/test_index_intake_contract.py
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_homepage.py
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
key_decisions:
  - Preserved existing route/template behavior in T01 and added integrated contract tests only because the tightened assertions exposed no production bug.
  - Fixed responsive overflow by widening only the index page shell and constraining the decorative pseudo-element, not by clipping the interactive page shell.
patterns_established:
  - Final intake workbench proof should combine route/security assertions and browser assertions so command card, mode state, recent history, fail-open behavior, no-preview exclusions, and fast Offline extraction are verified as one assembled user flow.
  - Responsive fixes for the intake workbench should preserve clickability of Recent Analyses rows; avoid shell clipping that masks overflow by interfering with interactive content.
  - Seed Playwright Recent Analyses rows through the live-server history fixture and click real `/history/<id>` links instead of depending on developer-local history databases or DOM-only mocks.
observability_surfaces:
  - Visible DOM diagnostics: `.recent-analysis-row`, `.recent-analyses-empty`, `.recent-analyses-unavailable`, `#mode-status`, and `#mode-input`.
  - Sanitized warning log when index recent-history lookup fails.
  - Verification commands: route/security contract command, focused browser assembly command, `make verify-fast`, and full `python3 -m pytest -q tests/e2e` browser lane.
drill_down_paths:
  - .gsd/milestones/M015/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-26T12:00:58.782Z
blocker_discovered: false
---

# S04: Integrated intake proof and polish

**Closed the Intake Workbench assembly by proving the command card, clarified mode control, compact Recent Analyses rail, history resume path, responsive layout, security contracts, build, and full browser regression lane together.**

## What Happened

S04 consumed the completed S01 command-card foundation, S02 mode-control clarification, and S03 server-rendered Recent Analyses rail, then converted the assembled Intake Workbench into explicit route/security and Playwright contracts. T01 added integrated `/` and no-input `/analyze` tests that treat the page as one workbench: stable paste form selectors, CSRF, hidden `mode=offline`, clarified mode copy/status, bounded `HistoryStore.list_recent(limit=4)`, safe/escaped stored history text, `/history/<id>` resume links, no preview/result surfaces, no provider calls during GET `/`, fail-open unavailable-history rendering, no-HTTP Offline behavior, Online-without-provider guard, and security headers. T01 required no production route/template changes because the existing assembled behavior satisfied the tightened contract.

T02 added final browser/page-object proof for the real application. The `IndexPage` page object now has reusable assertions for command-surface readiness, synchronized mode state, absent preview surfaces, recent resume links, desktop dominance, mobile stacking, and full-document horizontal overflow. Homepage E2E tests seed deterministic history through the live-server fixture, prove a populated desktop recent rail remains secondary, prove mobile rail stacking at 390px without overflow, click a Recent Analyses row into `/history/<id>` to verify resume, keep empty/unavailable history states non-blocking, and re-prove the real Offline paste-to-results flow without enrichment polling. The new mobile overflow check exposed a real composition regression: the default 960px shell plus workbench grid yielded horizontal overflow. The fix widened only the index page shell via `.site-main:has(.page-index)` and constrained the decorative `.page-index::before` inset, avoiding an earlier clipping approach that interfered with recent-row clicks. Generated CSS/JS were rebuilt through `make build`.

The final assembled proof validated the active M015 requirements: `R070` fast workbench, `R071` unchanged paste-to-results flow, `R075` desktop/mobile command-card plus compact rail layout, and `R076` no regression to extraction, history reload, security, TypeScript/build, generated assets, or E2E behavior. No product scope was expanded: there is still no pre-submit IOC preview, no client-side history fetch/polling, no provider/enrichment rewrite, no dashboard surface, and history remains a bounded server-rendered secondary aid that fails open.

## Verification

Fresh slice-level verification ran after the final code changes and passed:

1. `python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings tests/test_routes.py::test_security_headers_present tests/test_routes.py::test_csrf_token_required tests/test_history_routes.py` — exit 0, 27 passed in 0.67s.
2. `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_ui_controls.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` — exit 0, 34 passed in 5.21s.
3. `make verify-fast` — exit 0; 1026 non-E2E pytest tests passed, 125 deselected; 87 Vitest tests passed across 7 files; `npx tsc --noEmit` passed; `make build` regenerated `app/static/dist/style.css` and `app/static/dist/main.js` successfully.
4. `python3 -m pytest -q tests/e2e` — exit 0, 125 passed in 40.77s.

Diagnostic/observability surfaces confirmed by tests include `.recent-analysis-row`, `.recent-analyses-empty`, `.recent-analyses-unavailable`, `#mode-status`, `#mode-input`, CSRF hidden input presence, sanitized recent-history warning logging, bounded `list_recent(limit=4)` call assertions, absence of `.ioc-preview`/`.preview-rail`/pre-submit `.page-results`, and browser-level request observation proving Offline submission does not start enrichment polling.

## Requirements Advanced

- R070 — final proof completed and status updated to validated.
- R071 — final proof completed and status updated to validated.
- R075 — final proof completed and status updated to validated.
- R076 — direct S04 proof completed and status updated to validated.

## Requirements Validated

- R070 — S04 route/browser proof validates `/` as a fast analyst intake workbench with stable paste form, clarified mode state, submit enablement, secondary recent rail, no preview surface, and fail-open history.
- R071 — Focused and full Playwright lanes re-proved paste → Offline → Extract → results from the final assembled layout with no enrichment polling.
- R075 — Browser assertions validate desktop command-card dominance, mobile stacking below the command card, and no horizontal overflow.
- R076 — Fresh route/security, focused browser, `make verify-fast`, and full E2E verification passed after final code changes.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

No feature scope deviations. T01 stayed test-only because existing route/template behavior met the integrated contract. T02 made one source CSS/layout fix and regenerated assets after new browser assertions exposed real mobile horizontal overflow; this was within the planned polish/fix allowance.

## Known Limitations

None for the S04 acceptance criteria. The milestone remains active until milestone-level validation/closure runs, but all four M015 slices are now complete and their requirements have final proof.

## Follow-ups

Run milestone-level validation for M015 and then close the milestone if validation confirms the assembled slice evidence satisfies the roadmap success criteria.

## Files Created/Modified

- `tests/test_index_intake_contract.py` — Added integrated route/security/fail-open intake workbench contract assertions.
- `tests/e2e/pages/index_page.py` — Added reusable Playwright page-object assertions for assembled workbench readiness, recent rail behavior, resume links, and overflow.
- `tests/e2e/test_homepage.py` — Added/strengthened desktop, mobile, seeded history resume, empty/unavailable history, and Offline paste-to-results browser tests.
- `app/static/src/input.css` — Fixed index-only workbench shell width and decorative pseudo-element inset to remove mobile overflow while preserving clickability.
- `app/static/dist/style.css` — Regenerated minified CSS from source via `make build`.
- `app/static/dist/main.js` — Regenerated bundled frontend asset via `make build`.
