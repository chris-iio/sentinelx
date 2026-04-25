---
id: T02
parent: S02
milestone: M014
key_files:
  - tools/runtime_state_repair.py
  - tests/test_runtime_state_repair.py
  - tests/test_runtime_state_repair_git.py
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
key_decisions:
  - Extended the classifier-keyed repair action table with `unignored-transient -> quarantine` under `.gsd/runtime/repair-quarantine/<timestamp>/...` instead of adding a second cleanup rule set.
  - Made apply-mode repair succeed when only `.planning/**` manual-review findings remain so `make repair-runtime-state` can be the supported operator loop while conflicting/unknown blocker classes still fail closed via the follow-up audit.
duration: 
verification_result: passed
completed_at: 2026-04-25T11:13:10.601Z
blocker_discovered: false
---

# T02: Added quarantine-backed runtime-state repair coverage and the `make repair-runtime-state` operator loop.

**Added quarantine-backed runtime-state repair coverage and the `make repair-runtime-state` operator loop.**

## What Happened

Implemented the remaining supported repair path in `tools/runtime_state_repair.py` by extending the existing classifier-backed action table to quarantine `unignored-transient` findings into `.gsd/runtime/repair-quarantine/<timestamp>/<original-path>` while preserving relative path context inside the already ignored runtime subtree. The repair report now exposes per-action destinations in text/JSON output, counts deindex/quarantine/blocked/failed/no-op totals, validates that quarantine targets are actually ignored before moving files, and fails closed on destination collisions or filesystem/git errors without printing runtime file contents. I updated `tests/test_runtime_state_repair.py` to cover the new planner/action semantics, safe manual-review-only apply behavior, collision failure handling, and no-op reporting, and I replaced the placeholder `tests/test_runtime_state_repair_git.py` with temp-repo Git proofs for tracked deindexing, unignored-transient quarantine, manual-review safety, and repeated-run convergence to a clean no-op. I then added `make repair-runtime-state` to `Makefile` as the one supported operator entrypoint that runs the mutating repair CLI first and immediately re-runs the inspection-only boundary audit. Finally, I updated `README.md` and `docs/runtime-state-boundary.md` to document the repair action table, the quarantine location and contract, the supported `make repair-runtime-state` flow, and the explicit non-goals around `.planning/**` and blanket `.gsd/**` cleanup.

## Verification

Fresh post-change verification passed. `python3 -m pytest -q tests/test_runtime_state_repair_git.py` passed with the new temp-repo integration coverage (3 passed). `make repair-runtime-state` exited 0 on the live repo, reported zero actionable repairs (`deindex_count=0`, `quarantine_count=0`, `failed_count=0`), and still surfaced the existing `.planning/**` backlog as 237 visible `manual-review-path` findings without mutating it. `make verify-runtime-boundary` exited 0, kept both boundary pytest lanes green, and the live audit remained limited to the same manual-review backlog because there were no `tracked-transient`, `unignored-transient`, `conflicting-rule-match`, or `unknown-root` findings. I also verified the direct JSON observability surface with `python3 tools/runtime_state_repair.py --format json`, which returned the expected summary counts plus an explicit blocked action shape for a `.planning/**` path.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_runtime_state_repair_git.py` | 0 | ✅ pass | 487ms |
| 2 | `make repair-runtime-state` | 0 | ✅ pass | 233ms |
| 3 | `make verify-runtime-boundary` | 0 | ✅ pass | 948ms |
| 4 | `python3 tools/runtime_state_repair.py --format json` | 0 | ✅ pass | 130ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tools/runtime_state_repair.py`
- `tests/test_runtime_state_repair.py`
- `tests/test_runtime_state_repair_git.py`
- `Makefile`
- `README.md`
- `docs/runtime-state-boundary.md`
