# S03: Request-flow and persistence seam shipped fixes

**Goal:** Ship the request/status hot-path fix by moving `/enrichment/status` and `/api/status` to an orchestrator-owned incremental snapshot API, keep helper-owned terminal/diagnostic behavior truthful, and refresh the audit so WAL-backed cache/history persistence remains an evidence-backed keep-decision unless new contention proof appears.
**Demo:** After this: Status polling, history reload, cache continuity, and helper diagnostics still behave the same for users while any justified request-path or SQLite hot-path improvement is shipped and the rest is explicitly ranked as keep, later, or do next.

## Must-Haves

- ## Demo
- An analyst can continue polling live enrichment through the existing UI/API contract while the backend reads only the requested delta slice, preserves `next_since` / terminal semantics / `cached_at` markers, and refreshes the ranked audit with the shipped request-path change plus an explicit persistence keep-decision.
- ## Must-Haves
- Add an orchestrator-owned incremental status read API that snapshots scalar status fields, only the requested `results[since:]` tail, and the cached-marker data needed to serialize that tail, without weakening the existing full-snapshot `get_status()` contract used by history persistence and current tests.
- Move `app/routes/_helpers.py::_get_enrichment_status()` and the `/api/status/<job_id>` / `/enrichment/status/<job_id>` consumers onto that incremental API while preserving payload shape, `next_since` continuity, `unknown` vs `evicted` vs `job_failed` semantics, and current behavior for negative `since` values unless execution adds an explicit tested normalization decision.
- Refresh `tools/optimization_audit.py` and `.gsd/milestones/M013/M013-AUDIT.md` so the request/status row reflects the shipped cursor-native path, and the WAL-backed cache/history seam remains an explicit measured keep-decision unless fresh evidence justifies reopening store code.
- Slice-close proof must produce fresh evidence for `tests/test_orchestrator.py`, `tests/test_routes.py`, `tests/test_api.py`, `tests/test_optimization_audit.py`, `tests/test_cache_store.py`, `tests/test_history_store.py`, `make verify-fast`, and `make verify-deep`, satisfying R040.
- ## Threat Surface
- **Abuse**: untrusted `job_id` and `since` query parameters can probe terminal states or request repeated/tail slices; the incremental path must not collapse `unknown` / `evicted` semantics, leak extra historical rows, or introduce a route-level race by reading partial orchestrator state outside the lock.
- **Data exposure**: no raw analyst input, full result payload dumps, provider secrets, or helper-owned history diagnostics should widen; the new API may expose only the same result fields already returned today, including bounded `cached_at` timestamps for rows already visible to the analyst.
- **Input trust**: `request.args["since"]` and route `job_id` values remain fully untrusted; bounds handling, cached-marker selection, and status serialization must stay inside lock-protected orchestrator/helper code rather than in frontend assumptions.
- ## Requirement Impact
- **Requirements touched**: R008, R010, R018, R019 (owned) plus R022 and R040 (supporting); preserve R009 if helper diagnostics/state ownership shifts.
- **Re-verify**: live polling continuity, progress updates, result/cached-marker serialization, `/api/status` parity, terminal 404 handling, audit wording, WAL keep-decision evidence, and the final `make verify-fast` / `make verify-deep` lanes.
- **Decisions revisited**: D057, D058, and D059 remain binding; S03 should add an additive request-path API rather than rewriting the full-snapshot contract or reopening WAL persistence without stronger evidence.
- ## Verification
- `pytest tests/test_orchestrator.py tests/test_routes.py tests/test_api.py -q`
- `pytest tests/test_optimization_audit.py tests/test_cache_store.py tests/test_history_store.py -q`
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`
- `make verify-fast`
- `make verify-deep`

## Proof Level

- This slice proves: integration + operational proof for the request/status and persistence seam — the shipped backend path must prove cursor-native polling, unchanged analyst-visible contract semantics, and a refreshed audit/verification record on the same final code state.

## Integration Closure

- Upstream surfaces consumed: `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`, `app/routes/enrichment.py`, `app/routes/api.py`, `app/static/src/ts/types/api.ts`, `tools/optimization_audit.py`, and the focused route/orchestrator/store/audit verification suites.
- New wiring introduced in this slice: an orchestrator-owned incremental status snapshot consumed by the shared helper status endpoint, with the audit runner updated to report the shipped request/status fix and persistence keep-decision using the S01/S02 evidence vocabulary.
- What remains before the milestone is truly usable end-to-end: S04 still needs to ship the frontend/render seam and rerun the final audit, but S03 should leave no unresolved backend request/status ambiguity for that slice.

## Verification

- Runtime signals: incremental snapshot shape (`done`, `total`, `complete`, `terminal`, `terminal_reason`, `next_since`) plus tail-only cached-marker serialization and the refreshed request/status + persistence rows in `.gsd/milestones/M013/M013-AUDIT.md`.
- Inspection surfaces: `EnrichmentOrchestrator` status accessors, `_get_enrichment_status()` route responses, focused pytest suites for orchestrator/routes/API/store/audit coverage, and the regenerated audit artifact.
- Failure visibility: contract drift shows up as route/API assertion failures, stale audit wording, missing `cached_at` on delta results, or `make verify-deep` regressions in the mocked-online poller seam.
- Redaction constraints: keep helper/settings diagnostics aggregate-only and keep raw analyst input, stored result bodies beyond the existing contract, and provider secrets out of any new snapshot or audit surface.

## Tasks

- [x] **T01: Add a lock-safe incremental status snapshot API on the orchestrator** `est:0.75d`
  Design and implement the additive hot-path API on `EnrichmentOrchestrator` instead of weakening `get_status()`. The new method should snapshot, under one lock, the scalar job fields needed by polling plus only the requested result tail and the cached-marker data needed to serialize that tail. Keep `get_status()` as the full-snapshot contract for history persistence and existing callers, and preserve current negative-`since` behavior unless execution intentionally normalizes it with explicit test coverage.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/enrichment/orchestrator.py` job state and `_lock` | Return a coherent snapshot or `None`; never expose partially-mutated job state or live list references | N/A | Coerce missing/terminal state to the same safe defaults used by `get_status()` tombstones |
| `_cached_markers` bookkeeping | Keep marker reads under the same lock as the results slice so `cached_at` stays aligned with the returned tail | N/A | Omit only the missing marker for that row; do not fail the whole status read |
| Full-snapshot callers (`_run_enrichment_and_save()`, existing tests) | Leave `get_status()` semantics untouched and additive | N/A | Reject any design that requires history persistence to reconstruct state from deltas |

## Load Profile

- **Shared resources**: orchestrator `_jobs`, `_terminal_jobs`, `_cached_markers`, and the per-job lock.
- **Per-operation cost**: one lock acquisition plus O(new-results) result/marker copying for the incremental API; `get_status()` remains O(total-results) for full-history callers.
- **10x breakpoint**: copying whole result lists or whole cached-marker dicts on every poll; the task fails if the new API still scales with total retained rows instead of requested delta size.

## Negative Tests

- **Malformed inputs**: unknown job ids, evicted tombstones, negative `since`, and `since` values beyond the retained results length.
- **Error paths**: terminal failed jobs, empty result tails, and missing cached-marker entries for non-cached rows.
- **Boundary conditions**: `since=0`, `since=len(results)`, one cached row in the returned tail, and repeated reads proving returned delta lists cannot mutate internal state.

## Steps

1. Add a dedicated incremental status accessor in `app/enrichment/orchestrator.py` that snapshots scalar fields, the requested tail slice, relevant cached markers, and the correct `next_since` under one lock.
2. Keep `get_status()` and `_status_snapshot()` as the full-snapshot path used by history persistence and existing tests; do not widen this task into route or audit changes yet.
3. Extend `tests/test_orchestrator.py` to prove tail-only reads, snapshot safety, cached-marker alignment, terminal tombstone behavior, and the preserved full-snapshot contract.

## Must-Haves

- [ ] `get_status()` remains a full-list snapshot API with existing mutation-safety semantics.
- [ ] A new additive API returns only the requested tail plus marker data needed for that tail.
- [ ] The incremental API computes `next_since` from the underlying retained length without requiring helper-side recomputation.
- [ ] Tests pin both the new tail path and the preserved full-snapshot/history contract.
  - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`, `app/routes/_helpers.py`, `tools/optimization_audit.py`
  - Verify: pytest tests/test_orchestrator.py -q

- [ ] **T02: Adopt the incremental snapshot in helper status routes without changing the public contract** `est:0.75d`
  Move the hot request path to the new orchestrator accessor while keeping the analyst-visible payload contract stable for both HTML and API pollers. This task owns `_get_enrichment_status()` plus the route/API assertions that prove `results`, `next_since`, `terminal_reason`, and `cached_at` still behave the same from the frontend’s perspective. Preserve helper-owned terminal tombstones and do not widen history-save diagnostics or settings output.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/routes/_helpers.py` terminal/registry state | Keep `unknown`, helper-level `evicted`, and orchestrator `job_failed` payloads distinct and truthful | N/A | Fall back to the existing terminal payload shape rather than a partial 200 response |
| Incremental orchestrator API from T01 | Revert to test failure rather than reintroducing helper-side full snapshot copies | N/A | Treat missing fields as a contract break; do not synthesize frontend-only defaults beyond current behavior |
| API/frontend contract surfaces (`tests/test_routes.py`, `tests/test_api.py`, `app/static/src/ts/types/api.ts`) | Preserve field names and cursor semantics so live polling, export/copy/detail-link flows, and browser proof remain unchanged | N/A | If the contract must change, stop and replan instead of silently drifting types or tests |

## Load Profile

- **Shared resources**: helper orchestrator registry, module-level terminal tombstones, Flask request args, and mocked-online polling consumers.
- **Per-operation cost**: one helper call into the incremental orchestrator API plus serialization of only the returned delta rows.
- **10x breakpoint**: re-copying full results or full marker maps in the helper, or letting malformed `since` handling cause repeated large tail responses.

## Negative Tests

- **Malformed inputs**: unknown job ids, evicted jobs, negative `since`, and `since` values beyond the total result count.
- **Error paths**: terminal 404 payloads, result rows with and without `cached_at`, and empty delta responses that still preserve `next_since`.
- **Boundary conditions**: no `since` param, `since=0`, `since=len(results)`, and API/HTML parity for the same mocked job state.

## Steps

1. Replace helper-side `get_status()` + `cached_markers` full copies with the T01 incremental accessor in `app/routes/_helpers.py` while leaving `_run_enrichment_and_save()` on the full-snapshot path.
2. Keep `app/routes/enrichment.py` and `app/routes/api.py` thin wrappers, and update route/API tests to prove delta slicing, cached-marker serialization, and terminal semantics still match the existing contract.
3. Confirm `app/static/src/ts/types/api.ts` still matches the returned fields; only change it if execution proves the current type no longer describes reality.

## Must-Haves

- [ ] `_get_enrichment_status()` no longer reconstructs tail slices from a full status snapshot.
- [ ] `/enrichment/status/<job_id>` and `/api/status/<job_id>` preserve `results`, `next_since`, `complete`, `status`, `terminal`, `terminal_reason`, and `error` semantics.
- [ ] Cached delta rows still surface `cached_at` when the backing result came from cache.
- [ ] Helper-owned history-save diagnostics and settings surfaces stay bounded and unchanged unless execution explicitly widens them with tests.
  - Files: `app/routes/_helpers.py`, `tests/test_routes.py`, `tests/test_api.py`, `app/routes/api.py`, `app/routes/enrichment.py`, `app/static/src/ts/types/api.ts`
  - Verify: pytest tests/test_routes.py tests/test_api.py -q

- [ ] **T03: Refresh audit evidence and persistence keep-decisions on the final code path** `est:0.75d`
  Update the durable optimization artifact so S03 records the shipped request/status fix and keeps WAL-backed cache/history persistence on explicit evidence-based footing unless new contention proof appears during execution. This task should prefer audit/test refresh over speculative store rewrites: only modify `app/cache/store.py` or `app/enrichment/history_store.py` if a focused measurement or failing test proves a real persistence problem.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` baseline runner | Fail loudly and keep the artifact generation path readable; stale request/status wording is a slice blocker | Bound captures to the existing deterministic internal benchmarks and verification lanes | Render an explicit failed capture summary rather than silently dropping the seam |
| WAL-backed stores and their focused tests | Preserve the existing keep-decision if no new evidence appears; do not churn storage code to satisfy the slice title | Keep persistence proof local and deterministic; do not wait on external services | Treat malformed metrics or unclear contention data as insufficient evidence for store rewrites |
| Final verification lanes (`make verify-fast`, `make verify-deep`) | Do not mark the slice done until the audit refresh and both lanes pass on the same final state | Use the existing deterministic mocked-online browser proof instead of adding live-provider dependencies | Any route/poller/browser regression is a blocker because it threatens R008/R040 continuity |

## Load Profile

- **Shared resources**: audit artifact generation, temp SQLite WAL stores used by the internal capture, and the repo verification lanes.
- **Per-operation cost**: one audit refresh, focused pytest suites for audit/store continuity, plus the standard fast/deep end-to-end proof commands.
- **10x breakpoint**: reopening persistence implementation without actual lock/contention evidence, or letting the audit artifact drift from the verified code state.

## Negative Tests

- **Malformed inputs**: missing capture rows, malformed benchmark summaries, or audit text that still claims the request/status seam is unshipped.
- **Error paths**: focused cache/history store tests failing under the refreshed audit stance, or audit regeneration failing after the request-path code lands.
- **Boundary conditions**: persistence seam remains unchanged, request/status seam ships, and the final artifact still names WAL persistence as a measured keep-decision rather than a silent omission.

## Steps

1. Update `tools/optimization_audit.py` and `tests/test_optimization_audit.py` so the request/status row reflects the shipped delta path and the persistence row still cites current temp-WAL evidence unless new data justifies reopening it.
2. Run or strengthen focused `tests/test_cache_store.py` and `tests/test_history_store.py` only as needed to keep the persistence keep-decision evidence explicit and current without speculative store churn.
3. Regenerate `.gsd/milestones/M013/M013-AUDIT.md`, then run the focused pytest lanes plus `make verify-fast` and `make verify-deep` so the durable artifact matches the final repository state.

## Must-Haves

- [ ] The audit artifact no longer describes `/enrichment/status` as an unshipped do-now idea; it records the actual shipped request/status fix and its continuity notes.
- [ ] WAL-backed cache/history persistence remains an explicit measured keep-decision unless execution uncovers stronger contradictory evidence.
- [ ] The final audit refresh, focused pytest lanes, `make verify-fast`, and `make verify-deep` all run against the same final state.
- [ ] No store rewrite is shipped without a concrete measurement or failing-test reason documented in code/tests and the audit.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `tests/test_cache_store.py`, `tests/test_history_store.py`, `.gsd/milestones/M013/M013-AUDIT.md`, `app/cache/store.py`, `app/enrichment/history_store.py`
  - Verify: pytest tests/test_optimization_audit.py tests/test_cache_store.py tests/test_history_store.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md && make verify-fast && make verify-deep

## Files Likely Touched

- app/enrichment/orchestrator.py
- tests/test_orchestrator.py
- app/routes/_helpers.py
- tools/optimization_audit.py
- tests/test_routes.py
- tests/test_api.py
- app/routes/api.py
- app/routes/enrichment.py
- app/static/src/ts/types/api.ts
- tests/test_optimization_audit.py
- tests/test_cache_store.py
- tests/test_history_store.py
- .gsd/milestones/M013/M013-AUDIT.md
- app/cache/store.py
- app/enrichment/history_store.py
