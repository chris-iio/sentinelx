---
id: S03
parent: M014
milestone: M014
provides:
  - One supported local dev-server lifecycle surface via `make dev-server-start|status|restart|stop` backed by `tools/dev_server.py`.
  - A fixed secret-free readiness probe at `GET /api/health` for local lifecycle verification.
  - Crash/stale detection and cheap restart recovery that preserves host/port config, restart count, and failure metadata under `.gsd/runtime/dev-server/**`.
  - Boundary-aligned documentation stating that `.gsd/runtime/dev-server/**` is transient, `.bg-shell/**` is out of scope, and `.planning/**` remains manual-review.
requires:
  - slice: S01
    provides: Consumed the durable-vs-transient boundary policy so the dev-server manager state stays under `.gsd/runtime/dev-server/**` and outside durable milestone artifacts.
affects:
  - S04
key_files:
  - app/routes/api.py
  - tools/dev_server.py
  - tests/test_api.py
  - tests/test_dev_server.py
  - tests/test_dev_server_process.py
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
key_decisions:
  - Locked `GET /api/health` to an exact secret-free JSON contract so probes and tests can fail closed on malformed or secret-bearing responses.
  - Kept all manager-owned local server metadata under `.gsd/runtime/dev-server/**` and explicitly excluded `.bg-shell/**` from the supported SentinelX lifecycle surface.
  - Made `tools/dev_server.py` the single implementation source of truth and kept `make dev-server-start|status|restart|stop` as thin wrappers only.
  - Derived `status` truth from live `/api/health` probes rather than PID files alone so stale/crashed children surface explicit recovery metadata.
patterns_established:
  - Use a fixed metadata-only health contract for local lifecycle probes rather than broad diagnostic payloads.
  - Keep repo-native Make targets as thin wrappers over one checked-in CLI implementation to avoid lifecycle/doc drift.
  - Treat PID, log, and status files as manager-owned transient inspection state, not as durable workflow artifacts.
  - Persist failure timestamps/reasons and restart counts, but never emit runtime log contents from status output.
observability_surfaces:
  - `GET /api/health` fixed readiness payload
  - `python3 tools/dev_server.py status --format json` machine-readable lifecycle state
  - `make dev-server-status` human-readable lifecycle inspection
  - `.gsd/runtime/dev-server/status.json` manager-owned metadata ledger
  - `.gsd/runtime/dev-server/logs/*.log` path-only references surfaced through status output
drill_down_paths:
  - .gsd/milestones/M014/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M014/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-25T12:15:10.494Z
blocker_discovered: false
---

# S03: S03

**Shipped the supported SentinelX local dev-server lifecycle: a fixed secret-free `/api/health` probe, repo-owned `tools/dev_server.py`, repo-native `make dev-server-start|status|restart|stop` wrappers, and verified crash detection/restart recovery under `.gsd/runtime/dev-server/**`.**

## What Happened

## What Happened
S03 completed the supported local operator loop for SentinelX without widening the runtime boundary introduced in S01/S02. The slice added a fixed secret-free `GET /api/health` contract in `app/routes/api.py`, built `tools/dev_server.py` as the single checked-in lifecycle implementation, and exposed the supported repo-native surface through `make dev-server-start`, `make dev-server-status`, `make dev-server-restart`, and `make dev-server-stop`.

The lifecycle manager now owns repo-root discovery, host/port validation, status serialization, managed log-path creation, health probing, and child-process start/stop/restart behavior under `.gsd/runtime/dev-server/**`. It fails closed on malformed state, refuses non-local hosts, never trusts PID metadata alone, and derives operator-facing truth from the live `/api/health` probe so stale and crashed children surface explicit failure metadata instead of silent false positives.

The slice also closed the documentation/operator seam. `README.md` now points contributors to one canonical local-server path, and `docs/runtime-state-boundary.md` explicitly classifies `.gsd/runtime/dev-server/**` as manager-owned transient state while keeping `.bg-shell/**` outside the supported SentinelX lifecycle surface and `.planning/**` in manual-review territory. The resulting contract gives S04 a stable dev-loop boundary that composes with the repair tooling instead of competing with it.

## Operational Readiness
- **Health signal:** `GET /api/health` returns the fixed JSON probe contract `{service, status, ready}` and stayed secret-free under fresh verification.
- **Failure signal:** `python3 tools/dev_server.py status --format json` and `make dev-server-status` report status, pid, restart count, status/log paths, probe result, last failure timestamp, and last failure reason without dumping runtime log contents.
- **Recovery procedure:** crash recovery is explicit, not supervisory: when the managed child dies, `status` reports `crashed`, and `restart` reuses the recorded host/port configuration and increments `restart_count` before returning to healthy.
- **Monitoring gaps:** there is still no long-running supervisor or external alerting; this slice intentionally stops at local operator visibility and cheap manual restart for the repo-native dev loop.

## Downstream Handoff
S04 can now treat the local server loop as a closed seam: the supported process surface is `make dev-server-start|status|restart|stop`, the runtime subtree is `.gsd/runtime/dev-server/**`, and crash diagnosis/restart proof exists both in subprocess tests and in a fresh live repo exercise performed during slice closeout.

## Verification

Fresh slice-level verification passed after reading the landed code and re-running the planned commands from the slice plan:

- `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` → `36 passed in 2.72s`
- `make verify-runtime-boundary` → exit 0; classifier tests passed and the live audit reported only existing `.planning/**` `manual-review-path` findings, with no blocker classes.
- `make verify-fast` → exit 0; `1017` non-E2E pytest tests passed, `81` Vitest tests passed, TypeScript typecheck passed, and the production asset build completed successfully.

Fresh operational proof also passed in the live repo:

1. Started the managed server on an ephemeral localhost port with `python3 tools/dev_server.py start --host 127.0.0.1 --port <free-port> --format json` and observed `status=running`, `restart_count=0`, and `probe=healthy`.
2. Fetched `http://127.0.0.1:<free-port>/api/health` and confirmed the fixed payload `{"service":"sentinelx","status":"ok","ready":true}`.
3. Sent `SIGKILL` to the manager-owned child, then re-ran `python3 tools/dev_server.py status --format json` until it reported `status=crashed` with the recorded PID, `probe=refused`, and an explicit `last_failure_reason`.
4. Ran `python3 tools/dev_server.py restart --format json` and confirmed `status=running`, the same port, and `restart_count=1`, then re-fetched `/api/health` successfully.
5. Ran `make dev-server-stop` followed by `make dev-server-status` and confirmed the supported wrapper surface returned to `status: stopped` while preserving metadata-only failure/restart history.

These checks collectively re-proved the health-route contract, state helpers, CLI lifecycle flow, crashed-child detection, restart recovery, runtime-boundary continuity, and the broader fast verification lane required by the slice plan.

## Requirements Advanced

- R065 — Preserved the existing continuity lanes while landing the new dev-loop surface: `make verify-runtime-boundary` and `make verify-fast` both passed after the lifecycle/docs changes.

## Requirements Validated

- R064 — Fresh slice verification passed (`36` focused pytest tests, `make verify-runtime-boundary`, `make verify-fast`) and a live repo exercise confirmed start → healthy `/api/health` → crash detection → restart recovery → stop through the supported workflow.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

The supported workflow is intentionally local and manual: it provides explicit health, crash, and restart visibility, but it does not add a background supervisor, remote monitoring, or automated re-spawn outside the repo-native operator loop.

## Follow-ups

S04 should re-prove the combined `make repair-runtime-state` + `make dev-server-*` workflow together, then perform the planned review/refactor pass across the new boundary/repair/dev-loop seams.

## Files Created/Modified

- `app/routes/api.py` — Added the fixed secret-free `GET /api/health` probe contract for local lifecycle checks.
- `tools/dev_server.py` — Implemented repo-root/path ownership, status serialization, live probe synthesis, and the supported start/status/restart/stop lifecycle commands.
- `tests/test_api.py` — Pinned the `/api/health` contract and proved the route does not touch provider configuration.
- `tests/test_dev_server.py` — Covered helper contracts, malformed-state handling, wrapper/doc drift checks, and status transition synthesis.
- `tests/test_dev_server_process.py` — Added subprocess proof for start, crash detection, restart recovery, and clean stop on an ephemeral localhost port.
- `Makefile` — Added thin repo-native wrappers for the supported dev-server lifecycle commands.
- `README.md` — Documented the canonical local dev loop, crash-recovery path, and transient manager-owned runtime subtree.
- `docs/runtime-state-boundary.md` — Extended the boundary documentation to classify `.gsd/runtime/dev-server/**` as transient and keep `.bg-shell/**` / `.planning/**` distinctions explicit.
