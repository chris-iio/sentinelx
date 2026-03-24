---
id: T01
parent: S03
milestone: M004
provides:
  - Dead TS exports/functions removed from verdict-compute.ts and row-factory.ts
  - Dead CSS rules removed from input.css (.alert-success, .alert-warning, .consensus-badge family)
key_files:
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/verdict-compute.ts
  - app/static/src/input.css
key_decisions:
  - none
patterns_established:
  - none
observability_surfaces:
  - none — dead code removal only, no runtime behavior changes
duration: 8m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T01: Remove dead TS exports/functions and dead CSS rules

**Removed 2 dead TS functions (computeConsensus, consensusBadgeClass), un-exported getOrCreateSummaryRow, and deleted 6 dead CSS rules (~40 lines total)**

## What Happened

Three mechanical dead-code removals across TS and CSS:

1. **row-factory.ts** — Removed `export` keyword from `getOrCreateSummaryRow`. The function body is preserved and still called internally by `updateSummaryRow` at line 292. Verified no external imports exist.

2. **verdict-compute.ts** — Deleted `computeConsensus()` (18 lines incl. JSDoc) and `consensusBadgeClass()` (13 lines incl. JSDoc) entirely. Neither was imported anywhere in the codebase. Both were Phase 3 leftovers superseded by the verdict micro-bar.

3. **input.css** — Deleted `.alert-success` (5 lines), `.alert-warning` (5 lines), and the entire `.consensus-badge` section (comment header + 4 rules, ~30 lines). None were referenced in templates or TS. The consensus-badge rules were only consumed by the now-deleted `consensusBadgeClass()`.

Copied `tools/esbuild` and `tools/tailwindcss` binaries from the main project to the worktree to enable `make js` and `make css`.

## Verification

- `npx tsc --noEmit` — exits 0, zero errors
- `make js` — builds `app/static/dist/main.js` (26.1kb) successfully
- `make css` — builds `app/static/dist/style.css` successfully
- All 8 grep assertions pass confirming dead code absent and live code preserved

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx tsc --noEmit` | 0 | ✅ pass | ~3s |
| 2 | `make js` | 0 | ✅ pass | 7ms |
| 3 | `make css` | 0 | ✅ pass | 470ms |
| 4 | `! grep -q 'computeConsensus' verdict-compute.ts` | 0 | ✅ pass | <1s |
| 5 | `! grep -q 'consensusBadgeClass' verdict-compute.ts` | 0 | ✅ pass | <1s |
| 6 | `! grep -q 'export function getOrCreateSummaryRow' row-factory.ts` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'function getOrCreateSummaryRow' row-factory.ts` | 0 | ✅ pass | <1s |
| 8 | `! grep -q 'alert-success' input.css` | 0 | ✅ pass | <1s |
| 9 | `! grep -q 'alert-warning' input.css` | 0 | ✅ pass | <1s |
| 10 | `! grep -q 'consensus-badge' input.css` | 0 | ✅ pass | <1s |

## Diagnostics

None — this task removed dead code only. No runtime signals changed. Future agents can re-verify via the grep assertions above.

## Deviations

- Copied `tools/esbuild` and `tools/tailwindcss` from main project to worktree (worktree was missing build tool binaries). This was anticipated in the task plan's Must-Haves section.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/row-factory.ts` — Removed `export` from `getOrCreateSummaryRow` (line 233)
- `app/static/src/ts/modules/verdict-compute.ts` — Deleted `computeConsensus()` and `consensusBadgeClass()` functions
- `app/static/src/input.css` — Deleted `.alert-success`, `.alert-warning`, `.consensus-badge` family (6 rules, ~40 lines)
- `.gsd/milestones/M004/slices/S03/S03-PLAN.md` — Added Observability / Diagnostics section
- `.gsd/milestones/M004/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
