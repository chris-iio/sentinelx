---
phase: 01-contracts-and-foundation
plan: 01
subsystem: ui
tags: [css, tailwind, playwright, e2e, contracts, documentation]

# Dependency graph
requires: []
provides:
  - "CSS-CONTRACTS.md: authoritative do-not-rename catalog for 24 E2E selectors, 18 JS-created classes, 3 data-attribute contracts"
  - "Inline contract comment in _ioc_card.html documenting triple-consumer data-attribute contract"
  - "CSS layer ownership rule in input.css preventing Tailwind/component class specificity conflicts"
  - "E2E baseline confirmation: 89/91 (2 pre-existing title capitalization failures unrelated to Phase 1)"
affects:
  - phase: 02-typescript-extractions
    reason: CSS class renames in enrichment.ts must check CSS-CONTRACTS.md first
  - phase: 03-visual-redesign
    reason: All CSS changes must respect component class ownership rule from input.css comment
  - phase: 04-template-restructuring
    reason: Template edits must not move data-ioc-value, data-ioc-type, data-verdict off .ioc-card root
  - phase: 05-context-and-staleness
    reason: New elements must follow CSS layer ownership rule (Tailwind only for new structures)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Catalog-then-comment: enumerate all contracts in CSS-CONTRACTS.md, then add inline comments in source files pointing back to it"
    - "CSS layer ownership: component classes own all visual properties for existing elements; Tailwind utilities for new layout structures only"
    - "Data-attribute triple-consumer: data-ioc-value, data-ioc-type, data-verdict locked on .ioc-card root permanently"

key-files:
  created:
    - .planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md
  modified:
    - app/templates/partials/_ioc_card.html
    - app/static/src/input.css

key-decisions:
  - "E2E baseline is 89/91 — 2 pre-existing failures in test_homepage.py and test_settings.py (page title capitalization mismatch: expects 'SentinelX', actual 'sentinelx'); these predate Phase 1 and are out of scope"
  - "CSS-CONTRACTS.md placed in .planning/phases/01-contracts-and-foundation/ (not milestone-level) — it is produced by Phase 1 and consumed by subsequent phases via path reference"
  - "18 JS-created runtime classes catalogued separately from 24 template-sourced classes — both are equally contractual because E2E tests can query runtime DOM"

patterns-established:
  - "CSS contract catalog: all locked selectors documented in CSS-CONTRACTS.md; source files carry inline comments pointing to it"
  - "DO NOT RENAME discipline: catalog entries must be updated before any CSS class rename, not after"
  - "E2E as enforcement: the existing 89-test suite is the runtime enforcement mechanism; no new linting tools needed"

requirements-completed: []

# Metrics
duration: 3min
completed: 2026-03-17
---

# Phase 1 Plan 01: CSS-CONTRACTS.md catalog with triple-consumer data-attribute contracts and layer ownership rule

**CSS contract catalog documents 24 E2E-locked selectors, 18 JS-created runtime classes, and 3 data-attribute triple-consumer contracts with inline annotations at point-of-change in source files**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-16T20:07:06Z
- **Completed:** 2026-03-16T20:10:45Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 annotated)

## Accomplishments

- Created `CSS-CONTRACTS.md` with 7 sections covering all locked contracts — 58 table rows total, verified against actual source files
- Added Jinja2 comment to `_ioc_card.html` documenting the data-attribute triple-consumer contract with all 4 consumers explicitly named at point of change
- Added CSS layer ownership rule to `input.css` header distinguishing component classes (own all visual properties) from Tailwind utilities (new structures only)
- Confirmed E2E baseline: 89 passed, 2 pre-existing failures (title capitalization, unrelated to Phase 1)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CSS-CONTRACTS.md catalog** - `dcadc97` (docs)
2. **Task 2: Add inline contract comments and confirm E2E baseline** - `3e60cb2` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — authoritative do-not-rename catalog: 24 E2E-locked selectors, 18 JS-created runtime classes, 3 data-attribute contracts, information density acceptance criteria, CSS layer ownership rule, internal-only class documentation
- `app/templates/partials/_ioc_card.html` — Jinja2 contract comment added at top: documents data-ioc-value, data-ioc-type, data-verdict triple-consumer contract with all 4 consumers named; HTML body unchanged
- `app/static/src/input.css` — CSS LAYER OWNERSHIP RULE block added to header comment: component classes own all visual properties for existing elements; Tailwind utilities reserved for new layout structures only

## Decisions Made

- **E2E baseline is 89/91, not 91/91.** Two pre-existing failures in `test_homepage.py::test_page_title` and `test_settings.py::test_settings_page_title_tag` assert `expect(page).to_have_title("SentinelX")` but the actual title is `"sentinelx"` (lowercase). These existed before Phase 1, confirmed by stash-and-run verification. Out of scope for this plan.
- **CSS-CONTRACTS.md lives in `.planning/phases/01-contracts-and-foundation/`** (not milestone-level `.planning/`) — keeps phase artifacts co-located with their producing phase; downstream phases reference via explicit path.
- **18 JS-created runtime classes catalogued** in a dedicated section — the research identified that template classes and JS-created classes are equally fragile; missing either category would leave silent rename risk.

## Deviations from Plan

None — plan executed exactly as written. All 7 required sections in CSS-CONTRACTS.md, both inline annotations added, E2E baseline confirmed (pre-existing failures documented as out-of-scope per plan instruction).

## Issues Encountered

2 pre-existing E2E failures discovered during baseline run:
- `test_homepage.py::test_page_title[chromium]` — expects `"SentinelX"`, actual `"sentinelx"`
- `test_settings.py::test_settings_page_title_tag[chromium]` — same title capitalization mismatch

Per plan instructions: "If any test fails, it is a pre-existing issue unrelated to Phase 1 — document it but do not attempt to fix it in this plan." Confirmed pre-existing via stash verification.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 2 (TypeScript Extractions) can proceed immediately: CSS-CONTRACTS.md is the reference that Task extractors must check before renaming any class in `enrichment.ts`
- The `_ioc_card.html` inline comment explicitly warns about the data-attribute consumers at the most likely point of accidental breakage during Phase 4 template work
- The `input.css` layer ownership rule is in place before any visual work begins in Phase 3

---
*Phase: 01-contracts-and-foundation*
*Completed: 2026-03-17*
