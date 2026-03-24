---
estimated_steps: 4
estimated_files: 2
---

# T01: Debounce updateSummaryRow via summaryTimers map in enrichment.ts

**Slice:** S04 — Frontend Render Efficiency & Integration Verification
**Milestone:** M003

## Description

Add a `summaryTimers` debounce map to `enrichment.ts` that wraps the `updateSummaryRow()` call, limiting summary row DOM rebuilds to 1–2 per IOC during streaming enrichment instead of once per provider result (~10). This is the only production code change in S04 and directly satisfies R017.

The exact pattern to follow already exists in the same file: `sortTimers` (line 32) is a `Map<string, ReturnType<typeof setTimeout>>` with `clearTimeout` on existing timer → `setTimeout` at 100ms → `delete` on execution. Copy this pattern identically for `summaryTimers`.

## Steps

1. **Add `summaryTimers` map** at module scope, immediately after `sortTimers` (around line 33):
   ```ts
   /** Debounce timers for updateSummaryRow — keyed by ioc_value */
   const summaryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
   ```

2. **Add `debouncedUpdateSummaryRow()` function** after the `sortDetailRows()` function (after line 65). This wrapper has the same signature as the call site at line 359:
   ```ts
   function debouncedUpdateSummaryRow(
     slot: HTMLElement,
     iocValue: string,
     iocVerdicts: Record<string, VerdictEntry[]>
   ): void {
     const existing = summaryTimers.get(iocValue);
     if (existing !== undefined) clearTimeout(existing);
     const timer = setTimeout(() => {
       summaryTimers.delete(iocValue);
       updateSummaryRow(slot, iocValue, iocVerdicts);
     }, 100);
     summaryTimers.set(iocValue, timer);
   }
   ```

3. **Replace the direct call** at line 359 (inside `renderEnrichmentResult()`):
   - Old: `updateSummaryRow(slot, result.ioc_value, iocVerdicts);`
   - New: `debouncedUpdateSummaryRow(slot, result.ioc_value, iocVerdicts);`

4. **Build and verify:**
   - `make typecheck` → exit 0
   - `make js` → exit 0
   - `wc -c app/static/dist/main.js` → ≤ 30,000 bytes

## Must-Haves

- [ ] `summaryTimers` map declared at module scope with same type as `sortTimers`
- [ ] `debouncedUpdateSummaryRow()` wraps `updateSummaryRow()` with 100ms debounce per IOC
- [ ] Line 359's direct `updateSummaryRow()` call replaced with `debouncedUpdateSummaryRow()`
- [ ] `make typecheck` exits 0
- [ ] `make js` exits 0 and bundle ≤ 30,000 bytes

## Verification

- `make typecheck` exits 0
- `make js` exits 0
- `wc -c app/static/dist/main.js` → ≤ 30,000 bytes (current: 26,648; expect ~26,800 after adding ~10 lines)
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` → ≥ 3

## Observability Impact

**What changes:** The `updateSummaryRow()` call site in `renderEnrichmentResult()` is replaced with a debounced wrapper. The direct call count drops from ~10/IOC (one per provider result) to 1–2/IOC during streaming enrichment.

**How a future agent inspects this:**
- `grep -n 'debouncedUpdateSummaryRow\|summaryTimers' app/static/src/ts/modules/enrichment.ts` lists all timer map usage sites
- `grep -c 'summaryTimers' ...` ≥ 3 is the minimum gate (declaration + `.get`/`.set` inside wrapper + `.delete` inside callback)
- To confirm debounce fires: add `console.count('updateSummaryRow')` at the top of `updateSummaryRow` in `row-factory.ts` and count calls during a live enrichment run — expect ≤ 2 per IOC, not ~10

**Failure state:**
- If `debouncedUpdateSummaryRow` is removed, `updateSummaryRow` reverts to direct call; no error, but summary row re-renders ~10×/IOC (visible as flicker)
- Timer ID type mismatch (wrong type annotation) would surface immediately as a TypeScript compile error — caught by `make typecheck`
- No persistent failure artifact: the debounce lives entirely in browser memory

## Inputs

- `app/static/src/ts/modules/enrichment.ts` — existing file with `sortTimers` pattern at lines 32–65 and `updateSummaryRow()` call at line 359
- `updateSummaryRow` is imported from `row-factory.ts` (line 25) — no changes needed to row-factory.ts itself
- SEC-08 constraint: all DOM construction must use `createElement` + `textContent`. The debounce wrapper doesn't touch DOM — it only delays calling `updateSummaryRow()`. No security concern.

## Expected Output

- `app/static/src/ts/modules/enrichment.ts` — `summaryTimers` map + `debouncedUpdateSummaryRow()` function added; direct call replaced
- `app/static/dist/main.js` — rebuilt, ≤ 30,000 bytes
