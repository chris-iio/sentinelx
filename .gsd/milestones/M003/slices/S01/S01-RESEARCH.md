# S01: Per-Provider Concurrency & 429 Backoff — Research

**Date:** 2026-03-20
**Depth:** Targeted — known technology (Python threading, semaphores), but the concurrency model needs a specific seam redesign in the orchestrator.

## Requirements Targeted

- **R014** — Per-provider concurrency control: zero-auth providers must complete independently of VT's rate limit
- **R015** — 429 backoff: VT 429 responses trigger exponential backoff, not immediate quota-burning retry

## Summary

The current `EnrichmentOrchestrator` uses a single `ThreadPoolExecutor(max_workers=4)` for all adapters. This means if VT has 4 lookups in flight, zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are stuck waiting for an executor slot. The fix is straightforward: raise `max_workers` to allow all providers to run freely, then add a per-provider `threading.Semaphore` dict that caps VT-specific concurrency at 4. The semaphore approach avoids true rate-limiting complexity (token bucket) while solving the real problem — zero-auth starvation.

The `_do_lookup()` retry logic currently retries immediately on any `EnrichmentError`, including 429 rate-limit errors. This burns API quota. The fix: detect "429" or "Rate limit" in the error message string and apply exponential backoff with jitter (e.g. 15s base, 2× multiplier, up to ~60s) before retrying. Non-rate-limit errors continue with immediate retry (existing behavior).

Both changes are entirely within `orchestrator.py` and `test_orchestrator.py`. No adapter changes, no route changes, no template changes. Clean unit-testable scope.

## Recommendation

1. **Per-provider semaphore dict** — Add `_semaphores: dict[str, threading.Semaphore]` to `EnrichmentOrchestrator.__init__()`. For each adapter with `requires_api_key=True`, create a semaphore with a configurable limit (default 4 for VT). Zero-auth adapters (`requires_api_key=False`) get no semaphore — unlimited concurrency. `_do_lookup()` acquires the semaphore (if present) before calling `adapter.lookup()` and releases it after.

2. **Raise max_workers** — Increase `max_workers` default from 4 to a higher value (e.g. 20 or `len(dispatch_pairs)` capped at 20) so the thread pool is not the bottleneck. The semaphore becomes the concurrency gate for rate-limited providers.

3. **429-aware backoff in `_do_lookup()`** — On first `EnrichmentError`, check if the error message contains "429" or "Rate limit". If yes: sleep with exponential backoff (base 15s + jitter) before retry. If no: immediate retry (preserving current behavior). Allow up to 2 retries for 429 (total 3 attempts) since the backoff delay should respect the rate limit window.

## Implementation Landscape

### Key Files

- `app/enrichment/orchestrator.py` — **Primary change target.** `EnrichmentOrchestrator.__init__()` gets `_semaphores` dict. `_do_lookup()` gets semaphore acquisition and 429-aware backoff logic. `enrich_all()` may adjust `max_workers` or accept it as-is with the higher default.
- `app/enrichment/models.py` — No changes needed. `EnrichmentError.error` is already a string field that adapters populate with "Rate limit exceeded (429)" or "HTTP 429".
- `app/enrichment/provider.py` — No changes needed. `Provider.requires_api_key` is already on the protocol and all adapters implement it.
- `tests/test_orchestrator.py` — **Primary test target.** Add new test classes: `TestPerProviderSemaphore` and `TestBackoff429`. Existing 15 tests must continue passing unchanged.
- `app/routes.py` — No changes needed. It already passes `registry.configured()` as `adapters=` — the orchestrator is the only thing that changes.
- `app/enrichment/setup.py` — No changes needed. Registry construction is unchanged.

### Patterns to Follow

- **Semaphore in `_do_lookup()`** — Use `with self._semaphores[provider_name]:` context manager wrapping the `adapter.lookup()` call. The `with` statement handles acquire/release even on exceptions.
- **Building the semaphore dict** — In `__init__()`, iterate `adapters` and for each adapter with `requires_api_key=True`, create `Semaphore(concurrency_limit)`. Store by `adapter.name`. A `provider_concurrency` dict parameter (e.g. `{"VirusTotal": 4}`) gives flexibility; default all `requires_api_key=True` providers to some cap (4), leave `requires_api_key=False` uncapped.
- **Backoff detection** — Check `isinstance(result, EnrichmentError) and ("429" in result.error or "rate limit" in result.error.lower())`. This is fragile to error message changes but covers all current adapters (VT returns "Rate limit exceeded (429)", others return "HTTP 429").
- **Backoff implementation** — `time.sleep(base * (2 ** attempt) + random.uniform(0, jitter))`. stdlib only, no external dependencies.

### Build Order

1. **First: per-provider semaphore + raised max_workers** — This is the higher-risk change (threading behavior). Write the semaphore dict construction and acquisition logic. Write tests that prove: (a) VT adapter calls are capped at N concurrent even with many IOCs, (b) zero-auth adapter calls are NOT blocked by VT semaphore. Use `threading.Barrier` or timing-based assertions in tests.
2. **Second: 429 backoff** — Lower risk, isolated to `_do_lookup()` retry branch. Write the rate-limit detection and backoff sleep. Write tests that mock `time.sleep` to verify backoff is called with correct delays. Verify non-429 errors still retry immediately.

### Verification Approach

- `python3 -m pytest tests/test_orchestrator.py -v` — all existing 15 tests pass + new semaphore/backoff tests pass
- **Semaphore test strategy:** Create a mock VT adapter (slow lookup, 0.5s) and a mock zero-auth adapter (instant lookup). Submit 8 IOCs. Assert: zero-auth adapter completes in <1s (not blocked), VT adapter has max 4 concurrent calls (use a shared counter + lock to track peak concurrency).
- **Backoff test strategy:** Mock `time.sleep` via `unittest.mock.patch`. Create a mock adapter that returns 429 error on first call, success on second. Assert `time.sleep` was called with a value ≥ base backoff. Assert non-429 error does NOT call `time.sleep`.
- No E2E tests needed for S01 — this is purely backend orchestrator logic. S04 integration tests will verify the full pipeline.

## Constraints

- `EnrichmentOrchestrator.__init__()` public API must remain backward-compatible — existing callers in `app/routes.py` pass `adapters=` and optionally `cache=`/`cache_ttl_seconds=`. New parameters must have defaults.
- `max_workers=4` is the current default. Changing it to a higher value is safe since the semaphore becomes the real concurrency gate, but the parameter must still accept explicit values from callers.
- No new external dependencies — use `threading.Semaphore` and `time.sleep` from stdlib.
- The `requires_api_key` attribute is already on every adapter via the Provider protocol — no adapter changes needed to read it.

## Common Pitfalls

- **Semaphore deadlock risk** — If `_do_lookup()` acquires a semaphore then the retry also needs the semaphore, you get a deadlock (re-entrant acquire on non-reentrant Semaphore). Solution: acquire the semaphore once wrapping the entire lookup-retry cycle, not per-attempt. The semaphore should wrap the full `_do_lookup()` body, including retries.
- **`time.sleep` in thread pool** — Sleeping inside a `ThreadPoolExecutor` thread blocks that worker. With `max_workers=20`, blocking 4 VT workers on backoff still leaves 16 workers free for zero-auth. This is acceptable. If max_workers were still 4, backoff would block all workers — the raised max_workers is prerequisite.
- **Error message matching brittleness** — Current adapters use inconsistent 429 messages ("Rate limit exceeded (429)" vs "HTTP 429"). Match on `"429"` substring which covers both patterns. If a future adapter changes the message format, the backoff won't fire — but that's a graceful degradation (falls back to immediate retry, existing behavior).
- **Test flakiness from timing** — Semaphore tests using wall-clock assertions (elapsed time) can be flaky in CI. Prefer counting peak concurrency via a shared atomic counter rather than relying on timing. Use `threading.Event` barriers to create deterministic concurrency scenarios.

## Open Risks

- **Semaphore vs. rate-limit mismatch** — As noted in the roadmap, a semaphore of 4 is NOT a 4 req/min rate limiter. 4 requests could all fire in <1s. The pragmatic stance (from M003-ROADMAP.md): this already worked by coincidence, and fixing zero-auth starvation is the real goal. True token-bucket rate limiting is explicitly out of scope.
