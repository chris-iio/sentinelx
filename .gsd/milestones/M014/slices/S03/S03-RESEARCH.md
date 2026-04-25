# M014/S03 — Research

**Date:** 2026-04-25

## Summary

S03 is primarily about **R064** (one supported local dev-process path with cheap crash recovery) and it must support **R065** by preserving the existing verification contract. The current repo has no supported lifecycle surface for the local Flask app beyond manually running `python run.py`: `run.py` is the only real server entrypoint, it hardcodes `127.0.0.1:5000`, and there is no repo-native `make` target, status command, PID file, or generic health endpoint. `Makefile` already exposes repo-native surfaces for verification and runtime-state repair, so S03’s natural fit is “one Python tool + Makefile aliases + docs”, not ad hoc shell snippets.

S01/S02 already established the hard constraint: anything this slice writes must preserve the classifier-backed boundary. The safest place for dev-loop state is **`.gsd/runtime/**`**, which is already classified as transient and ignored. Avoid using `.bg-shell` as the source of truth for the supported dev loop even though it is transient too; `.bg-shell` is harness-owned runtime state, while S03 needs a repo-native workflow that works outside the agent harness. The S01 forward-intelligence rule still applies here: do not create new tracked/unignored runtime debris or widen the boundary policy.

The strongest planning guidance comes from the installed **`observability`** skill: for long-running processes, **log decisions, not activity**, **fail loudly and persist the reason**, and expose a cheap **health/status surface**. That points to a small server-manager tool that owns a persisted status file under `.gsd/runtime/`, probes the local server explicitly, and makes crash/restart state legible to the next operator instead of leaving them to inspect ports and orphaned processes by hand.

## Recommendation

Add one repo-native lifecycle tool (new `tools/dev_server.py`) and make it the only supported local dev-process entrypoint via `Makefile` wrappers.

Recommended contract:

- `tools/dev_server.py` owns `start`, `status`, `restart`, and `stop` subcommands.
- It persists process metadata and last-failure/status information under `.gsd/runtime/dev-server/` (PID, port, log path, started-at, last probe result, last failure reason, restart count).
- It launches the local app in a child process instead of depending on external supervisors; cheap crash recovery is then `status` → detect dead/stale child → `restart`.
- It performs an explicit readiness/liveness probe instead of trusting PID files alone.
- It follows the `runtime_state_repair.py` pattern: repo-root-aware CLI, text/json output, deterministic exit codes, and subprocess-based tests.

Add a small generic health endpoint for the manager to probe. The cleanest seam is `bp_api` in `app/routes/api.py` (or a new route module imported from `app/routes/__init__.py`) because it already holds JSON-only, CSRF-exempt operational endpoints. A minimal `GET /api/health` returning a fixed JSON object is sufficient; the point is not feature richness, but a stable liveness/readiness contract. If the planner wants to avoid a route addition, the manager can probe `GET /`, but that is a weaker seam and makes “healthy vs merely bound to a port” less explicit.

Do **not** build a hidden forever-supervisor. The milestone context explicitly rejected a heavier supervisor/orchestrator for now. S03 only needs an explicit supported path with cheap restart, not a self-healing daemon ecosystem.

## Implementation Landscape

### Key Files

- `run.py` — current manual server entrypoint; binds only to `127.0.0.1:5000` and offers no lifecycle/status surface. This fixed-port design is the main testability constraint for S03.
- `app/__init__.py` — app factory seam if S03 needs a lightweight app-level readiness response or startup metadata.
- `app/routes/api.py` — existing JSON/CSRF-exempt operational route surface; natural place for a new generic `GET /api/health` endpoint.
- `app/routes/__init__.py` — import/registration point if health/status lives in a dedicated route module instead of `api.py`.
- `Makefile` — the existing repo-native operator surface. S03 should expose the supported loop here the same way S01/S02 exposed `verify-runtime-boundary` and `repair-runtime-state`.
- `tools/runtime_state_boundary.py` — authoritative boundary contract. No classifier changes should be needed if S03 keeps all dev-loop state under `.gsd/runtime/**`.
- `tools/runtime_state_repair.py` — best reference for the new tool’s CLI/report shape: argparse subcommands/options, explicit exit semantics, JSON/text rendering, repo-root awareness, subprocess-heavy tests.
- `tests/e2e/conftest.py` — reusable patterns for free-port allocation and readiness polling (`_find_free_port`, `_wait_for_server`). Helpful both for test utilities and for the manager’s probe logic.
- `tests/test_routes.py` / `tests/test_api.py` — route-level proof surface if S03 adds `/api/health`.
- `README.md` — currently documents verification lanes and runtime-boundary/repair flows, but not a supported local server lifecycle. S03 should add the operator-facing start/status/restart instructions here.
- `tests/test_runtime_state_boundary.py` / `tests/test_runtime_state_boundary_git.py` — rerun after S03 to prove the new dev-loop state still stays on the transient side of the boundary.
- `tests/test_runtime_state_repair.py` / `tests/test_runtime_state_repair_git.py` — useful reference for temp-repo/subprocess testing style when designing the S03 process tests.

### Build Order

1. **Pin the ownership boundary first.** Decide the exact runtime-owned path(s) under `.gsd/runtime/dev-server/**` and the status model (`starting`, `running`, `stale`, `crashed`, `stopped`). This is the contract everything else depends on.
2. **Add the probe seam next.** Either add `GET /api/health` or explicitly choose the fallback HTTP/TCP probe contract. Without this, restart logic will collapse into PID folklore.
3. **Implement the manager tool.** Start/status/stop/restart, stale-PID handling, log/status persistence, and explicit exit codes.
4. **Wrap it in `Makefile` and document it.** The user-facing supported path should be Make targets, not direct internal script usage.
5. **Then prove crash recovery.** Launch the server via the supported tool, kill the child, assert `status` reports the failure cleanly, then assert `restart` returns to healthy.
6. **Finish with boundary + fast verification.** This slice should not need browser-E2E unless the planner chooses a UI-visible health surface.

### Verification Approach

- Focused unit/integration tests for the manager tool, e.g.:
  - `python3 -m pytest -q tests/test_dev_server.py tests/test_dev_server_process.py`
- If adding an HTTP health route:
  - `python3 -m pytest -q tests/test_api.py tests/test_routes.py`
- Boundary/regression guardrail after adding new runtime files/Make targets:
  - `make verify-runtime-boundary`
- Repo-wide non-E2E regression proof for R065 support:
  - `make verify-fast`

The highest-value integration proof is a subprocess test that uses the supported CLI end to end: start the local server, confirm readiness, kill the child process, confirm `status` reports stale/crashed state with a persisted reason, then `restart` and confirm the server becomes healthy again.

## Constraints

- `run.py` hardcodes `127.0.0.1:5000`; tests and the manager need either a wrapper with configurable port/host or a minimal override seam. Reusing `run.py` exactly as-is makes isolated crash-recovery tests fragile.
- The S01/S02 boundary contract must remain the single source of truth. New dev-loop artifacts must stay under already-transient roots (`.gsd/runtime/**` preferred), not in repo root or `.planning/**`.
- `make verify-runtime-boundary` is intentionally blocker-focused; S03 should reuse that contract, not widen it.
- `requirements.txt` has no `psutil`, `supervisor`, or similar process-management dependency. Prefer stdlib `subprocess`, `socket`, `signal`, and `urllib/http.client` over new infrastructure.
- Current JSON routes are job-specific (`/api/status/<job_id>` and `/enrichment/status/<job_id>`). There is no generic server-health endpoint today.

## Common Pitfalls

- **Using `.bg-shell` as the supported lifecycle state store** — it is transient, but it is harness-owned rather than repo-native. Keep S03’s source of truth under `.gsd/runtime/**`.
- **Treating a PID file as proof of health** — stale PIDs are exactly the failure class this slice needs to retire. Always combine persisted metadata with a live probe.
- **Hardcoding tests to port 5000** — this will create flaky crash-recovery tests and local collisions. Follow the `tests/e2e/conftest.py` free-port pattern or add a narrow override seam.
- **Overbuilding into a supervisor** — cheap explicit restart is in scope; a background self-healing daemon is not.

## Open Risks

- The planner needs to choose between two small seams for liveness: a new `/api/health` route or a manager-side probe against `/`. The route is cleaner; the probe-only path is narrower but less explicit.
- If `run.py` remains fixed to port 5000, the manager may need its own child-runner module to make automated tests deterministic.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Long-running process observability | `observability` | installed |
| Flask | `aj-geddes/useful-ai-prompts@flask-api-development` | available (790 installs) |
| Flask | `jezweb/claude-skills@flask` | available (430 installs) |
| Process supervision | none found from `npx skills find "process supervision"` | none found |
