# S04 Research: CSS Audit + Frontend TypeScript Dedup

## Summary

Two scopes: dead CSS removal and TypeScript function deduplication between `enrichment.ts` and `history.ts`. The CSS audit found **zero dead rules** — all 2,069 lines are actively referenced (statically or via dynamic class concatenation). The TypeScript dedup opportunity is real: ~120 lines of duplicated logic across 3 functions plus a 45-line verdict computation block.

## Recommendation

- **CSS audit**: Report "no dead CSS" as the finding. No rules to remove. The codebase has been well-maintained; every class is either directly referenced in templates/TS or dynamically constructed via string concatenation (`"verdict-" + verdict`, `"ioc-type-badge--" + type`, etc.). The Tailwind safelist in `tailwind.config.js` correctly covers all dynamic classes. **This scope is a documentation task, not a code change.**

- **TypeScript dedup**: Create a new shared module `app/static/src/ts/modules/shared-rendering.ts` extracting 4 items:
  1. `injectDetailLink(slot)` — identical in both files, pure function, no closure deps → direct extraction
  2. `initExportButton(resultsArray)` — identical logic, but closes over module-private `allResults` → parameterize with an `allResults` argument
  3. `sortDetailRows(container)` — the _inner_ sort logic is identical; enrichment.ts wraps it in a debounce. Extract the synchronous core; enrichment.ts keeps its debounce wrapper calling the shared core.
  4. `computeResultDisplay(result)` — the 45-line verdict/statText/summaryText computation block is duplicated verbatim between `renderEnrichmentResult()` and `replayResult()`. Extract as a pure function returning `{ verdict, statText, summaryText, detectionCount, totalEngines }`.

## Implementation Landscape

### CSS Audit (R046)

**Files**: `app/static/src/input.css` (2,069 LOC), all files under `app/templates/`, all `.ts` files under `app/static/src/ts/`

**Finding**: Every CSS class selector in `input.css` is referenced by at least one of:
- Direct class reference in HTML templates (e.g., `class="ioc-card"`)
- Dynamic Jinja2 interpolation (e.g., `ioc-type-badge--{{ ioc.type.value }}`)
- Dynamic JS/TS string concatenation (e.g., `"verdict-" + worstVerdict` in `row-factory.ts`)
- State toggle via classList (e.g., `classList.toggle("is-open")` in `enrichment.ts`)

The `tailwind.config.js` safelist correctly covers all dynamic classes that Tailwind's content scanner can't detect.

**Classes verified as dynamically generated (not dead):**
- `verdict-{clean,suspicious,malicious,no_data,error}` → `row-factory.ts`: `"verdict-badge verdict-" + verdict`
- `verdict-label--{*}` → `cards.ts`: `"verdict-label--" + worstVerdict`
- `micro-bar-segment--{*}` → `row-factory.ts`: `"micro-bar-segment--" + verdict`
- `ioc-type-badge--{*}` → templates: `ioc-type-badge--{{ ioc.type.value }}`
- `filter-pill--{email,ipv4,...}` → templates: `filter-pill--{{ ioc_type.value }}`

**Conclusion**: R046 finding is "no dead CSS exists." The audit itself is the deliverable.

### TypeScript Dedup (R047)

**Files**:
- `app/static/src/ts/modules/enrichment.ts` (582 LOC) — live enrichment polling
- `app/static/src/ts/modules/history.ts` (355 LOC) — history replay
- NEW: `app/static/src/ts/modules/shared-rendering.ts`

**Duplication inventory:**

| Function | enrichment.ts lines | history.ts lines | Extractable? | Notes |
|---|---|---|---|---|
| `injectDetailLink` | 25 | 27 | ✅ Pure function, no deps | Identical logic, no closure |
| `initExportButton` | 33 | 32 | ✅ With param change | Both close over module `allResults`; parameterize |
| `sortDetailRows` | 23 (debounced) | 15 (sync) | ✅ Extract core sort | Different signatures: enrichment version wraps in debounce |
| verdict/statText computation | 47 | 45 | ✅ Pure function | Identical block inside render/replay functions |

**Total extractable lines**: ~120 lines of duplication → ~60 lines in shared module + callers slim down

**KNOWLEDGE.md constraint (M006/S01/T03)**:
> "Duplicate small utility functions (≤20 lines each) in the new module rather than widening the export surface of a complex existing module... Before exporting from enrichment.ts, check if the function reads or writes module-level state (`allResults`, `iocVerdicts`, `iocResultCounts`). If it does, duplicate instead."

This constraint was about exporting FROM enrichment.ts. The new approach creates a SEPARATE shared module — neither enrichment.ts nor history.ts needs to export its private state. `initExportButton` receives `allResults` as a parameter instead of closing over module state.

**`wireExpandToggles`** is already shared (exported from enrichment.ts, imported by history.ts). No change needed.

### Existing module structure

```
modules/
  enrichment.ts (582 LOC) — exports: init(), wireExpandToggles()
  history.ts (355 LOC)    — exports: init(); imports wireExpandToggles from enrichment
  row-factory.ts           — shared DOM construction
  verdict-compute.ts       — shared verdict computation
  export.ts                — shared export functions (exportJSON, exportCSV, copyAllIOCs)
  cards.ts                 — card DOM manipulation
  filter.ts                — filter bar UI
  ...
```

Pattern: shared logic lives in dedicated modules (export.ts, verdict-compute.ts, row-factory.ts). A new `shared-rendering.ts` follows this pattern.

### Proposed shared module shape

```typescript
// shared-rendering.ts

import type { EnrichmentItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";
import { exportJSON, exportCSV, copyAllIOCs } from "./export";
import { formatDate } from "./row-factory";

/** Return type for computeResultDisplay */
export interface ResultDisplay {
  verdict: VerdictKey;
  statText: string;
  summaryText: string;
  detectionCount: number;
  totalEngines: number;
}

/** Pure function: compute display fields from an enrichment result */
export function computeResultDisplay(result: EnrichmentItem): ResultDisplay { ... }

/** Inject "View full detail →" link into enrichment details panel */
export function injectDetailLink(slot: HTMLElement): void { ... }

/** Sort .provider-detail-row elements by verdict severity descending */
export function sortDetailRows(container: HTMLElement): void { ... }

/** Wire export dropdown (JSON/CSV/copy) — pass allResults to avoid closure */
export function initExportButton(allResults: EnrichmentItem[]): void { ... }
```

### How callers change

**enrichment.ts**:
- Remove private `injectDetailLink` → import from `shared-rendering`
- Remove private `initExportButton` → import from `shared-rendering`, call with `allResults` arg
- `sortDetailRows` stays as private debounced version, but calls `sharedSortDetailRows(container)` for the inner logic
- `renderEnrichmentResult` calls `computeResultDisplay(result)` instead of inline computation

**history.ts**:
- Remove private `injectDetailLink` → import from `shared-rendering`
- Remove private `initExportButton` → import from `shared-rendering`, call with `allResults` arg
- Remove private `sortDetailRows` → import from `shared-rendering`
- `replayResult` calls `computeResultDisplay(result)` instead of inline computation

### Verification

```bash
make typecheck   # tsc --noEmit — catches any type errors
make js          # esbuild bundle — catches import/export issues
make css         # tailwindcss — confirms CSS still builds (no changes expected)
```

No test files reference the private functions being extracted. E2E tests exercise the behavior end-to-end and remain unchanged.

### Risk Assessment

**Low risk.** All extractions are mechanical. The functions being extracted are pure or can be made pure with a single parameter addition. `make typecheck` catches any type signature mismatches immediately. No behavioral changes — same functions, same logic, different module location.

### Natural task decomposition

1. **T01: CSS audit + documentation** — Cross-reference all CSS selectors against templates and TS. Document finding (no dead CSS). Verify `make css` passes. (~15 min)

2. **T02: Create shared-rendering.ts + extract functions** — Create the shared module with all 4 exported functions. Update enrichment.ts and history.ts to import from it. Verify `make typecheck && make js`. (~30 min)

3. **T03: Slice verification** — Run full frontend build chain, verify LOC reduction, run E2E tests to confirm no regressions. (~15 min)

### LOC impact estimate

- `shared-rendering.ts`: +~65 lines (new file)
- `enrichment.ts`: -~90 lines (remove 3 private functions + inline computation)
- `history.ts`: -~90 lines (remove 3 private functions + inline computation)
- Net: ~-115 lines of TypeScript

CSS: 0 lines removed (no dead CSS found).
