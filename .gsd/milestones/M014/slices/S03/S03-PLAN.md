# S03: Supported local dev process loop

**Goal:** Ship the repo-native local dev loop that starts, inspects, stops, and cheaply restarts SentinelX while keeping all manager state on the transient side of the runtime boundary.
**Demo:** After this: SentinelX has one supported local dev-process path, and a crashed local server can be detected and restarted through the supported workflow instead of manual archaeology.

## Must-Haves

- `tools/dev_server.py` plus repo-native `make dev-server-start`, `make dev-server-status`, `make dev-server-restart`, and `make dev-server-stop` become the only supported local server lifecycle surface; all lifecycle metadata, logs, and PID/state files stay under `.gsd/runtime/dev-server/**`.
- `GET /api/health` provides a stable secret-free readiness probe, and `tests/test_api.py`, `tests/test_dev_server.py`, and `tests/test_dev_server_process.py` prove the probe, state helpers, start/status/stop flow, crashed-child detection, and restart recovery on an ephemeral port.
- `README.md` and `docs/runtime-state-boundary.md` document the supported operator loop, explicitly keep `.bg-shell/**` out of scope, and preserve the S01/S02 durable-vs-transient boundary contract.
- **Threat surface:** keep the managed server bound to localhost by default, treat CLI arguments and persisted runtime-state files as untrusted, never expose provider/config state from `/api/health` or CLI status output, and only stop/restart the manager-owned child process recorded in `.gsd/runtime/dev-server/**`.
- **Requirement impact:** advances `R064` directly and supports `R065`; re-verify the health-route contract, subprocess crash/restart behavior, `make verify-runtime-boundary`, and `make verify-fast`; keep `D063`, `D065`, and `D069` aligned.

## Proof Level

- This slice proves: contract + integration + operational.
yes — subprocess tests must launch the app on an ephemeral localhost port and observe crash/restart transitions.
no.

## Integration Closure

- Upstream surfaces consumed: `create_app()` in `app/__init__.py`, `bp_api` in `app/routes/api.py`, the runtime-boundary policy in `tools/runtime_state_boundary.py`/`.gitignore`, and the existing `Makefile` verification lanes.
- New wiring introduced in this slice: `tools/dev_server.py`, `.gsd/runtime/dev-server/**` lifecycle state ownership, the `/api/health` probe, and repo-native `dev-server-*` Make targets.
- What remains before the milestone is truly usable end-to-end: S04 must re-prove the combined repair + dev-loop workflow and finish the planned review/refactor closure.

## Verification

- Verification commands: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`, `make verify-runtime-boundary`, and `make verify-fast`.
- Runtime signals: `.gsd/runtime/dev-server/status.json`, manager-owned PID/log paths, probe status, restart count, and last-failure timestamps.
- Inspection surfaces: `python3 tools/dev_server.py status --format json`, repo-native `make dev-server-status`, and `GET /api/health`.
- Failure visibility: stale/crashed child state must report the recorded PID, probe/launch failure reason, log path, and timestamps without dumping runtime log contents or secrets.
- Redaction constraints: health/status output stays path-and-metadata only; no provider keys, request bodies, or log contents are emitted.

## Tasks

- [x] **T01: Add a health probe and dev-loop state contract** `est:0.5d`
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
  - Files: `app/routes/api.py`, `tests/test_api.py`, `tools/dev_server.py`, `tests/test_dev_server.py`
  - Verify: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py`
`python3 tools/dev_server.py --help`

- [x] **T02: Implement lifecycle commands and crash-recovery subprocess proof** `est:0.75d`
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
  - Files: `tools/dev_server.py`, `tests/test_dev_server.py`, `tests/test_dev_server_process.py`, `run.py`
  - Verify: `python3 -m pytest -q tests/test_dev_server.py tests/test_dev_server_process.py`
`python3 tools/dev_server.py --help`

- [ ] **T03: Expose the supported Makefile workflow and continuity proof** `est:0.5d`
  Make the lifecycle manager the supported operator path and prove it composes with the existing boundary and fast verification lanes. This task closes the slice by turning the direct CLI into the documented repo-native workflow contributors are supposed to use.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `Makefile` wrapper targets | Stop and fix the wrapper names/flags instead of leaving multiple unsupported startup paths in the repo | N/A | Treat wrapper drift from `tools/dev_server.py` as a blocker, not doc debt |
| Contributor docs in `README.md` / `docs/runtime-state-boundary.md` | Keep one canonical flow; if docs and code disagree, update them together before closing the slice | N/A | Remove ambiguous or harness-specific guidance rather than layering alternatives |
| Existing repo verification lanes | If `make verify-runtime-boundary` or `make verify-fast` regress, repair the code/docs before claiming the supported loop is shippable | Let the repo-native commands own the timing; no background supervisors | Treat unexpected failures as slice blockers because they undermine `R065` support |

## Load Profile

- **Shared resources**: repo-native command surface, build/test lanes, and the ignored `.gsd/runtime/dev-server/**` subtree.
- **Per-operation cost**: thin Make wrappers plus the existing verification commands.
- **10x breakpoint**: wrapper/doc drift that sends contributors back to ad hoc `python run.py` habits.

## Negative Tests

- **Malformed inputs**: missing Make targets, stale docs, and unsupported references to `.bg-shell/**` or manual runtime-file cleanup.
- **Error paths**: wrapper targets that bypass lifecycle state, docs that imply PID files are enough, and verification lanes that fail after wiring.
- **Boundary conditions**: `make dev-server-status` when nothing is running, clean repo/no-op runtime boundary audit, and routine `make verify-fast` continuity after the new workflow lands.

## Steps

1. Add repo-native Make targets `dev-server-start`, `dev-server-status`, `dev-server-restart`, and `dev-server-stop` that wrap `tools/dev_server.py` and keep the CLI as the single implementation source of truth.
2. Update `README.md` with the supported local dev loop, the crash-recovery/status path, and the rule that `.gsd/runtime/dev-server/**` is manager-owned transient state rather than checked-in workflow data.
3. Update `docs/runtime-state-boundary.md` so the boundary documentation explicitly includes the dev-server runtime subtree and keeps `.bg-shell/**` and `.planning/**` guidance aligned with S01/S02.
4. Re-run the focused dev-loop tests plus `make verify-runtime-boundary` and `make verify-fast` so this slice advances `R064` without regressing the broader repo proof lane that S04 will depend on.

## Must-Haves

- [ ] The documented operator path is `make dev-server-start|status|restart|stop`, not ad hoc `python run.py` archaeology.
- [ ] Docs explain where lifecycle state lives and why it remains transient/ignored.
- [ ] The new workflow keeps the runtime-boundary verifier green and preserves the default `make verify-fast` continuity lane.
- [ ] Wrapper names, docs, and CLI flags stay in sync so contributors have one obvious local-server path.
  - Files: `Makefile`, `README.md`, `docs/runtime-state-boundary.md`, `tools/dev_server.py`
  - Verify: `grep -n "^dev-server-start:\|^dev-server-status:\|^dev-server-restart:\|^dev-server-stop:" Makefile`
`python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
`make verify-runtime-boundary`
`make verify-fast`

## Files Likely Touched

- app/routes/api.py
- tests/test_api.py
- tools/dev_server.py
- tests/test_dev_server.py
- tests/test_dev_server_process.py
- run.py
- Makefile
- README.md
- docs/runtime-state-boundary.md
