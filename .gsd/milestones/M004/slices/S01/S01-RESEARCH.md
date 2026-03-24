# S01: Backend Concurrency & Error Correctness — Research

**Date:** 2026-03-21
**Depth:** Light research — all fixes apply known Python threading patterns to known code; no new libraries or unfamiliar APIs.

## Summary

S01 targets four concurrency/correctness bugs in `app/enrichment/orchestrator.py` plus one error-message improvement across all 14 adapters. The orchestrator code is ~300 lines with 24 existing unit tests that all pass. Every fix is a surgical edit to an existing function — no new modules, no new dependencies, no architecture changes.

The four orchestrator bugs are: (1) semaphore held during `time.sleep()` backoff stalls all 4 VT slots; (2) `get_status()` returns a shallow copy that shares the live `results` list; (3) `_cached_markers` writes are unprotected by `_lock`; (4) non-429 retries have no delay (should wait 1s). The adapter fix adds explicit `ConnectionError`/`SSLError` handling before the blanket `except Exception` in all 14 adapters, producing actionable error strings instead of "Unexpected error during lookup".

## Recommendation

Fix all five issues in two tasks: one for the orchestrator (4 bugs), one for the adapters (error messages). The orchestrator task is the risky one — it restructures `_do_lookup` / `_do_lookup_inner` and must keep all 24 existing tests passing while adding new tests for the fixed behaviors. The adapter task is mechanical and safe.

## Implementation Landscape

### Key Files

- `app/enrichment/orchestrator.py` — all four concurrency bugs live here:
  - `_do_lookup()` (line ~171): semaphore `with sem:` wraps `_do_lookup_inner()` which contains the `time.sleep()` backoff loop. The sleep must happen **outside** the semaphore.
  - `get_status()` (line ~148): `return dict(job)` produces a shallow copy — `copy["results"]` is the **same list object** as the internal one. Workers appending results while Flask serializes can produce `RuntimeError: list changed size during iteration`.
  - `_do_lookup_inner()` (line ~224): `self._cached_markers[cache_key] = cached_at` runs in worker threads without holding `_lock`.
  - `_do_lookup_inner()` (line ~258): non-429 retry is immediate (`result = adapter.lookup(ioc)`) — should `time.sleep(1)` before retry.
  - `cached_markers` property (line ~169): reads `_cached_markers` without `_lock`.

- `tests/test_orchestrator.py` — 24 tests, all passing. Tests import `_BACKOFF_BASE` and `_MAX_RATE_LIMIT_RETRIES` from orchestrator module (KNOWLEDGE entry). Key test classes:
  - `TestPerProviderSemaphore` — 4 tests verifying semaphore cap behavior and VT/zero-auth independence. These MUST still pass after the semaphore restructure.
  - `TestBackoff429` — 5 tests verifying 429 backoff, exponential delay, and non-429 immediate retry. The `test_non_429_does_not_trigger_sleep` test currently asserts `mock_sleep.call_count == 0` — this **will break** when the 1s non-429 retry delay is added and must be updated.

- `app/enrichment/adapters/*.py` (14 files) — each has the same try/except pattern:
  ```
  except requests.exceptions.Timeout: ...
  except requests.exceptions.HTTPError as exc: ...
  except Exception: ...  # catches ConnectionError, SSLError silently
  ```
  None import or explicitly catch `requests.exceptions.ConnectionError` or `requests.exceptions.SSLError`. The `except Exception` produces "Unexpected error during lookup" with no network-specific context.

- `app/routes.py` (line ~357) — calls `orchestrator.get_status(job_id)` then iterates `status["results"]` to serialize. This is the consumer that can hit the shallow-copy race.

### Build Order

**Task 1: Orchestrator concurrency fixes** (risk: medium)

Four changes to `orchestrator.py`, in this order within the file:

1. **`get_status()` — return `list()` snapshot of results.** Change line ~160 from `return dict(job)` to a copy that also snapshots the results list:
   ```python
   copy = dict(job)
   copy["results"] = list(job["results"])
   return copy
   ```
   This is the simplest fix — `list()` creates a new list with the same elements. No test changes needed (existing tests never test concurrently reading `get_status` during `enrich_all`).

2. **`cached_markers` property and `_do_lookup_inner` — lock `_cached_markers` writes and reads.** Wrap the write at line ~224 and the property read at line ~169 with `self._lock`. Three lines changed total.

3. **`_do_lookup()` — release semaphore before sleep.** This is the core restructure. Currently:
   ```python
   if sem is not None:
       with sem:
           return self._do_lookup_inner(adapter, ioc, provider_name)
   return self._do_lookup_inner(adapter, ioc, provider_name)
   ```
   Must become: acquire semaphore → call `adapter.lookup(ioc)` → release semaphore → THEN if 429, sleep + re-acquire semaphore → retry. This means splitting `_do_lookup_inner` so the cache-check + HTTP call is one unit (under semaphore), while the backoff sleep + retry loop is at the `_do_lookup` level (outside semaphore). Approach:
   - Extract the single-attempt logic (cache-check → `adapter.lookup(ioc)` → cache-store) into a `_single_lookup()` method that runs under semaphore.
   - Keep retry/backoff orchestration in `_do_lookup()`, acquiring/releasing the semaphore per attempt via explicit `sem.acquire()`/`sem.release()` instead of `with sem:`.
   - This preserves the "semaphore wraps entire single attempt" invariant from KNOWLEDGE while allowing sleep between attempts without holding the semaphore.

4. **Non-429 retry — add 1s delay.** In the `else` branch (line ~258), add `time.sleep(1)` before the retry call. Update `test_non_429_does_not_trigger_sleep` to assert `mock_sleep.call_count == 1` and check the delay is ~1s.

**New tests to add:**
- `test_semaphore_released_during_backoff_sleep` — submit multiple IOCs with slow 429 response; verify that other IOCs can acquire the semaphore while one is sleeping. Use a barrier/event pattern: IOC-A gets 429 → sleeps (semaphore released) → IOC-B acquires semaphore and completes during A's sleep.
- `test_get_status_returns_list_snapshot` — call `get_status()`, mutate the returned `results` list, verify internal state unchanged.
- `test_cached_markers_thread_safe` — concurrent writes to `_cached_markers` via cache hits; verify no `RuntimeError`.

**Task 2: Adapter error messages** (risk: low)

Add explicit `except requests.exceptions.ConnectionError` and `except requests.exceptions.SSLError` handlers **before** `except Exception` in all 14 adapter `lookup()` methods. Pattern:

```python
except requests.exceptions.ConnectionError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="Connection failed")
except requests.exceptions.SSLError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="SSL/TLS error")
except Exception:
    ...  # existing handler unchanged
```

Note: `SSLError` is a subclass of `ConnectionError` in the `requests` library, so the `SSLError` catch must come **before** `ConnectionError` to avoid it being swallowed. The 14 files are:
- `abuseipdb.py`, `asn_cymru.py` (uses socket, not requests — skip or handle differently), `crtsh.py`, `dns_lookup.py` (uses `dnspython`, not requests — skip), `greynoise.py`, `hashlookup.py`, `ip_api.py`, `malwarebazaar.py`, `otx.py`, `shodan.py`, `threatfox.py`, `threatminer.py`, `urlhaus.py`, `virustotal.py`

`asn_cymru.py` and `dns_lookup.py` don't use `requests` — they use socket/dns.resolver respectively. These only need their existing exception handling reviewed, not the requests-specific `ConnectionError`/`SSLError` additions. That reduces the mechanical edit to **12 adapter files** that use `requests`.

### Verification Approach

1. **All 24 existing orchestrator tests pass** — `python3 -m pytest tests/test_orchestrator.py -v`
2. **New tests pass** — the 3+ new tests for semaphore-sleep separation, list snapshot, and cached_markers locking
3. **Grep verification:**
   - `rg 'ConnectionError' app/enrichment/adapters/ --type py -c` → 12 files (all requests-based adapters)
   - `rg 'SSLError' app/enrichment/adapters/ --type py -c` → 12 files
   - `rg 'Unexpected error during lookup' app/enrichment/adapters/ --type py -c` → still 14 (blanket handler preserved)
4. **Full unit test suite** — `python3 -m pytest tests/ -x -q` → 828+ pass, 0 fail

## Common Pitfalls

- **`SSLError` is a subclass of `ConnectionError`** in `requests.exceptions` — the `except SSLError` clause MUST precede `except ConnectionError`, or SSLError will be caught by the ConnectionError handler and the more specific "SSL/TLS error" message will never fire.
- **Semaphore restructure must keep `_BACKOFF_BASE` and `_MAX_RATE_LIMIT_RETRIES` importable at the same module paths** — tests import these constants directly (KNOWLEDGE entry). Do not move them or rename them.
- **`test_non_429_does_not_trigger_sleep`** currently asserts `mock_sleep.call_count == 0`. Adding a 1s non-429 retry delay will break this test. It must be updated to expect exactly 1 sleep call with delay ~1s.
- **`time.sleep` patch path** — must be `"app.enrichment.orchestrator.time.sleep"`, not `"time.sleep"` (KNOWLEDGE entry).

## Constraints

- All 24 existing orchestrator tests must pass after changes — zero tolerance for regressions.
- `_BACKOFF_BASE`, `_BACKOFF_MULTIPLIER`, `_BACKOFF_JITTER`, `_MAX_RATE_LIMIT_RETRIES` must remain importable from `app.enrichment.orchestrator`.
- The `asn_cymru.py` adapter uses `socket` (not `requests`) and `dns_lookup.py` uses `dnspython` — these two do NOT get the `requests.exceptions.ConnectionError`/`SSLError` treatment.
