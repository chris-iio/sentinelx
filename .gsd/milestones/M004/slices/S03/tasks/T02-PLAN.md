---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T02: Apply five R023 O(N²) performance patterns

**Slice:** S03 — Frontend tightening — TypeScript + CSS audit
**Milestone:** M004

## Description

Apply five targeted performance refactors specified by requirement R023. Each fixes an O(N²) pattern in the frontend TypeScript modules. All changes preserve existing function signatures and external behavior — the optimizations are internal.

## Steps

1. **Replace `findCopyButtonForIoc()` with attribute selector in `app/static/src/ts/modules/enrichment.ts`** (lines 95-99). The current implementation iterates all `.copy-btn` elements via `querySelectorAll`. Replace the function body with a single `document.querySelector` using an attribute selector:
   ```ts
   function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
     return document.querySelector<HTMLElement>('.copy-btn[data-value="' + CSS.escape(iocValue) + '"]');
   }
   ```
   This is O(1) browser-native lookup. `CSS.escape()` handles IOC values with special characters (URLs with quotes, etc.). It's available in all modern browsers and the project targets es2022.

2. **Move `updateDashboardCounts()` and `sortCardsBySeverity()` out of per-result loop in `app/static/src/ts/modules/enrichment.ts`**. Currently at lines 392-393 inside `renderEnrichmentResult()`, these are called once per result. In the poll tick handler (the `setInterval` callback), they run N times per tick where N = number of results in that batch.
   - Remove the `updateDashboardCounts()` and `sortCardsBySeverity()` calls from inside `renderEnrichmentResult()` (delete lines 392-393).
   - Add both calls ONCE after the for-loop in the poll tick's `.then(function(data) {...})` handler, right after the results loop ends and before `since = data.next_since`. The exact location is after the `}` closing the `for (let i = 0; i < results.length; i++)` loop (around line 557 in the current file).
   - **Keep `updateCardVerdict()` inside `renderEnrichmentResult()`** — it sets `data-verdict` on each card and must run per-result.
   - Since `updateDashboardCounts` and `sortCardsBySeverity` are imported at the top of the file, they remain available in the poll tick handler's closure scope. Add a guard: only call them if `results.length > 0` to avoid unnecessary work on empty ticks.

3. **Add debounce to `applyFilter()` on search input in `app/static/src/ts/modules/filter.ts`**. The search input `input` event handler at line 123 calls `applyFilter()` synchronously on every keystroke.
   - Add a module-scoped debounce timer variable inside the `init()` function closure: `let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;`
   - In the search input handler, replace the direct `applyFilter()` call with:
     ```ts
     if (searchDebounceTimer !== null) clearTimeout(searchDebounceTimer);
     searchDebounceTimer = setTimeout(() => {
       applyFilter();
     }, 100);
     ```
   - This matches the existing debounce pattern used in `cards.ts` (line 105-106) for `sortCardsBySeverity`.
   - **Do NOT debounce** the click handlers for verdict buttons, type pills, or dashboard badges — those remain synchronous (clicks should feel instant).

4. **Replace `Array.indexOf()` with pre-built Map in `app/static/src/ts/types/ioc.ts`**. The `verdictSeverityIndex()` function at line 70-72 uses `VERDICT_SEVERITY.indexOf(verdict)`.
   - After the `VERDICT_SEVERITY` array declaration, add:
     ```ts
     const SEVERITY_MAP: ReadonlyMap<string, number> = new Map(
       VERDICT_SEVERITY.map((v, i) => [v, i])
     );
     ```
   - Change `verdictSeverityIndex()` body to: `return SEVERITY_MAP.get(verdict) ?? -1;`
   - The function signature (`(verdict: VerdictKey): number`) stays identical. All 6 call sites across cards.ts, enrichment.ts, and verdict-compute.ts continue to work unchanged.

5. **Pre-build node index Map in graph edge loop in `app/static/src/ts/modules/graph.ts`** (lines 101-115). The edge loop currently calls `providerNodes.find(n => n.id === edge.to)` then `providerNodes.indexOf(targetNode)` — two O(N) scans per edge.
   - Before the edge loop (after `edgeGroup` is created, before `for (const edge of edges)`), add:
     ```ts
     const nodeIndexMap = new Map<string, number>(
       providerNodes.map((n, i) => [n.id, i])
     );
     ```
   - Inside the edge loop, replace:
     ```ts
     const targetNode = providerNodes.find((n) => n.id === edge.to);
     if (!targetNode) continue;
     const idx = providerNodes.indexOf(targetNode);
     ```
     with:
     ```ts
     const idx = nodeIndexMap.get(edge.to);
     if (idx === undefined) continue;
     ```
   - The rest of the loop body (angle calculation, line drawing) uses `idx` the same way.

## Must-Haves

- [ ] `findCopyButtonForIoc()` uses `querySelector` with attribute selector, no `querySelectorAll` iteration
- [ ] `updateDashboardCounts()` and `sortCardsBySeverity()` called once per poll tick after the results loop, not per-result inside `renderEnrichmentResult()`
- [ ] `applyFilter()` debounced ≥100ms on search input `input` event handler; click handlers remain synchronous
- [ ] `verdictSeverityIndex()` uses pre-built `Map`, no `indexOf` on array
- [ ] Graph edge loop uses pre-built `Map` for node index, no `.find()` or `.indexOf()`
- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] E2E tests pass (no behavioral regressions)

## Verification

- `npx tsc --noEmit` exits 0
- `grep -q 'querySelector.*copy-btn.*data-value' app/static/src/ts/modules/enrichment.ts` (attribute selector present)
- `! grep -q 'querySelectorAll.*copy-btn' app/static/src/ts/modules/enrichment.ts` (old pattern gone)
- `grep -q 'CSS.escape' app/static/src/ts/modules/enrichment.ts` (escape used)
- `grep -q 'new Map' app/static/src/ts/types/ioc.ts` (pre-built severity map)
- `! grep -q 'indexOf' app/static/src/ts/types/ioc.ts` (old pattern gone)
- `grep -q 'new Map' app/static/src/ts/modules/graph.ts` (pre-built node index map)
- `! grep -q '\.find' app/static/src/ts/modules/graph.ts` at the edge loop (only iocNode find at line 73 is OK — it's outside the edge loop)
- `grep -q 'clearTimeout\|setTimeout' app/static/src/ts/modules/filter.ts` (debounce present)
- `python3 -m pytest tests/e2e/ -x -q` — 105 E2E tests pass

## Inputs

- `app/static/src/ts/modules/enrichment.ts` — contains `findCopyButtonForIoc()` at lines 95-99, `updateDashboardCounts()` call at line 392, `sortCardsBySeverity()` at line 393, poll loop at lines 522-570
- `app/static/src/ts/modules/filter.ts` — contains search input handler at line 123 calling `applyFilter()` synchronously
- `app/static/src/ts/types/ioc.ts` — contains `verdictSeverityIndex()` at lines 70-72 using `indexOf`
- `app/static/src/ts/modules/graph.ts` — contains edge loop at lines 101-115 with `.find()` and `.indexOf()`
- `app/static/src/ts/modules/row-factory.ts` — modified by T01 (un-exported `getOrCreateSummaryRow`)
- `app/static/src/ts/modules/verdict-compute.ts` — modified by T01 (dead functions removed)

## Expected Output

- `app/static/src/ts/modules/enrichment.ts` — `findCopyButtonForIoc()` uses attribute selector; `updateDashboardCounts()`/`sortCardsBySeverity()` moved to poll tick level
- `app/static/src/ts/modules/filter.ts` — search input handler uses debounced `applyFilter()`
- `app/static/src/ts/types/ioc.ts` — `SEVERITY_MAP` pre-built; `verdictSeverityIndex()` uses Map lookup
- `app/static/src/ts/modules/graph.ts` — `nodeIndexMap` pre-built before edge loop; `.find()`/`.indexOf()` replaced

## Observability Impact

- **No new runtime signals** — all five patterns are internal performance optimizations. Function signatures and external behavior are unchanged.
- **Bundle size**: Observable via `make js` output (byte count). Should remain near prior 26.1kb (internal refactors only).
- **Inspection**: `grep` assertions confirm old O(N²) patterns removed and new Map/selector patterns present. `npx tsc --noEmit` confirms type safety.
- **Failure visibility**: If debounce causes UI lag, it's observable in E2E filter tests timing out. If Map lookups return wrong indices, E2E graph/sort tests fail.
