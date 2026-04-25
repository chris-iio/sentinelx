---
estimated_steps: 5
estimated_files: 4
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T02: Implement lifecycle commands and crash-recovery subprocess proof

Turn the probe/state contract into the supported direct CLI. This task delivers the actual start/status/restart/stop flow, keeps the child process manager lightweight, and proves cheap crash recovery end to end on an ephemeral port.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Child-process launch via `tools/dev_server.py` | Exit non-zero, persist the failure reason, and leave no half-written running state | Bound startup waits so a wedged child does not hang the operator forever | Treat missing PID/log metadata as a failed launch, not as success |
| Health probe against the live Flask app | Report `starting`, `stale`, or `crashed` with the last probe error instead of trusting the PID file alone | Convert probe timeout into explicit unhealthy status and restart guidance | Treat non-JSON or non-200 responses as unhealthy |
| Runtime-state files under `.gsd/runtime/dev-server/**` | Fail closed if state/log directories cannot be created or read | N/A | Reject malformed state JSON and surface it as operator-visible failure metadata |

## Load Profile

- **Shared resources**: one localhost port, one managed child process, and the manager-owned status/log files.
- **Per-operation cost**: one subprocess launch/termination and bounded polling during startup/status checks.
- **10x breakpoint**: leaking child processes or keeping stale PID state that makes repeated restart attempts ambiguous.

## Negative Tests

- **Malformed inputs**: invalid host/port flags, missing status files, and corrupted state JSON.
- **Error paths**: occupied ports, launch failures, crashed child processes, and probe timeouts.
- **Boundary conditions**: free-port startup, stop when nothing is running, stale PID recovery, and repeated restart after a crash.

## Steps

1. Extend `tools/dev_server.py` with `start`, `status`, `restart`, and `stop` subcommands plus a child-serving entrypoint that launches SentinelX through `create_app()` on configurable localhost host/port settings (defaulting to `127.0.0.1:5000`) without introducing new dependencies.
2. Persist lifecycle metadata under `.gsd/runtime/dev-server/**` (PID, port, host, log path, started-at, last probe result, last failure reason, and restart count) and make `status` combine recorded metadata with a live `/api/health` probe.
3. Keep crash recovery explicit rather than supervisory: `status` must detect stale/crashed children and `restart` must reuse the recorded config after cleaning up stale state.
4. Add `tests/test_dev_server_process.py` with subprocess proof that starts the server on a free port, confirms readiness, kills the managed child, observes the failed/stale status, restarts to healthy, and stops cleanly.
5. Extend `tests/test_dev_server.py` as needed for argument validation, status transitions, and malformed-state handling so the pure helpers and subprocess flow stay aligned.

## Must-Haves

- [ ] `tools/dev_server.py` exposes `start`, `status`, `restart`, and `stop` as the only direct lifecycle commands.
- [ ] Lifecycle state lives entirely under `.gsd/runtime/dev-server/**` and remains compatible with the S01/S02 boundary contract.
- [ ] `status` never treats a PID file alone as proof of health; it always reports live-probe truth plus the last known failure metadata.
- [ ] `tests/test_dev_server_process.py` proves crash detection and cheap restart on an ephemeral port.

## Inputs

- ``tools/dev_server.py``
- ``tests/test_dev_server.py``
- ``run.py``
- ``app/__init__.py``
- ``tests/e2e/conftest.py``

## Expected Output

- ``tools/dev_server.py``
- ``tests/test_dev_server.py``
- ``tests/test_dev_server_process.py``

## Verification

`python3 -m pytest -q tests/test_dev_server.py tests/test_dev_server_process.py`
`python3 tools/dev_server.py --help`

## Observability Impact

- Signals added/changed: status transitions (`starting`, `running`, `stale`, `crashed`, `stopped`), last probe result, restart count, timestamps, and log-path metadata.
- How a future agent inspects this: `python3 tools/dev_server.py status --format json` and the `.gsd/runtime/dev-server/**` state/log files.
- Failure state exposed: launch errors, stale PID detection, crashed-child status, and restart attempts are persisted instead of requiring port archaeology.
