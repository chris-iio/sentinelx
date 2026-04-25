---
estimated_steps: 4
estimated_files: 4
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T01: Add a health probe and dev-loop state contract

Define the readiness and runtime-state contract before wiring the operator surface. This task makes the supported dev loop inspectable by adding a stable health endpoint and a tracked helper layer for the manager's repo-root, state-path, and probe logic.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `bp_api` route registration in `app/routes/api.py` | Fail the route test and stop; do not fall back to probing `/` or HTML responses | N/A | Treat non-JSON or secret-bearing output as a contract failure |
| Repo-root and runtime-path helpers in `tools/dev_server.py` | Fail closed instead of writing outside `.gsd/runtime/dev-server/**` | N/A | Reject unexpected or incomplete state payloads instead of guessing defaults |
| Local health probe helper | Surface connection-refused/timeouts distinctly so later status logic can tell `starting` from `stale`/`crashed` | Keep probe windows short and explicit | Treat non-200 or non-JSON responses as unhealthy |

## Load Profile

- **Shared resources**: localhost port ownership plus `.gsd/runtime/dev-server/**` metadata files.
- **Per-operation cost**: one bounded HTTP probe and small JSON file reads/writes.
- **10x breakpoint**: tight probe loops or repeated status-file rewrites that turn inspection into noisy activity.

## Negative Tests

- **Malformed inputs**: missing or partially written state JSON, invalid ports, and unknown status strings.
- **Error paths**: refused connections, probe timeouts, and non-JSON health responses.
- **Boundary conditions**: default localhost settings, empty runtime directory, and secret-free health output when the app has no configured providers.

## Steps

1. Add `GET /api/health` to `bp_api` with a minimal JSON contract that is safe for repeated local liveness/readiness checks and does not expose provider or session state.
2. Create the initial `tools/dev_server.py` helper layer for repo-root discovery, `.gsd/runtime/dev-server/**` path ownership, status serialization, and health probing without starting/stopping child processes yet.
3. Add route coverage to `tests/test_api.py` and new helper coverage in `tests/test_dev_server.py` so the first task writes tracked proof files for the new contract.
4. Keep the helper output aligned with S01/S02's boundary rules: `.bg-shell/**` stays harness-owned and unsupported, while all new runtime metadata stays under `.gsd/runtime/**`.

## Must-Haves

- [ ] `/api/health` returns 200 JSON with fixed operational metadata only.
- [ ] `tools/dev_server.py` owns repo-root and `.gsd/runtime/dev-server/**` path resolution instead of scattering path logic across Makefile/docs/tests.
- [ ] Probe helpers distinguish healthy, refused, timeout, and malformed-response states without raising uncaught tracebacks.
- [ ] `tests/test_api.py` and `tests/test_dev_server.py` pin the contract before lifecycle commands are added.

## Inputs

- ``app/routes/api.py``
- ``tests/test_api.py``
- ``app/__init__.py``
- ``tools/runtime_state_boundary.py``
- ``.gitignore``

## Expected Output

- ``app/routes/api.py``
- ``tests/test_api.py``
- ``tools/dev_server.py``
- ``tests/test_dev_server.py``

## Verification

`python3 -m pytest -q tests/test_api.py tests/test_dev_server.py`
`python3 tools/dev_server.py --help`

## Observability Impact

- Signals added/changed: a secret-free `/api/health` contract plus manager state/probe helpers for later lifecycle reporting.
- How a future agent inspects this: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py` and the helper/state JSON written under `.gsd/runtime/dev-server/**` in later tasks.
- Failure state exposed: probe outcome categories and malformed-state handling become explicit instead of implicit PID folklore.
