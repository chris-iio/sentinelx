# S03 UAT: Frontend tightening — TypeScript + CSS audit

## Preconditions

- M004 worktree with S03 changes applied
- `tools/esbuild` and `tools/tailwindcss` binaries present
- Python virtualenv with Playwright browsers installed
- Node.js with TypeScript 5.8+ installed

---

## Test Case 1: Dead TypeScript code removed

**Goal:** Confirm dead functions and exports are gone, live code preserved.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep -c 'computeConsensus' app/static/src/ts/modules/verdict-compute.ts` | Returns `0` (function deleted) |
| 2 | `grep -c 'consensusBadgeClass' app/static/src/ts/modules/verdict-compute.ts` | Returns `0` (function deleted) |
| 3 | `grep 'export function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts` | No output (export keyword removed) |
| 4 | `grep 'function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts` | Matches — function body preserved |
| 5 | `grep -c 'getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts` | ≥2 (definition + call from updateSummaryRow) |

---

## Test Case 2: Dead CSS rules removed

**Goal:** Confirm unused CSS rules are absent from source.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep -c 'alert-success' app/static/src/input.css` | Returns `0` |
| 2 | `grep -c 'alert-warning' app/static/src/input.css` | Returns `0` |
| 3 | `grep -c 'consensus-badge' app/static/src/input.css` | Returns `0` |
| 4 | `grep -c 'alert-success\|alert-warning\|consensus-badge' app/static/dist/style.css` | Returns `0` (not in built output either) |

---

## Test Case 3: R023 Pattern 1 — Attribute selector for copy button

**Goal:** `findCopyButtonForIoc()` uses O(1) attribute selector, not O(N) iteration.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep 'querySelector.*copy-btn.*data-value' app/static/src/ts/modules/enrichment.ts` | Matches — attribute selector present |
| 2 | `grep 'CSS.escape' app/static/src/ts/modules/enrichment.ts` | Matches — special character escaping present |
| 3 | `grep 'querySelectorAll.*copy-btn' app/static/src/ts/modules/enrichment.ts` | No output — old iteration removed |

---

## Test Case 4: R023 Pattern 2 — Batched dashboard/sort per tick

**Goal:** `updateDashboardCounts()` and `sortCardsBySeverity()` called once per poll tick, not per result.

| # | Step | Expected |
|---|------|----------|
| 1 | Open `app/static/src/ts/modules/enrichment.ts` and locate the poll `.then()` handler | `updateDashboardCounts()` and `sortCardsBySeverity()` appear after the `for` loop over `results`, not inside it |
| 2 | Verify the calls are guarded | `if (results.length > 0)` wraps both calls |
| 3 | Verify `updateCardVerdict()` is still per-result | `updateCardVerdict()` appears inside the result loop |

---

## Test Case 5: R023 Pattern 3 — Debounced search filter

**Goal:** `applyFilter()` debounced ≥100ms on search input.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep 'setTimeout' app/static/src/ts/modules/filter.ts` | Matches — debounce timer present |
| 2 | `grep 'clearTimeout' app/static/src/ts/modules/filter.ts` | Matches — previous timer cancelled |
| 3 | `grep '100' app/static/src/ts/modules/filter.ts` | 100ms delay value present |
| 4 | Verify click handlers are NOT debounced | `applyFilter()` calls from verdict buttons/type pills/dashboard badges are direct (no setTimeout wrapper) |

---

## Test Case 6: R023 Pattern 4 — Pre-built Map for verdict severity

**Goal:** `verdictSeverityIndex()` uses Map lookup, not indexOf.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep 'SEVERITY_MAP' app/static/src/ts/types/ioc.ts` | Matches — Map defined and used |
| 2 | `grep 'new Map' app/static/src/ts/types/ioc.ts` | Matches — Map constructed from VERDICT_SEVERITY |
| 3 | `grep 'indexOf' app/static/src/ts/types/ioc.ts` | No output — old pattern removed |
| 4 | `grep 'SEVERITY_MAP.get' app/static/src/ts/types/ioc.ts` | Matches — Map.get() used in function body |

---

## Test Case 7: R023 Pattern 5 — Pre-built Map for graph node index

**Goal:** Graph edge loop uses Map instead of find/indexOf.

| # | Step | Expected |
|---|------|----------|
| 1 | `grep 'nodeIndexMap' app/static/src/ts/modules/graph.ts` | Matches — Map defined and used |
| 2 | `grep 'new Map' app/static/src/ts/modules/graph.ts` | Matches — Map built from providerNodes |
| 3 | `grep 'nodeIndexMap.get' app/static/src/ts/modules/graph.ts` | Matches — Map.get() replaces find+indexOf |

---

## Test Case 8: TypeScript strict-mode clean

**Goal:** No type errors in the codebase.

| # | Step | Expected |
|---|------|----------|
| 1 | `npx tsc --noEmit` | Exit code 0, no output |

---

## Test Case 9: Build artifacts

**Goal:** JS and CSS build cleanly with changes applied.

| # | Step | Expected |
|---|------|----------|
| 1 | `make js` | Exit 0, outputs `app/static/dist/main.js` with byte count |
| 2 | `make css` | Exit 0, outputs `app/static/dist/style.css` |
| 3 | `wc -c app/static/dist/main.js` | ≤ 27,000 bytes (no unexpected bloat) |

---

## Test Case 10: E2E regression suite

**Goal:** No visual regressions from CSS removal or TS changes.

| # | Step | Expected |
|---|------|----------|
| 1 | `python3 -m pytest tests/e2e/ -x -q` | 105 passed |
| 2 | Specifically check search filter test | `test_combined_type_and_search_filters` passes (accounts for 100ms debounce via 150ms POM wait) |

---

## Test Case 11: Full test suite regression

**Goal:** No regressions anywhere.

| # | Step | Expected |
|---|------|----------|
| 1 | `python3 -m pytest --tb=short -q` | 944+ passed, 0 failed |

---

## Edge Cases

- **IOC values with special characters in copy button:** The `CSS.escape()` in `findCopyButtonForIoc()` handles IOC values containing dots, colons, brackets (e.g., IPv6 addresses `2001:db8::1`, defanged domains `evil[.]com`). E2E tests covering these IOC types implicitly verify this.
- **Rapid search typing:** The 100ms debounce means typing "malicious" fires `applyFilter()` once after the last keystroke + 100ms, not 9 times. The POM `search()` method waits 150ms after `fill()` to ensure the debounced filter has executed before assertions.
- **Empty poll tick:** The `if (results.length > 0)` guard on `updateDashboardCounts()` / `sortCardsBySeverity()` prevents unnecessary DOM work when a poll tick returns no new results.
