---
id: S02
parent: M014
milestone: M014
provides:
  - A single supported repo-native repair entrypoint via `make repair-runtime-state` backed by `tools/runtime_state_repair.py`.
  - Conservative classifier-backed cleanup behavior: tracked transient files are deindexed, unignored transient files are quarantined, and manual-review / ambiguous paths remain report-only.
  - Temp-repo Git proof that the repair flow resolves the observed stash/conflict class without mutating durable milestone artifacts.
requires:
  - slice: S01
    provides: Consumed the durable/transient classifier, blocker-focused audit semantics, and temp-repo Git boundary fixture patterns so repair behavior stayed owned by one checked-in policy source.
affects:
  - S04
key_files:
  - tools/runtime_state_repair.py
  - tests/test_runtime_state_repair.py
  - tests/test_runtime_state_repair_git.py
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
key_decisions:
  - Kept repair action selection keyed entirely off `runtime_state_boundary` issue codes so no second cleanup rule table appears.
  - Limited automatic mutation to classifier-approved transient classes only: `tracked-transient` deindexes from Git, `unignored-transient` quarantines under `.gsd/runtime/repair-quarantine/`, and `manual-review-path` remains blocked/report-only.
  - Made `make repair-runtime-state` the single supported operator loop by running the mutating repair pass first, then immediately re-running the inspection-only boundary audit.
patterns_established:
  - One checked-in classifier owns both detection and cleanup policy; the repair tool is a thin mutating companion, not a parallel policy engine.
  - Safe repo repair prefers reversible or non-destructive actions first: preserve working-tree contents on deindex, quarantine rather than delete unignored runtime debris, and fail closed on ambiguous paths.
  - Temp-repo Git fixtures are the proof surface for repair semantics and convergence; summary-level claims should be backed by real repo behavior, not mocked file moves.
observability_surfaces:
  - `make repair-runtime-state` as the supported repair/recovery entrypoint.
  - `python3 tools/runtime_state_repair.py --format json` for machine-readable action/count reporting.
  - `make verify-runtime-boundary` as the post-repair blocker-focused audit.
  - Focused repair tests under `tests/test_runtime_state_repair.py` and `tests/test_runtime_state_repair_git.py`.
drill_down_paths:
  - .gsd/milestones/M014/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-25T11:22:39.929Z
blocker_discovered: false
---

# S02: Recovery tooling and safe cleanup

**S02 shipped the supported runtime-state repair path: a classifier-backed `tools/runtime_state_repair.py` / `make repair-runtime-state` loop that safely deindexes tracked transient files, quarantines unignored transient debris, leaves durable or ambiguous paths report-only, and proves the stash/conflict recovery path in temp-repo Git fixtures.**

## What Happened

S02 turned the boundary contract from S01 into an actionable recovery surface without creating a second policy engine. `tools/runtime_state_repair.py` reuses the classifier and issue-code model from `tools/runtime_state_boundary.py`, validates requested roots against the supported boundary, and plans cleanup actions directly from those issue codes instead of inventing new path rules. That kept S02 explicitly downstream of S01: the same durable/transient/manual-review decisions now drive both blocker detection and repo-native repair behavior.

The slice landed the conservative cleanup behavior needed for the original local-workflow problem. `tracked-transient` findings are repaired by `git rm --cached -- <path>` so the working-tree file stays intact while Git stops tracking the machine-owned runtime file. `unignored-transient` findings are moved into `.gsd/runtime/repair-quarantine/<timestamp>/...` so the operator gets a reversible cleanup path instead of silent deletion. `manual-review-path`, `conflicting-rule-match`, and `unknown-root` findings remain blocked/report-only with explicit counts and per-path action reporting in both text and JSON formats. The repo-native operator surface was then standardized in `Makefile` as `make repair-runtime-state`, which runs the mutating repair pass and immediately follows it with the blocker-focused boundary audit so the operator sees both what changed and what still requires manual review.

The proof surface closed the loop between S01 and S04. `tests/test_runtime_state_repair.py` covers planning, dry-run/apply semantics, safe no-op behavior, collision handling, and fail-closed blocked classes. `tests/test_runtime_state_repair_git.py` proves real temp-repo Git behavior for tracked transient deindexing, unignored transient quarantine, manual-review safety, and repeated-run convergence to a clean no-op. Those artifacts are the contract S04 later consumes when it re-proves that `make repair-runtime-state` stays conservative on the final milestone state while composing with the hardened boundary verifier and supported dev-server loop.

## Verification

Fresh slice-close verification passed from the landed code. `python3 -m pytest -q tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py` passed with the repair contract and temp-repo Git coverage in place. `make repair-runtime-state` exited 0 on the live repo, reported zero actionable repairs, and preserved the visible `.planning/**` backlog as blocked/manual-review output only. `make verify-runtime-boundary` exited 0 and confirmed that the repair path still composed with the S01 blocker-focused audit contract. The machine-readable operator surface also passed via `python3 tools/runtime_state_repair.py --format json`, which returned the expected summary/action shape without exposing transient file contents.

## Requirements Advanced

- R063 — Added the supported repo-native repair/recovery entrypoint and documented it as the canonical operator path.
- R061 — Extended the stash/conflict retirement story from prevention/surfacing into conservative supported recovery for tracked and unignored transient runtime-state.

## Requirements Validated

- R063 — `make repair-runtime-state`, JSON reporting, and temp-repo Git repair coverage proved the supported repair surface exists and behaves deterministically.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

- **Health signal:** `make repair-runtime-state` exits 0 with explicit summary counts when only non-actionable/manual-review findings remain.
- **Failure signal:** JSON/text output surfaces blocked, failed, deindex, quarantine, and no-op counts plus per-path actions without printing runtime file contents.
- **Recovery:** tracked transient blockers are deindexed conservatively, unignored transient files are quarantined under `.gsd/runtime/repair-quarantine/`, and ambiguous or durable paths are stopped for manual review.
- **Monitoring gaps:** the tool intentionally does not auto-resolve `manual-review-path` backlog under `.planning/**`; that remains a visible non-goal, not a silent cleanup target.

## Deviations

None.

## Known Limitations

Legacy `.planning/**` findings remain visible in repair output as blocked `manual-review-path` entries. This is intentional fail-closed behavior: the supported repair path does not mutate durable or ambiguous planning state.

## Follow-ups

S04 should keep treating `tools/runtime_state_boundary.py` as the sole policy source, re-prove `make repair-runtime-state` on final milestone state, and verify that the repair loop composes cleanly with the supported dev-server lifecycle.

## Files Created/Modified

- `tools/runtime_state_repair.py` — Implemented the classifier-backed mutating repair CLI with deindex, quarantine, dry-run/apply, and structured reporting.
- `tests/test_runtime_state_repair.py` — Covered action planning, dry-run/apply semantics, collision handling, and safe blocked/manual-review behavior.
- `tests/test_runtime_state_repair_git.py` — Added temp-repo Git proof for tracked transient deindexing, unignored transient quarantine, manual-review safety, and convergence to no-op.
- `Makefile` — Added `make repair-runtime-state` as the supported repo-native repair entrypoint.
- `README.md` — Documented the supported repair flow for operators.
- `docs/runtime-state-boundary.md` — Documented the repair action table, quarantine contract, and manual-review non-goal.
