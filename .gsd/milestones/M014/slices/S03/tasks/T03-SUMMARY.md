---
id: T03
parent: S03
milestone: M014
key_files:
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
  - tools/dev_server.py
  - tests/test_dev_server.py
key_decisions:
  - Made `make dev-server-start|status|restart|stop` the supported operator path while keeping `tools/dev_server.py` as the single implementation source of truth.
  - Documented `.gsd/runtime/dev-server/**` as manager-owned transient inspection state and explicitly kept `.bg-shell/**` and `.planning/**` out of the supported local server recovery path.
duration: 
verification_result: passed
completed_at: 2026-04-25T12:09:39.660Z
blocker_discovered: false
---

# T03: Added repo-native dev-server Make targets and documented the transient manager-owned workflow with continuity tests.

**Added repo-native dev-server Make targets and documented the transient manager-owned workflow with continuity tests.**

## What Happened

Implemented the supported local dev loop as thin Make wrappers over the existing lifecycle manager by adding `dev-server-start`, `dev-server-status`, `dev-server-restart`, and `dev-server-stop` to `Makefile` via a shared `DEV_SERVER` command. Updated `README.md` so a cold-start contributor now sees one canonical server path, the crash-recovery/inspection flow, the fixed `GET /api/health` probe, and the rule that `.gsd/runtime/dev-server/**` is manager-owned transient state rather than checked-in workflow data. Updated `docs/runtime-state-boundary.md` to explicitly classify the dev-server runtime subtree as transient, keep `.bg-shell/**` out of the supported SentinelX server lifecycle surface, and keep `.planning/**` in the documented manual-review bucket. Added continuity tests in `tests/test_dev_server.py` so wrapper names, wrapper recipes, README guidance, and runtime-boundary language fail closed if they drift back toward ad hoc startup habits. Also updated `tools/dev_server.py` help text/module docs so the checked-in CLI and the supported Make workflow stay aligned.

## Verification

Ran `grep -n "^dev-server-start:\|^dev-server-status:\|^dev-server-restart:\|^dev-server-stop:" Makefile` and confirmed all four supported targets are present. Ran `make dev-server-status` and `python3 tools/dev_server.py status --format json`; both reported the empty-state `stopped` contract with PID/log/status-path metadata only and no log contents. Ran `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` and it passed (`36 passed`). Ran `make verify-runtime-boundary` and it passed; the live audit still surfaced only documented `.planning/**` `manual-review-path` findings and no blocker classes. Ran `make verify-fast` and it passed end-to-end (`1017` non-E2E pytest tests, `81` Vitest tests, TypeScript typecheck, and production asset build).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -n "^dev-server-start:\|^dev-server-status:\|^dev-server-restart:\|^dev-server-stop:" Makefile` | 0 | ✅ pass | 0ms |
| 2 | `make dev-server-status` | 0 | ✅ pass | 40ms |
| 3 | `python3 tools/dev_server.py status --format json` | 0 | ✅ pass | 40ms |
| 4 | `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` | 0 | ✅ pass | 3010ms |
| 5 | `make verify-runtime-boundary` | 0 | ✅ pass | 1030ms |
| 6 | `make verify-fast` | 0 | ✅ pass | 9990ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `Makefile`
- `README.md`
- `docs/runtime-state-boundary.md`
- `tools/dev_server.py`
- `tests/test_dev_server.py`
