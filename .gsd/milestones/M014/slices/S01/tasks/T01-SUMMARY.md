---
id: T01
parent: S01
milestone: M014
key_files:
  - tools/runtime_state_boundary.py
  - tests/test_runtime_state_boundary.py
  - docs/runtime-state-boundary.md
key_decisions:
  - Treat `.planning/**` as fail-closed `manual-review` rather than auto-promoting it into the transient set.
  - Handle `continue.md` and `*-CONTINUE.md` as high-priority transient exceptions inside otherwise durable `.gsd/milestones/**` trees.
  - Pair `git ls-files` with `git check-ignore` in the audit path so tracked transient blockers remain visible.
duration: 
verification_result: mixed
completed_at: 2026-04-25T08:46:31.548Z
blocker_discovered: false
---

# T01: Added a checked-in runtime-state boundary classifier with audit CLI, focused pytest coverage, and handoff docs.

**Added a checked-in runtime-state boundary classifier with audit CLI, focused pytest coverage, and handoff docs.**

## What Happened

Implemented `tools/runtime_state_boundary.py` as the authoritative repo-boundary seam for `durable`, `transient`, and `manual-review` path classes. The classifier normalizes relative and absolute paths against the repo root, fails closed on empty/out-of-repo inputs, and resolves conflicting highest-priority rules to `manual-review` with an explicit `conflicting-rule-match` issue code. The `audit` subcommand walks `.gsd`, `.planning`, and `.bg-shell`, inspects Git state without mutating the repo, and emits the named findings later slices need: `tracked-transient`, `unignored-transient`, and `manual-review-path`. Added focused pytest coverage for representative classifications, malformed inputs, conflicting rules, and audit behavior in a temp repo. Wrote `docs/runtime-state-boundary.md` to document the supported classes, the non-goal of blanket `.planning/**` cleanup, and the S02/S03 handoff. During execution I refined the durable allowlist to include checked-in `.gsd/PROJECT.md` and `.gsd/reports/**` after the first real-repo audit surfaced them as noisy unknowns; the conservative fail-closed handling for `.planning/**` remained unchanged.

## Verification

Fresh verification after the last code edit: `pytest tests/test_runtime_state_boundary.py -q` passed (6 tests). `python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json` returned the expected durable/transient/manual-review classes. `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues` exited 1 by design and surfaced the repo’s current blockers explicitly (237 manual-review legacy `.planning` paths, 14 tracked transient blockers, 23 unignored transient paths), which is the intended T01 observability outcome before S02 changes ignore/index state. Slice inspection surfaces also ran: `git status --short --ignored .gsd .planning .bg-shell` showed the current ignored runtime areas, `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json` still exited 1 because those ignore changes are owned by S02, and `python3 -m py_compile tools/runtime_state_boundary.py tests/test_runtime_state_boundary.py` passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_runtime_state_boundary.py -q` | 0 | ✅ pass | 306ms |
| 2 | `python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json` | 0 | ✅ pass | 26ms |
| 3 | `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues` | 1 | ❌ fail (expected pre-S02; surfaced tracked/unignored/manual-review findings) | 103ms |
| 4 | `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json` | 1 | ❌ fail (expected pre-S02; target transient paths are not ignored yet) | 1ms |
| 5 | `git status --short --ignored .gsd .planning .bg-shell` | 0 | ✅ pass | 7ms |
| 6 | `python3 -m py_compile tools/runtime_state_boundary.py tests/test_runtime_state_boundary.py` | 0 | ✅ pass | 15ms |

## Deviations

Added durable classifier rules for `.gsd/PROJECT.md` and `.gsd/reports/**` after the first repo audit showed they were checked-in evidence artifacts, not transient/runtime surfaces. This was a local-reality correction to the allowlist, not a scope change.

## Known Issues

The repo still contains explicit boundary findings that this task intentionally surfaced rather than repaired: 14 tracked-transient blockers, 23 unignored transient paths, and 237 `.planning/**` manual-review findings. `git check-ignore -v` also still returns no matches for the representative transient paths because S02 has not yet aligned `.gitignore` and the index with the new classifier.

## Files Created/Modified

- `tools/runtime_state_boundary.py`
- `tests/test_runtime_state_boundary.py`
- `docs/runtime-state-boundary.md`
