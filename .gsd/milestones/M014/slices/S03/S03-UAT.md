# S03: S03 — UAT

**Milestone:** M014
**Written:** 2026-04-25T12:15:10.494Z

# S03: Supported local dev process loop — UAT

**Milestone:** M014  
**Slice:** S03  
**Goal:** Confirm SentinelX has one supported local dev-server path, that crash detection/restart works through the supported workflow, and that all manager state stays on the transient side of the runtime boundary.

## Preconditions
- Run from the repo root.
- Python 3 and project dependencies are installed.
- A free localhost port is available.
- No assumption is made about existing `.gsd/runtime/dev-server/**` contents; the workflow must behave correctly from either a clean or previously used transient runtime directory.

## Test Case 1 — Supported cold-start and inspection flow
1. Run `make dev-server-status` before starting the server.  
   **Expected:** command succeeds and reports `status: stopped` (or another explicit metadata state) using `.gsd/runtime/dev-server/status.json`; no log contents or secrets are printed.
2. Run `make dev-server-start`.  
   **Expected:** command succeeds, starts only a localhost-bound manager-owned child, and reports `status: running` once the fixed health probe is healthy.
3. In another shell, run `python3 tools/dev_server.py status --format json`.  
   **Expected:** JSON output includes status, host, port, pid, restart count, status path, log path, and probe metadata only.
4. Fetch `GET /api/health` on the reported port.  
   **Expected:** HTTP 200 JSON exactly matching the fixed secret-free readiness contract (`service`, `status`, `ready`) with no provider/config/session data.

## Test Case 2 — Crash detection and cheap restart recovery
1. With the server running, read the current PID from `python3 tools/dev_server.py status --format json`.  
   **Expected:** a positive integer PID is present for the manager-owned child.
2. Kill that PID externally (for example, `kill -9 <pid>`).  
   **Expected:** the child exits immediately.
3. Re-run `make dev-server-status` or `python3 tools/dev_server.py status --format json`.  
   **Expected:** the manager reports `status: crashed`, preserves the recorded PID/port/log path, and includes an explicit last-failure timestamp/reason plus an unhealthy probe result.
4. Run `make dev-server-restart`.  
   **Expected:** the manager reuses the recorded localhost configuration, increments `restart_count`, and returns to `status: running`.
5. Fetch `GET /api/health` again.  
   **Expected:** the endpoint returns the same fixed healthy JSON payload after restart.

## Test Case 3 — Supported stop flow
1. Run `make dev-server-stop`.  
   **Expected:** only the manager-owned child is stopped; the command succeeds without requiring manual PID-file cleanup.
2. Run `make dev-server-status` immediately afterward.  
   **Expected:** `status: stopped` with metadata-only output; restart/failure history may remain visible, but there is no live healthy probe.

## Test Case 4 — Boundary and continuity proof
1. Run `make verify-runtime-boundary`.  
   **Expected:** command exits 0; any `.planning/**` findings are reported only as `manual-review-path`, and `.gsd/runtime/dev-server/**` remains classified as transient rather than durable.
2. Run `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`.  
   **Expected:** the focused health-route, helper, and subprocess crash/restart proof suite passes.
3. Run `make verify-fast`.  
   **Expected:** the broader non-E2E repo verification lane still passes, proving the supported dev loop did not regress existing SentinelX behavior.

## Edge Cases
- `make dev-server-status` with no prior runtime state must fail closed into a clean metadata response rather than a traceback.
- Corrupted `.gsd/runtime/dev-server/status.json` must surface as an explicit contract failure, not be silently repaired or guessed.
- Non-local host arguments (for example `0.0.0.0`) must be rejected before launch.
- Status/restart output must remain metadata-only; log contents, provider keys, and request bodies must never appear in `/api/health` or CLI status output.
