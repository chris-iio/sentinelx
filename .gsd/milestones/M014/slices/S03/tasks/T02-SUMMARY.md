---
id: T02
parent: S03
milestone: M014
key_files:
  - tools/dev_server.py
  - tests/test_dev_server.py
  - tests/test_dev_server_process.py
key_decisions:
  - Kept the child-serving entrypoint internal and hidden so the supported operator surface remains only `start`, `status`, `restart`, and `stop`.
  - Made `status` persist probe-derived transitions and failure metadata, but never emit runtime log contents or other secret-bearing output.
duration: 
verification_result: passed
completed_at: 2026-04-25T12:04:04.211Z
blocker_discovered: false
---

# T02: Implemented repo-native dev-server lifecycle commands with crash detection and restart proof.

**Implemented repo-native dev-server lifecycle commands with crash detection and restart proof.**

## What Happened

Extended `tools/dev_server.py` from a helper-only probe contract into the supported local lifecycle manager. The CLI now exposes `start`, `status`, `restart`, and `stop`, keeps runtime state under `.gsd/runtime/dev-server/**`, launches a hidden child-serving entrypoint for the real Flask app via `create_app()`, persists host/port/pid/log-path/start timestamps/restart counts/last-failure metadata, and derives operator-facing state from live `/api/health` probes instead of trusting a pid file alone. `status` now writes back `running`, `starting`, `stale`, `crashed`, and `stopped` transitions with bounded probe outcomes, malformed-state failures, and secret-free diagnostics. I updated `tests/test_dev_server.py` to cover the tightened contract, non-local host rejection, malformed status handling, and transition synthesis, and added `tests/test_dev_server_process.py` to prove the real subprocess flow on an ephemeral port: start healthy, kill the managed child, observe `crashed`, restart on the recorded config, and stop cleanly.

## Verification

Fresh verification after the last code change covered both the task-level and slice-level bars. `python3 -m pytest -q tests/test_dev_server.py tests/test_dev_server_process.py` passed (`10 passed`) for helper-state and subprocess lifecycle proof. `python3 tools/dev_server.py --help` passed and showed only the supported public lifecycle commands. A direct `python3 tools/dev_server.py --repo-root <tmp> status --format json` check confirmed the persisted status surface stays metadata-only while reporting probe truth. The broader slice lane also passed: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` (`33 passed`), `make verify-runtime-boundary`, and `make verify-fast` all exited 0 after the lifecycle implementation landed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_dev_server.py tests/test_dev_server_process.py` | 0 | ✅ pass | 3004ms |
| 2 | `python3 tools/dev_server.py --help` | 0 | ✅ pass | 42ms |
| 3 | `python3 tools/dev_server.py --repo-root /tmp/sentinelx-dev-server-status-ocattzwo status --format json` | 0 | ✅ pass | 41ms |
| 4 | `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` | 0 | ✅ pass | 2915ms |
| 5 | `make verify-runtime-boundary` | 0 | ✅ pass | 1011ms |
| 6 | `make verify-fast` | 0 | ✅ pass | 10729ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tools/dev_server.py`
- `tests/test_dev_server.py`
- `tests/test_dev_server_process.py`
