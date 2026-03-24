# S03 Research: Frontend Tightening — TypeScript + CSS Audit

**Slice:** S03 — Frontend tightening — TypeScript + CSS audit
**Risk:** Low
**Dependencies:** None (independent of S01/S02)
**Requirements:** R022 (TypeScript tightening), R023 (CSS dead rule cleanup + performance patterns)

## Summary

TypeScript strict mode is already enabled and clean (`npx tsc --noEmit` passes with zero errors). The work divides into two independent concerns: (1) dead code removal from TS modules + CSS, and (2) five O(N²) performance patterns specified in R023. CSS dead rules are minimal — 2 truly dead classes plus 4 consensus-badge classes orphaned by a Phase 3 design change. The TS dead code is 3 unused exports and 2 dead functions. This is a light, low-risk slice.

## Recommendation

Split into two tasks:
1. **Dead code removal** (TS exports + functions + CSS rules) — mechanical, low risk
2. **R023 performance patterns** — five targeted refactors in four files

Both can be verified with `npx tsc --noEmit`, `make js`, `make css`, and the full test suite.

## Implementation Landscape

### Current State

| Concern | Status |
|---|---|
| tsconfig.json strict mode | ✅ Already `"strict": true` with `noUncheckedIndexedAccess` |
| `npx tsc --noEmit` | ✅ Clean — zero errors |
| Total TS files | 15 files, 2,498 LOC |
| Total CSS | 2,027 lines in `app/static/src/input.css` |
| Total CSS class selectors | 197 unique |
| Build tooling | `make typecheck`, `make js`, `make css` (requires `tools/tailwindcss` + `tools/esbuild` binaries) |
| Test count | 944 tests (839 unit + 105 E2E) |

### Dead TS Code Inventory

| Item | File | Line | Status |
|---|---|---|---|
| `export function getOrCreateSummaryRow()` | `modules/row-factory.ts` | 233 | Only used internally within the same file (called by `updateSummaryRow` at line 292). The `export` keyword is unnecessary — remove it. |
| `export function computeConsensus()` | `modules/verdict-compute.ts` | 50 | Never imported anywhere. Function body is dead. Comment at line 72 confirms "Phase 3: No longer consumed by row-factory". Remove entirely. |
| `export function consensusBadgeClass()` | `modules/verdict-compute.ts` | 72 | Never imported anywhere. Returns consensus-badge CSS class names that are themselves dead CSS. Comment says "Kept exported for API stability" — but there is no external API; this is a bundled IIFE. Remove entirely. |

### Dead CSS Inventory

| Selector | File:Line | Reason |
|---|---|---|
| `.alert-success` | `input.css:327` | No usage in any template or TS file. Only `.alert-error` is used (in `index.html:11`). |
| `.alert-warning` | `input.css:333` | Same — defined but never applied. |
| `.consensus-badge` | `input.css:1238` | Only referenced by dead `consensusBadgeClass()` in `verdict-compute.ts`. |
| `.consensus-badge--green` | `input.css:1247` | Same — dead function output. |
| `.consensus-badge--yellow` | `input.css:1253` | Same. |
| `.consensus-badge--red` | `input.css:1259` | Same. |

Total dead CSS: 6 class rules (~30 lines).

**NOT dead (dynamic class construction):**
- `.ioc-type-badge--{type}` — Jinja template: `ioc-type-badge--{{ ioc.type.value }}`
- `.micro-bar-segment--{verdict}` — TS: `"micro-bar-segment--" + verdict`
- `.verdict-label--{verdict}` — TS: `"verdict-label--" + worstVerdict`
- `.verdict-{verdict}` (standalone) — TS: `"verdict-badge verdict-" + worstVerdict`

### R023 Performance Pattern Inventory

R023 specifies five O(N²) patterns that must be fixed. Current state of each:

#### 1. `findCopyButtonForIoc()` — attribute selector (O(1))

**File:** `modules/enrichment.ts:95-99`
**Current:** Iterates all `.copy-btn` elements via `querySelectorAll`, comparing `data-value` attribute until match.
**Fix:** Replace with `document.querySelector('.copy-btn[data-value="' + CSS.escape(iocValue) + '"]')`. Single selector, browser-native O(1) lookup.
**Note:** Use `CSS.escape()` to handle IOC values containing special characters (URLs with quotes, etc.).

#### 2. `updateDashboardCounts()` — once per poll tick

**File:** `modules/enrichment.ts:392` (called inside `renderEnrichmentResult`)
**Current:** Called once per result inside `renderEnrichmentResult()`. The poll loop at line 534 iterates `results.length` items per tick, so for a tick returning 50 results, `updateDashboardCounts()` runs 50 times — each time doing a full DOM scan of all `.ioc-card` elements.
**Fix:** Remove the `updateDashboardCounts()` call from `renderEnrichmentResult()`. Add a single call after the for-loop in the poll tick handler (after line 557, before `since = data.next_since`). Also move `sortCardsBySeverity()` outside the loop for the same reason — it's already debounced but the debounce timer reset 50 times is wasteful.
**Key constraint:** `updateCardVerdict()` must stay inside the per-result loop (it sets `data-verdict` on the card). Only the *aggregation* calls move out.

#### 3. `applyFilter()` — debounce ≥100ms

**File:** `modules/filter.ts:37` (the function), called from `input` event at line 123
**Current:** Called synchronously on every `input` event keystroke from the search box. No debounce.
**Fix:** Add a debounce wrapper around the `applyFilter()` call in the search input handler. Use `setTimeout`/`clearTimeout` pattern (already used elsewhere in the codebase — see `sortCardsBySeverity` in `cards.ts:104` and `debouncedUpdateSummaryRow` in `enrichment.ts:80`). Keep non-debounced calls from click handlers (verdict buttons, type pills, dashboard badges) — debounce only applies to the text input.

#### 4. `verdictSeverityIndex()` — pre-built Map

**File:** `types/ioc.ts:70-72`
**Current:** Uses `Array.indexOf()` on the 5-element `VERDICT_SEVERITY` array. O(N) per call.
**Fix:** Build a `Map<string, number>` from `VERDICT_SEVERITY` at module load time. Replace `indexOf()` with `.get() ?? -1`. The function signature and return value stay identical.
**Call sites:** 6 call sites across `cards.ts`, `enrichment.ts`, and `verdict-compute.ts` — none need to change since the function signature is preserved.

#### 5. Graph edge loop — pre-built index Map

**File:** `modules/graph.ts:107-115`
**Current:** Inside the edge loop: `providerNodes.find(n => n.id === edge.to)` then `providerNodes.indexOf(targetNode)` — two O(N) scans per edge.
**Fix:** Before the edge loop, build `const nodeIndexMap = new Map(providerNodes.map((n, i) => [n.id, i]))`. Inside the loop, use `nodeIndexMap.get(edge.to)` for O(1) lookup. Compute position from the index.

### Verification Strategy

1. **TypeScript typecheck:** `npx tsc --noEmit` — must pass with zero errors after all changes
2. **JS build:** `make js` — must produce `app/static/dist/main.js` without errors
3. **CSS build:** `make css` — must produce `app/static/dist/style.css` without errors
4. **Grep assertions (dead code removed):**
   - `grep -c 'computeConsensus' app/static/src/ts/modules/verdict-compute.ts` → 0
   - `grep -c 'consensusBadgeClass' app/static/src/ts/modules/verdict-compute.ts` → 0
   - `grep -c 'export function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts` → 0
   - `grep -c 'alert-success' app/static/src/input.css` → 0
   - `grep -c 'alert-warning' app/static/src/input.css` → 0
   - `grep -c 'consensus-badge' app/static/src/input.css` → 0
5. **Grep assertions (R023 patterns applied):**
   - `grep 'querySelector.*copy-btn.*data-value' app/static/src/ts/modules/enrichment.ts` → matches (attribute selector)
   - `grep -c 'querySelectorAll.*copy-btn' app/static/src/ts/modules/enrichment.ts` → 0 (old pattern removed)
   - Verify `updateDashboardCounts()` is NOT inside `renderEnrichmentResult()` function body
   - `grep 'new Map' app/static/src/ts/types/ioc.ts` → matches (pre-built severity map)
   - `grep 'indexOf' app/static/src/ts/types/ioc.ts` → 0 (old pattern removed)
   - `grep 'new Map' app/static/src/ts/modules/graph.ts` → matches (pre-built node index)
   - `grep '\.find\|\.indexOf' app/static/src/ts/modules/graph.ts` edge loop → 0
6. **Full test suite:** `python3 -m pytest tests/ -x -q` — 944 tests must pass
7. **E2E subset:** `python3 -m pytest tests/e2e/ -x -q` — 105 E2E tests must pass (confirms no visual regressions from CSS changes)

### Build Tooling Notes

- `tools/tailwindcss` and `tools/esbuild` binaries may be absent in the worktree (see KNOWLEDGE.md). Copy from main project tree or run `make tailwind-install && make esbuild-install`.
- `make build` runs both `css` and `js` targets.
- `make typecheck` runs `tsc --noEmit`.

### File Change Map

| File | Changes |
|---|---|
| `app/static/src/ts/modules/row-factory.ts` | Remove `export` from `getOrCreateSummaryRow` (keep the function, just un-export it) |
| `app/static/src/ts/modules/verdict-compute.ts` | Delete `computeConsensus()` and `consensusBadgeClass()` functions entirely |
| `app/static/src/ts/modules/enrichment.ts` | Replace `findCopyButtonForIoc()` with attribute selector; move `updateDashboardCounts()` and `sortCardsBySeverity()` out of per-result loop |
| `app/static/src/ts/modules/filter.ts` | Add debounce (≥100ms) to `applyFilter()` call from search input handler |
| `app/static/src/ts/types/ioc.ts` | Replace `VERDICT_SEVERITY.indexOf()` with pre-built Map in `verdictSeverityIndex()` |
| `app/static/src/ts/modules/graph.ts` | Pre-build node index Map before edge loop |
| `app/static/src/input.css` | Delete `.alert-success` (line 327), `.alert-warning` (line 333), `.consensus-badge` family (lines 1238-1263) |

### Risks

- **Minimal.** All changes are internal to the frontend bundle. No API changes, no template changes, no Python changes.
- The `CSS.escape()` usage in `findCopyButtonForIoc` is safe — it's available in all modern browsers and the project targets `es2022`.
- Moving `updateDashboardCounts()` outside the render loop is the only behavioral change — it changes when the dashboard updates (from per-result to per-tick) but the end state is identical since the dashboard reflects the same accumulated card verdicts.
