---
id: S01
parent: M003
milestone: M003
uat_mode: artifact-driven
completed_at: 2026-03-20
---

# S01: Per-Provider Concurrency & 429 Backoff — UAT

**Milestone:** M003
**Written:** 2026-03-20

## UAT Type

- **UAT mode:** artifact-driven
- **Why this mode is sufficient:** S01 is a pure backend contract change with no frontend surface. The slice plan explicitly states "Real runtime required: no; Human/UAT required: no." The proof is the pytest suite: semaphore behavior and 429 backoff are fully verified by deterministic mocked-adapter unit tests that exercise the exact code paths in production. No browser, server, or manual step can add verification signal not already provided by the 24-test suite.

## Preconditions

1. Working directory: `/home/chris/.gsd/projects/bb1bd2fe6965/worktrees/M003`
2. Python environment active with all dependencies installed (`pip install -r requirements.txt` if needed)
3. No uncommitted changes to `app/enrichment/orchestrator.py` or `tests/test_orchestrator.py` that aren't part of S01

## Smoke Test

Run the orchestrator test file and confirm all 24 tests pass:

```bash
python3 -m pytest tests/test_orchestrator.py -v
```

**Expected:** `24 passed` with no failures or errors. Duration ~2–3 seconds.

## Test Cases

### 1. All pre-existing orchestrator tests pass unchanged

Verifies that the per-provider semaphore and backoff changes did not break any existing behavior.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestEnrichAll tests/test_orchestrator.py::TestRetryBehavior tests/test_orchestrator.py::TestJobStatusTracking tests/test_orchestrator.py::TestLRUEviction tests/test_orchestrator.py::TestMultiAdapterDispatch -v`
2. **Expected:** All 15 tests pass. No adapter dispatch, job status tracking, LRU eviction, parallel execution, or error isolation tests should fail.

---

### 2. VT peak concurrency is capped at ≤ 4

Verifies that a keyed adapter (simulating VirusTotal) with a default semaphore cap never exceeds 4 concurrent lookups even when 8 IOCs are submitted simultaneously.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestPerProviderSemaphore::test_vt_peak_concurrency_capped_at_4 -v`
2. **Expected:** PASSED. The atomic counter (tracking concurrent threads inside the slow adapter) must never exceed 4 across all 8 lookups.

---

### 3. Zero-auth providers complete without waiting for VT slots

Verifies that a zero-auth adapter (requires_api_key=False) is not gated by VT's semaphore and can complete all its lookups while VT is still running.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestPerProviderSemaphore::test_zero_auth_completes_without_waiting_for_vt -v`
2. **Expected:** PASSED. The public adapter completes all 8 lookups. Total results = 16 (8 VT + 8 DNS). The zero-auth results arrive before VT finishes.

---

### 4. Semaphore dict built only for keyed adapters

Verifies that the orchestrator's `_semaphores` dict is empty when only public adapters are registered, and has exactly one entry when one keyed adapter is present.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestPerProviderSemaphore::test_semaphore_built_only_for_keyed_adapters -v`
2. **Expected:** PASSED. Public-only orchestrator: `_semaphores == {}`. Orchestrator with one keyed adapter: `len(_semaphores) == 1` and `"VT" in _semaphores`.

---

### 5. provider_concurrency override respected

Verifies that passing `provider_concurrency={"VT": 2}` reduces the semaphore for "VT" from the default 4 to 2.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestPerProviderSemaphore::test_provider_concurrency_override -v`
2. **Expected:** PASSED. Default cap semaphore `._value == 4`. Custom cap semaphore `._value == 2`.

---

### 6. 429 error triggers exponential backoff sleep

Verifies that when a provider returns an EnrichmentError with "429" in the message, `time.sleep` is called with a delay ≥ `_BACKOFF_BASE` (15 seconds) before retrying.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_429_triggers_backoff_sleep -v`
2. **Expected:** PASSED. `time.sleep` called exactly once. Sleep duration ≥ 15.0. `adapter.lookup` called exactly 2 times (first call = 429, second call = success). Final result is a successful EnrichmentResult, not an error.

---

### 7. Non-429 error does NOT trigger sleep

Verifies that a non-rate-limit error (e.g., connection timeout, DNS failure) retries immediately without sleeping, preserving pre-S01 behavior.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_non_429_does_not_trigger_sleep -v`
2. **Expected:** PASSED. `time.sleep` NOT called. `adapter.lookup` called exactly 2 times. Second call returns success.

---

### 8. Triple 429 exhausts retries and returns final error

Verifies that three consecutive 429 responses exhaust the retry budget (3 total attempts, 2 retries) and return the final EnrichmentError without infinite looping.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_triple_429_exhausts_retries -v`
2. **Expected:** PASSED. `time.sleep` called exactly 2 times (one per retry, not per original attempt). `adapter.lookup` called exactly 3 times. Final result is an `EnrichmentError`. No hang or exception.

---

### 9. Backoff delays increase exponentially across retries

Verifies that the second backoff sleep is longer than the first (exponential, not constant, backoff).

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_backoff_delays_increase_exponentially -v`
2. **Expected:** PASSED. `time.sleep.call_args_list[1][0][0]` > `time.sleep.call_args_list[0][0][0]`. The second sleep must be strictly larger than the first.

---

### 10. "rate limit" string (no numeric 429) also triggers backoff

Verifies that `_is_rate_limit_error` matches on the phrase "rate limit" as well as the numeric code "429".

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_rate_limit_string_without_429_triggers_backoff -v`
2. **Expected:** PASSED. An error message of "Rate limit exceeded" (no "429") triggers at least 1 sleep call.

---

### 11. Full unit suite has no regressions

Verifies that no other test in the project was broken by the orchestrator changes.

1. Run: `python3 -m pytest tests/ -q --ignore=tests/e2e`
2. **Expected:** 808 tests pass, 1 pre-existing failure (`tests/test_routes.py::test_analyze_deduplicates` — present before this slice). Exit code 1 only due to that pre-existing failure.

## Edge Cases

### Keyed adapter with empty name

If a `requires_api_key=True` adapter has `name == ""`, it must be excluded from the semaphore dict (would create a key of `""` which is correct but undiagnosable). The current implementation filters on `provider_name` being truthy.

1. Run: `python3 -m pytest tests/test_orchestrator.py::TestPerProviderSemaphore::test_semaphore_built_only_for_keyed_adapters -v`
2. **Expected:** PASSED (this test uses named adapters; the no-name edge case is a documentation note, not a regression risk).

### 429 on retry (not first call)

If a provider returns success on first call but 429 on retry (unusual but possible), `_is_rate_limit_error` only fires on the error path. This edge case cannot happen with the current retry structure (retry only fires on error), so no test is needed.

### Backoff with jitter

`random.uniform(0, _BACKOFF_JITTER)` adds 0–2 seconds of jitter per retry. Sleep durations in tests include the jitter range — threshold assertions use `>= _BACKOFF_BASE` (not `== _BACKOFF_BASE`) to account for this.

## Failure Signals

- Any test in `TestPerProviderSemaphore` or `TestBackoff429` failing → S01 implementation has regressed
- `test_vt_peak_concurrency_capped_at_4` counter exceeds 4 → semaphore not wrapping `_do_lookup_inner` correctly
- `test_non_429_does_not_trigger_sleep` failing with sleep called → retry path branching is broken
- `test_triple_429_exhausts_retries` hanging → infinite loop in backoff retry logic (missing break or return)
- `time.sleep` not being intercepted by `patch("app.enrichment.orchestrator.time.sleep")` → wrong patch target (check `import time` is module-level in orchestrator.py)

## Not Proven By This UAT

- **Runtime backoff timing:** Tests patch `time.sleep` — actual 15–30s sleep in production is not exercised. This is intentional; a real 429 from VT would make the suite take minutes.
- **VT token-bucket rate limiting:** The semaphore prevents >4 concurrent calls but does not enforce 4 req/min. True rate limiting is out of scope (milestone roadmap documents this explicitly).
- **E2E concurrency under real VT load:** No live provider calls are made. Real-world concurrency behavior (VT returning 429 during actual enrichment job) is verified operationally, not by this UAT.
- **Semaphore interaction with Redis/job caching:** The semaphore operates at the thread level inside a single process. It is not distributed — if the app runs behind multiple workers, each process has its own semaphore.

## Notes for Tester

- All test classes run in ~2.3 seconds total (sleep is mocked; semaphore tests use 0.3s adapter delays).
- The `test_analyze_deduplicates` failure in `test_routes.py` predates this slice and is unrelated. Ignore it during S01 verification.
- If `test_vt_peak_concurrency_capped_at_4` flaps on a slow CI system, the 0.3s adapter delay may be insufficient for all 8 threads to acquire the semaphore before the first one releases. Increase the `time.sleep(0.3)` in `_make_keyed_adapter` to 0.5s if needed.
- The 24-test count (15 pre-existing + 4 `TestPerProviderSemaphore` + 5 `TestBackoff429`) is the expected total. Any count other than 24 indicates test discovery issues or file conflicts.
