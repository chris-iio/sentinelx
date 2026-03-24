---
id: T01
parent: S01
milestone: M001
provides:
  - "CSS-CONTRACTS.md: authoritative do-not-rename catalog for 24 E2E selectors, 18 JS-created classes, 3 data-attribute contracts"
  - "Inline contract comment in _ioc_card.html documenting triple-consumer data-attribute contract"
  - "CSS layer ownership rule in input.css preventing Tailwind/component class specificity conflicts"
  - "E2E baseline confirmation: 89/91 (2 pre-existing title capitalization failures unrelated to Phase 1)"
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---
# T01: 01-contracts-and-foundation 01

**# Phase 1 Plan 01: CSS-CONTRACTS.md catalog with triple-consumer data-attribute contracts and layer ownership rule**

## What Happened

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
