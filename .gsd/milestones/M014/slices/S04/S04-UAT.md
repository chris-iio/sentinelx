# S04: Verification, review, and refactor closure — UAT

**Milestone:** M014
**Written:** 2026-04-26T01:47:59.534Z

# S04 UAT — workflow hardening closure

## Preconditions
- Repository root is `/home/chris/projects/sentinelx`.
- No manual cleanup of `.planning/**` is expected; those paths should remain visible but non-mutating.
- A free localhost port is available for the supported dev-server exercise.

## Test Case 1 — Review artifact captures the seam decisions
1. Open `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`.
2. Confirm it names the seam files (`tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`) and separates `refactor-now` from `leave-alone`.
3. Confirm it explicitly states that the health contract is single-sourced and that `.planning/**` remains `manual-review-path` / report-only.

**Expected outcome:** The review artifact is non-empty, names the inspected seam, records the landed `app/health_contract.py` refactor, and explicitly preserves classifier-owned repair policy plus the single supported dev-server surface.

## Test Case 2 — Repair and boundary verification stay conservative
1. Run `make repair-runtime-state`.
2. Confirm exit code 0 and inspect the summary counts.
3. Run `make verify-runtime-boundary`.
4. Confirm exit code 0 and inspect the issue-code summary.

**Expected outcome:** `make repair-runtime-state` reports `actionable_issue_count: 0` and applies no deindex/quarantine changes on a clean repo; `.planning/**` findings remain visible only as blocked `manual-review-path` output. `make verify-runtime-boundary` passes and reports only the manual-review class, with no `tracked-transient`, `unignored-transient`, `conflicting-rule-match`, or `unknown-root` blocker findings.

## Test Case 3 — Shared health contract and crash-recovery loop work on the supported path
1. Run `python3 tools/dev_server.py stop --format json` to normalize baseline state.
2. Run `python3 tools/dev_server.py start --host 127.0.0.1 --port <free-port> --format json`.
3. Fetch `http://127.0.0.1:<free-port>/api/health`.
4. Kill the managed child process using the `pid` reported by the start/status output.
5. Run `python3 tools/dev_server.py status --format json`.
6. Run `python3 tools/dev_server.py restart --format json`.
7. Fetch `http://127.0.0.1:<free-port>/api/health` again.
8. Run `python3 tools/dev_server.py stop --format json`.

**Expected outcome:**
- Start returns `status: running` with a healthy probe.
- `/api/health` returns the exact shared payload `{"service":"sentinelx","status":"ok","ready":true}`.
- After the forced kill, `status` becomes `crashed`, `probe.status` becomes `refused`, and `last_failure_reason` is explicit and secret-free.
- Restart returns the manager to `running`/`healthy` and increments `restart_count`.
- Stop returns `status: stopped` with `pid: null`.

## Test Case 4 — Full project verification still passes after hardening
1. Run `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`.
2. Run `make verify`.
3. Confirm the closure artifacts exist: `test -s .gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json && test -s .gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md`.

**Expected outcome:** The focused seam suite passes (`57 passed`), the repo-wide verification lane passes end to end (`1018` non-E2E pytest passes, `81` Vitest passes, clean TypeScript/build, `113` E2E passes), and both closure-proof artifacts are present and non-empty.

## Edge / regression expectations
- Any extra or secret-bearing key added to `/api/health` must remain a focused-test failure and classify as `malformed` to the dev-server probe rather than healthy.
- `.planning/**` may remain visible in boundary/repair output, but only as manual-review/report-only findings; the supported repair path must not mutate those files automatically.
- The lifecycle proof must use the repo-managed `.gsd/runtime/dev-server/status.json` seam so `restart_count`, `last_failure_reason`, and final stop state are re-proved on the supported operator path.
