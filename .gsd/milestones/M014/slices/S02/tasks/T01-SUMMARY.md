---
id: T01
parent: S02
milestone: M014
key_files:
  - tools/runtime_state_repair.py
  - tests/test_runtime_state_repair.py
  - tests/test_runtime_state_repair_git.py
key_decisions:
  - Kept repair action selection strictly keyed off `runtime_state_boundary` issue codes so no second cleanup rule table appears.
  - Limited T01 mutation to `tracked-transient` via `git rm --cached -- <path>` and left all other finding classes fail-closed as blocked/report-only.
duration: 
verification_result: mixed
completed_at: 2026-04-25T11:03:46.738Z
blocker_discovered: false
---

# T01: Added the classifier-backed runtime_state_repair CLI with tracked-transient deindexing, dry-run/text+JSON reporting, and fail-closed blocker handling.

**Added the classifier-backed runtime_state_repair CLI with tracked-transient deindexing, dry-run/text+JSON reporting, and fail-closed blocker handling.**

## What Happened

Implemented `tools/runtime_state_repair.py` as the only mutating repair entrypoint for this slice stage, reusing `audit_paths`, repo-root/path normalization, default audit roots, and issue-code constants from `tools/runtime_state_boundary.py` instead of copying any path rules. The repair tool now validates requested targets against supported boundary roots, audits with the existing classifier, maps findings through a conservative action table, and only mutates `tracked-transient` findings via `git rm --cached -- <path>` while preserving working-tree files. `unignored-transient`, `manual-review-path`, `conflicting-rule-match`, and `unknown-root` findings remain explicit blocked/report-only actions with machine-readable JSON and text output that surface mode, counts, per-path actions, and Git stderr/detail strings without printing file contents. Added `tests/test_runtime_state_repair.py` to cover action planning, dry-run reporting, tracked-transient deindex behavior in a temp repo, unsupported-root rejection, and clean no-op runs. To satisfy the first-task slice test-path requirement without pretending T02 integration coverage exists, I also created a skipped placeholder `tests/test_runtime_state_repair_git.py` that T02 will replace with real temp-repo Git/quarantine coverage. No boundary rule changes were needed in `tools/runtime_state_boundary.py`; the existing exports were sufficient.

## Verification

Fresh post-change verification passed for the T01 contract: `python3 -m pytest -q tests/test_runtime_state_repair.py` passed (5/5), and `python3 tools/runtime_state_repair.py --help` confirmed the supported CLI surface (`--repo-root`, `--format`, `--dry-run`, optional boundary paths). The broader slice-in-progress lane also behaved correctly for this intermediate task: `python3 -m pytest -q tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py` passed with the new placeholder file skipped (5 passed, 1 skipped), and `make verify-runtime-boundary` still passed, showing the new work did not regress the inspection-only boundary tool. Direct observability verification also succeeded: `python3 tools/runtime_state_repair.py --dry-run --format json .planning/STATE.md` exited non-zero with a blocked `manual-review-path` action and explicit counts/detail, which is the intended fail-closed behavior. The only failing slice-level check was `make repair-runtime-state`, which still exits with “No rule to make target 'repair-runtime-state'” because that repo-native wrapper is owned by T02, not this task.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_runtime_state_repair.py` | 0 | ✅ pass | 719ms |
| 2 | `python3 tools/runtime_state_repair.py --help` | 0 | ✅ pass | 30ms |
| 3 | `python3 -m pytest -q tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py` | 0 | ✅ pass | 459ms |
| 4 | `make verify-runtime-boundary` | 0 | ✅ pass | 1027ms |
| 5 | `make repair-runtime-state` | 2 | ❌ fail | 1ms |
| 6 | `python3 tools/runtime_state_repair.py --dry-run --format json .planning/STATE.md` | 1 | ✅ pass | 31ms |

## Deviations

Minor planned-scope deviation: I added a skipped placeholder `tests/test_runtime_state_repair_git.py` early so the slice-level integration test path now exists and can be filled in by T02 without destabilizing the current repo. No other deviations.

## Known Issues

`make repair-runtime-state` is still missing and must be added in T02. `unignored-transient` findings are intentionally blocked/report-only until T02 adds quarantine support under `.gsd/runtime/repair-quarantine/`.

## Files Created/Modified

- `tools/runtime_state_repair.py`
- `tests/test_runtime_state_repair.py`
- `tests/test_runtime_state_repair_git.py`
