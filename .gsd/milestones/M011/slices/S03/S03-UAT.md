# S03: Dead CSS Removal & Orchestrator Test Speed — UAT

**Milestone:** M011
**Written:** 2026-04-04T12:55:24.575Z

## UAT: Dead CSS Removal & Orchestrator Test Speed

### Preconditions
- Working directory: `/home/chris/projects/sentinelx`
- Python 3.10+ with pytest installed
- All project dependencies installed

---

### TC-01: Orchestrator test suite speed

**Steps:**
1. Run `python3 -m pytest tests/test_orchestrator.py -q --durations=10`

**Expected:**
- All 27 tests pass
- Total wall-clock time < 1.0s
- None of these tests appear in slowest 10 with >0.1s: `test_error_isolation`, `test_retry_on_failure`, `test_retry_still_fails`, `test_adapter_failure_isolated_across_providers`, `test_enrich_all_parallel_execution`, `test_vt_peak_concurrency_capped_at_4`, `test_zero_auth_completes_without_waiting_for_vt`

---

### TC-02: Retry-path tests still verify retry behavior

**Steps:**
1. Run `python3 -m pytest tests/test_orchestrator.py -k "test_retry_on_failure or test_retry_still_fails" -v`

**Expected:**
- Both tests pass
- `test_retry_on_failure` verifies `mock_adapter.lookup.call_count == 2` (retry happened)
- `test_retry_still_fails` verifies the IOC ends with error status after 2 failed attempts

---

### TC-03: Barrier parallelism test proves concurrency

**Steps:**
1. Run `python3 -m pytest tests/test_orchestrator.py -k "test_enrich_all_parallel_execution" -v`

**Expected:**
- Test passes (barrier didn't timeout → all 5 threads ran concurrently)
- 5 results returned in status

---

### TC-04: VT semaphore cap test proves rate limiting

**Steps:**
1. Run `python3 -m pytest tests/test_orchestrator.py -k "test_vt_peak_concurrency_capped_at_4" -v`

**Expected:**
- Test passes
- `peak_vt <= 4` assertion holds (semaphore caps VT concurrency)
- All 8 results returned

---

### TC-05: Zero-auth adapter independence test

**Steps:**
1. Run `python3 -m pytest tests/test_orchestrator.py -k "test_zero_auth_completes_without_waiting_for_vt" -v`

**Expected:**
- Test passes
- 16 total results (8 VT + 8 DNS)
- DNS completed all 8 lookups

---

### TC-06: Full test suite regression

**Steps:**
1. Run `python3 -m pytest --tb=short -q`

**Expected:**
- 1012 tests pass
- Zero failures, zero errors

---

### TC-07: CSS class coverage — dynamic classes verified

**Steps:**
1. Run `grep -n "micro-bar-segment--" app/static/src/ts/modules/row-factory.ts`
2. Run `grep -n "verdict-badge verdict-" app/static/src/ts/modules/row-factory.ts`
3. Run `grep -n "verdict-label--" app/static/src/ts/modules/cards.ts`

**Expected:**
- Step 1: Line 336 shows `"micro-bar-segment micro-bar-segment--" + verdict`
- Step 2: Lines 309 and/or 416 show `"verdict-badge verdict-" + worstVerdict/verdict`
- Step 3: Line 60 shows `"verdict-label--" + worstVerdict`

---

### TC-08: No time.sleep in orchestrator test side-effects

**Steps:**
1. Run `grep -n "time.sleep" tests/test_orchestrator.py`

**Expected:**
- All occurrences are inside `patch("app.enrichment.orchestrator.time.sleep")` context managers
- Zero bare `time.sleep()` calls in mock side-effect functions (no `time.sleep(0.3)`, `time.sleep(0.5)`, etc.)

---

### Edge Cases

**EC-01: Barrier timeout safety**
- If threading.Barrier(5, timeout=2) in test_enrich_all_parallel_execution ever triggers its timeout, the test fails with BrokenBarrierError — a clear signal that parallelism broke, not a silent hang.

**EC-02: Event timeout safety**
- All threading.Event.wait() calls in the rewritten tests have explicit timeout parameters (timeout=2 or timeout=0.01). No infinite waits possible.
