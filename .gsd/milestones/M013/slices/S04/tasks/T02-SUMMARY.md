---
id: T02
parent: S04
milestone: M013
key_files:
  - tools/optimization_audit.py
  - tests/test_optimization_audit.py
  - .gsd/milestones/M013/M013-AUDIT.md
key_decisions:
  - Recorded the shipped frontend/render work in baseline stance and seam notes, but kept only the broader flush-wide dashboard recount/reorder work in the ranked deferred finding.
  - Kept the audit artifact DB/source-of-truth contract intact by regenerating `.gsd/milestones/M013/M013-AUDIT.md` from `tools/optimization_audit.py` instead of editing markdown directly.
duration: 
verification_result: passed
completed_at: 2026-04-25T07:09:10.649Z
blocker_discovered: false
---

# T02: Updated the M013 audit runner and pinned tests so the frontend/render entry records the shipped coordinator-local DOM-handle cache while deferring only the remaining flush-wide recount/reorder work.

**Updated the M013 audit runner and pinned tests so the frontend/render entry records the shipped coordinator-local DOM-handle cache while deferring only the remaining flush-wide recount/reorder work.**

## What Happened

Updated `tools/optimization_audit.py` so the baseline artifact stops describing coordinator-local handle caching as queued work. The baseline stance now calls out the shipped frontend/render change explicitly, the frontend/render ranked finding now points only at the remaining deferred flush-wide `updateDashboardCounts()`/`sortCardsBySeverity()` follow-up, the seam note reflects the new cached-handle reality, and the guardrail coverage text stays aligned with that narrower deferred work. I then updated `tests/test_optimization_audit.py` to pin the new shipped-vs-deferred wording, reject regression back to the pre-S04 `Cache IOC card/slot handles...` language, and keep the existing request/status and persistence keep-decision assertions intact. Finally, I regenerated `.gsd/milestones/M013/M013-AUDIT.md` from `tools/optimization_audit.py` so the checked-in artifact matches the runner constants instead of being hand-edited.

## Verification

Ran the focused audit contract suite after the last code change with `pytest tests/test_optimization_audit.py -q`, which passed 6/6 tests. Then regenerated the milestone audit with `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` and read the resulting artifact to confirm it now records the shipped frontend/render cache, keeps the request/status and persistence rows unchanged, and leaves only the flush-wide frontend follow-up deferred. The regeneration emitted the runner's expected synthetic RateLimitBeta 429 diagnostic to stderr during internal capture, but exited 0 and produced the updated artifact successfully.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_optimization_audit.py -q` | 0 | ✅ pass | 654ms |
| 2 | `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` | 0 | ✅ pass | 151ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M013/M013-AUDIT.md`
