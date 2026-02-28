---
phase: 13-results-page-redesign
plan: "02"
subsystem: ui
tags: [tailwind, css-custom-properties, heroicons, jinja2, hover, animation]

# Dependency graph
requires:
  - phase: 13-results-page-redesign
    plan: "01"
    provides: "Jinja2 partial templates including _filter_bar.html and _ioc_card.html for independent editability"

provides:
  - "IOC card hover lift via translateY(-1px) + box-shadow + border-color transition"
  - "IOC type badge colored dot indicator via ::before pseudo-element using currentColor"
  - "Search input magnifying-glass icon prefix with .filter-search-wrapper layout"
  - "magnifying-glass outline icon in Heroicons macro (variant=outline support)"
  - "RESULTS-08 left-border accent confirmed present (existing implementation verified)"

affects:
  - 13-04-PLAN (visual verification checkpoint for all Phase 13 changes)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Outline icon variant: icon() macro variant=outline parameter for stroke-based SVG icons"
    - "Relative-position icon prefix: wrapper div + absolute-positioned SVG + padding-left on input"
    - "currentColor dot: ::before pseudo-element with background-color:currentColor inherits parent color without per-type overrides"

key-files:
  created: []
  modified:
    - app/templates/macros/icons.html
    - app/templates/partials/_filter_bar.html
    - app/static/src/input.css
    - app/static/dist/style.css

key-decisions:
  - "Card hover lift uses transition on the base .ioc-card element to ensure smooth enter/exit; 150ms matches design spec"
  - "Dot indicator uses currentColor so each .ioc-type-badge--{type} variant automatically gets the right dot color without additional CSS selectors"
  - "icon() macro extended with variant parameter defaulting to 'solid' — backward-compatible, existing calls unchanged"
  - "RESULTS-08 (left-border accent) was already implemented in prior phase CSS — verified and documented, no changes needed"
  - "CSS for hover/dots/wrapper was committed in feat(13-03) commit 47ced4a by previous session; this plan commits the remaining template changes"

patterns-established:
  - "Icon macro variant pattern: {% if variant == 'outline' %}fill='none' stroke='currentColor'{% else %}fill='currentColor'{% endif %}"
  - "Search icon prefix: .filter-search-wrapper (position:relative) wraps .filter-search-icon (position:absolute, left:0.6rem) and input (padding-left:2rem)"

requirements-completed:
  - RESULTS-02
  - RESULTS-03
  - RESULTS-04
  - RESULTS-08

# Metrics
duration: 4min
completed: "2026-02-28"
---

# Phase 13 Plan 02: Card Hover Lift, Badge Dots & Search Icon Prefix Summary

**IOC card hover lift (translateY + shadow), type badge currentColor dot indicators, and magnifying-glass search icon prefix via extended Heroicons macro**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-28T06:30:49Z
- **Completed:** 2026-02-28T06:35:44Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- IOC card hover interaction: `.ioc-card:hover` produces translateY(-1px) lift + 0 4px 12px shadow + border-color shift, all within 150ms transition
- Type badge dot indicator: `.ioc-type-badge::before` adds a 6px circle using `background-color: currentColor`, automatically inheriting the type-specific accent color from each `.ioc-type-badge--{type}` variant — zero per-type overrides needed
- Search icon prefix: `_filter_bar.html` updated with `.filter-search-wrapper` (relative-positioned) containing the magnifying-glass SVG (absolute, left 0.6rem) and input (padding-left 2rem)
- Heroicons macro extended: `icon()` now accepts `variant="outline"` parameter, switching from `fill="currentColor"` to `fill="none" stroke="currentColor" stroke-width="1.5"` — backward-compatible
- RESULTS-08 left-border accent confirmed already present: `.ioc-card { border-left: 3px solid var(--border) }` + verdict-colored overrides for all 5 states

## Task Commits

Each task was committed atomically:

1. **Task 1: Add card hover lift, dot indicators, and search icon CSS + icon macro** - `2bf1049` (feat)
   - Note: CSS changes for hover lift, dot indicators, and search wrapper were committed in prior session as part of `47ced4a` (feat(13-03) empty state commit) — this commit covers the template changes (icons.html + _filter_bar.html)

**Plan metadata:** (committed with SUMMARY.md)

## Files Created/Modified

- `app/templates/macros/icons.html` - Added variant parameter (solid/outline) and magnifying-glass outline path
- `app/templates/partials/_filter_bar.html` - Added icon macro import, wrapped search input in .filter-search-wrapper with icon prefix
- `app/static/src/input.css` - Card hover lift (.ioc-card:hover), badge dot (::before), search wrapper CSS — committed in prior feat(13-03) commit 47ced4a
- `app/static/dist/style.css` - Rebuilt from input.css via make css

## Decisions Made

- **currentColor for dot:** The `.ioc-type-badge--{type}` variants set `color` to the type accent color. Using `background-color: currentColor` on the `::before` dot automatically picks up the right hue per type without needing 8 separate overrides — cleaner and more maintainable.
- **variant parameter default:** `variant="solid"` default ensures all existing `{{ icon("shield-check") }}` and `{{ icon("cog-6-tooth") }}` calls continue to work without modification.
- **CSS already committed:** The previous session included 13-02 CSS changes within the `feat(13-03)` commit (`47ced4a`). Rather than reverting and recommitting, the template changes were committed separately in `2bf1049`, completing the full 13-02 feature set.

## Deviations from Plan

None - plan executed exactly as written (CSS changes were already in place from prior session work).

## Issues Encountered

The previous session committed the 13-02 CSS changes (card hover lift, badge dots, search wrapper CSS) within a `feat(13-03)` commit (`47ced4a`) while skipping a dedicated 13-02 commit. The template changes (icons.html and _filter_bar.html) were left uncommitted. This plan execution completed the remaining template work and committed it as `2bf1049`.

E2E test results: 57 passed, 2 known pre-existing failures (`test_online_mode_indicator`, `test_online_mode_shows_verdict_dashboard`) — both require VT API key, not regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 4 RESULTS-02/03/04/08 requirements implemented
- Card hover lift, badge dots, and search icon prefix complete
- RESULTS-05/06/07 already completed in Plan 13-03 (committed in prior session)
- Ready for Plan 13-04: visual verification checkpoint

---
*Phase: 13-results-page-redesign*
*Completed: 2026-02-28*

## Self-Check: PASSED

- icons.html: FOUND
- _filter_bar.html: FOUND
- 13-02-SUMMARY.md: FOUND
- Commit 2bf1049: FOUND
- translateY in input.css: FOUND
- ::before in input.css: FOUND
- magnifying-glass in icons.html: FOUND
- filter-search-wrapper in _filter_bar.html: FOUND
