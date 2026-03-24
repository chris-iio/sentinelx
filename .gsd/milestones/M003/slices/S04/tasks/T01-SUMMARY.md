---
id: T01
parent: S04
milestone: M003
provides:
  - summaryTimers debounce map in enrichment.ts limiting summary row DOM rebuilds to 1–2 per IOC
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/dist/main.js
key_decisions:
  - Copied sortTimers pattern verbatim for summaryTimers — same type, same 100ms delay, same clear/set/delete lifecycle — for consistency and to avoid introducing any novel pattern
patterns_established:
  - Debounce map pattern (Map<string, ReturnType<typeof setTimeout>> + clear/set/delete in wrapper function) now used for both sort and summary row updates in enrichment.ts
observability_surfaces:
  - "grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts → ≥ 3 (declaration + get + set inside debouncedUpdateSummaryRow + delete inside callback)"
  - "wc -c app/static/dist/main.js → bundle size sanity gate ≤ 30,000 bytes"
duration: ~5m
verification_result: passed
completed_at: 2026-03-20T06:17:00+09:00
blocker_discovered: false
---

# T01: Debounce updateSummaryRow via summaryTimers map in enrichment.ts

**Added `summaryTimers` debounce map and `debouncedUpdateSummaryRow()` wrapper to enrichment.ts, replacing the direct `updateSummaryRow()` call at line 359 to limit summary row DOM rebuilds to 1–2 per IOC during streaming enrichment (R017).**

## What Happened

Three surgical edits to `app/static/src/ts/modules/enrichment.ts`:

1. **Added `summaryTimers` map** at module scope immediately after `sortTimers` (line 33):
   ```ts
   /** Debounce timers for updateSummaryRow — keyed by ioc_value */
   const summaryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
   ```

2. **Added `debouncedUpdateSummaryRow()` function** after `sortDetailRows()`, using the identical pattern — `get` existing timer → `clearTimeout` → new `setTimeout(100)` → `delete` + call inside callback → `set` new timer:
   ```ts
   function debouncedUpdateSummaryRow(slot, iocValue, iocVerdicts): void { ... }
   ```

3. **Replaced the direct call** in `renderEnrichmentResult()`:
   - Before: `updateSummaryRow(slot, result.ioc_value, iocVerdicts);`
   - After: `debouncedUpdateSummaryRow(slot, result.ioc_value, iocVerdicts);`

The pre-flight observability gaps in S04-PLAN.md and T01-PLAN.md were also patched (added `## Observability / Diagnostics` and `## Observability Impact` sections respectively).

## Verification

- `grep -c 'summaryTimers' enrichment.ts` → **4** (declaration + `.get` + `.set` + `.delete`) — satisfies ≥ 3 gate
- `make typecheck` → exit 0 (tsc --noEmit, no errors)
- `make js` → exit 0 (esbuild, 26.2kb output)
- `wc -c app/static/dist/main.js` → **26,783 bytes** — satisfies ≤ 30,000 gate

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` | 0 (output: 4) | ✅ pass | <1s |
| 2 | `make typecheck` | 0 | ✅ pass | 2.7s |
| 3 | `make js` | 0 | ✅ pass | 2.7s |
| 4 | `wc -c app/static/dist/main.js` → 26783 ≤ 30000 | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect debounce map usage:** `grep -n 'debouncedUpdateSummaryRow\|summaryTimers' app/static/src/ts/modules/enrichment.ts`
- **Confirm rebuild count in browser:** Add `console.count('updateSummaryRow')` at the top of `updateSummaryRow` in `row-factory.ts` and observe calls during a live enrichment run — expect ≤ 2 per IOC, not ~10
- **Timer leak check:** After enrichment completes, `summaryTimers.size` should be 0. If non-zero, a timer fired against a detached slot (harmless but detectable via DevTools breakpoint in `debouncedUpdateSummaryRow`)

## Deviations

None — implementation followed the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts` — added `summaryTimers` map at module scope, `debouncedUpdateSummaryRow()` function, replaced direct `updateSummaryRow()` call
- `app/static/dist/main.js` — rebuilt by `make js` (26,783 bytes)
- `.gsd/milestones/M003/slices/S04/S04-PLAN.md` — added `## Observability / Diagnostics` section (pre-flight fix)
- `.gsd/milestones/M003/slices/S04/tasks/T01-PLAN.md` — added `## Observability Impact` section (pre-flight fix)
