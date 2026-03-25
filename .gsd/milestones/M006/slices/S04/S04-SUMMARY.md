---
id: S04
parent: M006
milestone: M006
provides:
  - Fully tokenized index page CSS — all pages now share the same design token system
  - Correct vertical stacking layout for input card + recent analyses list
requires:
  - slice: S01
    provides: Recent analyses list HTML structure in index.html with .recent-analyses CSS classes
affects:
  []
key_files:
  - app/static/src/input.css
  - app/static/dist/style.css
key_decisions:
  - Replace transition:all with explicit property list on .btn to follow 'never use transition: all' design principle
  - Map .alert-error hardcoded #ff6b6b to var(--verdict-malicious-text) design token for consistency
patterns_established:
  - All index page CSS rules now use design tokens exclusively — no hardcoded colors, timings, or easing functions remain in the index page section
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M006/slices/S04/tasks/T01-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T12:21:23.370Z
blocker_discovered: false
---

# S04: Input Page Redesign

**Fixed .page-index flex layout (row→column) and replaced all remaining hardcoded transition timings and colors with design tokens for full quiet-precision consistency.**

## What Happened

The index page already used most design tokens from M002 (zinc surfaces, Inter Variable font, sky-blue accents), and S01 added a well-tokenized recent analyses list. However, `.page-index` defaulted to `flex-direction: row`, causing the input card and recent analyses list to sit side-by-side instead of stacking vertically — the primary visual bug this slice was created to fix.

T01 fixed the layout by setting `flex-direction: column; align-items: center` on `.page-index` and removing the now-unnecessary `justify-content: center`. A full audit of all index page CSS rules (lines 276–500) and recent analyses rules (lines 1977–2055) revealed five additional token inconsistencies:

1. Mode toggle track transition: hardcoded `0.2s ease` → `var(--duration-fast) var(--ease-out-quart)`
2. Mode toggle thumb transition: hardcoded `0.2s ease` → `var(--duration-fast) var(--ease-out-quart)`
3. Mode toggle label transition: hardcoded `0.15s ease` → `var(--duration-fast) var(--ease-out-quart)`
4. `.btn` base rule: `transition: all` → explicit property list (background-color, border-color, color, opacity, transform)
5. `.alert-error` color: hardcoded `#ff6b6b` → `var(--verdict-malicious-text)`

The recent analyses section added in S01 was already fully tokenized and required no changes. Only `app/static/src/input.css` was edited; no template changes were needed. The built `app/static/dist/style.css` was regenerated via `make css`.

## Verification

Independent verification performed (not trusting task summaries per KNOWLEDGE.md rule):

1. `make css` — builds cleanly, exit 0
2. `make js` — builds cleanly (30.2kb bundle), exit 0
3. `grep -n 'flex-direction' app/static/src/input.css` — confirms `.page-index` at line 278 has `flex-direction: column`
4. `grep -n 'transition: all' app/static/src/input.css` — no matches on `.btn` (only 2 unrelated matches at lines 794/866)
5. `grep -n '#ff6b6b' app/static/src/input.css` — zero matches (hardcoded color eliminated)
6. `git diff HEAD~1 -- app/static/src/input.css` — confirms exactly 6 hunks of CSS-only changes
7. `python3 -m pytest tests/e2e/test_homepage.py -v` — 11/11 pass
8. `python3 -m pytest tests/test_history_routes.py -v` — 13/13 pass
9. `python3 -m pytest --tb=short -q` — 1043 passed, zero failures, zero regressions

## Requirements Advanced

None.

## Requirements Validated

- R013 — .page-index uses flex-direction:column + align-items:center. All transitions use --duration-fast/--ease-out-quart tokens. .alert-error uses var(--verdict-malicious-text). .btn uses explicit property list. All 1043 tests pass with zero regressions.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None. All changes align with the task plan.

## Known Limitations

Two `transition: all` usages remain at lines 794 and 866 in input.css — these are on `.filter-pill` and `.chevron-icon-wrapper` components from the results page section, outside the scope of this index-page-focused slice.

## Follow-ups

The remaining two `transition: all` instances (lines 794, 866) on results page components could be converted to explicit property lists in a future cleanup pass.

## Files Created/Modified

- `app/static/src/input.css` — Fixed .page-index flex-direction to column, replaced hardcoded transition timings on mode toggle components with design tokens, replaced transition:all on .btn with explicit property list, replaced hardcoded #ff6b6b on .alert-error with var(--verdict-malicious-text)
- `app/static/dist/style.css` — Rebuilt via make css — reflects all input.css changes in minified output
