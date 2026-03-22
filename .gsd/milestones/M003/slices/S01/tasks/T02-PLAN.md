---
estimated_steps: 5
estimated_files: 2
---

# T02: Add 429-aware exponential backoff to _do_lookup retry logic

**Slice:** S01 — Per-Provider Concurrency & 429 Backoff
**Milestone:** M003

## Description

The current `_do_lookup()` retry logic retries failed lookups exactly once, immediately — including 429 rate-limit errors. This burns API quota since the retry hits the same rate limit wall. The fix: detect 429/rate-limit errors via substring match on `EnrichmentError.error` and apply exponential backoff with jitter before retrying. Non-rate-limit errors keep their existing immediate retry. Rate-limit errors get up to 2 retries (3 total attempts) with increasing backoff delays.

This delivers requirement R015: VT 429 responses trigger exponential backoff, not immediate quota-burning retry.

**Relevant skills:** `test` skill for test generation patterns.

## Steps

1. **Read current `_do_lookup()` / `_do_lookup_inner()`** as modified by T01 to understand the retry path. After T01, the structure is approximately:
   ```python
   def _do_lookup_inner(self, adapter, ioc, provider_name):
       # cache check...
       result = adapter.lookup(ioc)
       if isinstance(result, EnrichmentError):
           result = adapter.lookup(ioc)  # immediate retry
       # cache store...
       return result
   ```

2. **Add imports** at top of `orchestrator.py`:
   - `import logging`, `import random`, `import time`
   - Create module-level logger: `logger = logging.getLogger(__name__)`

3. **Replace the retry logic** in the lookup method with 429-aware backoff:
   ```python
   _BACKOFF_BASE = 15  # seconds
   _BACKOFF_MULTIPLIER = 2
   _BACKOFF_JITTER = 2.0  # seconds
   _MAX_RATE_LIMIT_RETRIES = 2  # up to 2 retries for 429 (3 total attempts)
   
   def _is_rate_limit_error(self, result):
       """Check if an EnrichmentError is a rate-limit (429) error."""
       if not isinstance(result, EnrichmentError):
           return False
       err = result.error.lower()
       return "429" in err or "rate limit" in err
   ```
   
   In the lookup method, replace the simple single-retry with:
   ```python
   result = adapter.lookup(ioc)
   if isinstance(result, EnrichmentError):
       if self._is_rate_limit_error(result):
           # 429: exponential backoff with jitter, up to _MAX_RATE_LIMIT_RETRIES
           for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
               delay = _BACKOFF_BASE * (_BACKOFF_MULTIPLIER ** (attempt - 1)) + random.uniform(0, _BACKOFF_JITTER)
               logger.warning(
                   "Rate limit (429) from %s for %s — backoff attempt %d, sleeping %.1fs",
                   provider_name, ioc.value, attempt, delay
               )
               time.sleep(delay)
               result = adapter.lookup(ioc)
               if not isinstance(result, EnrichmentError):
                   break
               if not self._is_rate_limit_error(result):
                   break  # different error, stop retrying
       else:
           # Non-429 error: single immediate retry (existing behavior)
           result = adapter.lookup(ioc)
   ```

4. **Add `TestBackoff429` test class** in `tests/test_orchestrator.py`:
   
   **Test 1 — 429 triggers backoff sleep:**
   - Mock adapter returns `EnrichmentError(error="Rate limit exceeded (429)")` on first call, `EnrichmentResult` on second
   - Patch `time.sleep` with `unittest.mock.patch`
   - Assert `time.sleep` was called at least once
   - Assert sleep argument ≥ `_BACKOFF_BASE` (15s)
   - Assert final result is `EnrichmentResult`
   
   **Test 2 — non-429 error does NOT trigger sleep:**
   - Mock adapter returns `EnrichmentError(error="Timeout")` on first call, `EnrichmentResult` on second
   - Patch `time.sleep`
   - Assert `time.sleep` was NOT called
   - Assert final result is `EnrichmentResult` (immediate retry still works)
   
   **Test 3 — triple-429 exhausts retries:**
   - Mock adapter returns `EnrichmentError(error="HTTP 429")` on all 3 calls
   - Patch `time.sleep`
   - Assert `time.sleep` was called exactly 2 times (2 retries)
   - Assert final result is `EnrichmentError`
   - Assert adapter.lookup was called exactly 3 times (1 initial + 2 retries)
   
   **Test 4 — backoff delays increase exponentially:**
   - Mock adapter returns 429 on all 3 calls
   - Capture sleep arguments
   - Assert second sleep arg > first sleep arg (exponential increase)
   
   **Test 5 — "Rate limit" string variant also triggers backoff:**
   - Mock adapter returns `EnrichmentError(error="Rate limit exceeded")` (no "429" substring)
   - Patch `time.sleep`
   - Assert sleep was called (case-insensitive "rate limit" match works)

5. **Run full test suite:**
   ```
   python3 -m pytest tests/test_orchestrator.py -v
   python3 -m pytest tests/ -q --ignore=tests/e2e
   ```

## Must-Haves

- [ ] 429/rate-limit detection via substring match on `EnrichmentError.error` (covers "Rate limit exceeded (429)", "HTTP 429", "Rate limit exceeded")
- [ ] Exponential backoff: base 15s × 2^attempt + jitter, up to 2 retries (3 total attempts)
- [ ] Non-429 errors preserve existing single immediate retry behavior
- [ ] `logging.warning()` when backoff fires with provider name, attempt count, delay
- [ ] All existing + T01 tests pass unchanged
- [ ] New `TestBackoff429` tests prove backoff behavior

## Verification

- `python3 -m pytest tests/test_orchestrator.py -v` — all tests pass
- `python3 -m pytest tests/ -q --ignore=tests/e2e` — full unit suite passes
- Backoff tests use `unittest.mock.patch("time.sleep")` — no real sleeping in tests

## Inputs

- `app/enrichment/orchestrator.py` — as modified by T01 (with semaphore dict and refactored `_do_lookup`)
- `tests/test_orchestrator.py` — as modified by T01 (with `TestPerProviderSemaphore` class)
- Error message patterns from adapters: `"Rate limit exceeded (429)"` (VT, AbuseIPDB), `"HTTP 429"` (GreyNoise, ip-api, Shodan, ThreatMiner)

## Expected Output

- `app/enrichment/orchestrator.py` — `_do_lookup()` / inner method updated with 429-aware backoff loop, `_is_rate_limit_error()` helper, module constants for backoff params, logger setup
- `tests/test_orchestrator.py` — new `TestBackoff429` class with ≥5 tests proving backoff triggers on 429, doesn't trigger on non-429, exhausts retries correctly, and delays increase exponentially
