---
estimated_steps: 8
estimated_files: 9
---

# T01: Verify integration pipeline — export, filter, sort, progress, warnings, copy, detail links

**Slice:** S04 — Functionality integration + polish
**Milestone:** M002

## Description

R008 requires that all existing functionality — enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — continues working after the S01–S03 layout rework. S01–S03 preserved all selector names and data attributes (D015: no selector renames), so the pipeline should be intact. This task is primarily diagnostic: run the build + E2E suite, then systematically code-review each wiring point to produce a verification matrix. If any wiring is broken, fix it.

## Steps

1. Run `make typecheck` — expect 0 errors. If errors exist, investigate and fix before proceeding.
2. Run `make css && make js-dev` — expect successful build. Note any warnings.
3. Run `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — expect 36/36 pass. If any fail, diagnose and fix.
4. Verify export wiring: Open `app/static/src/ts/modules/export.ts` and confirm it reads from `allResults[]` (accumulated in `enrichment.ts`). Trace the data flow: `enrichment.ts` accumulates results → `export.ts` reads them. Confirm `#export-btn` and `#export-dropdown` selectors match elements in `results.html`.
5. Verify dashboard-click-to-filter: Open `app/static/src/ts/modules/filter.ts` and confirm `init()` binds `.verdict-kpi-card[data-verdict]` click → `applyFilter()`. Open `app/templates/partials/_verdict_dashboard.html` and confirm `.verdict-kpi-card` elements have `data-verdict` attribute. Confirm filter reads `data-verdict`, `data-ioc-type`, `data-ioc-value` from `.ioc-card` elements — open `app/templates/partials/_ioc_card.html` to confirm attributes present.
6. Verify sort wiring: Open `app/static/src/ts/modules/cards.ts` and confirm `sortCardsBySeverity()` queries `.ioc-card` children of `#ioc-cards-grid` and reads `data-verdict`. Confirm `#ioc-cards-grid` exists in `results.html`.
7. Verify progress bar and warning banner: Confirm `#enrich-progress-fill`, `#enrich-progress-text`, and `#enrich-warning` elements exist in `app/templates/results.html`. Cross-reference with `enrichment.ts` progress update code.
8. Verify copy buttons: Confirm `.copy-btn` with `data-value` attribute present in `app/templates/partials/_ioc_card.html`. Cross-reference with `clipboard.ts` init binding.

Document results for each check in the task summary.

## Must-Haves

- [ ] `make typecheck` passes with 0 errors
- [ ] `make css && make js-dev` build succeeds
- [ ] E2E suite passes 36/36
- [ ] Export wiring verified: `allResults[]` accumulation → export.ts consumption path intact
- [ ] Dashboard-click-to-filter wiring verified: `.verdict-kpi-card[data-verdict]` → `applyFilter()` chain intact
- [ ] Verdict sorting verified: `sortCardsBySeverity()` → `.ioc-card[data-verdict]` chain intact
- [ ] Progress bar elements present: `#enrich-progress-fill`, `#enrich-progress-text`
- [ ] Warning banner element present: `#enrich-warning`
- [ ] Copy button wiring verified: `.copy-btn[data-value]` in template, `clipboard.ts` binds it

## Verification

- `make typecheck` — 0 errors
- `make css && make js-dev` — exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36/36 pass
- Each wiring point documented with file:line evidence

## Inputs

- All S01–S03 code in working tree (no changes expected from this task)
- D015 decision: no selector renames — all `.ioc-card`, `data-*` attributes preserved
- S03 forward intelligence: `injectDetailLink()` depends on `.ioc-card`'s `data-ioc-type` and `data-ioc-value`

## Expected Output

- Verification matrix documenting pass/fail for each R008 sub-feature with file:line evidence
- If any fixes were needed: the fix applied with explanation of what broke
- All builds and tests green
