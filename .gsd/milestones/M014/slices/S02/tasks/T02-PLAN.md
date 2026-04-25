---
estimated_steps: 4
estimated_files: 6
skills_used:
  - best-practices
  - test
  - verify-before-complete
---

# T02: Prove quarantine repair flows and expose `make repair-runtime-state`

**Slice:** S02 — Recovery tooling and safe cleanup
**Milestone:** M014

## Description

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

## Verification

- `python3 -m pytest -q tests/test_runtime_state_repair_git.py`
- `make repair-runtime-state`
- `make verify-runtime-boundary`

## Observability Impact

- Signals added/changed: repair runs now report quarantine destinations, blocked findings, and final no-op/actionable counts.
- How a future agent inspects this: `make repair-runtime-state`, `python3 tools/runtime_state_repair.py --format json`, and the quarantine tree under `.gsd/runtime/repair-quarantine/`.
- Failure state exposed: follow-up audit failures, Git/quarantine errors, and blocked manual-review findings remain visible.

## Inputs

- `tools/runtime_state_repair.py` — the classifier-backed repair engine from T01.
- `tools/runtime_state_boundary.py` — authoritative issue codes and audit behavior that the supported command must preserve.
- `tests/test_runtime_state_repair.py` — T01 unit coverage to extend without regressing action-selection behavior.
- `tests/test_runtime_state_boundary_git.py` — temp-repo Git fixture patterns to reuse for repair integration proof.
- `Makefile` — repo-native command surface where `make repair-runtime-state` must live.
- `README.md` — top-level operator guidance that should advertise the supported repair command.
- `docs/runtime-state-boundary.md` — boundary contract doc to extend with the repair action table and non-goals.

## Expected Output

- `tools/runtime_state_repair.py` — now supporting both deindex and quarantine actions.
- `tests/test_runtime_state_repair_git.py` — temp-repo integration proof for tracked repair, quarantine, and manual-review safety.
- `Makefile` — supported `make repair-runtime-state` entrypoint.
- `README.md` — contributor-facing repair guidance.
- `docs/runtime-state-boundary.md` — detailed repair contract, quarantine location, and explicit non-goals.
