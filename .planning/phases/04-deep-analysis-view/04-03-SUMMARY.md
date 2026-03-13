---
phase: 04-deep-analysis-view
plan: 03
subsystem: ui
tags: [flask, typescript, sqlite, annotations, csrf, filter]

# Dependency graph
requires:
  - phase: 04-01
    provides: AnnotationStore with notes/tags CRUD and get_all_for_ioc_values
  - phase: 04-02
    provides: ioc_detail.html with .page-ioc-detail root, textarea, tag input, graph
provides:
  - Annotation API routes (POST notes, POST/DELETE tags) with rate limiting
  - annotations.ts client module for notes save and tag add/delete on detail page
  - Tags displayed as pills on IOC cards in results list
  - Tag filter dimension in filter bar (clickable pills filter results)
  - CSRF token sent via X-CSRFToken header on all annotation mutations
affects: [results-page, filter-bar, ioc-detail-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Annotation API routes follow same limiter.limit decorator pattern as existing routes
    - CSRF header (X-CSRFToken) accepted by Flask-WTF CSRFProtect automatically for JSON requests
    - Tag filter pills rendered dynamically from data-tags attributes at init time
    - DOM safety: createElement + textContent only in annotations.ts (SEC-08)

key-files:
  created:
    - app/static/src/ts/modules/annotations.ts
  modified:
    - app/routes.py
    - app/templates/ioc_detail.html
    - app/templates/partials/_ioc_card.html
    - app/static/src/ts/modules/filter.ts
    - app/static/src/ts/main.ts
    - tests/test_ioc_detail_routes.py

key-decisions:
  - "Annotation API routes use AnnotationStore() directly (no injection) — consistent with existing route pattern"
  - "annotations.ts clears server-rendered tag pills on load and re-renders from data-tags — avoids duplication when JS is present"
  - "Tag dedup on POST is idempotent: read current list, append only if absent, save — no unique constraint needed"
  - "filter.ts tag pill row inserted after .filter-bar, using insertBefore for correct DOM position"

patterns-established:
  - "data-tags JSON attribute on .ioc-card and .page-ioc-detail — single source of truth for tag state"
  - "Filter dimension pattern: add field to FilterState, add match logic in applyFilter, add UI row after init"

requirements-completed: [DEEP-02, DEEP-03]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 4 Plan 3: Annotation API + Tags + Filter Summary

**Per-IOC notes and tags via JSON API with CSRF header auth, tag pills on results cards, and clickable tag filter in filter bar**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T14:43:09Z
- **Completed:** 2026-03-13T14:48:34Z
- **Tasks:** 2 auto tasks complete (Task 3 is checkpoint awaiting human verify)
- **Files modified:** 7

## Accomplishments
- Three annotation API routes with rate limiting: POST notes (10K cap), POST tag (dedup), DELETE tag
- annotations.ts: notes save with CSS "Saved" feedback, tag add/delete via fetch with X-CSRFToken header
- Tags on results page: `_ioc_card.html` renders data-tags attribute and static tag pills from annotations_map
- filter.ts: `tag` dimension added to FilterState; tag filter pill row rendered dynamically from card data-tags
- TDD: 15 new tests written (RED commit) then all pass (GREEN commits) for all annotation API behaviors

## Task Commits

Each task was committed atomically:

1. **RED: Test suite for annotation API + tags on results** - `551a75c` (test)
2. **Task 1: Annotation API routes + annotations.ts client module** - `7d0ef12` (feat)
3. **Task 2: Tags on results page + filter bar tag dimension** - `5961033` (feat)

_Note: TDD tasks have a RED commit followed by implementation commit_

## Files Created/Modified
- `app/static/src/ts/modules/annotations.ts` - Notes + tags CRUD via fetch API, CSRF header, DOM-safe pill rendering
- `app/routes.py` - Three annotation API routes + annotations_map in analyze route
- `app/templates/ioc_detail.html` - data-tags attribute added to .page-ioc-detail
- `app/templates/partials/_ioc_card.html` - data-tags attribute + static tag pills from annotations_map
- `app/static/src/ts/modules/filter.ts` - tag field in FilterState, tag match logic, tag filter pill row
- `app/static/src/ts/main.ts` - initAnnotations() added to init chain
- `tests/test_ioc_detail_routes.py` - 15 new tests: TestAnnotationApiRoutes (7) + TestTagsOnResultsPage (1)

## Decisions Made
- Annotation API routes use `AnnotationStore()` directly — consistent with `CacheStore()` pattern in existing routes, no injection complexity needed
- annotations.ts clears server-rendered static pills on load and re-renders from data-tags JSON attribute — avoids duplicates when JS is present while preserving graceful degradation when JS is absent
- Tag dedup on POST: read current list, append only if absent, save — idempotent, no race condition concern for single-user tool
- filter.ts tag pills inserted after `.filter-bar` using DOM insertBefore — maintains filter bar visual layout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing `test_analyze_deduplicates` failure (count >= 10 for `192.168.1.1` occurrences) was present before this plan's changes — confirmed by stash test. Out of scope; logged to deferred items. Not caused by annotation changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Task 3 (human-verify checkpoint) is pending — user must verify the complete deep analysis view flow
- All automation complete: annotation API, notes/tags UI, tag pills on cards, tag filter in filter bar
- Full test suite: 559 unit/integration pass (1 pre-existing failure in test_routes.py unrelated to this plan)

---
*Phase: 04-deep-analysis-view*
*Completed: 2026-03-13*
