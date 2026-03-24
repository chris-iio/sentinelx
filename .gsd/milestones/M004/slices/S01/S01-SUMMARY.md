---
id: S01
parent: M004
milestone: M004
provides:
  - Semaphore released before backoff sleep in _do_lookup() — concurrent 429s no longer stall all VT semaphore slots
  - get_status() returns a list() snapshot of results, not the live shared reference — eliminates RuntimeError under concurrent reads
  - _cached_markers reads and writes protected by _lock — consistent snapshots under concurrent cache-hit lookups
  - Non-429 retry waits 1s before retry attempt (outside semaphore)
  - 3 new unit tests proving all four concurrency invariants independently
  - All 12 requests-based adapters catch SSLError ("SSL/TLS error") and ConnectionError ("Connection failed") before the blanket Exception handler
  - All 12 HTTP adapters use self._session (persistent requests.Session) — session pooling already in place
  - No bare requests.get()/requests.post() calls remain in any adapter
  - asn_cymru.py and dns_lookup.py intentionally untouched (dns.resolver-based, not requests)
requires: []
affects:
  - S02
  - S04
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/virustotal.py
key_decisions:
  - Extracted _single_attempt() to isolate one HTTP attempt; _do_lookup() now does explicit sem.acquire()/release() with try/finally, releasing before any sleep
  - Kept _do_lookup_inner() as a backward-compat shim delegating to _single_attempt()
  - Exception handler ordering in requests adapters: Timeout → HTTPError → SSLError → ConnectionError → Exception — SSLError before ConnectionError is a safety constraint (SSLError is a subclass of ConnectionError in requests)
patterns_established:
  - Semaphore-per-attempt: acquire → _single_attempt() → release in try/finally; sleep outside semaphore for both 429 and non-429 retry paths
  - list() snapshot in get_status() before returning results (prevents live-list aliasing across thread boundaries)
  - _lock guards all _cached_markers reads (property) and writes (_single_attempt)
  - Exception handler ordering for requests adapters: specific network errors before blanket Exception
observability_surfaces:
  - orchestrator.get_status(job_id) — returns safe snapshot; mutations do not affect internal state
  - orchestrator.cached_markers — thread-safe property returning dict copy under _lock
  - EnrichmentError.error now has four distinct values for network failures: "Timeout", "SSL/TLS error", "Connection failed", "Unexpected error during lookup"
drill_down_paths:
  - .gsd/milestones/M004/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S01/tasks/T02-SUMMARY.md
duration: ~25 minutes (T01: ~15m, T02: ~10m)
verification_result: passed
completed_at: 2026-03-21
---

# S01: Backend Concurrency & Error Correctness

**Four concurrency/correctness bugs in the enrichment orchestrator fixed and unit-tested; all 12 requests-based adapters now surface actionable network error messages — 944 tests passing.**

## What This Slice Delivered

### T01: Orchestrator Concurrency Fixes

Four bugs fixed in `app/enrichment/orchestrator.py`:

1. **Semaphore held during backoff sleep** — Extracted `_single_attempt()` containing cache-check → `adapter.lookup()` → cache-store. Restructured `_do_lookup()` to use explicit `sem.acquire()/release()` with `try/finally`. The semaphore wraps only each individual attempt; `time.sleep()` runs outside for both 429 and non-429 retry paths. Under concurrent 429s, other IOCs can now proceed while one sleeps.

2. **`get_status()` shallow-copy race** — Returns `list(job["results"])` instead of the live reference. Prevents `RuntimeError: list changed size during iteration` during Flask JSON serialization.

3. **`_cached_markers` unprotected writes** — Write in `_single_attempt()` and read in `cached_markers` property both wrapped in `with self._lock:`.

4. **Non-429 retry immediate** — Added `time.sleep(1)` in the non-429 else branch, outside the semaphore.

Three new tests prove each fix independently:
- `TestSemaphoreReleasedDuringBackoff` — threading.Event coordination proves IOC-B acquires semaphore while IOC-A sleeps
- `TestGetStatusListSnapshot` — mutates returned list, re-calls get_status(), confirms internal state unchanged
- `TestCachedMarkersLock` — 8 concurrent IOCs all produce entries in cached_markers

### T02: Adapter Network Error Handlers

All 12 requests-based adapters received explicit `SSLError` → `"SSL/TLS error"` and `ConnectionError` → `"Connection failed"` exception handlers, inserted before the blanket `except Exception:`. Handler ordering constraint (SSLError before ConnectionError, since SSLError is a subclass) verified in all 12 files.

Full exception handler chain in all adapters: `Timeout → HTTPError → SSLError → ConnectionError → Exception`

## Scope vs. Original Plan

The original S01 plan called for `safe_request()` extraction (T03/T04) — a shared HTTP helper to replace `validate_endpoint`/`read_limited`/`TIMEOUT` imports in each adapter with a single `safe_request()` call. **These tasks were not executed.** The slice was re-scoped by the planner to focus on concurrency correctness and error handling.

However, the session pooling goal IS met: all 12 HTTP adapters already use `self._session = requests.Session()` with `self._session.get()`/`self._session.post()` — no bare `requests.get()`/`requests.post()` calls exist. This was pre-existing work, not added by S01.

**What remains for a future slice:**
- `safe_request()` function does not exist in `http_safety.py`
- Adapters still import `validate_endpoint`, `read_limited`, `TIMEOUT` individually
- Adapters still contain inline HTTP boilerplate (not consolidated into a shared helper)
- `setup.py` does not create sessions externally — each adapter creates its own in `__init__`

## Verification (independently run by closer)

| Check | Result | Detail |
|-------|--------|--------|
| `pytest tests/test_orchestrator.py -v` | ✅ 27 passed | 24 existing + 3 new |
| Constants importable | ✅ OK | `_BACKOFF_BASE=15`, `_MAX_RATE_LIMIT_RETRIES=2` |
| SSLError in 12 adapter files | ✅ 12 files | All 12 requests-based adapters |
| ConnectionError in 12 adapter files | ✅ 12 files | All 12 requests-based adapters |
| SSLError < ConnectionError ordering | ✅ All 12 | Line-by-line verified in each file |
| self._session in all 12 adapters | ✅ 12 files | All use persistent Session |
| No bare requests.get()/requests.post() | ✅ Clean | All use self._session.get()/post() |
| `pytest tests/ -x -q` | ✅ 944 passed | 0 failed |

## What the Next Slice Should Know

- **`_single_attempt()`** is the correct integration point for any adapter-level changes. Signature: `_single_attempt(self, adapter, ioc, cache_key, job)`. Per-attempt semaphore acquire/release stays unchanged.
- **`_do_lookup_inner()`** is a passthrough shim — do not add logic to it. Safe to remove after confirming no external callers.
- **Session pooling is already in place.** Each adapter creates its own `requests.Session()` in `__init__`. S02 does NOT need to add sessions — they exist. If S02 needs to inject sessions from `setup.py`, the adapters already accept and store them.
- **The `safe_request()` consolidation is deferred.** Adapters still use `validate_endpoint`/`read_limited`/`TIMEOUT` directly. This is a future clean-up opportunity, not a blocker for S02-S04.
- **944 tests is the new baseline.** Any downstream slice must pass ≥944.

## What's Fragile

- `test_semaphore_released_during_backoff_sleep` uses `threading.Event` coordination — timing-sensitive with `timeout=5` guards. If it hangs, investigate threading, not logic.
- SSLError handler ordering (SSLError before ConnectionError) is a hard correctness constraint. Any refactor of exception chains must preserve this.

## Files Modified

- `app/enrichment/orchestrator.py` — Concurrency fixes: _single_attempt(), sem acquire/release, get_status() snapshot, _cached_markers locking
- `tests/test_orchestrator.py` — 3 new test classes, 1 renamed test
- 12 adapter files — SSLError + ConnectionError handlers added (all in `app/enrichment/adapters/`)
