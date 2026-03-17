---
id: T01
parent: S01
milestone: M002
provides:
  - Single-column full-width row layout for IOC cards (no 2-column breakpoint)
  - Compact inline flex bar for verdict dashboard
  - Single-row flex layout for filter bar
  - display:flex on .ioc-card enabling vertical composition of card regions
key_files:
  - app/static/src/input.css
  - app/templates/partials/_ioc_card.html
  - app/templates/partials/_verdict_dashboard.html
  - app/templates/partials/_filter_bar.html
  - app/templates/results.html
key_decisions:
  - All structural CSS was already migrated to the target state in prior worktree setup; T01 added display:flex;flex-direction:column to .ioc-card as the only missing piece
  - No template structure changes were needed — DOM contracts were already intact
  - tools/tailwindcss and tools/esbuild binaries were absent and installed via make tailwind-install / esbuild-install
patterns_established:
  - .ioc-card uses flex-direction column; .ioc-card-header inside uses flex row (header + enrichment slot stack vertically)
  - Verdict dashboard uses flex-direction row with border-right dividers and border-top color accent per verdict
  - Filter bar uses flex row with flex-wrap for responsive single-row collapse
observability_surfaces:
  - "make css exits 0: Tailwind compiles cleanly, no warnings about unused grid selectors"
  - "make typecheck exits 0: zero TS errors, confirming all DOM contract selectors intact"
  - "make js-dev exits 0: bundle builds at 194.9kb"
  - "grep -A 3 '.ioc-card {' app/static/src/input.css — confirm display:flex present"
  - "grep -n 'grid-cols-2|repeat(2' app/static/src/input.css — must return 0 lines"
duration: 15min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Convert grid layout to single-column rows — restructure templates + structural CSS

**Added `display:flex;flex-direction:column` to `.ioc-card` to complete single-column row layout; all DOM contracts, build tools, and structural CSS were already in target state.**

## What Happened

On inspection, the working tree already had the structural CSS and template DOM in the target state:
- `.ioc-cards-grid` already had `grid-template-columns: 1fr` with no 2-column media query breakpoint
- `#verdict-dashboard` already had `display: flex; flex-direction: row` (compact inline bar)
- `.filter-bar` already had `display: flex; flex-direction: row`
- All four template partials already had the correct horizontal row composition with all contract selectors intact

The one missing piece was `display: flex; flex-direction: column` on `.ioc-card` itself (the plan's diagnostic check requires this). This was added as the sole CSS change.

Additionally, `tools/tailwindcss` and `tools/esbuild` binaries were absent (not committed to the worktree). Both were installed via `make tailwind-install` and `make esbuild-install` before verification.

## Verification

- `make css` exits 0 — Tailwind compiled cleanly (461ms)
- `make typecheck` exits 0 — TypeScript passes with zero errors
- `make js-dev` exits 0 — esbuild bundle at 194.9kb
- All contract selectors confirmed present via grep:
  - `.ioc-card` root retains `data-ioc-value`, `data-ioc-type`, `data-verdict` attributes
  - `#ioc-cards-grid` in results.html
  - `#verdict-dashboard` in _verdict_dashboard.html
  - `.filter-bar-wrapper`, `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input` in _filter_bar.html
  - `.ioc-context-line`, `.verdict-label`, `.ioc-type-badge`, `.copy-btn` in _ioc_card.html
  - `[data-verdict-count]` on all 5 verdict kpi spans in _verdict_dashboard.html
  - `.enrichment-slot` in _enrichment_slot.html (untouched)
- No `grid-cols-2` or `repeat(2` in input.css (single-column confirmed)
- `.verdict-dashboard` and `.filter-bar` both render as flex rows

## Diagnostics

```bash
# Confirm single-column grid (no 2-col breakpoint)
grep -n 'grid-cols-2\|repeat(2' app/static/src/input.css
# Expected: no output

# Confirm flex on .ioc-card
grep -A 3 '\.ioc-card {' app/static/src/input.css
# Expected: display: flex; flex-direction: column;

# Confirm all data attrs on card root
grep 'data-ioc-value\|data-ioc-type\|data-verdict' app/templates/partials/_ioc_card.html | head -1
# Expected: line containing class="ioc-card" data-ioc-value=...

# All three builds
make css && make typecheck && make js-dev
```

## Deviations

The task plan described substantial restructuring of all four template files. In practice, the working tree had already been set up with the target DOM structure as part of milestone initialization — no template structural changes were needed. Only the single CSS addition (`display:flex` on `.ioc-card`) was required to satisfy the plan's diagnostic check and complete the layout contract.

## Known Issues

None. All must-haves satisfied.

## Files Created/Modified

- `app/static/src/input.css` — Added `display:flex;flex-direction:column` to `.ioc-card` rule block
