---
id: S03
parent: M015
milestone: M015
provides:
  - Index route recent-analysis summary contract: bounded `HistoryStore.list_recent(limit=4)` read passed to `index.html`.
  - Compact, server-rendered Recent Analyses rail with safe links to `/history/<id>` plus empty and unavailable states.
  - CSS and browser proof that recent history remains secondary on desktop and stacks below the command card on mobile.
  - Fail-open history-listing behavior that preserves paste form, CSRF, hidden mode input, and offline extraction.
requires:
  - slice: S01
    provides: Command-card structure, stable intake form selectors, and responsive workbench shell consumed by the Recent Analyses rail.
  - slice: S02
    provides: Clarified mode UI and hidden `mode` input semantics preserved while adding recent history.
affects:
  - S04
key_files:
  - app/routes/analysis.py
  - app/templates/index.html
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/test_index_intake_contract.py
  - tests/test_history_routes.py
  - tests/e2e/pages/index_page.py
  - tests/e2e/conftest.py
  - tests/e2e/test_homepage.py
  - .gsd/PROJECT.md
key_decisions:
  - Kept Recent Analyses server-rendered through `HistoryStore.list_recent(limit=4)` instead of adding client fetch/polling or a new API state system.
  - Made index history lookup fail open with sanitized warning logging so storage health cannot deny service to paste-and-extract.
  - Kept the recent rail CSS-only and visually secondary to the command card on desktop, stacked below it on mobile.
  - Isolated E2E history data by patching `HistoryStore.DEFAULT_DB_PATH` before live app startup and seeding through the live store.
patterns_established:
  - Bounded, fail-open secondary data surfaces on `/` should never block the primary paste form.
  - Recent-history DOM inspection surfaces are `.recent-analyses-rail`, `.recent-analysis-row`, `.recent-analyses-empty`, and `.recent-analyses-unavailable`.
  - Homepage E2E tests can seed deterministic history through the isolated live `HistoryStore` fixture rather than relying on user-local SQLite state.
  - Secondary intake UI should remain server-rendered/CSS-only unless a later slice has a measured need for client state.
observability_surfaces:
  - Sanitized warning log emitted when index recent-history lookup fails.
  - Deterministic DOM states for recent rows, empty history, and unavailable history.
  - Focused route tests and Playwright geometry/link assertions for fail-open and secondary-hierarchy behavior.
drill_down_paths:
  - .gsd/milestones/M015/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-26T11:01:54.216Z
blocker_discovered: false
---

# S03: Compact Recent Analyses rail

**The intake page now server-renders a compact, secondary Recent Analyses rail with safe resume links and fail-open history handling while preserving paste-and-extract.**

## What Happened

S03 added the recent-history resume surface to the Intake Workbench without making history a prerequisite for intake. GET `/` now performs one bounded read through `current_app.history_store.list_recent(limit=4)`, catches storage failures narrowly, logs only sanitized failure context, and passes `recent_analyses` plus an unavailable flag into `index.html`. The shared index template renders three deliberate states inside `.intake-workbench`: linked `.recent-analysis-row` entries for saved analyses, a compact empty state when history has no rows, and a quiet unavailable state when listing fails. Rows link to `/history/<id>` through `url_for('main.history_detail', analysis_id=...)`, retain Jinja autoescaping for stored user text, and avoid exposing raw results JSON, provider credentials, secrets, CSRF tokens, or unbounded input snippets.

The frontend CSS now makes `.intake-workbench` a command-card-plus-rail layout: `.command-card` stays the dominant surface on desktop, `.recent-analyses-rail` is visually secondary with compact rows and accessible link hit areas, and the recent rail stacks below the command card on mobile without horizontal overflow. No client polling, fetches, browser storage, per-row detail loads, preview extraction, or provider/enrichment rewrites were introduced.

The E2E seam was hardened so homepage browser tests seed deterministic history through an isolated live `HistoryStore` temp database instead of depending on a developer's real `~/.sentinelx/history.db`. Homepage page-object helpers now expose stable recent rail/row/empty/unavailable locators and geometry assertions, allowing downstream S04 to reuse the same browser proof patterns when validating the fully assembled workbench.

## Verification

Fresh slice-level verification was run after the code/test implementation and before completion. The combined verification command executed `make build`, `npx tsc --noEmit`, focused route/history/security tests, and focused Playwright homepage/extraction tests with exit code 0. `make build` regenerated `app/static/dist/style.css` and `app/static/dist/main.js`; it still prints the pre-existing Browserslist `caniuse-lite is outdated` advisory but exits successfully. TypeScript produced no errors. Route/history/security verification passed 18 tests covering bounded recent reads, recent links, empty state, fail-open history exceptions, preserved form/CSRF selectors, offline no-HTTP behavior, and security headers. Browser verification passed 22 tests covering seeded recent-row visibility and `/history/<id>` hrefs, desktop secondary hierarchy, mobile stacking below the command card, empty/unavailable states that do not block form visibility or submit enablement, and the existing offline paste-to-results flow.

## Requirements Advanced

- R075 — S03 added the compact recent rail portion of the command-card-plus-rail responsive layout and proved desktop/mobile hierarchy for that surface; S04 still owns final integrated responsive validation.
- R076 — S03 preserved CSRF output, hidden offline mode semantics, offline no-HTTP behavior, generated asset consistency, TypeScript validity, security headers, and the existing offline paste-to-results browser path for touched surfaces.

## Requirements Validated

- R073 — Recent Analyses renders on `/` from bounded history summaries, links to `/history/<id>`, remains visually secondary on desktop/mobile, and passed route plus Playwright proof.
- R074 — History listing exceptions are caught and rendered as a quiet unavailable state with status 200; tests prove the paste form, CSRF, mode controls, submit enablement, and offline path remain available.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

T01 also passes recent-analysis context to the no-input POST error render so the shared index template receives the same fail-open state when validation errors re-render `/`. This is within the slice intent and avoids divergent template assumptions. Otherwise none.

## Known Limitations

No functional S03 gaps remain. The milestone still needs S04 integrated proof across S01/S02/S03 together, including final desktop/mobile polish, history resume, extraction/enrichment/history reload, CSRF/security, TypeScript/build, and broader E2E lanes. `make build` continues to print the existing Browserslist `caniuse-lite is outdated` advisory while exiting successfully; dependency metadata was not part of this slice.

## Follow-ups

S04 should reuse the S03 route and E2E selectors (`.recent-analyses-rail`, `.recent-analysis-row`, `.recent-analyses-empty`, `.recent-analyses-unavailable`) to validate the assembled Intake Workbench with full regression coverage.

## Files Created/Modified

- `app/routes/analysis.py` — Added fail-open bounded recent-history retrieval for GET `/` and shared no-input re-render context.
- `app/templates/index.html` — Added compact Recent Analyses rail markup with linked rows, empty state, unavailable state, safe escaping, and preserved intake form selectors.
- `app/static/src/input.css` — Styled command-card-plus-rail desktop layout, compact recent rows, empty/unavailable states, accessible links, and mobile stacking.
- `app/static/dist/style.css` — Regenerated compiled CSS from the source Tailwind input.
- `app/static/dist/main.js` — Regenerated bundled frontend asset through `make build`.
- `tests/test_index_intake_contract.py` — Added route/HTML contract tests for seeded rows, bounded reads, empty state, fail-open exceptions, safe rendering, preserved CSRF/form selectors, and offline behavior.
- `tests/test_history_routes.py` — Adjusted stale assumptions while preserving dedicated history list/detail behavior.
- `tests/e2e/pages/index_page.py` — Added page-object helpers for recent rail/row/empty/unavailable locators and command-card hierarchy assertions.
- `tests/e2e/conftest.py` — Isolated live-server HistoryStore to a temp DB and exposed deterministic seeding fixtures.
- `tests/e2e/test_homepage.py` — Added browser coverage for seeded recent links, desktop/mobile hierarchy, empty/unavailable states, submit enablement, and preserved offline extraction.
- `.gsd/PROJECT.md` — Refreshed project state to note S03 completion and remaining S04 integration proof.
