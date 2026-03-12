---
phase: 04-deep-analysis-view
plan: 01
subsystem: database
tags: [sqlite, annotations, csrf, cache, notes, tags]

# Dependency graph
requires:
  - phase: 05-cache
    provides: CacheStore pattern (SQLite, threading.Lock, tmp_path fixture)
provides:
  - AnnotationStore SQLite CRUD for notes and tags per IOC
  - CacheStore.get_all_for_ioc() — all provider results without TTL filtering
  - CSRF meta tag in base.html for client-side fetch authentication
affects:
  - 04-02-detail-route
  - 04-03-annotations-api
  - 04-04-frontend

# Tech tracking
tech-stack:
  added: []
  patterns:
    - AnnotationStore mirrors CacheStore pattern (DEFAULT_PATH, _CREATE_TABLE, _connect, threading.Lock)
    - INSERT OR REPLACE preserves sibling fields (notes/tags) via read-before-write in upsert
    - Bulk read method returns "value|type" keyed dict with default fallbacks for missing entries

key-files:
  created:
    - app/annotations/__init__.py
    - app/annotations/store.py
    - tests/test_annotation_store.py
  modified:
    - app/cache/store.py
    - app/templates/base.html
    - tests/test_cache_store.py

key-decisions:
  - "AnnotationStore uses a separate annotations.db so CacheStore.clear() never erases analyst notes"
  - "set_notes/set_tags each read existing sibling field before INSERT OR REPLACE to preserve it"
  - "Tags stored as JSON string in TEXT column — avoids join table for simple list semantics"
  - "get_all_for_ioc_values returns default entries for missing IOCs so callers never need nil checks"

patterns-established:
  - "Bulk annotation read pattern: get_all_for_ioc_values(pairs) -> dict['value|type', annotation]"
  - "SEC-17 pattern applied: parent dir mode=0o700, DB file chmod 0o600 after creation"

requirements-completed: [DEEP-02, DEEP-03]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 4 Plan 1: Deep Analysis Data Layer Summary

**SQLite AnnotationStore (notes + tags per IOC) plus CacheStore.get_all_for_ioc() and CSRF meta tag — backend primitives for Phase 04 detail view**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T20:48:40Z
- **Completed:** 2026-03-12T20:51:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- AnnotationStore with full CRUD: set_notes, set_tags, get, delete, get_all_for_ioc_values
- Annotations survive CacheStore.clear() — stored in separate annotations.db file
- CacheStore.get_all_for_ioc() returns all provider results without TTL filtering
- CSRF meta tag injected in base.html for upcoming annotations.ts fetch headers
- 29 tests across both files (14 new annotation tests + 4 new cache tests), 743 total passing

## Task Commits

Each task was committed atomically:

1. **Task 1: AnnotationStore with full test suite** - `2df3f5c` (feat)
2. **Task 2: CacheStore.get_all_for_ioc and CSRF meta tag** - `d90403e` (feat)

_Note: TDD tasks used RED (failing tests) then GREEN (implementation) pattern_

## Files Created/Modified

- `app/annotations/__init__.py` - Package init
- `app/annotations/store.py` - AnnotationStore SQLite CRUD with threading.Lock, SEC-17 file permissions
- `tests/test_annotation_store.py` - 14 tests: init, notes, tags, dedup, upsert, delete, bulk read, cache-clear survival
- `app/cache/store.py` - Added get_all_for_ioc() method (TTL-free bulk provider fetch)
- `app/templates/base.html` - CSRF meta tag after color-scheme meta
- `tests/test_cache_store.py` - 4 new tests: all providers, TTL bypass, empty, key presence

## Decisions Made

- AnnotationStore uses a separate annotations.db (not cache.db) so CacheStore.clear() never erases analyst notes
- set_notes/set_tags each read the existing sibling field before INSERT OR REPLACE to avoid clobbering it
- Tags stored as JSON string in TEXT column — avoids a join table for simple list semantics
- get_all_for_ioc_values returns default entries for missing IOCs so callers never need nil checks

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- AnnotationStore ready for 04-02 (detail route) to read annotations alongside cached provider results
- CacheStore.get_all_for_ioc() ready for 04-02 detail page query
- CSRF meta tag ready for 04-03 (annotations API fetch calls from TypeScript)
- All Plans 04-02, 04-03, 04-04 can now proceed

---
*Phase: 04-deep-analysis-view*
*Completed: 2026-03-12*
