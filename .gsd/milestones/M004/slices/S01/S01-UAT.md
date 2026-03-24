# S01: Backend Concurrency & Error Correctness — UAT

**Milestone:** M004
**Written:** 2026-03-24 (closer verification)

## UAT Type

- UAT mode: artifact-driven
- Why: All concurrency fixes are proven by unit tests with threading coordination. Network error handler correctness is proven by grep-verified handler ordering + full suite regression. No runtime server or UI interaction needed.

## Preconditions

- Working directory: `/home/chris/projects/sentinelx/.gsd/worktrees/M004`
- Python 3.10+ available
- `pip install -e .` or equivalent has been run

## Smoke Test

```bash
python3 -m pytest tests/test_orchestrator.py -v --tb=short
```

**Expected:** `27 passed` — no failures, no errors.

---

## Test Cases

### 1. Semaphore released before backoff sleep

Proves the core concurrency fix: a 429 backoff on one IOC does not stall others waiting for the same semaphore.

```bash
python3 -m pytest tests/test_orchestrator.py::TestSemaphoreReleasedDuringBackoff -v
```

**Expected:** `1 passed` within 5 seconds.

**What it proves:** IOC-B acquires the semaphore while IOC-A is sleeping in backoff. Before the fix, IOC-B blocked indefinitely at `sem.acquire()`.

**Failure signal:** Test hangs past 5s or fails with "b_completed_before_sleep_returns was not set".

---

### 2. get_status() returns a list snapshot

```bash
python3 -m pytest tests/test_orchestrator.py::TestGetStatusListSnapshot -v
```

**Expected:** `1 passed`.

**What it proves:** Appending to the returned results list does not affect internal state. Before the fix, the second `get_status()` call showed the mutated list.

**Failure signal:** `AssertionError: 2 != 1` on second `get_status()` call.

---

### 3. _cached_markers writes protected by _lock

```bash
python3 -m pytest tests/test_orchestrator.py::TestCachedMarkersLock -v
```

**Expected:** `1 passed`.

**What it proves:** 8 concurrent cache writes all produce entries in `cached_markers` — no data loss from unsynchronized dict mutation.

**Failure signal:** `len(markers) != 8` or `RuntimeError: dictionary changed size during iteration`.

---

### 4. Non-429 retry waits 1 second

```bash
python3 -m pytest tests/test_orchestrator.py::TestBackoff429::test_non_429_retry_sleeps_1s -v
```

**Expected:** `1 passed`.

**What it proves:** `time.sleep(1)` called exactly once before retry. Before the fix, no delay was applied.

---

### 5. All orchestrator tests pass (zero regressions)

```bash
python3 -m pytest tests/test_orchestrator.py -v
```

**Expected:** `27 passed` — all 24 original + 3 new tests.

---

### 6. Backoff constants importable

```bash
python3 -c "from app.enrichment.orchestrator import _BACKOFF_BASE, _BACKOFF_MULTIPLIER, _BACKOFF_JITTER, _MAX_RATE_LIMIT_RETRIES; print('OK')"
```

**Expected:** Prints `OK` with exit code 0.

**Failure signal:** `ImportError` — constant renamed or removed.

---

### 7. SSLError handler in all 12 requests-based adapters

```bash
grep -rl 'SSLError' app/enrichment/adapters/*.py | sort | wc -l
```

**Expected:** `12`

**Confirm non-requests adapters NOT modified:**
```bash
grep -l 'SSLError' app/enrichment/adapters/asn_cymru.py app/enrichment/adapters/dns_lookup.py 2>/dev/null
```
**Expected:** No output (exit code 1).

---

### 8. ConnectionError handler in all 12 requests-based adapters

```bash
grep -rl 'ConnectionError' app/enrichment/adapters/*.py | sort | wc -l
```

**Expected:** `12` — same files as SSLError.

---

### 9. SSLError precedes ConnectionError in every adapter

```bash
for f in app/enrichment/adapters/{abuseipdb,crtsh,greynoise,hashlookup,ip_api,malwarebazaar,otx,shodan,threatfox,threatminer,urlhaus,virustotal}.py; do
  ssl=$(grep -n 'SSLError' "$f" | head -1 | cut -d: -f1)
  conn=$(grep -n 'except.*ConnectionError' "$f" | head -1 | cut -d: -f1)
  [ "$ssl" -lt "$conn" ] && echo "✅ $(basename $f)" || echo "❌ $(basename $f) WRONG ORDER"
done
```

**Expected:** All 12 show ✅.

**Why it matters:** SSLError is a subclass of ConnectionError. Reversed order silently catches SSL errors as "Connection failed" instead of "SSL/TLS error".

---

### 10. Session pooling in all 12 HTTP adapters

```bash
grep -rl 'self\._session' app/enrichment/adapters/*.py | sort | wc -l
```

**Expected:** `12`

```bash
grep -rn 'requests\.get(\|requests\.post(' app/enrichment/adapters/*.py
```

**Expected:** No output (exit code 1) — all adapters use `self._session.get()`/`self._session.post()`.

---

### 11. Full test suite — zero regressions

```bash
python3 -m pytest tests/ -x -q
```

**Expected:** `944 passed` (or more), `0 failed`.

---

## Edge Cases

### SSLError subclass ordering
If SSLError and ConnectionError handlers are swapped, SSLError instances silently fall into ConnectionError handler. Not detectable at runtime without explicit mocking. The grep ordering check (Test Case 9) is the guard.

### _do_lookup_inner() shim
Still exists as a passthrough to `_single_attempt()`. Any code calling it directly still works but goes through a shim. No external callers exist.

### Threading sensitivity
`test_semaphore_released_during_backoff_sleep` uses `threading.Event` with real threading. Mock sleep uses `side_effect` with a blocking event. If it fails, investigate threading, not logic.

---

## Not Proven By This UAT

- Runtime behavior under actual 429 responses from VirusTotal (proven by mock, not live API)
- Actual SSL certificate failures reaching the new handler (handler is present and ordered correctly, but no integration test triggers a real TLS error)
- Performance improvement of the semaphore fix (test proves isolation, not throughput)
- `safe_request()` consolidation (deferred — not part of executed scope)
