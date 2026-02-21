---
phase: 02-core-enrichment
plan: "02"
subsystem: enrichment
tags: [threadpoolexecutor, concurrent.futures, ordereddict, threading, lock, lru]

# Dependency graph
requires:
  - phase: 02-01
    provides: "VTAdapter with lookup(ioc) interface and ENDPOINT_MAP; EnrichmentResult/EnrichmentError models"
provides:
  - "EnrichmentOrchestrator class with parallel execution via ThreadPoolExecutor"
  - "Per-IOC error isolation: one failure does not block other results"
  - "Retry-once behavior: EnrichmentError results automatically retried once"
  - "Thread-safe job status tracking with LRU eviction"
affects:
  - "02-03 (Flask routes that call enrich_all from threading.Thread)"
  - "02-04 (Phase 2 integration)"

# Tech tracking
tech-stack:
  added: [concurrent.futures, collections.OrderedDict, threading.Lock]
  patterns:
    - "ThreadPoolExecutor with as_completed for parallel IOC enrichment"
    - "OrderedDict as simple LRU queue (popitem(last=False) for FIFO eviction)"
    - "Lock-protected status dict with shallow copy return to prevent external mutation"
    - "Inner _do_lookup method with explicit retry-once on EnrichmentError"

key-files:
  created:
    - app/enrichment/orchestrator.py
    - tests/test_orchestrator.py
  modified: []

key-decisions:
  - "max_workers=4 default: respects VT free tier 4 req/min rate limit (Pitfall 7)"
  - "OrderedDict for LRU: no external dependency, popitem(last=False) gives FIFO eviction"
  - "max_jobs parameter on __init__ (not hardcoded) — enables test isolation without patching"
  - "get_status() returns shallow copy to prevent external state mutation"
  - "_do_lookup is a method (not a closure) for clarity and testability"

patterns-established:
  - "TDD RED->GREEN->REFACTOR with per-phase commits for each stage"
  - "Retry pattern: isinstance(result, EnrichmentError) check triggers single retry"
  - "Thread safety pattern: Lock wraps all _jobs mutations, get_status returns copy"

requirements-completed: [ENRC-04, ENRC-06]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 2 Plan 02: Enrichment Orchestrator Summary

**EnrichmentOrchestrator with ThreadPoolExecutor parallel execution, per-IOC error isolation, retry-once behavior, thread-safe LRU job tracking — 100% test coverage, 11 tests**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-21T09:50:49Z
- **Completed:** 2026-02-21T09:52:41Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments

- ThreadPoolExecutor fires all enrichable IOC lookups in parallel (proven by wall-clock timing test: 5 x 0.5s lookups complete in <1.5s vs 2.5s sequential)
- Per-IOC error isolation: one EnrichmentError does not block or crash other results (verified: 3 IOCs with one failure returns all 3 results)
- Retry-once: failed EnrichmentError results are automatically retried once; adapter.lookup called exactly 2 times per failed IOC
- Thread-safe job status tracking: Lock protects all _jobs mutations; get_status() returns shallow copy
- LRU eviction: OrderedDict.popitem(last=False) evicts oldest job when max_jobs exceeded; tested with configurable max_jobs param
- 100% test coverage, zero regressions across full 168-test suite

## Task Commits

1. **Task 1: RED — Write failing tests** - `74e7b80` (test)
2. **Task 2: GREEN + REFACTOR — Implement orchestrator** - `fcf9055` (feat)

## Files Created/Modified

- `app/enrichment/orchestrator.py` - EnrichmentOrchestrator class with parallel execution, retry-once, thread-safe LRU job tracking
- `tests/test_orchestrator.py` - 11 tests covering parallel execution, error isolation, retry behavior, job status, LRU eviction

## Decisions Made

- **max_workers=4 default**: Respects VT free tier rate limit of 4 requests/minute (Pitfall 7 from Phase 2 research). Callers can override for higher tiers.
- **max_jobs parameter**: Passed to `__init__` instead of hardcoded class constant. Allows test `test_job_cleanup_lru` to use `max_jobs=5` for fast eviction testing without mocking.
- **OrderedDict for LRU**: No external library needed. `popitem(last=False)` gives deterministic FIFO eviction consistent with insertion order.
- **get_status() returns shallow copy**: `dict(job)` prevents external callers from mutating internal job state. The `results` list is shared (deep copy avoided for performance), which is safe because results are immutable frozen dataclasses.

## Deviations from Plan

None — plan executed exactly as written. The `max_jobs` parameter was already implied by the plan's LRU test design; it was made explicit as an `__init__` parameter as the natural implementation choice.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- EnrichmentOrchestrator is ready to be wired into Flask routes (Plan 03)
- `enrich_all(job_id, iocs)` is designed for threading.Thread invocation (non-blocking call pattern)
- `get_status(job_id)` provides polling endpoint for job progress
- CVE IOCs are silently skipped (not in ENDPOINT_MAP) — Plan 03 should document this in API response

---
*Phase: 02-core-enrichment*
*Completed: 2026-02-21*
