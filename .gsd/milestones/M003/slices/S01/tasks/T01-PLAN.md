---
estimated_steps: 5
estimated_files: 2
---

# T01: Add per-provider semaphore dict and raise max_workers

**Slice:** S01 — Per-Provider Concurrency & 429 Backoff
**Milestone:** M003

## Description

The current `EnrichmentOrchestrator` uses a single `ThreadPoolExecutor(max_workers=4)` for all adapters. When VT fills all 4 slots, zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are stuck waiting. The fix: raise `max_workers` so the thread pool isn't the bottleneck, then add per-provider `threading.Semaphore` entries that cap rate-limited providers (VT, etc.) at a configurable concurrency limit while leaving zero-auth providers uncapped.

This delivers requirement R014: zero-auth providers must complete independently of VT's rate limit.

**Relevant skills:** `test` skill for test generation patterns.

## Steps

1. **Read current `orchestrator.py`** to confirm `__init__()` signature, `_do_lookup()` body, and thread pool usage. The current signature is:
   ```python
   def __init__(self, adapters, max_workers=4, max_jobs=100, cache=None, cache_ttl_seconds=86400)
   ```

2. **Modify `__init__()`** in `app/enrichment/orchestrator.py`:
   - Add `import threading` at top (already has `from threading import Lock`, so extend to `from threading import Lock, Semaphore`)
   - Add optional parameter `provider_concurrency: dict[str, int] | None = None` (default `None` → empty dict)
   - Change `max_workers` default from `4` to `20`
   - Build `self._semaphores: dict[str, Semaphore]` by iterating `adapters`:
     ```python
     concurrency = provider_concurrency or {}
     self._semaphores = {}
     for adapter in adapters:
         name = getattr(adapter, "name", "")
         if getattr(adapter, "requires_api_key", False) and name:
             limit = concurrency.get(name, 4)  # default 4 for key-required
             self._semaphores[name] = Semaphore(limit)
     ```

3. **Modify `_do_lookup()`** — wrap the entire body (cache check + lookup + retry + cache store) inside the semaphore context if one exists:
   ```python
   provider_name = getattr(adapter, "name", "")
   sem = self._semaphores.get(provider_name)
   if sem:
       with sem:
           return self._do_lookup_inner(adapter, ioc, provider_name)
   else:
       return self._do_lookup_inner(adapter, ioc, provider_name)
   ```
   Extract the current body into `_do_lookup_inner()` or inline with a conditional. The key constraint: the semaphore wraps the **entire** lookup+retry cycle to avoid re-entrant deadlock.

4. **Add `TestPerProviderSemaphore` test class** in `tests/test_orchestrator.py`:
   - Create a mock "VT" adapter (`requires_api_key=True`, name="VirusTotal") with a slow lookup (0.3s sleep + result)
   - Create a mock "DNS" adapter (`requires_api_key=False`, name="DNS") with instant lookup
   - Use a shared `threading.Lock` + counter to track peak VT concurrency:
     ```python
     peak_vt = 0
     current_vt = 0
     vt_lock = threading.Lock()
     
     def slow_vt_lookup(ioc):
         nonlocal peak_vt, current_vt
         with vt_lock:
             current_vt += 1
             peak_vt = max(peak_vt, current_vt)
         time.sleep(0.3)
         with vt_lock:
             current_vt -= 1
         return _make_result(ioc, provider="VirusTotal")
     ```
   - Submit 8 IOCs of type IPV4 to orchestrator with both adapters
   - Assert: `peak_vt <= 4` (semaphore works)
   - Assert: DNS adapter completed all 8 lookups (not blocked by VT)
   - Assert: all 16 results returned (8 VT + 8 DNS)

   Also test: orchestrator with only zero-auth adapters — no semaphore created, no blocking.

5. **Run full test suite** to verify no regressions:
   ```
   python3 -m pytest tests/test_orchestrator.py -v
   python3 -m pytest tests/ -q --ignore=tests/e2e
   ```

## Must-Haves

- [ ] `_semaphores` dict built from `requires_api_key=True` adapters with configurable concurrency (default 4)
- [ ] `max_workers` default raised from 4 to 20
- [ ] Semaphore wraps entire lookup+retry cycle in `_do_lookup()` (not per-attempt)
- [ ] Zero-auth adapters have no semaphore — unlimited concurrency
- [ ] `__init__()` backward-compatible — existing callers pass no new args
- [ ] All 15 existing tests pass unchanged
- [ ] New `TestPerProviderSemaphore` tests prove VT capped at ≤4 concurrent, zero-auth unblocked

## Verification

- `python3 -m pytest tests/test_orchestrator.py -v` — all old + new tests pass
- `python3 -m pytest tests/ -q --ignore=tests/e2e` — full unit suite passes
- Peak concurrency assertion proves semaphore cap works
- Zero-auth completion assertion proves no starvation

## Inputs

- `app/enrichment/orchestrator.py` — current `EnrichmentOrchestrator` class with `ThreadPoolExecutor(max_workers=4)` and `_do_lookup()` retry logic
- `app/enrichment/provider.py` — `Provider` protocol with `requires_api_key: bool` attribute
- `tests/test_orchestrator.py` — 15 existing tests that must continue passing

## Expected Output

- `app/enrichment/orchestrator.py` — modified with `_semaphores` dict, raised `max_workers`, semaphore acquisition in `_do_lookup()`
- `tests/test_orchestrator.py` — new `TestPerProviderSemaphore` class with ≥3 tests proving concurrency cap and zero-auth independence
