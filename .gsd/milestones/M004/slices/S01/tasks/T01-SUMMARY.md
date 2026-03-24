---
id: T01
parent: S01
milestone: M004
provides:
  - Semaphore released before backoff sleep in _do_lookup() — concurrent 429s no longer stall all semaphore slots
  - get_status() returns a list() snapshot of results, preventing RuntimeError on concurrent reads
  - _cached_markers reads and writes protected by _lock
  - Non-429 retry waits 1s before the retry attempt
  - 3 new unit tests proving all four concurrency fixes
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
key_decisions:
  - Extracted _single_attempt() to isolate one HTTP attempt; _do_lookup() now does explicit sem.acquire()/release() with try/finally, releasing before any sleep — avoids holding semaphore across multi-second backoff delays
  - Kept _do_lookup_inner() as a deprecated shim delegating to _single_attempt() for backward compatibility
patterns_established:
  - Semaphore-per-attempt pattern: acquire → _single_attempt() → release in try/finally, then sleep outside semaphore for both 429 and non-429 retry paths
  - list() snapshot in get_status() before returning results (prevents live-list aliasing across thread boundaries)
  - _lock guards all _cached_markers reads and writes (property + write in _single_attempt)
observability_surfaces:
  - orchestrator.get_status(job_id) — returns safe snapshot; mutations to returned list do not affect internal state
  - orchestrator.cached_markers — thread-safe property returning dict copy under _lock
  - logger.warning() on 429 backoff (existing); 1s non-429 retry delay is now visible if lookups are slow
duration: ~15 minutes
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Fix orchestrator concurrency bugs and update unit tests

**Fixed four concurrency/correctness bugs in orchestrator.py and added 3 new tests proving the fixes; all 27 orchestrator tests pass and full suite counts 936 passing.**

## What Happened

Four bugs were fixed in `app/enrichment/orchestrator.py`:

1. **Semaphore held during backoff sleep** — Restructured `_do_lookup()` to use explicit `sem.acquire()`/`sem.release()` with `try/finally`. Extracted `_single_attempt()` containing the cache-check → `adapter.lookup()` → cache-store logic. The semaphore now wraps only each individual attempt, not the sleep between retries. `_do_lookup_inner()` kept as a shim for any direct callers.

2. **`get_status()` shallow-copy race** — Changed `return dict(job)` to `copy = dict(job); copy["results"] = list(job["results"]); return copy` so the returned dict has an independent list, not a live reference.

3. **`_cached_markers` unprotected writes** — Wrapped the write `self._cached_markers[cache_key] = cached_at` inside `with self._lock:` in `_single_attempt()`. Also wrapped the `cached_markers` property body in `with self._lock: return dict(self._cached_markers)`.

4. **Non-429 retry immediate** — Added `time.sleep(1)` in the non-429 else branch, outside the semaphore. The sleep happens before re-acquiring the semaphore and retrying.

The existing `test_non_429_does_not_trigger_sleep` was renamed to `test_non_429_retry_sleeps_1s` and updated to expect `mock_sleep.call_count == 1` and `call_args_list[0][0][0] == 1`.

Three new tests were added:
- `TestSemaphoreReleasedDuringBackoff::test_semaphore_released_during_backoff_sleep` — Uses `threading.Event` coordination: IOC-A gets 429 → sets "sleeping" event → enters mock sleep; IOC-B waits for event → acquires semaphore → completes; asserts IOC-B completed while mock sleep was still active. Uses semaphore cap=1 for maximum strictness.
- `TestGetStatusListSnapshot::test_get_status_returns_list_snapshot` — Appends a dummy to the returned results list and re-calls `get_status()` to confirm internal state is unchanged.
- `TestCachedMarkersLock::test_cached_markers_write_protected_by_lock` — 8 IOCs concurrent with an always-hit cache mock; verifies `cached_markers` has all 8 entries after completion.

## Verification

All three slice verification commands for T01 were run:

```
python3 -m pytest tests/test_orchestrator.py -v   → 27 passed, 0 failed
python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES; print('OK')"   → OK
python3 -m pytest tests/ -x -q   → 936 passed, 0 failed
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_orchestrator.py -v` | 0 | ✅ pass | 6.30s |
| 2 | `python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES; print('OK')"` | 0 | ✅ pass | <1s |
| 3 | `python3 -m pytest tests/ -x -q` | 0 | ✅ pass | 47.09s (936 passed) |

## Diagnostics

- `orchestrator.get_status(job_id)` returns a dict whose `results` value is a new list — safe to serialize in Flask without `RuntimeError: list changed size during iteration`.
- `orchestrator.cached_markers` acquires `_lock` during the copy — returns a consistent snapshot even under concurrent cache-hit lookups.
- If semaphore-hold-during-sleep regresses: `test_semaphore_released_during_backoff_sleep` will timeout (b_completed_before_sleep_returns never set).
- If list-copy regresses: `test_get_status_returns_list_snapshot` will fail on the second `get_status()` call showing 2 results instead of 1.

## Deviations

- Kept `_do_lookup_inner()` as a backward-compat shim rather than removing it, since the plan permitted either approach. This avoids any risk of hidden direct callers outside the test file.
- The module docstring comment about semaphore scope was updated to reflect the new per-attempt semantics.

## Known Issues

None — all must-haves met, full suite passes.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — Fixed all four concurrency bugs; extracted `_single_attempt()`, restructured `_do_lookup()` with explicit sem acquire/release, updated `get_status()` and `cached_markers` property
- `tests/test_orchestrator.py` — Renamed/updated `test_non_429_does_not_trigger_sleep` → `test_non_429_retry_sleeps_1s`; added `TestSemaphoreReleasedDuringBackoff`, `TestGetStatusListSnapshot`, `TestCachedMarkersLock` (3 new classes, 3 new tests)
