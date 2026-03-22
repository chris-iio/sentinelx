---
id: S01
parent: M003
milestone: M003
provides:
  - Per-provider threading.Semaphore dict in EnrichmentOrchestrator (cap 4 for requires_api_key=True adapters, unlimited for zero-auth)
  - max_workers default raised from 4 to 20 (thread pool no longer the concurrency bottleneck)
  - _do_lookup/_do_lookup_inner split: outer acquires semaphore, inner runs full cache+lookup+retry+cache-store cycle
  - 429-aware exponential backoff in _do_lookup_inner (base 15s × 2^attempt + jitter, up to 2 retries / 3 total attempts)
  - _is_rate_limit_error() method (substring match on "429" or "rate limit", case-insensitive)
  - Module-level backoff constants (_BACKOFF_BASE, _BACKOFF_MULTIPLIER, _BACKOFF_JITTER, _MAX_RATE_LIMIT_RETRIES)
  - logging.warning() when 429 backoff fires (provider name, IOC value, attempt, delay)
  - TestPerProviderSemaphore (4 tests) + TestBackoff429 (5 tests) — 9 new tests added to 15 pre-existing (24 total)
requires: []
affects:
  - S04
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
key_decisions:
  - Semaphore wraps entire _do_lookup_inner body (cache-check + lookup + retry), not individual adapter.lookup() calls — avoids re-entrant deadlock
  - Zero-auth adapters (requires_api_key=False) receive no semaphore — unlimited concurrency preserved
  - provider_concurrency dict param allows per-name cap overrides at construction time
  - Two independent retry paths: rate-limit (sleep + retry) and non-rate-limit (immediate retry) — keeps non-429 throughput unchanged
  - _is_rate_limit_error is an instance method (not free function) so it's mockable via orchestrator instance
  - Patch target is app.enrichment.orchestrator.time.sleep (module-level import, not builtins)
patterns_established:
  - _do_lookup → _do_lookup_inner split: outer handles semaphore acquisition; inner contains all business logic
  - Backoff constants at module level — importable for threshold assertions in tests
  - "rate limit" backoff loop: for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1) with break on success or non-429 error
observability_surfaces:
  - logging.WARNING emitted on every 429 backoff: "Rate limit (429) from {provider} for {ioc} — backoff attempt {n}, sleeping {t}s"
  - Exhausted retries surface final EnrichmentError in job["results"] — no silent swallow
  - _semaphores dict inspectable at runtime: orchestrator._semaphores[name]._value = remaining slots
  - grep "backoff attempt" app.log to count VT saturation episodes
drill_down_paths:
  - .gsd/milestones/M003/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003/slices/S01/tasks/T02-SUMMARY.md
duration: 22m (T01: 12m, T02: 10m)
verification_result: passed
completed_at: 2026-03-20
---

# S01: Per-Provider Concurrency & 429 Backoff

**EnrichmentOrchestrator now gates VT (and any API-key provider) at ≤4 concurrent lookups via per-provider Semaphores, while zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh) run freely; 429 errors trigger exponential backoff sleep instead of immediate quota-burning retry.**

## What Happened

### T01: Per-provider semaphore dict + max_workers raise

Read `orchestrator.py`, `provider.py`, and the existing 15-test suite before writing code.

`EnrichmentOrchestrator.__init__()` was extended with an optional `provider_concurrency: dict[str, int] | None` parameter. On construction, it iterates all registered adapters and creates a `threading.Semaphore(cap)` for each adapter with `requires_api_key=True` and a non-empty name. Adapters with `requires_api_key=False` get no semaphore entry — they are intentionally excluded from concurrency gating.

`max_workers` was raised from 4 to 20, removing the thread pool as a de-facto concurrency gate. The semaphore is now the only constraint for keyed providers.

`_do_lookup()` was split into two methods: `_do_lookup()` acquires the semaphore (via `with` context manager) if the provider has one, then delegates to `_do_lookup_inner()` which contains the original cache-check + lookup + retry + cache-store logic. The split is essential: wrapping the *entire inner cycle* prevents re-entrant deadlock and caps *concurrent lookups* correctly (not just concurrent first-attempts).

`TestPerProviderSemaphore` added 4 tests confirming: VT peak concurrency ≤ 4 (atomic counter + threading.Event across 8 IOC batch), zero-auth adapter completes all 8 lookups while VT is running, semaphore dict is empty for public-only orchestrators and has a single entry for keyed ones, and `provider_concurrency` overrides are respected.

All 15 pre-existing tests passed unchanged. 19 total.

### T02: 429-aware exponential backoff

Read the post-T01 `orchestrator.py` and test file before writing code.

Added `import logging`, `import random`, `import time` at module level. Added `logger = logging.getLogger(__name__)`. Added four module-level backoff constants (`_BACKOFF_BASE=15`, `_BACKOFF_MULTIPLIER=2`, `_BACKOFF_JITTER=2.0`, `_MAX_RATE_LIMIT_RETRIES=2`).

Added `_is_rate_limit_error(self, result)` method: returns True if `result` is an `EnrichmentError` with "429" or "rate limit" (case-insensitive) in `.error`. Made it an instance method for mockability.

Replaced the single-immediate-retry in `_do_lookup_inner` with two independent paths: if the first lookup returns a rate-limit error, enter an exponential backoff loop (up to `_MAX_RATE_LIMIT_RETRIES` retries, `_BACKOFF_BASE × _BACKOFF_MULTIPLIER^attempt + random.uniform(0, _BACKOFF_JITTER)` sleep, `logger.warning()` before each sleep). If the first lookup returns any other error, preserve the original single immediate retry. This keeps non-429 throughput identical to pre-S01 behavior.

`TestBackoff429` added 5 tests confirming: 429 triggers sleep ≥ base, non-429 does not trigger sleep, triple-429 exhausts retries with exactly 2 sleeps and a final EnrichmentError, backoff delays increase exponentially across retries, and "rate limit" string without numeric code also triggers backoff.

All 19 previous tests passed. 24 total.

## Verification

| # | Command | Exit Code | Verdict |
|---|---------|-----------|---------|
| 1 | `python3 -m pytest tests/test_orchestrator.py -v` | 0 | ✅ 24/24 passed |
| 2 | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 1* | ✅ 808 passed, 1 pre-existing failure |

*Exit code 1 from pre-existing `test_analyze_deduplicates` failure in `test_routes.py` — confirmed failing on baseline before T01, unrelated to this slice.

## New Requirements Surfaced

- none

## Deviations

None. Both tasks implemented exactly as planned. No scope changes, no surprising behavior from the existing code.

## Known Limitations

- The semaphore cap (default 4) prevents >4 concurrent VT calls, but does not enforce a 1-minute sliding window. True token-bucket rate limiting (e.g., 4 requests/minute max) is out of scope per the milestone roadmap. The existing behavior already worked under VT's limit by coincidence; the semaphore prevents the *starvation* problem while respecting the same intent.
- `test_analyze_deduplicates` in `tests/test_routes.py` is a pre-existing failure, not introduced by this slice. It remains for the relevant S04 task to investigate or defer.

## Follow-ups

- S04 should investigate and resolve `test_analyze_deduplicates` if it's blocking the full test suite gate, or document it as a known skip.
- Runtime inspection of semaphore state could be surfaced via a `/admin/diagnostics` endpoint in a future milestone if VT saturation becomes a production concern.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — added `import logging/random/time`, logger, backoff constants, `_is_rate_limit_error()`, `provider_concurrency` param, `_semaphores` dict, raised `max_workers` to 20, split `_do_lookup` into `_do_lookup`/`_do_lookup_inner`, 429-aware backoff in `_do_lookup_inner`
- `tests/test_orchestrator.py` — added `threading` import, `patch` import, backoff constant imports, `_make_keyed_adapter()`, `_make_public_adapter()`, `_make_vt_adapter()` helpers, `TestPerProviderSemaphore` (4 tests), `TestBackoff429` (5 tests)

## Forward Intelligence

### What the next slice should know
- R014 (zero-auth starvation) and R015 (429 backoff) are now proven at contract level — tests are the evidence, no runtime E2E required.
- The `_do_lookup_inner` name is the canonical entry point for all cache/lookup/retry/cache-store logic. Any future retry or caching changes should be made there, not in `_do_lookup()`.
- Module-level constants `_BACKOFF_BASE` and `_MAX_RATE_LIMIT_RETRIES` should be imported in any future test that makes threshold assertions — hardcoding values creates drift risk.
- S04 integration tests don't need to verify orchestrator semaphore or backoff behavior via E2E — that's already proven here. S04's orchestrator coverage is "no regressions from S02/S03 changes."

### What's fragile
- `test_vt_peak_concurrency_capped_at_4` uses `threading.Event` and a shared counter with `time.sleep(0.3)` delays. It has passed reliably in development but is timing-sensitive on very slow CI systems. If it flaps, increase the sleep to 0.5s.
- MagicMock adapters without explicit `requires_api_key=False` are treated as keyed (truthy attribute). For small test batches this is harmless; for tests that assert semaphore dict contents, use `_make_keyed_adapter()` / `_make_public_adapter()` helpers to be explicit.

### Authoritative diagnostics
- `python3 -m pytest tests/test_orchestrator.py -v` — definitive health check; all 24 tests must pass
- `grep "backoff attempt" <logfile>` — counts VT saturation episodes in production log
- `orchestrator._semaphores["VirusTotal"]._value` — remaining VT slots at any point in runtime (0 = fully saturated)

### What assumptions changed
- Original plan assumed the thread pool starvation *was* the bug. Actually, the thread pool (max_workers=4) and the lack of per-provider gating were *both* the bug. Raising max_workers to 20 alone wouldn't solve it — the semaphore is what prevents VT from monopolizing all worker threads. Both changes were needed together.
