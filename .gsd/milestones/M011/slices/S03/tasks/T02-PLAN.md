---
estimated_steps: 117
estimated_files: 1
skills_used: []
---

# T02: Replace time.sleep concurrency proofs with threading synchronization primitives

## Description

Rewrite 3 orchestrator concurrency tests that use real `time.sleep()` inside mock side-effect functions. Replace the sleep-based timing with `threading.Barrier`, `threading.Event`, and `threading.Lock` synchronization primitives that prove concurrency without wall-clock delays. Target: all 3 tests complete in <0.1s each (down from 0.6-1.0s), bringing total orchestrator suite under 1s.

**CRITICAL for all 3 rewrites:** Each test's mock side_effect calls `time.sleep()` to create artificial latency. But the orchestrator's retry path ALSO calls `time.sleep(1)`. After T01, the 4 retry-path tests are patched — but these 3 concurrency tests need their OWN `time.sleep` patches too, because if any IOC triggers a retry (unlikely in these tests but defensive), the unpatched sleep would add 1s. Always patch `"app.enrichment.orchestrator.time.sleep"` alongside the sync primitive rewrite.

### Test 1: `test_enrich_all_parallel_execution` (currently ~1.0s)

**Current approach:** 5 IOCs, each mock sleeps 0.5s. Asserts wall-clock `elapsed < 3.0s` to prove parallelism.

**New approach:** Use `threading.Barrier(6)` (5 worker threads + 1 for the timeout). Each mock lookup waits at the barrier. If execution is parallel, all 5 threads reach the barrier simultaneously and proceed. If sequential, the barrier would timeout (only 1 thread at a time). The barrier itself proves parallelism — no wall-clock assertion needed.

```python
def test_enrich_all_parallel_execution(self, mock_adapter):
    """5 IOCs dispatched in parallel — barrier proves all 5 threads run concurrently."""
    iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(5)]
    barrier = threading.Barrier(5, timeout=2)

    def barrier_lookup(ioc):
        barrier.wait()  # blocks until all 5 threads arrive
        return _make_result(ioc)

    mock_adapter.lookup.side_effect = barrier_lookup

    orchestrator = _make_orchestrator(mock_adapter, max_workers=5)
    with patch("app.enrichment.orchestrator.time.sleep"):
        orchestrator.enrich_all("job-parallel", iocs)

    status = orchestrator.get_status("job-parallel")
    assert len(status["results"]) == 5
    # If barrier.wait() didn't timeout, all 5 threads were concurrent
```

The barrier's timeout=2 is a safety net — if threads are sequential, only 1 arrives and `barrier.wait()` raises `BrokenBarrierError` after 2s, failing the test with a clear message.

### Test 2: `test_vt_peak_concurrency_capped_at_4` (currently ~0.6s)

**Current approach:** 8 IOCs, VT adapter sleeps 0.3s per lookup. Uses shared counter + Lock to measure peak concurrent VT invocations. Asserts `peak_vt <= 4`.

**New approach:** Keep the counter+lock peak measurement (it's correct). Replace `time.sleep(0.3)` with `Event.wait()` that releases after all expected threads have entered the critical section. Use a `threading.Event` that gets set once `current_vt` reaches 4 (the semaphore cap), meaning the first batch of 4 threads are all inside the lookup. Each thread waits on this event before decrementing, ensuring overlap is measurable.

```python
def test_vt_peak_concurrency_capped_at_4(self):
    peak_vt = 0
    current_vt = 0
    vt_lock = threading.Lock()
    batch_full = threading.Event()

    iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(8)]
    vt_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})

    def coordinated_vt_lookup(ioc):
        nonlocal peak_vt, current_vt
        with vt_lock:
            current_vt += 1
            peak_vt = max(peak_vt, current_vt)
            if current_vt >= 4:
                batch_full.set()
        batch_full.wait(timeout=2)  # hold threads until batch measured
        with vt_lock:
            current_vt -= 1
        return _make_result(ioc, provider="VirusTotal")

    vt_adapter.lookup.side_effect = coordinated_vt_lookup
    orchestrator = EnrichmentOrchestrator(adapters=[vt_adapter], max_workers=20)
    with patch("app.enrichment.orchestrator.time.sleep"):
        orchestrator.enrich_all("job-semaphore-cap", iocs)

    status = orchestrator.get_status("job-semaphore-cap")
    assert len(status["results"]) == 8
    assert peak_vt <= 4, f"VT peak concurrency {peak_vt} exceeded semaphore cap of 4"
```

### Test 3: `test_zero_auth_completes_without_waiting_for_vt` (currently ~0.6s)

**Current approach:** VT sleeps 0.3s per lookup (slow). DNS is instant. Asserts all 16 results present and DNS completed all 8.

**New approach:** VT waits on an `Event` that never gets set until after we check DNS completion. DNS is instant. After `enrich_all`, DNS should have completed all 8 calls regardless of VT being "stuck". Then release VT to let it finish.

```python
def test_zero_auth_completes_without_waiting_for_vt(self):
    iocs = [_make_ioc(IOCType.IPV4, f"10.0.1.{i}") for i in range(8)]
    vt_adapter = _make_keyed_adapter("VirusTotal", supported_types={IOCType.IPV4})
    dns_adapter = _make_public_adapter("DNS", supported_types={IOCType.IPV4})

    vt_gate = threading.Event()
    dns_done = threading.Event()
    dns_calls = [0]
    dns_lock = threading.Lock()

    def gated_vt_lookup(ioc):
        vt_gate.wait(timeout=2)  # block until released
        return _make_result(ioc, provider="VirusTotal")

    def instant_dns_lookup(ioc):
        with dns_lock:
            dns_calls[0] += 1
            if dns_calls[0] == 8:
                dns_done.set()
        return _make_result(ioc, provider="DNS")

    vt_adapter.lookup.side_effect = gated_vt_lookup
    dns_adapter.lookup.side_effect = instant_dns_lookup

    # Run in a thread so we can check DNS while VT is blocked
    orchestrator = EnrichmentOrchestrator(adapters=[vt_adapter, dns_adapter], max_workers=20)
    import threading as _t
    enrich_thread = _t.Thread(target=orchestrator.enrich_all, args=("job-dns-free", iocs))
    with patch("app.enrichment.orchestrator.time.sleep"):
        enrich_thread.start()
        # DNS should complete quickly while VT is gated
        assert dns_done.wait(timeout=2), "DNS did not complete 8 lookups in time"
        # Now release VT
        vt_gate.set()
        enrich_thread.join(timeout=5)

    status = orchestrator.get_status("job-dns-free")
    assert len(status["results"]) == 16
    assert dns_adapter.lookup.call_count == 8
```

**IMPORTANT:** Test 3 is the most complex rewrite. The key insight is that `enrich_all` blocks until completion. To observe DNS completing *while* VT is still blocked, we must run `enrich_all` in a separate thread. This is the only safe way to assert the temporal ordering.

Alternative simpler approach for test 3: Keep the test synchronous but just replace `time.sleep(0.3)` with an `Event.wait(timeout=0.01)` that expires almost instantly. The test still proves DNS and VT coexist, and the `dns_call_count` event still verifies all 8 DNS calls completed. This is simpler and still valid — the original test didn't actually assert temporal ordering, just that all 16 results arrived and DNS completed all 8. **Use the simpler approach unless the synchronous version fails.**

## Steps

1. Open `tests/test_orchestrator.py`. Add `import threading` to imports if not already present (check — it's likely already imported for the semaphore tests).
2. Rewrite `test_enrich_all_parallel_execution` with `threading.Barrier(5, timeout=2)` pattern. Remove the `time.sleep(0.5)` side effect and the wall-clock elapsed assertion. Add `with patch("app.enrichment.orchestrator.time.sleep"):` around `enrich_all`.
3. Rewrite `test_vt_peak_concurrency_capped_at_4` — keep counter+lock peak measurement, replace `time.sleep(0.3)` with `Event.wait()` coordination. Add sleep patch.
4. Rewrite `test_zero_auth_completes_without_waiting_for_vt` — replace VT `time.sleep(0.3)` with `Event.wait(timeout=0.01)` (near-instant). Keep DNS as instant. Add sleep patch. Keep existing assertions.
5. Run `python3 -m pytest tests/test_orchestrator.py -q --durations=10` — verify 27 passed in <1s total. None of the 7 previously-slow tests should appear in slowest durations.
6. Run `python3 -m pytest --tb=short -q` — verify all 1012 tests pass.

## Must-Haves

- [ ] `test_enrich_all_parallel_execution` uses `threading.Barrier` instead of `time.sleep`
- [ ] `test_vt_peak_concurrency_capped_at_4` uses `threading.Event` coordination instead of `time.sleep(0.3)`
- [ ] `test_zero_auth_completes_without_waiting_for_vt` uses `threading.Event` instead of `time.sleep(0.3)`
- [ ] All 3 rewritten tests have `timeout` parameters on blocking calls (no infinite waits)
- [ ] All 3 rewritten tests include `with patch("app.enrichment.orchestrator.time.sleep"):` for defense
- [ ] 27 orchestrator tests pass in <1s total
- [ ] 1012 total tests pass with zero failures

## Verification

```bash
# Orchestrator tests fast
python3 -m pytest tests/test_orchestrator.py -q --durations=10
# Target: 27 passed in <1s

# Full suite
python3 -m pytest --tb=short -q
# Target: 1012 passed
```

## Inputs

- ``tests/test_orchestrator.py` — file from T01 with 4 sleep-patched tests already applied`

## Expected Output

- ``tests/test_orchestrator.py` — 3 concurrency tests rewritten with sync primitives, all 27 pass in <1s`

## Verification

python3 -m pytest tests/test_orchestrator.py -q --durations=10 && python3 -m pytest --tb=short -q
