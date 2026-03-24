---
estimated_steps: 7
estimated_files: 2
---

# T01: Fix orchestrator concurrency bugs and update unit tests

**Slice:** S01 — Backend Concurrency & Error Correctness
**Milestone:** M004

## Description

Fix four concurrency/correctness bugs in `app/enrichment/orchestrator.py` and add unit tests proving the fixes. This is the high-risk task — the semaphore restructure changes the core `_do_lookup()` control flow and must preserve all 24 existing test invariants while adding new coverage.

The four bugs:
1. **Semaphore held during backoff sleep** — `_do_lookup()` uses `with sem:` around `_do_lookup_inner()`, which contains the `time.sleep()` backoff loop. Under concurrent 429s, all 4 VT slots sleep simultaneously, stalling every queued IOC.
2. **`get_status()` shallow-copy race** — `return dict(job)` shares the live `results` list. Workers appending while Flask serializes can cause `RuntimeError: list changed size during iteration`.
3. **`_cached_markers` unprotected writes** — worker threads write `self._cached_markers[cache_key] = cached_at` without holding `self._lock`. The `cached_markers` property reads without the lock too.
4. **Non-429 retry has no delay** — the `else` branch retries immediately. Should wait 1s.

**Critical constraints** (from KNOWLEDGE):
- `_BACKOFF_BASE`, `_BACKOFF_MULTIPLIER`, `_BACKOFF_JITTER`, `_MAX_RATE_LIMIT_RETRIES` must remain importable from `app.enrichment.orchestrator` at the same module paths. Tests import them directly.
- `time.sleep` must be patched at `"app.enrichment.orchestrator.time.sleep"`, not `"time.sleep"`.
- The existing `test_non_429_does_not_trigger_sleep` currently asserts `mock_sleep.call_count == 0`. Adding the 1s non-429 delay will break it — update to expect exactly 1 sleep call with `call_args[0][0] == 1`.

**Relevant skill:** `test` (for test writing patterns).

## Steps

1. **Fix `get_status()` — snapshot results list.** In `get_status()`, change from `return dict(job)` to:
   ```python
   copy = dict(job)
   copy["results"] = list(job["results"])
   return copy
   ```
   This is the safest fix — `list()` creates a new list with the same elements. Existing tests don't test concurrent reads so no test changes needed.

2. **Fix `cached_markers` property — add `_lock`.** Wrap the property body:
   ```python
   @property
   def cached_markers(self) -> dict[str, str]:
       with self._lock:
           return dict(self._cached_markers)
   ```

3. **Fix `_do_lookup_inner()` — lock `_cached_markers` writes.** In the cache-hit branch (around line 224), wrap the write:
   ```python
   with self._lock:
       self._cached_markers[cache_key] = cached_at
   ```

4. **Restructure `_do_lookup()` — release semaphore before sleep.** This is the core change. Replace the current `with sem:` block pattern with explicit acquire/release so the semaphore wraps only the single-attempt logic (cache-check → `adapter.lookup()` → cache-store) but NOT the backoff sleep between retry attempts. The approach:

   - Extract a new `_single_attempt()` method containing: cache check, `adapter.lookup(ioc)`, and cache store on success. This method does NOT contain any retry/backoff logic.
   - In `_do_lookup()`, implement the retry loop at this level:
     - Acquire semaphore (if exists) → call `_single_attempt()` → release semaphore
     - If result is 429 error: sleep (outside semaphore) → re-acquire → retry → release
     - If result is non-429 error: sleep 1s → re-acquire → retry → release
     - If success: return result
   - Use `try/finally` to guarantee semaphore release even on exceptions.

   **Key invariant**: the semaphore still wraps each individual attempt (cache + lookup + store), just not the sleep between attempts. This prevents more than `cap` concurrent HTTP calls per provider at any instant.

   **Implementation detail for `_single_attempt()`**: Move the cache-check logic, `adapter.lookup(ioc)` call, and cache-store logic from `_do_lookup_inner()` into `_single_attempt()`. Keep `_do_lookup_inner()` as the retry orchestration method (or fold it into `_do_lookup()` — either approach works as long as the semaphore wraps only `_single_attempt()`).

5. **Add 1s delay for non-429 retry.** In the non-429 retry path of the restructured `_do_lookup()`, add `time.sleep(1)` before the retry attempt. This sleep happens outside the semaphore (same as 429 backoff sleep).

6. **Update `test_non_429_does_not_trigger_sleep`.** The test currently asserts `mock_sleep.call_count == 0`. Change to:
   ```python
   assert mock_sleep.call_count == 1, "Non-429 retry should sleep exactly once (1s delay)"
   assert mock_sleep.call_args_list[0][0][0] == 1, "Non-429 retry delay should be 1 second"
   ```
   Also rename the test to `test_non_429_retry_sleeps_1s` to reflect the new behavior.

7. **Add three new tests:**

   a) `test_semaphore_released_during_backoff_sleep` — Submit 8 IOCs via a VT adapter with semaphore cap 2. First 2 IOCs return 429 (triggering backoff sleep). During that sleep, the other IOCs should be able to acquire the semaphore and complete. Use `threading.Event` coordination: IOC-A gets 429 → sets "sleeping" event → sleeps; IOC-B waits for "sleeping" event → acquires semaphore → completes. Assert that IOC-B completed while IOC-A was still sleeping.

   b) `test_get_status_returns_list_snapshot` — Run `enrich_all()`, get status, mutate the returned `results` list (append a dummy), verify the internal job's results list is unchanged (original length).

   c) `test_cached_markers_write_protected_by_lock` — Create an orchestrator with a cache mock that returns hits. Submit multiple IOCs concurrently. After completion, verify `cached_markers` property returns consistent data (no KeyError, no missing entries). The primary goal is regression coverage — the fix is simple (add `with self._lock:`), but the test proves it stays locked.

## Must-Haves

- [ ] `get_status()` returns `list()` copy of results, not the live reference
- [ ] `cached_markers` property holds `_lock` during read
- [ ] `_cached_markers` writes in `_do_lookup_inner` / `_single_attempt` hold `_lock`
- [ ] Semaphore released before `time.sleep()` in backoff path
- [ ] Non-429 retry waits `time.sleep(1)` before retry
- [ ] `_BACKOFF_BASE`, `_BACKOFF_MULTIPLIER`, `_BACKOFF_JITTER`, `_MAX_RATE_LIMIT_RETRIES` importable from `app.enrichment.orchestrator`
- [ ] All 24 existing tests pass unchanged (except the renamed non-429 test)
- [ ] 3+ new tests pass

## Verification

- `python3 -m pytest tests/test_orchestrator.py -v` → 27+ tests pass, 0 fail
- `python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES; print('OK')"` → prints "OK"
- `python3 -m pytest tests/ -x -q` → 933+ pass, 0 fail

## Observability Impact

- Signals added/changed: non-429 retry now has a 1s delay visible in logs (existing `logger.warning` covers 429 path; non-429 retry path has no explicit log — consider adding one, but not required)
- How a future agent inspects this: `orchestrator.get_status(job_id)` returns safe snapshot; `orchestrator.cached_markers` is thread-safe
- Failure state exposed: if semaphore deadlock regressed, `test_semaphore_released_during_backoff_sleep` would timeout/fail

## Inputs

- `app/enrichment/orchestrator.py` — current orchestrator with the four bugs
- `tests/test_orchestrator.py` — 24 existing tests (all passing) that must remain green

## Expected Output

- `app/enrichment/orchestrator.py` — fixed orchestrator with all four bugs resolved
- `tests/test_orchestrator.py` — 27+ tests (24 existing, 1 renamed/updated, 3 new)
