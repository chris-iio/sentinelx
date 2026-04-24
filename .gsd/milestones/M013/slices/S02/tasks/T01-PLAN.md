---
estimated_steps: 3
estimated_files: 4
skills_used:
  - observability
  - verify-before-complete
---

# T01: Add job-scoped runtime/provider diagnostics to the orchestrator

**Slice:** S02 — Runtime/provider seam shipped fixes
**Milestone:** M013

## Description

Implement bounded, thread-safe diagnostics on `EnrichmentOrchestrator` so each job can report provider dispatch counts, cache hits/misses, retries, rate-limit retries, latency aggregates, and per-provider error tallies without moving mutable state into shared adapter instances or widening the helper/status contract. Keep diagnostics owned by the orchestrator/job and safe to snapshot alongside existing `results` semantics.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/enrichment/orchestrator.py` concurrent job state | Keep updates under the existing lock and leave `results` / `done` semantics unchanged | N/A | Return default-zero diagnostics rather than partial structures |
| Shared adapter instances from `app/enrichment/setup.py` / `app/__init__.py` | Never store mutable counters on adapters; keep diagnostics job-local | N/A | Ignore missing adapter names and fall back to a bounded `unknown` bucket |
| Existing retry/backoff/cache paths | Preserve current retry counts, semaphore release timing, and cached-marker behavior | Continue the current backoff flow; diagnostics only observe it | Count failures without letting the metrics path raise |

## Load Profile

- **Shared resources**: orchestrator `_jobs` state, `_lock`, per-provider semaphores, and the shared cache store.
- **Per-operation cost**: O(1) counter/timing updates per dispatch/attempt; no extra provider or network calls.
- **10x breakpoint**: lock contention or oversized status snapshots if diagnostics become per-result or unbounded, so keep them aggregate and bounded per job.

## Negative Tests

- **Malformed inputs**: adapters with blank/missing `name`, unsupported IOCs, and cache records missing optional fields.
- **Error paths**: non-429 failure, repeated 429 backoff, job-level exception, and all-cache-hit runs.
- **Boundary conditions**: zero dispatch pairs, concurrent cache hits, max retry path, and snapshot reads while workers are still appending results.

## Steps

1. Add a private bounded diagnostics structure in `app/enrichment/orchestrator.py` and update `enrich_all()`, `_do_lookup()`, and `_single_attempt()` so dispatch, cache, retry, latency, and error aggregates are recorded per job without changing provider concurrency behavior.
2. Expose the diagnostics through a snapshot-safe accessor or status field that later audit code can read without copying raw provider payloads or mutating live job state.
3. Extend `tests/test_orchestrator.py` with targeted unit coverage for cache-hit accounting, retry/rate-limit counters, per-provider latency aggregation, and snapshot stability under concurrent updates.

## Must-Haves

- [ ] Job-scoped diagnostics exist for dispatch counts, cache hits/misses, retries, rate-limit retries, latency totals/max, and per-provider error counts.
- [ ] Diagnostics stay owned by `EnrichmentOrchestrator`; adapters and the app-cached registry remain stateless with respect to metrics.
- [ ] Existing semaphore/backoff/cache behavior stays unchanged except for additive measurement.
- [ ] Snapshot access returns stable copies suitable for later audit capture.

## Verification

- `pytest tests/test_orchestrator.py -q`

## Observability Impact

- Signals added/changed: job-scoped runtime/provider diagnostics for dispatch, cache, retry, latency, and provider/error aggregates.
- How a future agent inspects this: focused orchestrator unit tests and the snapshot-safe diagnostics accessor used by the audit runner.
- Failure state exposed: missing cache-hit accounting, retry inflation, or provider hot spots become explicit counter mismatches instead of hidden runtime behavior.

## Inputs

- `app/enrichment/orchestrator.py` — current dispatch, retry/backoff, cache, and snapshot implementation
- `tests/test_orchestrator.py` — existing guardrail coverage for concurrency, backoff, cache markers, and snapshots
- `app/enrichment/setup.py` — confirms adapters are long-lived shared registry instances
- `app/__init__.py` — confirms registry and stores are app-cached singletons

## Expected Output

- `app/enrichment/orchestrator.py` — additive job-scoped diagnostics surface
- `tests/test_orchestrator.py` — focused diagnostics coverage proving additive behavior
