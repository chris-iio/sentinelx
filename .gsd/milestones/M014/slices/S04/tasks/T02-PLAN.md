---
estimated_steps: 5
estimated_files: 6
skills_used:
  - review
  - test
  - verify-before-complete
---

# T02: Retire the shared health-contract drift with a minimal seam-local refactor

**Slice:** S04 — Verification, review, and refactor closure
**Milestone:** M014

## Description

Use the review artifact from T01 plus `verify-before-complete` before making any completion claim. Implement the smallest code change that removes the real drift found during review: introduce `app/health_contract.py` as the single source for the local `HEALTH_PATH` / `HEALTH_PAYLOAD`, update both `app/routes/api.py` and `tools/dev_server.py` to consume it, and keep the rest of the workflow seam unchanged unless T01 documented an equally small helper extraction in the same files. Do not widen repair scope, change `.planning/**` handling, or add another operator surface.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Shared health-contract module | Fail the focused tests and stop; do not fall back to duplicated literals | N/A | Treat missing/changed contract fields as a regression that must be fixed in code, not papered over in docs |
| `tools/dev_server.py` probe/status flow | Preserve current non-zero exit behavior and recorded failure reasons | Keep existing bounded startup/probe windows | Keep non-200, non-JSON, or secret-bearing responses classified as `malformed` |
| `/api/health` route in `app/routes/api.py` | Keep the route importable and 200/JSON-only | N/A | Reject any change that exposes provider/config state or stops matching the shared contract |

## Load Profile

- **Shared resources**: one localhost probe endpoint plus `.gsd/runtime/dev-server/**` status files.
- **Per-operation cost**: one tiny shared import and the existing bounded HTTP probe.
- **10x breakpoint**: producer/consumer drift that causes false unhealthy states or leaks new keys into health/status output.

## Negative Tests

- **Malformed inputs**: corrupted status JSON, invalid host/port values, and a health response with extra secret-bearing keys.
- **Error paths**: refused/timeout probes and mismatched health payloads.
- **Boundary conditions**: healthy exact-match payload, default localhost settings, and crash/stale state synthesis remaining unchanged after the refactor.

## Steps

1. Create `app/health_contract.py` with the shared local `HEALTH_PATH` and exact secret-free `HEALTH_PAYLOAD` expected by the supported dev loop.
2. Update `app/routes/api.py` and `tools/dev_server.py` to import the shared contract instead of maintaining duplicated literals, keeping CLI semantics, fail-closed probe behavior, and local-only host validation unchanged.
3. Apply only the additional seam-local helper extraction(s) explicitly justified in `S04-REVIEW.md`; if none were justified, keep the change set limited to the shared contract and related test adjustments.
4. Update `tests/test_api.py` and `tests/test_dev_server.py` so the shared contract, malformed-response handling, and existing status semantics remain pinned after the refactor.
5. Append the landed change and any intentionally deferred cleanup to `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`.

## Must-Haves

- [ ] `app/health_contract.py` becomes the single source of truth for the supported local health contract.
- [ ] `app/routes/api.py` and `tools/dev_server.py` stay behaviorally identical at the CLI/API boundary except for the removed duplication.
- [ ] Focused tests prove that extra keys or payload drift still surface as malformed/unhealthy rather than silently succeeding.
- [ ] The review artifact records exactly what changed and what was intentionally left alone.

## Verification

- `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
- `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_repair.py`

## Observability Impact

- Signals added/changed: the health producer and consumer share one exact contract instead of drifting literals.
- How a future agent inspects this: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` and `python3 tools/dev_server.py status --format json`.
- Failure state exposed: health payload drift, malformed responses, and stale/crashed dev-server states remain explicit after the refactor.

## Inputs

- `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` — seam review decisions and invariants from T01.
- `app/routes/api.py` — current `/api/health` producer.
- `tools/dev_server.py` — current health consumer and lifecycle manager.
- `tests/test_api.py` — API proof surface for the health contract.
- `tests/test_dev_server.py` — helper/status proof surface for the dev-server contract.

## Expected Output

- `app/health_contract.py` — shared health contract module for the supported local dev loop.
- `app/routes/api.py` — updated to import the shared contract.
- `tools/dev_server.py` — updated to consume the shared contract without changing lifecycle semantics.
- `tests/test_api.py` — updated/pinned shared health producer behavior.
- `tests/test_dev_server.py` — updated/pinned shared health consumer and malformed-response behavior.
- `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` — amended with landed change notes and deferred cleanup rationale.
