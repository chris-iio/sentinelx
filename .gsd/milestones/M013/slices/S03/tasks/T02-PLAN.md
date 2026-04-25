---
estimated_steps: 24
estimated_files: 6
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T02: Adopt the incremental snapshot in helper status routes without changing the public contract

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

## Inputs

- `app/routes/_helpers.py` — current helper-owned status serialization and terminal payload behavior
- `app/routes/api.py` — thin API wrapper that must stay contract-compatible
- `app/routes/enrichment.py` — thin HTML polling wrapper that must stay contract-compatible
- `tests/test_routes.py` — current HTML polling endpoint assertions for `since`, terminal states, and serialization
- `tests/test_api.py` — current API polling assertions for `next_since`, terminal states, and parity
- `app/static/src/ts/types/api.ts` — frontend type contract that should remain stable if the payload shape is preserved

## Expected Output

- `app/routes/_helpers.py` — helper status path switched to orchestrator-owned incremental reads
- `tests/test_routes.py` — updated HTML status-route assertions for delta reads and cached markers
- `tests/test_api.py` — updated API status-route assertions proving parity with the helper path

## Verification

pytest tests/test_routes.py tests/test_api.py -q

## Observability Impact

- Signals added/changed: the live request path now exposes delta-only status reads while keeping the same top-level polling/terminal fields.
- How a future agent inspects this: run the route/API tests and inspect one helper response payload to confirm `next_since`, `terminal_reason`, and `cached_at` alignment.
- Failure state exposed: cache-marker drift, cursor regressions, or collapsed terminal semantics fail in focused route/API assertions before they surface as flaky browser behavior.
