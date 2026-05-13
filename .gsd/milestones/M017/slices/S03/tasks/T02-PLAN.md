---
estimated_steps: 52
estimated_files: 2
skills_used: []
---

# T02: Ship tail-only enrichment status snapshots

---
estimated_steps: 7
estimated_files: 2
skills_used:
  - tdd
  - best-practices
---

# T02: Ship tail-only enrichment status snapshots

**Slice:** S03 — Best Optimization Implementation
**Milestone:** M017

## Description

Implement or harden the actual S03 optimization: normal status polling should take a lock-safe scalar snapshot and copy only `results[since:]`, carrying only cached markers needed by that returned tail, while preserving all additive terminal/status fields and the existing cursor contract.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Orchestrator job state | Return `None` for unknown jobs or tombstone payload for evicted/failed jobs, matching current route behavior | N/A; in-memory operation | Defensive snapshot helpers should tolerate missing/non-list `results` and missing diagnostics |
| Cache-marker map | Omit unavailable marker rather than failing the status request | N/A | Include only string marker values already present for returned `EnrichmentResult` rows |

## Load Profile

- **Shared resources**: orchestrator `_lock`, per-job result list, `_cached_markers`, Flask route registry lock.
- **Per-operation cost**: O(delta results) result copy and marker lookup after the scalar status snapshot; no full result-list copy in normal route polling.
- **10x breakpoint**: JSON serialization of returned delta and client polling frequency, not internal snapshot copying of all retained results.

## Negative Tests

- **Malformed inputs**: preserve existing `request.args.get("since", 0, type=int)` behavior and negative `since` compatibility.
- **Error paths**: unknown job, helper-level evicted job, orchestrator-level evicted job, and job_failed all preserve terminal metadata and appropriate status code.
- **Boundary conditions**: no results, `since=0`, exact length, beyond length, mixed result/error rows, and cached-marker tails.

## Steps

1. In `app/enrichment/orchestrator.py`, ensure `get_incremental_status(job_id, since=0)` exists and returns scalar fields, a copied `results[since:]` tail, `next_since`, and tail-aligned `cached_markers` under the orchestrator lock.
2. Keep `get_status()` intact for diagnostics/history save call sites that intentionally need full snapshots.
3. In `app/routes/_helpers.py`, ensure `_get_enrichment_status()` calls `orchestrator.get_incremental_status(job_id, since=since)` for normal route polling and passes returned `cached_markers` into `_serialize_result()`.
4. Preserve `_build_status_payload()` response fields: `total`, `done`, `complete`, `results`, `next_since`, `status`, `terminal`, `terminal_reason`, and `error`.
5. Preserve existing 404 behavior only for terminal unknown/evicted states; job_failed remains a terminal payload without hiding the failure.
6. Do not change provider fan-out, retry/backoff, cache-store, history-save, CSP, CSRF, SSRF, or DOM-safety behavior.
7. Run focused tests from T01, then the broader backend route/orchestrator tests.

## Must-Haves

- [ ] Normal polling path copies only delta results and required cached markers.
- [ ] Full `get_status()` remains available and unchanged for call sites that need full snapshots.
- [ ] All terminal/status response fields and cursor semantics remain backward-compatible.

## Verification

- `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py -k "IncrementalStatusSnapshot or enrichment_status"`
- `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py`

## Observability Impact

- Signals added/changed: no new runtime fields; preserves existing status/terminal/error/next_since diagnostics while reducing internal poll cost.
- How a future agent inspects this: `/enrichment/status/<job_id>?since=N`, `get_orchestration_diagnostics_snapshot(job_id)`, and focused pytest failures.
- Failure state exposed: unknown, evicted, and job_failed remain machine-readable terminal states.

## Inputs

- `app/enrichment/orchestrator.py` — orchestrator status snapshot implementation.
- `app/routes/_helpers.py` — Flask status route helper and result serialization.
- `tests/test_orchestrator.py` — expected contract from T01.
- `tests/test_routes.py` — route-level expected contract from T01.

## Expected Output

- `app/enrichment/orchestrator.py` — tail-only incremental snapshot implementation hardened as needed.
- `app/routes/_helpers.py` — route polling path wired to incremental snapshots as needed.

## Inputs

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `tests/test_orchestrator.py`
- `tests/test_routes.py`

## Expected Output

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`

## Verification

python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py

## Observability Impact

Preserves existing status/terminal/error/next_since fields while making status polling cheaper and easier to reason about under load.
