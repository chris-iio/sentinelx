---
phase: 12-shared-component-elevation
plan: "01"
subsystem: ui
tags: [css, tailwind, design-system, verdict-badges, focus-rings, buttons, wcag]

# Dependency graph
requires:
  - phase: 11-design-foundation
    provides: Design tokens (verdict color triples, accent-interactive, border-default/hover, bg-hover)
provides:
  - Unified verdict badge borders (tinted-bg + colored-border + colored-text on both badge systems)
  - Global :focus-visible rule with teal outline replacing all box-shadow focus indicators
  - Ghost button variant with hover and disabled states
  - Secondary button disabled state
affects:
  - 12-02 (results page components depend on verdict badge triple pattern)
  - 12-03 (settings page may use ghost/secondary buttons)
  - 13-page-input, 13-page-results, 13-page-settings

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Verdict triple pattern: tinted-bg + colored-border + colored-text on .verdict-badge base with border: 1px solid transparent
    - Global :focus-visible in @layer base — component overrides only add supplementary border-color shift
    - Button variants: primary (emerald), secondary (zinc), ghost (transparent+border)

key-files:
  created: []
  modified:
    - app/static/src/input.css
    - app/static/dist/style.css

key-decisions:
  - "Global :focus-visible in @layer base replaces three per-component outline: none + box-shadow patterns"
  - "border: 1px solid transparent on .verdict-badge base ensures layout stability before JS applies verdict class"
  - ".btn-ghost uses var(--border-default) not var(--border) — the more prominent 10% opacity white border"

patterns-established:
  - "Verdict triple: always use all three tokens (bg, text, border) — no mixing single tokens across badge systems"
  - "Focus rings: global :focus-visible handles outline, components only add border-color shift via :focus-visible"
  - "Button disabled: opacity 0.4 + cursor: not-allowed — consistent across primary, secondary, ghost"

requirements-completed: [COMP-01, COMP-02, COMP-03]

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 12 Plan 01: Shared Component Elevation Summary

**Unified verdict badge borders with triple pattern, global teal focus rings replacing three blue box-shadow overrides, and ghost button variant completing three-variant button system**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-27T17:16:31Z
- **Completed:** 2026-02-27T17:18:42Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `border: 1px solid transparent` to `.verdict-badge` base and `border-color: var(--verdict-*-border)` to all five `.verdict-*` enrichment badge classes — matching the triple pattern already used by `.verdict-label--*`
- Replaced three per-component `:focus { outline: none; box-shadow: ... }` overrides with a single global `:focus-visible` rule in `@layer base` using `var(--accent-interactive)` (teal-500), eliminating all blue glow focus indicators
- Added `.btn-ghost` variant (transparent + zinc border + secondary text, with hover to zinc-700 + primary text) and `.btn-secondary:disabled`, completing the three-variant button system

## Task Commits

Each task was committed atomically:

1. **Task 1: Unify verdict badge borders (COMP-01)** - `68772a6` (feat)
2. **Task 2: Standardize focus rings with global :focus-visible (COMP-02)** - `e31c565` (feat)
3. **Task 3: Add ghost button variant and secondary disabled state (COMP-03)** - `c1d9028` (feat)

## Files Created/Modified

- `app/static/src/input.css` - All CSS changes (verdict badges, focus rings, button variants)
- `app/static/dist/style.css` - Rebuilt compiled output via `make css`

## Decisions Made

- Used `border: 1px solid transparent` on `.verdict-badge` base to reserve border space before JS adds the verdict class — prevents layout shift when class is applied dynamically
- Used `var(--border-default)` (10% white opacity) for `.btn-ghost` border rather than `var(--border)` (6% white opacity) — matches the more prominent `--border-default` value to make the ghost outline visible at rest without being heavy
- Added `color 0.15s ease` to `.btn` base transition to support smooth text color changes on ghost hover — applies to all button variants without side effects

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all CSS changes compiled cleanly, 224 unit/integration tests passed without modification.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three core shared component systems elevated: verdict badges, focus rings, button variants
- `input.css` design tokens remain the single source — no hardcoded colors introduced
- Phase 12 Plan 02 (results page component elevation) can proceed, depending on the verdict triple pattern now applied to both badge systems

---
*Phase: 12-shared-component-elevation*
*Completed: 2026-02-27*
