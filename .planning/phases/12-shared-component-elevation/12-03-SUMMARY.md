---
phase: 12-shared-component-elevation
plan: "03"
subsystem: ui
tags: [heroicons, jinja2, svg-macro, inter-variable, emerald-accent, header-footer]

# Dependency graph
requires:
  - phase: 12-shared-component-elevation
    provides: COMP-01 through COMP-05 — unified verdict badges, focus rings, ghost button, form-input, filter bar
  - phase: 11-foundation-design-tokens
    provides: CSS custom properties for --font-ui, --accent, --weight-heading, --text-secondary
provides:
  - Jinja2 icon macro at templates/macros/icons.html (shield-check, cog-6-tooth Heroicons v2 inline SVG)
  - Header brand name with Inter Variable and emerald accent on "Sentinel" via .brand-accent CSS class
  - Footer updated from "Phase 1 Offline Pipeline" placeholder to "IOC Triage Tool"
  - Nav link cog icon using the macro system
  - .nav-icon CSS utility class for inline SVG sizing/alignment
affects:
  - phase-13-results-page
  - phase-14-input-page

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Jinja2 macro for inline SVG icons — avoids CDN dependency and enables full CSS currentColor control"
    - "Icon usage via {{ icon('name', class='w-4 h-4') }} — class parameterized for size flexibility"
    - "Brand accent via span.brand-accent wrapping partial text — no duplicate markup needed"

key-files:
  created:
    - app/templates/macros/icons.html
  modified:
    - app/templates/base.html
    - app/static/src/input.css
    - app/static/dist/style.css

key-decisions:
  - "Heroicons v2 24px solid variant SVG paths embedded directly in macro — avoids CDN, enables currentColor"
  - "brand-accent wraps only 'Sentinel' substring inside site-logo — minimal markup change for visual accent"
  - "Tagline changed from 'Offline IOC Extractor' to 'IOC Triage Tool' — reflects dual online/offline capability"
  - ".nav-icon uses vertical-align: -3px for optical baseline alignment with nav-link text"
  - ".site-logo font-family changed from var(--font-mono) to var(--font-ui) — brand name in Inter, not JetBrains Mono"

patterns-established:
  - "Icon macro: all icons via {% from 'macros/icons.html' import icon %} then {{ icon('name') }}"
  - "Inline SVG icons: aria-hidden by default, aria-label optional parameter for semantic icons"

requirements-completed:
  - COMP-06
  - COMP-07

# Metrics
duration: continuation
completed: 2026-02-27
---

# Phase 12 Plan 03: Shared Component Elevation — Icons + Header/Footer Summary

**Heroicons v2 Jinja2 macro system with parameterized inline SVG, emerald brand accent on header "Sentinel" text, and updated footer replacing Phase 1 placeholder copy**

## Performance

- **Duration:** Continuation session (visual checkpoint approved by user)
- **Started:** 2026-02-27
- **Completed:** 2026-02-27T17:40:59Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 4

## Accomplishments

- Created Heroicons Jinja2 macro at `app/templates/macros/icons.html` providing shield-check and cog-6-tooth inline SVG icons with full CSS currentColor support (COMP-06)
- Redesigned header with emerald brand accent on "Sentinel" text using Inter Variable typography and added cog icon to Settings nav link (COMP-07)
- Updated footer from "Phase 1 Offline Pipeline" placeholder to "IOC Triage Tool" to reflect current functionality
- Visual verification checkpoint approved — all Phase 12 components (COMP-01 through COMP-07) confirmed rendering correctly

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Heroicons Jinja2 macro and update header/footer (COMP-06 + COMP-07)** - `0b8d7e6` (feat)
2. **Task 2: Visual verification of all Phase 12 components** - Checkpoint approved (no code commit)

## Files Created/Modified

- `app/templates/macros/icons.html` — New Heroicons v2 macro file with shield-check and cog-6-tooth SVG paths
- `app/templates/base.html` — Added icon macro import, emerald brand-accent span, updated tagline and footer text, cog icon in nav
- `app/static/src/input.css` — Added .brand-accent, .nav-icon CSS classes; updated .site-logo to use var(--font-ui); added font-family to .site-footer
- `app/static/dist/style.css` — Generated output (make css)

## Decisions Made

- Used Heroicons v2 24px solid variant SVG paths embedded directly in the macro rather than loading from CDN — ensures offline operation, enables full CSS `currentColor` inheritance for icon color
- `brand-accent` wraps only the "Sentinel" substring inside `site-logo` span — minimal markup change that achieves the visual accent without duplicating the full brand name in markup
- Tagline changed from "Offline IOC Extractor" to "IOC Triage Tool" — the tool now supports both offline and online (VirusTotal enrichment) modes, making "offline" in the tagline misleading
- `.nav-icon` uses `vertical-align: -3px` for optical baseline alignment — negative offset corrects the visual baseline drop that inline-block SVGs exhibit next to text
- `.site-logo` font-family changed from `var(--font-mono)` to `var(--font-ui)` — brand name should use Inter Variable (UI font), not JetBrains Mono (code font)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all steps completed without errors. Flask unit/integration tests passed with no TemplateNotFound errors after icon macro import was added to base.html.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 12 is fully complete (all 7 COMP requirements delivered across plans 01-03):
- COMP-01: Verdict badge triple pattern (tinted-bg + border + colored-text)
- COMP-02: Global :focus-visible with 2px teal outline
- COMP-03: Ghost button variant
- COMP-04: .form-input dark-theme class
- COMP-05: Frosted-glass filter bar backdrop
- COMP-06: Heroicons Jinja2 macro system
- COMP-07: Header/footer with Inter Variable + emerald brand accent

Phase 13 (Results Page) can begin immediately. The icon macro (shield-check for empty state), verdict triple tokens, focus rings, and form-input classes are all available for use.

## Self-Check: PASSED

- `app/templates/macros/icons.html` — FOUND
- `.planning/phases/12-shared-component-elevation/12-03-SUMMARY.md` — FOUND
- Commit `0b8d7e6` (Task 1: Heroicons Jinja2 macro + header/footer) — FOUND

---
*Phase: 12-shared-component-elevation*
*Completed: 2026-02-27*
