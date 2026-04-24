# S02: Runtime/provider seam shipped fixes

**Goal:** Add bounded runtime/provider diagnostics, capture them in the durable M013 audit workflow, and use that evidence to either ship a narrow cache-hit/dispatch optimization or an explicit keep-decision without weakening existing concurrency, backoff, cache-marker, or adapter-session guarantees.
**Demo:** After this: An analyst can run enrichment through the existing UI with the same concurrency/backoff/cache guarantees and either lower measured runtime overhead or a justified leave-alone decision recorded in the ranked audit.

## Must-Haves

- Orchestrator jobs expose bounded runtime/provider diagnostics sufficient to measure provider mix, cache-hit ratio, retry/rate-limit cost, latency, and error distribution without moving mutable state into shared adapters or widening the analyst-visible status contract by default.
- The audit workflow gains a deterministic runtime/provider capture and refreshes `.gsd/milestones/M013/M013-AUDIT.md` using the S01 ranked-finding vocabulary.
- Any shipped runtime change stays narrow and preserves R014, R015, R018, and R020; if measurements do not justify code churn, the audit records an explicit keep-decision instead of a speculative rewrite.
- Final slice-close proof includes a fresh audit refresh plus `make verify-fast` and `make verify-deep` evidence, satisfying R040.

## Proof Level

- This slice proves: - This slice proves: integration + operational proof for the runtime/provider seam — a local enrichment run can emit durable runtime/provider evidence and either a measured hot-path improvement or a justified keep-decision while preserving verified behavior.
- Real runtime required: no
- Human/UAT required: no

## Integration Closure

- Upstream surfaces consumed: `app/enrichment/orchestrator.py`, `app/enrichment/setup.py`, `app/__init__.py`, `app/routes/_helpers.py`, `tools/optimization_audit.py`, and the existing unit/browser verification lanes.
- New wiring introduced in this slice: orchestrator-owned runtime/provider diagnostics consumed by the audit runner and, only if measurements justify it, a narrow cache-hit/dispatch fast path at the orchestrator boundary.
- What remains before the milestone is truly usable end-to-end: S03 and S04 still need to refresh the shared audit after request/status and frontend/render work, but nothing else should be required to justify the runtime/provider seam.

## Verification

- Runtime signals: per-job provider dispatch counts, cache hits/misses, retry and rate-limit retry counts, latency aggregates, and provider/error tallies recorded on the orchestrator.
- Inspection surfaces: a snapshot-safe orchestrator diagnostics accessor plus runtime/provider capture rows in `tools/optimization_audit.py` and `.gsd/milestones/M013/M013-AUDIT.md`.
- Failure visibility: missing or regressing counts surface in focused orchestrator/audit tests and in the slice-close `make verify-fast` / `make verify-deep` evidence.
- Redaction constraints: keep API keys, raw provider bodies, and unbounded raw IOC payloads out of the diagnostics surface and artifact summaries.

## Tasks

- [x] **T01: Add job-scoped runtime/provider diagnostics to the orchestrator** `est:0.75d`
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
  - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`, `app/enrichment/setup.py`, `app/__init__.py`
  - Verify: pytest tests/test_orchestrator.py -q

- [ ] **T02: Capture runtime/provider evidence in the audit workflow** `est:0.5d`
  Extend the audit workflow so S02 can capture deterministic runtime/provider evidence from the orchestrator and carry it into the durable ranked artifact. Keep the measurement synthetic/local and based only on tracked code paths — no live provider keys, no `.gsd` fixtures, and no dependency on hidden temp-state beyond task-local temporary files.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` measurement harness | Fail the capture loudly and preserve the rest of the artifact generation path | Bound runtime with the existing command timeout path | Surface a readable capture failure summary instead of crashing markdown generation |
| Orchestrator diagnostics from T01 | Fall back to an explicit audit capture failure until the diagnostics contract is fixed | Keep captures local and deterministic; do not block on real providers | Validate expected keys and summarize missing fields as a failed capture |
| Audit rendering/tests | Keep template and baseline modes readable even when the new runtime/provider capture fails | N/A | Escape summary text and keep markdown tables structurally valid |

## Load Profile

- **Shared resources**: local thread pool/orchestrator state during the synthetic capture, temp cache or in-memory fixtures, and markdown artifact generation.
- **Per-operation cost**: one deterministic local enrichment measurement plus updated baseline/template rendering and unit assertions.
- **10x breakpoint**: flaky timing assertions or heavy synthetic workloads; keep the capture shape deterministic and assert on counters/structure rather than brittle absolute timings.

## Negative Tests

- **Malformed inputs**: missing diagnostics keys, empty adapter lists, and capture helpers returning incomplete summaries.
- **Error paths**: capture helper exception, failed output write, and summary text containing markdown table delimiters.
- **Boundary conditions**: all-cache-hit run, mixed success/retry run, and baseline mode with no external `--capture-command` arguments.

## Steps

1. Add a deterministic runtime/provider measurement helper to `tools/optimization_audit.py` that exercises the orchestrator with synthetic adapters/cache state and records provider mix, cache-hit ratio, retry/rate-limit cost, and latency summary fields from T01.
2. Update the baseline/runtime-provider audit text so the S02 row can cite the new capture and clearly distinguish a measured ship target from an explicit keep-decision.
3. Extend `tests/test_optimization_audit.py` to pin the new capture label/summary and keep the artifact format stable.

## Must-Haves

- [ ] The audit runner emits a deterministic runtime/provider capture without real provider credentials or network calls.
- [ ] `.gsd/milestones/M013/M013-AUDIT.md` can carry provider-mix/cache-hit/retry evidence in the same durable vocabulary S01 established.
- [ ] Audit tests pin the new capture so later slices can refresh the artifact without drifting the runtime/provider evidence shape.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`, `docs/optimization-audit.md`
  - Verify: pytest tests/test_optimization_audit.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md

- [ ] **T03: Ship the measured runtime fix or codify the keep-decision and rerun proof** `est:0.75d`
  Use the T02 measurements to decide whether this slice should ship a narrow runtime/provider code change or refresh the audit with an explicit keep-decision. The only acceptable code-path optimization is a cache-hit-heavy dispatch reduction that avoids scheduling needless work before the thread-pool/semaphore path while preserving cached-marker output, retry/backoff behavior, provider concurrency, and adapter-owned session reuse. If the measurements do not show a meaningful win, do not reopen concurrency/session policy; instead refresh the audit so the leave-alone stance is explicit and durable.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| T02 runtime/provider evidence | Default to the audit-only keep-decision path; do not invent an optimization without evidence | Keep proof bounded to the repo verification lanes | Treat incomplete evidence as a blocker for code churn, not as permission to guess |
| Orchestrator hot path in `app/enrichment/orchestrator.py` | Preserve cached markers, retries, and semaphore semantics or revert to audit-only outcome | Existing provider timeout/backoff behavior must stay unchanged | Reject any optimization that depends on raw provider payload shape |
| Full verification lanes (`make verify-fast`, `make verify-deep`) | Do not mark the slice done until both lanes are green after the final audit refresh | Use the existing deterministic mocked-online proof instead of live-provider retries | Treat browser/status regressions as slice blockers because they threaten R008/R040 continuity |

## Load Profile

- **Shared resources**: orchestrator thread pool, shared cache store, provider semaphores, and the full regression/browser verification lanes.
- **Per-operation cost**: one final measured runtime/provider pass, focused unit regressions, and the standard slice-close verification commands.
- **10x breakpoint**: an over-broad optimization that changes global concurrency/session behavior; keep the implementation narrow or stay with the explicit keep-decision.

## Negative Tests

- **Malformed inputs**: mixed cache-hit/miss batches, unsupported IOC/provider pairs, and adapters returning malformed errors.
- **Error paths**: 429 retries after an initial miss, non-429 single-retry behavior, and audit refresh after a no-optimization keep decision.
- **Boundary conditions**: all-cache-hit runs, zero-auth providers mixed with key-required providers, and concurrent status snapshots while work completes.

## Steps

1. Read the T02 capture results and decide explicitly whether the slice will ship a narrow cache-hit/dispatch reduction or preserve the current runtime seam as a measured keep-decision.
2. If the evidence justifies a code change, implement only the measured hot-path reduction in `app/enrichment/orchestrator.py` and extend `tests/test_orchestrator.py` / `tests/test_optimization_audit.py` to pin the new behavior; otherwise update the audit text so the keep-decision is explicit and traceable.
3. Refresh `.gsd/milestones/M013/M013-AUDIT.md`, then run the full slice-close proof so the artifact and verification evidence match the final code path.

## Must-Haves

- [ ] The final state is either a measured runtime/provider code improvement or an explicit audited keep-decision; there is no speculative middle ground.
- [ ] Provider concurrency, 429 backoff, cached-marker correctness, snapshot safety, and adapter-owned session reuse remain preserved.
- [ ] The final audit refresh, `make verify-fast`, and `make verify-deep` all run against the same final code state.
  - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`, `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`, `tests/test_http_safety.py`, `tests/test_base_adapter.py`
  - Verify: pytest tests/test_orchestrator.py tests/test_http_safety.py tests/test_base_adapter.py tests/test_optimization_audit.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md && make verify-fast && make verify-deep

## Files Likely Touched

- app/enrichment/orchestrator.py
- tests/test_orchestrator.py
- app/enrichment/setup.py
- app/__init__.py
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M013/M013-AUDIT.md
- docs/optimization-audit.md
- tests/test_http_safety.py
- tests/test_base_adapter.py
