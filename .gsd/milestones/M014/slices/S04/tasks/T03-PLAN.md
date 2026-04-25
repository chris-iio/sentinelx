---
estimated_steps: 5
estimated_files: 8
skills_used:
  - test
  - verify-before-complete
---

# T03: Re-prove the assembled workflow and capture closure evidence

**Slice:** S04 — Verification, review, and refactor closure
**Milestone:** M014

## Description

Load `verify-before-complete` before claiming the slice is done. After the last edit from T02, rerun the focused workflow proof surface, exercise the supported repair and dev-server commands on the live repo, and finish with the full repository verification lane. Capture both a machine-readable lifecycle transcript and a narrative closure artifact so S04 closes on fresh evidence instead of inherited summaries.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Focused pytest workflow surface | Stop and fix the regression before any broader proof claims | N/A | Treat mismatched expectations as a slice blocker |
| `make repair-runtime-state` / `make verify-runtime-boundary` | Treat actionable blocker findings as failures; manual-review `.planning/**` findings may remain visible but must stay non-mutating | CLI commands already bound their own runtime | Treat unexpected issue-code or action drift as a blocker |
| Live `tools/dev_server.py` lifecycle exercise | Stop and diagnose via status/log-path metadata before running `make verify` | Bound startup/status waits and fail if health never turns healthy or crashed state never surfaces | Treat non-exact `/api/health` output as unhealthy and stop the proof |
| `make verify` | Treat any failing lane as slice-incomplete | Let the repo-native commands own timeouts/build duration | Treat unexpected suite/build output changes as regressions, not flaky noise |

## Load Profile

- **Shared resources**: repo-local `.gsd` boundary roots, one ephemeral localhost port, and the full backend/frontend verification lanes.
- **Per-operation cost**: focused pytest runs, one repair audit/apply pass, one live lifecycle exercise, and one full repo verification pass.
- **10x breakpoint**: repeated crash/restart or boundary regressions that only appear when the seams compose instead of when each tool is tested alone.

## Negative Tests

- **Malformed inputs**: exact-payload health mismatch, corrupted status metadata, and unsupported boundary findings.
- **Error paths**: tracked/unignored transient blockers, blocked `.planning/**` manual-review findings, crashed child detection, and restart recovery.
- **Boundary conditions**: no-op repair on the live repo, manual-review findings staying visible-but-non-blocking, and clean stop after a forced crash/restart cycle.

## Steps

1. Re-run `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` after the last code change.
2. Run `make repair-runtime-state` and `make verify-runtime-boundary`, confirming that blocker classes stay at zero while `.planning/**` remains visible only as report-only manual-review output.
3. Exercise the supported dev loop on an ephemeral localhost port: start the manager, fetch `/api/health`, kill the managed child, wait for `status` to report `crashed`, restart to healthy, stop cleanly, and save the transcript to `.gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json`.
4. Run `make verify` only after the focused workflow and live operator proofs are green.
5. Write `.gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md` with the exact commands run, exit codes, key observations, and any residual manual-review/non-goal notes.

## Must-Haves

- [ ] Fresh evidence is produced after the final edit; no completion claim relies on prior slice summaries.
- [ ] The live repair command stays conservative and the boundary verifier still surfaces `.planning/**` without mutating it.
- [ ] The supported dev loop proves start → healthy probe → crashed detection → restart → stop on a real localhost port.
- [ ] `make verify` passes after the focused seam proof, and both proof artifacts are non-empty.

## Verification

- `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
- `make repair-runtime-state`
- `make verify-runtime-boundary`
- `make verify`
- `test -s .gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json && test -s .gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md`

## Observability Impact

- Signals added/changed: none in product code; this task captures the existing issue codes, repair summaries, health probe results, restart count, and failure metadata as fresh closure evidence.
- How a future agent inspects this: `make repair-runtime-state`, `make verify-runtime-boundary`, `python3 tools/dev_server.py status --format json`, and the two proof artifacts under `.gsd/milestones/M014/slices/S04/`.
- Failure state exposed: blocker-class audit findings, conservative repair behavior, crashed-child detection, and full-suite regressions are all recorded explicitly.

## Inputs

- `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` — review/risk decisions from T01 and T02.
- `app/health_contract.py` — shared health contract introduced in T02.
- `tools/runtime_state_boundary.py` — authoritative boundary verifier.
- `tools/runtime_state_repair.py` — supported repair entrypoint.
- `tools/dev_server.py` — supported dev lifecycle implementation.
- `Makefile` — repo-native wrapper and verification entrypoints.
- `tests/test_runtime_state_boundary_git.py` — temp-repo Git blocker proof.
- `tests/test_dev_server_process.py` — subprocess crash/restart proof.

## Expected Output

- `.gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json` — machine-readable transcript of the live start/health/crash/restart/stop exercise.
- `.gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md` — fresh narrative evidence covering focused tests, repair/boundary commands, the live lifecycle exercise, and `make verify`.
