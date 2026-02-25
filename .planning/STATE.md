# Session State

## Project Reference

See: .planning/PROJECT.md

## Position

**Milestone:** v1.1 UX Overhaul
**Current phase:** Phase 8 of 10 — Input Page Polish
**Current Plan:** Plan 02 at checkpoint — Task 1 complete, awaiting human-verify (2/2)
**Status:** In progress — awaiting human verification

## Progress

Phases 1-4: v1.0 MVP ✓
Phase 6: Foundation — Tailwind + Alpine + Card Layout ✓ (commit 148b15b)
Phase 7: Filtering & Search — Plan 01 complete ✓ (commit 71f39a8), Plan 02 complete ✓ (commit 533b4b8)
Phase 8: Input Page Polish — Plan 01 complete ✓ (commits 020e192, e128086), Plan 02 Task 1 complete ✓ (commit c11c976)
Phases 9-10: Not started

## Recent Decisions

- data-verdict attribute is single source of truth (CSS border, JS sorting, dashboard counts)
- Alpine CSP build (alpine.csp.min.js) cannot evaluate inline x-data JS, function args, $el, $event — use vanilla JS or data attributes instead
- Filter bar replaced with vanilla JS initFilterBar() — reads data-filter-verdict/data-filter-type attributes, toggled CSS classes
- card.style.display via DOM JS is NOT blocked by CSP style-src (only HTML style= attributes are blocked)
- Tailwind safelist critical for dynamic class names in Jinja2/JS
- Filter bar renders in both online and offline modes — type pills and search are useful in offline mode
- ioc_type.value must be used in Jinja2 when iterating grouped.keys() because group_by_type returns IOCType enums as keys
- Dashboard verdict badges made clickable with toggle pattern (click once to filter, click again to reset to all)
- Alpine CSP vendor file removed — no longer needed since Phase 7 switched to pure vanilla JS initFilterBar()
- Human visual verification confirmed filter bar works: verdict buttons, type pills, text search, sticky positioning all functional in browser
- Toggle widget uses data-mode attribute on wrapper div as single source of truth; CSS [data-mode=online] selectors drive thumb position and label color without JS class manipulation
- Hidden input name=mode carries form POST value — Flask route unchanged (backward compatible)
- paste-feedback uses style.display toggle matching existing main.js patterns; inline style=display:none in HTML is safe under current CSP

## Pending Todos

None

## Blockers/Concerns

- Pre-existing: E2E tests test_online_mode_indicator and test_online_mode_shows_verdict_dashboard fail without VT API key (not a regression)

## Session Continuity

Last session: 2026-02-25
Stopped at: 08-02-PLAN.md Task 2 checkpoint (human-verify) — E2E tests updated, awaiting visual verification of toggle switch, paste feedback, and reactive label in browser
