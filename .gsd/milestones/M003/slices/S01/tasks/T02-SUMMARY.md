---
id: T02
parent: S01
milestone: M003
provides:
  - 429-aware exponential backoff in EnrichmentOrchestrator._do_lookup_inner (base 15s × 2^attempt + jitter, up to 2 retries / 3 total attempts)
  - _is_rate_limit_error() helper (substring match on "429" or "rate limit", case-insensitive)
  - Module-level backoff constants (_BACKOFF_BASE, _BACKOFF_MULTIPLIER, _BACKOFF_JITTER, _MAX_RATE_LIMIT_RETRIES)
  - logging.warning() when 429 backoff fires (provider name, attempt, delay)
  - TestBackoff429 test class (5 tests) proving all backoff behaviors
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
key_decisions:
  - _is_rate_limit_error is a method not a free function so it's mockable and testable via orchestrator instance
  - Patch target is app.enrichment.orchestrator.time.sleep (module-level import, not builtins)
  - Non-429 errors preserve original single-retry behavior (no sleep); only the 429 path calls time.sleep
  - If a retry returns a different (non-429) error, the 429-backoff loop exits immediately to avoid masking other error types
patterns_established:
  - "rate limit" backoff loop: for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1) with break on success or non-429 error
  - Backoff constants as module-level names (importable in tests for threshold assertions)
  - patch("app.enrichment.orchestrator.time.sleep") — correct patch path for module-level time import
observability_surfaces:
  - logging.warning("Rate limit (429) from %s for %s — backoff attempt %d, sleeping %.1fs", provider_name, ioc.value, attempt, delay)
  - Log visible at WARNING level; configure handler on "app.enrichment.orchestrator" logger to surface in production
  - Failure state: if all retries exhaust, final EnrichmentError from last attempt surfaces in job["results"]; no silent swallow
  - Diagnostic: set logging level DEBUG on orchestrator logger to see every backoff sleep; count "backoff attempt" occurrences to detect VT saturation episodes
duration: 10m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Add 429-aware exponential backoff to _do_lookup retry logic

**Replaced the single-immediate-retry in `_do_lookup_inner` with 429-aware exponential backoff: rate-limit errors sleep 15s × 2^attempt + jitter before retrying (up to 3 total attempts), while non-429 errors still retry immediately.**

## What Happened

Read `app/enrichment/orchestrator.py` (post-T01 state) and `tests/test_orchestrator.py` before writing code.

Modified `app/enrichment/orchestrator.py`:
- Added `import logging`, `import random`, `import time` at the top
- Added module-level logger: `logger = logging.getLogger(__name__)`
- Added four module-level backoff constants (`_BACKOFF_BASE=15`, `_BACKOFF_MULTIPLIER=2`, `_BACKOFF_JITTER=2.0`, `_MAX_RATE_LIMIT_RETRIES=2`)
- Added `_is_rate_limit_error(self, result)` method: returns True if `result` is `EnrichmentError` with "429" or "rate limit" (case-insensitive) in `.error`
- Replaced the single `result = adapter.lookup(ioc)` retry in `_do_lookup_inner` with a branching retry path:
  - 429/rate-limit: loop up to `_MAX_RATE_LIMIT_RETRIES` times, compute exponential delay with jitter, call `logger.warning()`, call `time.sleep(delay)`, retry; break on success or non-429 error
  - Non-429: single immediate retry (original behavior preserved exactly)

Modified `tests/test_orchestrator.py`:
- Added `patch` to `from unittest.mock import MagicMock, patch`
- Added `_BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES` to import from `app.enrichment.orchestrator`
- Added `_make_vt_adapter()` helper and `TestBackoff429` class with 5 tests:
  1. `test_429_triggers_backoff_sleep` — 429 on first call, success on second; assert sleep ≥ base, call count = 2
  2. `test_non_429_does_not_trigger_sleep` — Timeout on first call, success on second; assert sleep NOT called, call count = 2
  3. `test_triple_429_exhausts_retries` — all 3 calls return 429; assert sleep called exactly 2 times, final result is EnrichmentError, lookup called 3 times
  4. `test_backoff_delays_increase_exponentially` — all 3 calls return 429; assert second sleep arg > first sleep arg
  5. `test_rate_limit_string_without_429_triggers_backoff` — "Rate limit exceeded" (no numeric code); assert sleep called ≥ 1

## Verification

Ran `python3 -m pytest tests/test_orchestrator.py -v`: all 24 tests passed (15 pre-existing + 4 from T01 + 5 new) in 2.29s.

Ran `python3 -m pytest tests/ -q --ignore=tests/e2e`: 808 passed, 1 pre-existing failure (`test_analyze_deduplicates` in `tests/test_routes.py`) — confirmed same failure as T01 baseline, not a regression.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_orchestrator.py -v` | 0 | ✅ pass | 2.29s |
| 2 | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 1 | ✅ pass (pre-existing failure, not a regression) | 4.58s |

## Diagnostics

- Backoff log lines are emitted at WARNING level via `logger = logging.getLogger("app.enrichment.orchestrator")`
- To surface in production: add a handler to the `app.enrichment.orchestrator` logger (or root logger)
- Log format: `"Rate limit (429) from VirusTotal for 1.2.3.4 — backoff attempt 1, sleeping 16.3s"`
- To count VT saturation episodes: `grep "backoff attempt" app.log | wc -l`
- Exhausted retries: final `EnrichmentError` appears in `job["results"]` — no silent drop
- Module-level constants `_BACKOFF_BASE` and `_MAX_RATE_LIMIT_RETRIES` are importable for threshold assertions

## Deviations

None. Implementation followed the plan exactly.

## Known Issues

`tests/test_routes.py::test_analyze_deduplicates` was failing before T01 and continues to fail — unrelated to orchestrator changes.

## Observability Impact

**New signals added by this task:**

- `logging.WARNING` emitted every time a 429 backoff fires: includes provider name, IOC value, attempt number (1 or 2), and sleep duration in seconds.
- If all retries exhaust, the final `EnrichmentError` (with the adapter's original error message) surfaces as a result in `job["results"]` — no silent swallow.
- To inspect backoff activity at runtime: configure a handler on the `app.enrichment.orchestrator` logger (or the root logger) at WARNING or above.
- Failure visibility: retry count and delay values are visible in log output; `grep "backoff attempt"` in log files quickly surfaces VT saturation episodes.
- No new endpoints or metrics surfaces; backoff is fully internal to the orchestrator's worker threads.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — added logging/random/time imports, logger, backoff constants, `_is_rate_limit_error()`, replaced simple retry with 429-aware backoff loop in `_do_lookup_inner`
- `tests/test_orchestrator.py` — added `patch` import, backoff constant imports, `_make_vt_adapter()` helper, `TestBackoff429` class (5 tests)
