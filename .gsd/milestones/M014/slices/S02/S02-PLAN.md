# S02: Recovery tooling and safe cleanup

**Goal:** Ship the supported repair surface that turns the classifier-backed boundary into a safe, repo-native recovery loop for transient runtime-state and git-workflow blockers.
**Demo:** After this: there is one supported repo-native recovery entrypoint that detects and repairs transient-state/git-workflow issues without silently touching durable milestone artifacts.

## Must-Haves

- `tools/runtime_state_repair.py` is the only mutating repair CLI, reusing `tools/runtime_state_boundary.py` helpers and never mutating `.planning/**`, conflicting rules, or unknown roots.
- `tests/test_runtime_state_repair.py` and `tests/test_runtime_state_repair_git.py` prove tracked-transient deindex, unignored-transient quarantine, blocked manual-review safety, and clean no-op/idempotent behavior.
- `make repair-runtime-state` exists as the supported repo-native recovery entrypoint and `make verify-runtime-boundary` still passes after the repair path lands.
- `README.md` and `docs/runtime-state-boundary.md` document the action table, quarantine location, and explicit non-goals for blanket cleanup.

## Proof Level

- This slice proves: - This slice proves: contract + integration proof plus a live-repo operational no-op proof for the supported recovery entrypoint.
- Real runtime required: yes — the proof must exercise real Git behavior in temp repos and the live repo command.
- Human/UAT required: no.

## Integration Closure

- Upstream surfaces consumed: `tools/runtime_state_boundary.py`, `.gitignore`, Git index/ignore semantics, and the S01 temp-repo boundary fixtures.
- New wiring introduced in this slice: `tools/runtime_state_repair.py`, repair pytest coverage, `make repair-runtime-state`, and the repair/docs contract in `README.md` plus `docs/runtime-state-boundary.md`.
- What remains before the milestone is truly usable end-to-end: S03 must compose the supported start/restart flow around this repair surface without inventing new boundary rules.

## Verification

- Runtime signals: repair summaries report deindexed, quarantined, blocked, and no-op counts with per-path actions.
- Inspection surfaces: `python3 tools/runtime_state_repair.py --format text|json`, `make repair-runtime-state`, and `.gsd/runtime/repair-quarantine/`.
- Failure visibility: blocked issue codes, Git stderr, quarantine destinations, and follow-up audit failures remain visible without dumping file contents.
- Redaction constraints: diagnostics report path metadata only; no runtime file contents should be printed.

## Tasks

- [x] **T01: Implement classifier-backed repair CLI and safe action table** `est:0.5d`
  Create the mutating repair surface on top of S01's inspection-only boundary tool. This task closes the highest-risk seam first: action selection must stay classifier-owned and conservative before any repo-native wrapper or live-repo usage exists.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Shared helpers/constants from `tools/runtime_state_boundary.py` | Stop and expose the missing seam instead of copying glob rules into a second tool | N/A | Treat ambiguous classifications as blocked/manual-review, not as permission to mutate |
| Local Git CLI for tracked-transient repair | Fail loudly and preserve the working tree if `git rm --cached -- <path>` does not succeed | Keep operations local and bounded; no long-running commands expected | Report stderr and leave the finding unresolved rather than hiding the error |
| CLI/report contract for later automation | Exit non-zero on actionable failures and emit machine-readable output for later wrappers/docs | N/A | Reject unsupported flags/paths with clear usage text |

## Load Profile

- **Shared resources**: Git index state plus the classifier-owned boundary rule table.
- **Per-operation cost**: one audit plus bounded per-finding action selection; no directory-wide recursion or blanket deletes.
- **10x breakpoint**: accidental re-derivation of rules or broad filesystem mutation outside the audited findings.

## Negative Tests

- **Malformed inputs**: unsupported roots, empty path lists, dry-run invocations, and repeated runs with nothing actionable.
- **Error paths**: `git rm --cached` failures, conflicting/manual-review findings, and unknown-root findings that must stay blocked.
- **Boundary conditions**: tracked transient files that are already ignored, findings that mix actionable and blocked paths, and a clean repo with zero actionable repairs.

## Steps

1. Add `tools/runtime_state_repair.py` that imports `audit_paths`, normalization helpers, and issue-code constants from `tools/runtime_state_boundary.py` and maps each finding to an explicit action.
2. Implement conservative CLI/report behavior with `--repo-root`, `--format`, and `--dry-run`, keeping `tracked-transient` as the only mutating action in this task.
3. Add focused pytest coverage in `tests/test_runtime_state_repair.py` for action planning, dry-run summaries, tracked-transient deindex behavior, and report-only handling of manual-review/conflicting/unknown findings.
4. Expose only the minimal shared helper seams needed from `tools/runtime_state_boundary.py`; keep `audit` itself inspection-only.

## Must-Haves

- [ ] Only classifier findings drive repair actions; no second rule table appears.
- [ ] `tracked-transient` repair uses `git rm --cached -- <path>` and preserves working-tree contents.
- [ ] `manual-review-path`, `conflicting-rule-match`, and `unknown-root` remain report-only blockers.
- [ ] The CLI supports dry-run plus text/JSON output for later wiring and diagnostics.
  - Files: `tools/runtime_state_repair.py`, `tests/test_runtime_state_repair.py`, `tools/runtime_state_boundary.py`, `tests/test_runtime_state_boundary.py`
  - Verify: python3 -m pytest -q tests/test_runtime_state_repair.py && python3 tools/runtime_state_repair.py --help

- [x] **T02: Prove quarantine repair flows and expose `make repair-runtime-state`** `est:0.75d`
  Extend the repair surface to the remaining actionable transient case, then wire and document the single supported operator entrypoint. This task closes R063 by proving the repair path in temp repos and by making the live-repo contract explicit.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| T01 repair CLI plus S01 boundary audit seam | Stop and repair the shared action logic before adding Make/docs wiring; do not fork classifications in tests or `Makefile` | N/A | Treat mismatched issue codes or action summaries as blockers |
| Temp-repo Git fixtures for repair behavior | Fail the test and preserve fixture evidence if quarantine/deindex actions do not clear the intended findings | Keep fixtures small and local so pytest stays fast | Capture command output and quarantine destinations in assertions |
| Supported repo-native command/docs surface | Keep one obvious recovery entrypoint; if docs and command drift, fix the code or docs before closing the task | N/A | Report unsupported actions clearly instead of widening cleanup scope |

## Load Profile

- **Shared resources**: temp Git repos, the ignored `.gsd/runtime/repair-quarantine/` subtree, and the repo-native operator command.
- **Per-operation cost**: one audit plus bounded per-file quarantine/deindex actions; no recursive deletes or broad worktree pruning.
- **10x breakpoint**: quarantine copying entire directories or repeated runs that keep mutating already-clean repos instead of converging to a no-op.

## Negative Tests

- **Malformed inputs**: unignored transient files under `.gsd/**`, repeated repair runs, and repos that contain only manual-review `.planning/**` findings.
- **Error paths**: quarantine destination collisions, blocked/manual-review findings, and repair runs that must exit non-zero when actionable mutations fail.
- **Boundary conditions**: tracked transient blockers become untracked without losing working-tree content, unignored transient files move under `.gsd/runtime/repair-quarantine/<timestamp>/...`, and `.planning/**` files remain untouched.

## Steps

1. Add `unignored-transient` quarantine behavior that moves files into `.gsd/runtime/repair-quarantine/<timestamp>/...` while preserving relative path context inside an already ignored subtree.
2. Add `tests/test_runtime_state_repair_git.py` covering tracked-transient repair, unignored-transient quarantine, manual-review safety, and clean repeated/no-action runs.
3. Wire `make repair-runtime-state` in `Makefile` and keep `make verify-runtime-boundary` green without changing `tools/runtime_state_boundary.py`'s inspection-only contract.
4. Update `README.md` and `docs/runtime-state-boundary.md` with the action table, quarantine location, supported command, and explicit non-goals for `.planning/**` or blanket `.gsd` cleanup.

## Must-Haves

- [ ] `unignored-transient` files move into ignored quarantine and disappear from follow-up audit results.
- [ ] The live repo command is safe when no actionable findings exist and still surfaces blocked/manual-review paths.
- [ ] Temp-repo tests prove tracked-transient repair, unignored quarantine, and manual-review safety.
- [ ] Docs explain exactly what `make repair-runtime-state` will and will not touch.
  - Files: `tools/runtime_state_repair.py`, `tests/test_runtime_state_repair_git.py`, `tests/test_runtime_state_repair.py`, `Makefile`, `README.md`, `docs/runtime-state-boundary.md`
  - Verify: python3 -m pytest -q tests/test_runtime_state_repair_git.py && make repair-runtime-state && make verify-runtime-boundary

## Files Likely Touched

- tools/runtime_state_repair.py
- tests/test_runtime_state_repair.py
- tools/runtime_state_boundary.py
- tests/test_runtime_state_boundary.py
- tests/test_runtime_state_repair_git.py
- Makefile
- README.md
- docs/runtime-state-boundary.md
