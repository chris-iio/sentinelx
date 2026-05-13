---
estimated_steps: 53
estimated_files: 6
skills_used: []
---

# T04: Run integrated regression proof for analyst continuity

---
estimated_steps: 4
estimated_files: 0
skills_used:
  - verify-before-complete
  - test
---

# T04: Run integrated regression proof for analyst continuity

**Slice:** S03 — Best Optimization Implementation
**Milestone:** M017

## Description

Close the slice with fresh, current verification evidence. Because the optimized path touches live enrichment/status polling, run focused tests, `make verify-fast`, `make verify-deep`, and audit regeneration/structure checks before marking the slice complete.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Local verification commands | Capture failing command, exit code, and first actionable failure; do not claim completion | Re-run only if timeout cause is environmental and documented | Treat malformed test/audit output as failure until reproduced |
| Mocked-online browser lane | Preserve failure evidence for S04/S05 rather than weakening tests | Do not skip without documenting why the environment cannot run it | N/A |

## Load Profile

- **Shared resources**: local test environment, browser/e2e fixtures, audit benchmark fixtures.
- **Per-operation cost**: full fast verification lane plus deep mocked-online proof.
- **10x breakpoint**: CI/runtime duration, not production code.

## Negative Tests

- **Malformed inputs**: covered by focused route/orchestrator/audit tests from prior tasks.
- **Error paths**: verify-deep and backend tests must preserve failed/unknown/evicted status behavior and analyst-visible continuity.
- **Boundary conditions**: no-since, exact-length, beyond-length, negative-since cursor polling.

## Steps

1. Run focused backend and audit tests to catch local failures quickly.
2. Run `make verify-fast` for repo-wide fast backend/frontend/build proof.
3. Run `make verify-deep` because the slice touched enrichment polling/status flow.
4. Record exact commands, exit codes, and any caveats in the task/slice completion evidence; do not mark complete if either required lane fails.

## Must-Haves

- [ ] Focused route/orchestrator/audit tests pass.
- [ ] `make verify-fast` passes.
- [ ] `make verify-deep` passes or a concrete blocker is filed before completion is refused.
- [ ] Generated audit artifact remains structurally valid after all code changes.

## Verification

- `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py tests/test_optimization_audit.py`
- `make verify-fast`
- `make verify-deep`
- `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md`

## Observability Impact

- Signals added/changed: no production signals; produces fresh command evidence for completion.
- How a future agent inspects this: task summary command table and regenerated audit artifact.
- Failure state exposed: failed command, exit code, and focused failing test name.

## Inputs

- `app/enrichment/orchestrator.py` — optimized runtime seam.
- `app/routes/_helpers.py` — optimized request/status seam.
- `tests/test_orchestrator.py` — focused runtime regression coverage.
- `tests/test_routes.py` — route/status regression coverage.
- `tests/test_optimization_audit.py` — audit runner regression coverage.
- `.gsd/milestones/M017/M017-AUDIT.md` — generated proof artifact to refresh/check.
- `Makefile` — repo-native verification command surface.

## Expected Output

## Inputs

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `tests/test_orchestrator.py`
- `tests/test_routes.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M017/M017-AUDIT.md`
- `Makefile`

## Expected Output

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `tests/test_orchestrator.py`
- `tests/test_routes.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M017/M017-AUDIT.md`

## Verification

python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py tests/test_optimization_audit.py && make verify-fast && make verify-deep && python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md

## Observability Impact

Produces fresh verification evidence only; no production observability changes.
