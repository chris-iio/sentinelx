# S01: Per-Provider Concurrency & 429 Backoff

**Goal:** Zero-auth enrichment providers run independently of VT's rate limit; VT 429 errors trigger exponential backoff instead of immediate quota-burning retry.
**Demo:** `python3 -m pytest tests/test_orchestrator.py -v` passes all existing 15 tests plus new tests proving: (a) VT calls capped at 4 concurrent while zero-auth providers complete freely, (b) 429 errors trigger backoff sleep before retry, (c) non-429 errors still retry immediately.

## Must-Haves

- `EnrichmentOrchestrator.__init__()` builds a per-provider `threading.Semaphore` dict keyed by adapter name; adapters with `requires_api_key=True` get a configurable concurrency cap (default 4); adapters with `requires_api_key=False` get no semaphore (unlimited concurrency)
- `max_workers` default raised from 4 to accommodate all providers running freely (the semaphore is the real concurrency gate, not the thread pool)
- `_do_lookup()` acquires the provider's semaphore (if any) before the lookup-retry cycle and releases after — wrapping the entire body, not per-attempt, to avoid re-entrant deadlock
- `_do_lookup()` detects 429/rate-limit errors via substring match on `EnrichmentError.error` and applies exponential backoff with jitter before retry
- Non-rate-limit errors continue immediate retry (existing behavior preserved)
- All 15 existing `test_orchestrator.py` tests pass unchanged
- `__init__()` public API remains backward-compatible — new parameters have defaults

## Proof Level

- This slice proves: contract
- Real runtime required: no
- Human/UAT required: no

## Verification

- `python3 -m pytest tests/test_orchestrator.py -v` — all 15 existing tests pass + new tests pass
- New test class `TestPerProviderSemaphore`: mock VT adapter (slow, 0.3s) + mock zero-auth adapter (instant). Submit 8 IOCs. Assert zero-auth completes without waiting for VT. Assert VT peak concurrency ≤ 4 via shared atomic counter.
- New test class `TestBackoff429`: mock adapter returns 429 error on first call, success on second. Patch `time.sleep`. Assert sleep called with value ≥ base backoff. Assert non-429 error does NOT trigger sleep.
- `python3 -m pytest tests/ -q --ignore=tests/e2e` — full unit test suite still passes (no regressions)

## Observability / Diagnostics

- Runtime signals: Python `logging.warning` when 429 backoff fires (provider name, attempt, delay)
- Inspection surfaces: none (no new endpoints; backoff is internal to orchestrator thread)
- Failure visibility: backoff delay and retry count visible in log output; if all retries exhaust, the final `EnrichmentError` surfaces in job status results
- Redaction constraints: none (no secrets in log — only provider name and delay)

## Integration Closure

- Upstream surfaces consumed: `app/enrichment/provider.py` (`Provider.requires_api_key`), `app/enrichment/models.py` (`EnrichmentError.error`)
- New wiring introduced in this slice: none (orchestrator's public API is unchanged; routes.py calls it identically)
- What remains before the milestone is truly usable end-to-end: S02 (email extraction), S03 (detail page), S04 (integration verification)

## Tasks

- [x] **T01: Add per-provider semaphore dict and raise max_workers** `est:45m`
  - Why: The current single ThreadPoolExecutor(max_workers=4) starves zero-auth providers when VT fills all slots. Adding per-provider semaphores lets VT be capped independently while zero-auth providers run freely. This delivers R014.
  - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`
  - Do: (1) Add `_semaphores: dict[str, threading.Semaphore]` to `__init__()`, built from adapters with `requires_api_key=True`. Accept optional `provider_concurrency` param (default `{}`) for per-provider overrides, with fallback cap of 4 for any `requires_api_key=True` adapter. (2) Raise `max_workers` default from 4 to 20 so thread pool isn't the bottleneck. (3) In `_do_lookup()`, wrap the entire lookup+retry body in `with self._semaphores[provider_name]:` if provider has a semaphore. (4) Add `TestPerProviderSemaphore` test class with threading.Event/counter-based concurrency assertions. (5) Verify all 15 existing tests pass unchanged.
  - Verify: `python3 -m pytest tests/test_orchestrator.py -v`
  - Done when: new semaphore tests pass proving VT capped at 4 concurrent while zero-auth is unblocked; all 15 existing tests pass

- [x] **T02: Add 429-aware exponential backoff to _do_lookup retry logic** `est:30m`
  - Why: The current retry logic immediately retries 429 errors, burning API quota. Backoff respects rate limits and avoids quota exhaustion. This delivers R015.
  - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`
  - Do: (1) In `_do_lookup()`, after detecting an `EnrichmentError`, check if error contains "429" or "rate limit" (case-insensitive). (2) If rate-limit detected: sleep with exponential backoff (base=15s, multiplier=2×, jitter=random.uniform(0,2)) before retry. Allow up to 2 retries for 429 (3 total attempts). (3) If non-rate-limit error: preserve existing immediate single-retry behavior. (4) Add `logging.warning()` when backoff fires. (5) Add `TestBackoff429` test class: patch `time.sleep`, mock adapter returning 429 then success — assert sleep called with correct delay range. Test non-429 error does NOT trigger sleep. Test that 3 consecutive 429s exhaust retries and return final error. (6) Verify all existing + T01 tests pass.
  - Verify: `python3 -m pytest tests/test_orchestrator.py -v`
  - Done when: backoff tests pass proving 429 triggers sleep, non-429 doesn't, triple-429 exhausts retries; all existing + semaphore tests pass

## Files Likely Touched

- `app/enrichment/orchestrator.py`
- `tests/test_orchestrator.py`
