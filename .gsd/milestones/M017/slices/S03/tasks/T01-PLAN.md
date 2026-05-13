---
estimated_steps: 50
estimated_files: 2
skills_used: []
---

# T01: Lock the incremental status contract with focused regressions

---
estimated_steps: 6
estimated_files: 2
skills_used:
  - tdd
  - test
---

# T01: Lock the incremental status contract with focused regressions

**Slice:** S03 — Best Optimization Implementation
**Milestone:** M017

## Description

Add or tighten focused tests before changing production code so the optimization target is executable: cursor polling must return only the requested tail, preserve `next_since`, align `cached_markers` only to returned results, keep negative/out-of-range compatibility, expose terminal failure states, and prove the Flask route calls `get_incremental_status()` rather than `get_status()` for normal polling.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| In-memory `EnrichmentOrchestrator` job registry | Return existing unknown/evicted/job_failed terminal payloads with 404 only for unknown/evicted | N/A; lookup is in-memory | Coerce/guard response payloads through existing status payload builders |

## Load Profile

- **Shared resources**: `_orchestrators`, per-job `results`, `_cached_markers`, orchestrator lock.
- **Per-operation cost**: expected O(delta results) result serialization plus scalar metadata; test should fail if route falls back to full `get_status()` snapshots.
- **10x breakpoint**: repeated full-list snapshot copying during polling, especially with large retained result lists.

## Negative Tests

- **Malformed inputs**: non-integer `since` should keep Flask default behavior; negative `since` preserves existing Python tail semantics.
- **Error paths**: unknown, evicted, and job_failed status paths continue to expose terminal metadata.
- **Boundary conditions**: `since=0`, no `since`, `since == len(results)`, and `since > len(results)`.

## Steps

1. Review current cursor tests in `tests/test_routes.py` and incremental snapshot tests in `tests/test_orchestrator.py`.
2. Add any missing route assertion that `get_incremental_status(job_id, since=...)` is called and `get_status()` is not called for normal `/enrichment/status/<job_id>` polling.
3. Add or tighten orchestrator tests for tail-only cached marker alignment, out-of-range and negative `since`, and terminal failed/evicted snapshots.
4. Ensure tests use in-memory fixtures only and do not read `.gsd/`, `.planning/`, `.audits/`, or gitignored artifacts.
5. Keep the tests behavior-focused, not implementation-string focused.
6. Run the focused pytest command.

## Must-Haves

- [ ] Route tests fail if normal polling uses `get_status()` instead of `get_incremental_status()`.
- [ ] Orchestrator tests prove returned result/cached-marker snapshots are copies and cannot mutate internal state.
- [ ] Terminal/unknown/evicted behavior remains explicit and compatible.

## Verification

- `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py -k "IncrementalStatusSnapshot or enrichment_status"`
- Confirm no test reads `.gsd/` or other gitignored planning/audit paths.

## Observability Impact

- Signals added/changed: test assertions around `status`, `terminal`, `terminal_reason`, `error`, and `next_since` response fields.
- How a future agent inspects this: run the focused pytest command above.
- Failure state exposed: regression failures identify whether cursor semantics, cached markers, or terminal metadata broke.

## Inputs

- `tests/test_orchestrator.py` — existing orchestrator concurrency, status, diagnostics, and incremental snapshot coverage.
- `tests/test_routes.py` — existing Flask route behavior and cursor polling tests.
- `app/enrichment/orchestrator.py` — production contract under test.
- `app/routes/_helpers.py` — route helper contract under test.

## Expected Output

- `tests/test_orchestrator.py` — focused incremental status contract coverage updated as needed.
- `tests/test_routes.py` — route polling regression coverage updated as needed.

## Inputs

- `tests/test_orchestrator.py`
- `tests/test_routes.py`
- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`

## Expected Output

- `tests/test_orchestrator.py`
- `tests/test_routes.py`

## Verification

python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py -k "IncrementalStatusSnapshot or enrichment_status"

## Observability Impact

Adds focused failure messages around cursor, terminal, and cached-marker signals so future agents can localize polling regressions quickly.
