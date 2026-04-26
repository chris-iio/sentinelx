# S04: Verification, review, and refactor closure

**Goal:** Close M014 by explicitly reviewing the boundary/repair/dev-server seam, landing only the smallest justified refactor, and re-proving the assembled workflow end to end.
**Demo:** After this: the assembled workflow is re-proved against the original stash/conflict and crash-recovery classes, existing SentinelX verification still passes, and the changed seams get an explicit code review/refactor pass.

## Must-Haves

- `R069`: `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` captures a seam-by-seam review of `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, and their focused proof surface, with explicit `refactor-now` vs `leave-alone` decisions.
- The duplicated local health contract is retired through one shared source (`app/health_contract.py`) consumed by both `app/routes/api.py` and `tools/dev_server.py`, without widening cleanup scope, weakening classifier ownership, or adding a second lifecycle surface.
- `R065`: focused workflow tests plus `make repair-runtime-state`, `make verify-runtime-boundary`, a live start → health → crash → status=crashed → restart → stop exercise, and `make verify` all pass after the last edit, with fresh evidence recorded in `.gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md`.
- **Threat surface:** keep repair mutation classifier-backed and fail-closed, keep `GET /api/health` and `dev-server status` secret-free/local-only, and keep `.planning/**` / `.bg-shell/**` outside automatic cleanup or lifecycle ownership.
- **Requirement impact:** advances `R065` and `R069`; re-verify boundary blocker detection, report-only `.planning/**`, exact health payload matching, crash/restart behavior, and the full `make verify` lane while keeping `D067`, `D068`, and `D069` aligned.

## Proof Level

- This slice proves: - This slice proves: final-assembly.
- Real runtime required: yes — repair/boundary commands must run against the live repo and the dev-server lifecycle must be exercised on an ephemeral localhost port.
- Human/UAT required: no.

## Integration Closure

- Upstream surfaces consumed: `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, `Makefile`, `README.md`, `docs/runtime-state-boundary.md`, and the focused workflow tests.
- New wiring introduced in this slice: a shared health-contract module plus closure artifacts (`S04-REVIEW.md`, `S04-LIFECYCLE-PROOF.json`, `S04-CLOSURE-PROOF.md`) that capture the review and final proof without creating a second operator surface.
- What remains before the milestone is truly usable end-to-end: nothing once the closure proof passes and the review artifact records any accepted residual debt.

## Verification

- Runtime signals: boundary issue codes, repair action summaries/quarantine destinations, `GET /api/health`, `.gsd/runtime/dev-server/status.json`, `restart_count`, and `last_failure_reason`.
- Inspection surfaces: `make repair-runtime-state`, `make verify-runtime-boundary`, `python3 tools/dev_server.py status --format json`, `make dev-server-status`, and the closure proof artifacts under `.gsd/milestones/M014/slices/S04/`.
- Failure visibility: blocker audit findings, blocked manual-review paths, malformed/secret-bearing health responses, stale/crashed child states, and repo verification regressions remain explicit and secret-free.
- Redaction constraints: do not emit provider keys, runtime log contents, or transient file contents in repair/status/proof output.

## Tasks

- [x] **T01: Review the workflow seam and capture closure findings** `est:0.5d`
  Load the `review` skill first and inspect the shipped workflow seam as code, not summary text. Re-read `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, and the highest-signal integration tests to identify only real drift or maintainability risks, then write a durable review artifact at `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`. Keep the review conservative: no style churn, no second path-policy table, no `.planning/**` auto-cleanup, and no second local-server workflow besides `make dev-server-*` / `tools/dev_server.py`.

## Steps

1. Load the `review` skill, inspect the boundary/repair/dev-server/API seam files, and cross-check them against the focused Git/lifecycle proof files instead of relying on prior slice summaries.
2. In `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`, record the seam invariants that must not change: classifier-owned repair policy, report-only `.planning/**`, thin Make wrappers, local-only dev-server ownership, and secret-free status/health output.
3. Record the minimal justified refactor to land in T02, explicitly deciding whether the duplicated health contract between `app/routes/api.py` and `tools/dev_server.py` should be retired now.
4. Record any accepted no-change areas so T02 stays seam-local and does not broaden scope beyond the review findings.

## Must-Haves

- [ ] `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` names the files inspected and separates `refactor-now` findings from `leave-alone` seams.
- [ ] The review preserves `tools/runtime_state_boundary.py` as the sole path-policy source and keeps `.planning/**` manual-review behavior explicit.
- [ ] The review makes an explicit decision about the shared health contract seam instead of leaving the duplication implicit.
- [ ] The artifact is precise enough for a fresh executor to perform T02 without reopening the slice research.

## Verification

- `test -s .gsd/milestones/M014/slices/S04/S04-REVIEW.md`
- `rg -n "refactor-now|leave-alone|health contract|classifier-owned" .gsd/milestones/M014/slices/S04/S04-REVIEW.md`
  - Files: `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, `tests/test_runtime_state_boundary_git.py`, `tests/test_runtime_state_repair_git.py`, `tests/test_dev_server_process.py`, `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`
  - Verify: test -s .gsd/milestones/M014/slices/S04/S04-REVIEW.md
rg -n "refactor-now|leave-alone|health contract|classifier-owned" .gsd/milestones/M014/slices/S04/S04-REVIEW.md

- [x] **T02: Retire the shared health-contract drift with a minimal seam-local refactor** `est:0.5d`
  Use the review artifact from T01 plus `verify-before-complete` before making any completion claim. Implement the smallest code change that removes the real drift found during review: introduce `app/health_contract.py` as the single source for the local `HEALTH_PATH` / `HEALTH_PAYLOAD`, update both `app/routes/api.py` and `tools/dev_server.py` to consume it, and keep the rest of the workflow seam unchanged unless T01 documented an equally small helper extraction in the same files. Do not widen repair scope, change `.planning/**` handling, or add another operator surface.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Shared health-contract module | Fail the focused tests and stop; do not fall back to duplicated literals | N/A | Treat missing/changed contract fields as a regression that must be fixed in code, not papered over in docs |
| `tools/dev_server.py` probe/status flow | Preserve current non-zero exit behavior and recorded failure reasons | Keep existing bounded startup/probe windows | Keep non-200, non-JSON, or secret-bearing responses classified as `malformed` |
| `/api/health` route in `app/routes/api.py` | Keep the route importable and 200/JSON-only | N/A | Reject any change that exposes provider/config state or stops matching the shared contract |

## Load Profile

- **Shared resources**: one localhost probe endpoint plus `.gsd/runtime/dev-server/**` status files.
- **Per-operation cost**: one tiny shared import and the existing bounded HTTP probe.
- **10x breakpoint**: producer/consumer drift that causes false unhealthy states or leaks new keys into health/status output.

## Negative Tests

- **Malformed inputs**: corrupted status JSON, invalid host/port values, and a health response with extra secret-bearing keys.
- **Error paths**: refused/timeout probes and mismatched health payloads.
- **Boundary conditions**: healthy exact-match payload, default localhost settings, and crash/stale state synthesis remaining unchanged after the refactor.

## Steps

1. Create `app/health_contract.py` with the shared local `HEALTH_PATH` and exact secret-free `HEALTH_PAYLOAD` expected by the supported dev loop.
2. Update `app/routes/api.py` and `tools/dev_server.py` to import the shared contract instead of maintaining duplicated literals, keeping CLI semantics, fail-closed probe behavior, and local-only host validation unchanged.
3. Apply only the additional seam-local helper extraction(s) explicitly justified in `S04-REVIEW.md`; if none were justified, keep the change set limited to the shared contract and related test adjustments.
4. Update `tests/test_api.py` and `tests/test_dev_server.py` so the shared contract, malformed-response handling, and existing status semantics remain pinned after the refactor.
5. Append the landed change and any intentionally deferred cleanup to `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`.

## Must-Haves

- [ ] `app/health_contract.py` becomes the single source of truth for the supported local health contract.
- [ ] `app/routes/api.py` and `tools/dev_server.py` stay behaviorally identical at the CLI/API boundary except for the removed duplication.
- [ ] Focused tests prove that extra keys or payload drift still surface as malformed/unhealthy rather than silently succeeding.
- [ ] The review artifact records exactly what changed and what was intentionally left alone.

## Verification

- `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
- `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_repair.py`
  - Files: `app/health_contract.py`, `app/routes/api.py`, `tools/dev_server.py`, `tests/test_api.py`, `tests/test_dev_server.py`, `.gsd/milestones/M014/slices/S04/S04-REVIEW.md`
  - Verify: python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py
python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_repair.py

- [x] **T03: Re-prove the assembled workflow and capture closure evidence** `est:0.75d`
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
  - Files: `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `Makefile`, `tests/test_runtime_state_boundary_git.py`, `tests/test_runtime_state_repair_git.py`, `tests/test_dev_server_process.py`, `.gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md`
  - Verify: python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py
make repair-runtime-state
make verify-runtime-boundary
make verify
test -s .gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json && test -s .gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md

## Files Likely Touched

- tools/runtime_state_boundary.py
- tools/runtime_state_repair.py
- tools/dev_server.py
- app/routes/api.py
- tests/test_runtime_state_boundary_git.py
- tests/test_runtime_state_repair_git.py
- tests/test_dev_server_process.py
- .gsd/milestones/M014/slices/S04/S04-REVIEW.md
- app/health_contract.py
- tests/test_api.py
- tests/test_dev_server.py
- Makefile
- .gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md
