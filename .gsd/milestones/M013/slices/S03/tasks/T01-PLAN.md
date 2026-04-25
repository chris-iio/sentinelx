---
estimated_steps: 24
estimated_files: 4
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T01: Add a lock-safe incremental status snapshot API on the orchestrator

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

## Inputs

- `app/enrichment/orchestrator.py` — current full-snapshot `get_status()` implementation, `_cached_markers` lock discipline, and terminal tombstones
- `tests/test_orchestrator.py` — existing snapshot, retry/backoff, and cached-marker guardrail coverage
- `app/routes/_helpers.py` — current helper-side `since` slicing that this task will replace in T02
- `tools/optimization_audit.py` — current request/status benchmark text that assumes whole-list snapshots

## Expected Output

- `app/enrichment/orchestrator.py` — additive incremental snapshot API with lock-safe tail/marker reads
- `tests/test_orchestrator.py` — focused coverage proving tail reads, marker alignment, and preserved full-snapshot semantics

## Verification

pytest tests/test_orchestrator.py -q

## Observability Impact

- Signals added/changed: an inspectable orchestrator-level delta snapshot path that makes tail size, `next_since`, and terminal state explicit without route-side reconstruction.
- How a future agent inspects this: call the focused orchestrator tests and inspect the incremental snapshot accessor used by the status helper.
- Failure state exposed: route regressions localize quickly to tail-size, marker-alignment, or tombstone-snapshot failures instead of ambiguous polling behavior.
