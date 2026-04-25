---
id: T02
parent: S01
milestone: M014
key_files:
  - .gitignore
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
  - tests/test_runtime_state_boundary.py
  - .bg-shell/manifest.json
  - .gsd/audit/events.jsonl
  - .gsd/notifications.jsonl
key_decisions:
  - Used the classifier audit output as the sole source of truth for deindexing instead of hand-maintaining a narrower path list.
  - Kept the supported verifier failing on manual-review legacy paths so the backlog stays explicit while transient blocker classes are forced to zero.
duration: 
verification_result: mixed
completed_at: 2026-04-25T10:02:40.403Z
blocker_discovered: false
---

# T02: Aligned repo ignore/index state with the runtime-boundary classifier and added a repo-native verifier target.

**Aligned repo ignore/index state with the runtime-boundary classifier and added a repo-native verifier target.**

## What Happened

Updated `.gitignore` so the classifier-owned transient runtime surfaces are actually ignored in repo behavior, including `.gsd/audit/**`, `.gsd/exec/**`, `.gsd/graphs/**`, `.gsd/safety/**`, `.gsd/completed-units-*.json`, `.gsd/event-log.jsonl`, `.gsd/notifications.jsonl`, and `.gsd/state-manifest.json`, while leaving durable milestone artifacts and canonical ledgers untouched. Added `make verify-runtime-boundary` to `Makefile` as the supported repo-native boundary command, documented the lane in `README.md` and `docs/runtime-state-boundary.md`, and expanded the focused pytest coverage to cover the newly owned transient classes plus the ignored-transient negative case. After the policy/documentation changes, I removed every live `tracked-transient` finding from the Git index with `git rm --cached -- ...` so working-tree runtime files remain locally available but no longer block stash/pop or checkout flows; this included the planned example files plus stale tracked runtime artifacts under `.gsd/exec/**`, `.gsd/graphs/graph.json`, `.gsd/safety/**`, and `.bg-shell/manifest.json`. A post-change audit now reports only the intentionally fail-closed `.planning/**` manual-review backlog and no longer reports any tracked-transient or unignored-transient findings.

## Verification

Fresh verification after the last code edit: `python3 -m pytest -q tests/test_runtime_state_boundary.py` passed with 6 tests. `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues` still exits non-zero, but now only because the repo intentionally retains 237 `.planning/**` `manual-review-path` findings; the transient blocker classes are gone. `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json .gsd/completed-units-M001.json .gsd/notifications.jsonl` confirmed the representative transient paths are ignored by `.gitignore`, and `test -z "$(git ls-files .gsd/audit/events.jsonl .gsd/notifications.jsonl .bg-shell/manifest.json)"` confirmed the known blocker files are no longer tracked. `make verify-runtime-boundary` exercised the supported command surface: pytest passed, then the audit failed exactly on the remaining manual-review backlog, which is the expected visibility behavior for this slice stage.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_runtime_state_boundary.py` | 0 | ✅ pass | 342ms |
| 2 | `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues` | 1 | ❌ fail (expected: reports only 237 manual-review `.planning/**` findings; no tracked/unignored transient findings remain) | 109ms |
| 3 | `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json .gsd/completed-units-M001.json .gsd/notifications.jsonl` | 0 | ✅ pass | 1ms |
| 4 | `test -z "$(git ls-files .gsd/audit/events.jsonl .gsd/notifications.jsonl .bg-shell/manifest.json)"` | 0 | ✅ pass | 1ms |
| 5 | `make verify-runtime-boundary` | 2 | ❌ fail (expected wrapper failure: pytest passes, then audit exits on remaining manual-review backlog) | 453ms |

## Deviations

Expanded the deindex step from the task plan’s exemplar files to the full live `tracked-transient` set reported by the classifier so the repo-native boundary command would not leave stale `.gsd/exec/**`, `.gsd/graphs/**`, or `.gsd/safety/**` blockers behind.

## Known Issues

`make verify-runtime-boundary` still exits non-zero because `.planning/**` remains intentionally classified as `manual-review`. That is expected for S01/T02 and should stay visible until a later slice decides whether those legacy paths are migrated, retained, or explicitly ignored.

## Files Created/Modified

- `.gitignore`
- `Makefile`
- `README.md`
- `docs/runtime-state-boundary.md`
- `tests/test_runtime_state_boundary.py`
- `.bg-shell/manifest.json`
- `.gsd/audit/events.jsonl`
- `.gsd/notifications.jsonl`
