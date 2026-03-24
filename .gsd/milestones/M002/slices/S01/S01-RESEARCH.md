# M002/S01 — Research

**Date:** 2026-03-18

## Summary

S01 is mostly a **template/CSS rewrite with strong selector-contract constraints**, not a greenfield frontend rebuild. The current results page already has the runtime structure S02/S03 need: `.ioc-card` roots with the required `data-ioc-value` / `data-ioc-type` / `data-verdict` attributes, a per-card `.ioc-context-line` placeholder from M001/S05, and the full `.enrichment-slot` / `.chevron-toggle` / `.enrichment-details` subtree already wired by TypeScript. The biggest risk is not implementation complexity; it is accidentally breaking the existing TS + E2E contract while restyling the page.

Primary requirements targeted here are **R001** and **R003**, with supporting groundwork for **R002**, **R005**, **R006**, and **R008**. The current page is still structurally a responsive grid (`#ioc-cards-grid` becomes 2 columns at `min-width: 768px`) and still uses loud non-verdict color on IOC type badges and filter pills. That means S01 can deliver real value by changing layout and token hierarchy now, while leaving enrichment behavior, provider rendering, and filter/export logic intact.

## Recommendation

Treat S01 as a **contract-preserving layout migration**:

1. **Keep existing root selectors and data attributes** in place:
   - `.ioc-card`
   - `#ioc-cards-grid`
   - `#verdict-dashboard`
   - `.filter-bar-wrapper`
   - `.verdict-label`
   - `.ioc-type-badge`
   - `.copy-btn`
   - `.enrichment-slot`
   - `.ioc-context-line`
2. **Do not rename files/classes just because the roadmap says “replaces.”** In this codebase, changing internals is cheap; renaming contract selectors pulls in `cards.ts`, `filter.ts`, `ui.ts`, and E2E immediately.
3. **Land the single-column/list feel primarily through HTML structure + CSS**:
   - remove the 2-column grid behavior from `.ioc-cards-grid`
   - restyle each `.ioc-card` into a full-width row/list item with clearer left-to-right hierarchy
   - compress dashboard/filter chrome without changing the JS hooks that drive counts and filtering
4. **Quiet precision means muting non-verdict color everywhere**, not only on the card row. Current loud color still exists on:
   - `.ioc-type-badge--*`
   - `.filter-pill--{type}.filter-pill--active`
   - mode pills / various accents
   S01 should push those toward neutral border/text treatment so verdict remains the only loud signal.

This path keeps S01 focused on structure and design system, while preserving the existing enrichment slot so S02 can layer the at-a-glance surface into the already-working DOM.

## Implementation Landscape

### Key Files

- `app/templates/results.html` — top-level results page orchestration. Current order is `results-header` → warning/progress → `#filter-root` → optional `#verdict-dashboard` → filter bar → `#ioc-cards-grid`. This is the main place to add/adjust wrappers for the new single-column information-first composition while preserving `#filter-root`, `#verdict-dashboard`, and `#ioc-cards-grid`.
- `app/templates/partials/_ioc_card.html` — current IOC root contract. The `.ioc-card` root already carries all locked `data-*` attributes. Existing child hooks that should survive S01: `.ioc-value`, `.ioc-type-badge`, `.verdict-label`, `.copy-btn`, detail link, `.ioc-original`, `.ioc-context-line`, and conditional `.enrichment-slot` include.
- `app/templates/partials/_filter_bar.html` — JS contract is driven by `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input`, and `.filter-bar-wrapper`. The markup can be compressed into a tighter single-row structure without changing filter logic.
- `app/templates/partials/_verdict_dashboard.html` — `cards.ts` only updates `[data-verdict-count]`, and `filter.ts` only listens for clicks on `.verdict-kpi-card[data-verdict]` inside `#verdict-dashboard`. The visual structure can change a lot as long as those hooks remain.
- `app/templates/partials/_enrichment_slot.html` — already contains the S03-style expand/collapse scaffold (`.ioc-summary-row` inserted by JS, `.chevron-toggle`, `.enrichment-details`, section containers). S01 should not re-architect this subtree; only reposition/restyle around it.
- `app/static/src/input.css` — main implementation surface for S01. Current blockers to R001/R003 are here:
  - `.ioc-cards-grid` flips to 2 columns at `768px`
  - `.ioc-card` still reads as a card, not a row/list item
  - `.ioc-type-badge--*` and active filter pills are brightly type-colored
  - dashboard is still large KPI-card chrome
  - filter bar is still stacked vertically
- `app/static/src/ts/modules/cards.ts` — can remain unchanged if `.ioc-card`, `.verdict-label`, `#ioc-cards-grid`, and dashboard `data-verdict-count` hooks stay in place. If those selectors change, this file must change in the same task.
- `app/static/src/ts/modules/filter.ts` — can remain unchanged if `.ioc-card`, `.filter-bar-wrapper`, `[data-filter-verdict]`, `[data-filter-type]`, and `#filter-search-input` survive. It uses `card.style.display` directly on `.ioc-card`.
- `app/static/src/ts/modules/ui.ts` — currently toggles `.filter-bar-wrapper.is-scrolled` and sets `--card-index` on `.ioc-card`. Another reason to preserve those selectors in S01.
- `tests/e2e/pages/results_page.py` + inline selectors in `tests/e2e/test_extraction.py` / `tests/e2e/test_results_page.py` — current selectors are still hard-coded to the old contract (`.ioc-card`, `#ioc-cards-grid`, `#verdict-dashboard`, `.filter-bar-wrapper`, `.enrichment-slot`). Avoid taking an E2E migration dependency in S01 unless absolutely necessary.
- `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — explicit selector lockfile. The most fragile rule is the `.ioc-card` root data-attribute triple; moving or renaming that root silently breaks CSS, TS, filtering, and E2E together.

### Build Order

1. **Lock the DOM contract first**
   - Keep `.ioc-card` as the root list item.
   - Keep `data-ioc-value`, `data-ioc-type`, and `data-verdict` on that root.
   - Keep `#ioc-cards-grid`, `#verdict-dashboard`, `.filter-bar-wrapper`, `.ioc-context-line`, and `.enrichment-slot` present.
   - If possible, keep the existing partial filenames and only change internals.

2. **Restructure templates for the new skeleton**
   - `results.html`: simplify page composition around dashboard/filter/list.
   - `_ioc_card.html`: convert the current header into a more list-row-like internal layout (identity/meta/actions) without dropping child hooks.
   - `_filter_bar.html` and `_verdict_dashboard.html`: compress chrome while preserving data attributes and click targets.

3. **Rewrite the visual system in `input.css`**
   - Remove the 2-column breakpoint on `.ioc-cards-grid`.
   - Rework `.ioc-card` spacing/borders/hover to read as quiet full-width rows.
   - Mute `.ioc-type-badge` and type filter pill styles so verdict is the only loud color.
   - Restyle dashboard and filter bar into lighter, denser controls.
   - Preserve the existing enrichment runtime class styling unless intentionally improving layout around it.

4. **Only touch TS if the HTML contract actually changed**
   - If `.ioc-card`, `.verdict-label`, `#ioc-cards-grid`, dashboard `data-verdict-count`, and filter data attributes remain stable, S01 likely needs little or no TS work.
   - If any of those hooks move/rename, update `cards.ts`, `filter.ts`, and `ui.ts` together.

### Verification Approach

- `make typecheck` — confirms selector-preserving template changes did not force TS breakage.
- `make js-dev` — ensures the existing browser bundle still builds after any TS updates.
- `make css` — ensures the rewritten design system compiles.
- `pytest tests/e2e/test_extraction.py -q` — catches `#ioc-cards-grid`, `.ioc-card`, and base results-page regressions quickly.
- `pytest tests/e2e/test_results_page.py -q` — catches filter bar, verdict dashboard, and enrichment-slot structural regressions.
- Browser/manual spot check on `/analyze`:
  - results list is single-column at desktop widths
  - verdict remains the strongest color signal
  - filter bar still filters cards
  - online mode still shows `#verdict-dashboard` and per-card `.enrichment-slot`
  - offline mode still omits `.enrichment-slot`

## Constraints

- `.ioc-card` root must continue to carry **all three** attributes: `data-ioc-value`, `data-ioc-type`, `data-verdict`.
- `cards.ts` sorts by appending `.ioc-card` elements inside `#ioc-cards-grid`; if the root list container changes, sorting changes too.
- `filter.ts` filters by toggling `style.display` on `.ioc-card`; filtering is not abstracted through a row adapter.
- `ui.ts` sets `--card-index` on `.ioc-card` and toggles `.filter-bar-wrapper.is-scrolled`.
- `#verdict-dashboard` children still need `[data-verdict-count]` for count updates and `.verdict-kpi-card[data-verdict]` for click-to-filter.
- `_enrichment_slot.html` is already the runtime contract for S02/S03. S01 should keep it intact even if the visual treatment changes.

## Common Pitfalls

- **Renaming `.ioc-card` to `.ioc-row` too early** — this cascades into `cards.ts`, `filter.ts`, `ui.ts`, E2E selectors, and the CSS contracts file. Preserve the root selector unless the slice explicitly budgets for that migration.
- **Keeping bright type colors while only restyling verdict badges** — R003 will still fail visually because active type pills and type badges currently compete with verdict severity.
- **Compressing the dashboard but dropping JS hooks** — `#verdict-dashboard` alone is not enough; keep child `data-verdict` and `data-verdict-count` hooks or update `cards.ts` and `filter.ts` in the same change.
- **Removing `.ioc-context-line` because S01 doesn’t populate it** — S02 depends on that placeholder already existing; keep it in the new row skeleton.
- **Over-editing the enrichment subtree in S01** — expand/collapse and summary-row scaffolding already exist. Rebuilding them now would create unnecessary risk before S02/S03 use them.

## Open Risks

- The roadmap language suggests new partial names (`_ioc_row.html`, `_verdict_summary.html`), but the current codebase is safer if S01 mutates existing partials in place. Renaming files now is optional cleanup, not a functional need.
- Because the enrichment slot already exists, a big visual rewrite can accidentally make half-finished online-mode surfaces feel prominent before S02 adds the final at-a-glance presentation. Keep the enrichment area visually subordinate in S01.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Frontend UI / CSS layout | `frontend-design` | available |
