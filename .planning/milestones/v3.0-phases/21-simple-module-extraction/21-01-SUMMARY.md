---
phase: 21-simple-module-extraction
plan: "01"
subsystem: ui
tags: [typescript, dom, modules, settings, scroll, animation]

# Dependency graph
requires:
  - phase: 20-type-definitions-foundation
    provides: "ioc.ts and api.ts shared type layer (available for import)"
provides:
  - "attr() DOM utility helper in utils/dom.ts — null-safe getAttribute returning string"
  - "settings.ts init() — API key show/hide toggle with HTMLInputElement typing"
  - "ui.ts init() — scroll-aware filter bar and card stagger animation"
affects: [22-module-extraction-continued, 23-typescript-bundle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single named export per module (attr for utils, init for feature modules)"
    - "Null guard pattern: if (!el) return — no non-null assertions"
    - "document.querySelector<HTMLElement>() for typed DOM queries"
    - "forEach((item, i)) over indexed for-loop to satisfy noUncheckedIndexedAccess"
    - "classList.toggle(class, bool) over if/else add/remove pair"

key-files:
  created:
    - app/static/src/ts/utils/dom.ts
    - app/static/src/ts/modules/settings.ts
    - app/static/src/ts/modules/ui.ts
  modified: []

key-decisions:
  - "settings.ts casts getElementById result to HTMLInputElement|null — required to access .type property, avoids non-null assertion"
  - "ui.ts uses classList.toggle(class, bool) — cleaner than if/else add/remove, identical behavior"
  - "ui.ts uses forEach() not indexed for-loop — avoids noUncheckedIndexedAccess compile error on NodeListOf"

patterns-established:
  - "Module pattern: single init() export calls private helper functions"
  - "DOM null safety: cast to specific element type | null, guard with if (!el) return"
  - "utils/ directory: shared helpers imported by feature modules"

requirements-completed: [MOD-07, MOD-08]

# Metrics
duration: 3min
completed: 2026-02-28
---

# Phase 21 Plan 01: Simple Module Extraction Summary

**Three TypeScript modules extracted from main.js: attr() DOM utility, settings API-key toggle, and scroll/stagger UI enhancements — all passing strict typecheck with zero errors**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-28T15:32:52Z
- **Completed:** 2026-02-28T15:35:40Z
- **Tasks:** 2
- **Files modified:** 3 created, 0 modified

## Accomplishments
- Created `utils/dom.ts` with `attr()` helper — typed getAttribute wrapper that returns string (not string|null), with optional fallback parameter
- Created `modules/settings.ts` with `init()` — API key show/hide toggle, casting getElementById to HTMLInputElement|null for typed access to `.type`
- Created `modules/ui.ts` with `init()` — scroll-aware filter bar using classList.toggle() and card stagger using forEach() to satisfy noUncheckedIndexedAccess

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DOM utilities and settings module** - `3551ae7` (feat)
2. **Task 2: Create UI utilities module** - `518b4a4` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/static/src/ts/utils/dom.ts` - Typed getAttribute wrapper returning string with optional fallback
- `app/static/src/ts/modules/settings.ts` - API key show/hide toggle, init() export
- `app/static/src/ts/modules/ui.ts` - Scroll-aware filter bar + card stagger, init() export

## Decisions Made
- `settings.ts` casts `getElementById("api-key")` to `HTMLInputElement | null` — the only way to access `.type` without a non-null assertion under strict mode
- `ui.ts` uses `classList.toggle("is-scrolled", scrolled)` rather than the if/else add/remove pattern from main.js — simpler, identical behavior
- `ui.ts` uses `.forEach((card, i) =>` instead of indexed for-loop — avoids `noUncheckedIndexedAccess` compile error on `NodeListOf<HTMLElement>`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all three files passed `make typecheck` on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The module authoring pattern is established: single `init()` export, private helpers, null guards, no non-null assertions
- `utils/dom.ts` with `attr()` is ready for import by form.ts, clipboard.ts, cards.ts, and filter.ts in Phase 21 Plan 02
- Phase 22 (continued extraction) can proceed immediately

---
*Phase: 21-simple-module-extraction*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: app/static/src/ts/utils/dom.ts
- FOUND: app/static/src/ts/modules/settings.ts
- FOUND: app/static/src/ts/modules/ui.ts
- FOUND: commit 3551ae7 (feat(21-01): add DOM util attr() helper and settings module)
- FOUND: commit 518b4a4 (feat(21-01): add UI module with scroll-aware filter bar and card stagger)
