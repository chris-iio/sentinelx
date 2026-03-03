---
phase: 21-simple-module-extraction
plan: "03"
subsystem: ui
tags: [typescript, cards, filter, dom, verdict, ioc]

# Dependency graph
requires:
  - phase: 20-type-definitions
    provides: VerdictKey, VERDICT_SEVERITY, VERDICT_LABELS from types/ioc.ts
  - phase: 21-01
    provides: attr() helper from utils/dom.ts

provides:
  - cards.ts with 5 exported functions (init, findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity)
  - filter.ts with init() encapsulating all filter bar event wiring

affects: [22-enrichment-module, 23-main-entry]

# Tech tracking
tech-stack:
  added: []
  patterns: [forEach-replaces-IIFE-for-loop, ReturnType-typeof-setTimeout, attr-helper-replaces-getAttribute, narrowed-const-for-closure-null-safety]

key-files:
  created:
    - app/static/src/ts/modules/cards.ts
    - app/static/src/ts/modules/filter.ts
  modified: []

key-decisions:
  - "cards.ts init() is a no-op placeholder — cards functions are called by enrichment module, not on DOMContentLoaded"
  - "FilterState interface defined inside filter.ts (not exported) — it is an implementation detail, not part of the public API"
  - "filterRoot narrowed from HTMLElement|null to HTMLElement after null guard, assigned to typed const — required for TypeScript closure safety"
  - "as VerdictKey cast on attr() result in doSortCards — acceptable since values come from data-verdict attributes that the module itself sets"

patterns-established:
  - "Narrowed const pattern: const el = document.getElementById('x'); if (!el) return; const typed: HTMLElement = el — required when closures reference variables that tsc cannot re-narrow"
  - "forEach replaces IIFE-in-for-loop: forEach with arrow functions gives block scope without the var closure capture bug workaround"
  - "attr() everywhere: all getAttribute calls replaced with attr() from utils/dom — returns string (not string|null), eliminates manual fallbacks"

requirements-completed: [MOD-05, MOD-06]

# Metrics
duration: 8min
completed: 2026-03-01
---

# Phase 21 Plan 03: Cards and Filter Module Summary

**cards.ts exporting 4-function public API for enrichment consumption plus filter.ts closure-pattern module with IIFE-to-forEach migration, all passing strict TypeScript under noUncheckedIndexedAccess**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-01T15:36:36Z
- **Completed:** 2026-03-01T15:44:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- cards.ts provides the 4 functions enrichment.ts will import: findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity — plus init() placeholder
- filter.ts ports 110-line initFilterBar() into a typed module with FilterState interface, forEach closures, and attr() throughout
- Zero TypeScript errors across all 5 modules in app/static/src/ts/ (dom, settings, ui, cards, filter)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create card management module** - `4d7c36d` (feat)
2. **Task 2: Create filter bar module** - `e46263e` (feat)

## Files Created/Modified

- `app/static/src/ts/modules/cards.ts` — Card verdict updates, dashboard counts, debounced severity sort; imports VERDICT_SEVERITY/VERDICT_LABELS from types/ioc and attr from utils/dom
- `app/static/src/ts/modules/filter.ts` — Filter bar wiring with FilterState interface; verdict/type/search filtering plus dashboard badge click sync

## Decisions Made

- `init()` in cards.ts is a deliberate no-op: card functions are invoked by the enrichment module during poll results, not during page load setup
- FilterState interface stays internal to filter.ts — it is not part of the public contract, only `init()` is exported
- `filterRoot` narrowed after null guard into a new typed const — TypeScript cannot re-narrow a variable captured in a nested function closure, so assigning to a typed const is the correct pattern
- `as VerdictKey` cast in doSortCards sort comparator is safe: data-verdict values on .ioc-card elements are set exclusively by updateCardVerdict which already takes VerdictKey

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript closure null narrowing failure in filter.ts**
- **Found during:** Task 2 (filter bar module)
- **Issue:** `filterRoot` typed as `HTMLElement | null` — TypeScript cannot re-narrow it inside nested `applyFilter()` function even after early return guard at top of `init()`
- **Fix:** Added `const filterRoot: HTMLElement = filterRootEl;` after null check, using a typed const that TypeScript knows is non-null throughout the closure
- **Files modified:** app/static/src/ts/modules/filter.ts
- **Verification:** `make typecheck` exits 0
- **Committed in:** e46263e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - type narrowing bug)
**Impact on plan:** Required fix to satisfy strict TypeScript null checking in closure context. No scope creep, no behavioral change.

## Issues Encountered

None beyond the auto-fixed TypeScript narrowing issue above.

## Next Phase Readiness

- cards.ts public API (findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity) is ready for Phase 22's enrichment.ts to import
- All 5 Phase 21 modules passing strict TypeScript: dom, settings, ui, cards, filter
- Phase 22 will extract the enrichment polling loop (the most complex module) and wire all modules together in main.ts

## Self-Check: PASSED

All created files confirmed on disk. All task commits confirmed in git history.

---
*Phase: 21-simple-module-extraction*
*Completed: 2026-03-01*
