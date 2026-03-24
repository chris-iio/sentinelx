# Phase 2: TypeScript Module Extractions - Research

**Researched:** 2026-03-17
**Domain:** TypeScript module splitting, esbuild IIFE bundling, zero-behavioral-change refactoring
**Confidence:** HIGH

---

## Summary

Phase 2 splits the 928-line `enrichment.ts` monolith into three focused modules with zero
behavioral change. The extraction is pure code movement: no logic changes, no new features,
no API surface changes visible to the browser. The resulting three files are `verdict-compute.ts`
(pure computation functions, ~80 LOC), `row-factory.ts` (all DOM row construction, ~150 LOC),
and a slimmed `enrichment.ts` (~300 LOC) that owns only the polling orchestrator and module
state.

The critical constraint is the esbuild IIFE bundling model. Because esbuild resolves all
TypeScript imports at build time and outputs a single `main.js` bundle, there is no runtime
module boundary visible to E2E tests. The 91 E2E tests interact only with the compiled DOM
output — they do not reference TypeScript module names, function names, or import paths. This
means any correctly-implemented split that preserves DOM behavior passes E2E unchanged.

The primary risk is not the split itself — it is accidentally mutating logic while moving code.
The discipline is: move first, verify, then clean up. Never refactor at the same time as
extracting.

**Primary recommendation:** Do the extraction in one atomic commit per module addition. Add
`verdict-compute.ts` first (pure functions, no DOM — easiest to verify), then `row-factory.ts`
(DOM code with well-defined inputs and outputs), then trim `enrichment.ts` last.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| esbuild | 0.27.3 (in tools/) | TypeScript bundler | Already in use; IIFE output bundles all imports into single main.js |
| TypeScript | 5.8 | Type-checking | Already in use; tsconfig.json has strict + noUncheckedIndexedAccess |
| tsc | (bundled with TypeScript) | Type-check without emit | `make typecheck` is the validation command |

### No new dependencies required
This phase adds no new libraries. It only reorganizes code within the existing TypeScript
module tree under `app/static/src/ts/modules/`.

---

## Architecture Patterns

### IIFE Bundling — Why Module Splits Are Safe

esbuild with `--format=iife --bundle` resolves all `import` statements at build time and
produces a single `main.js` file. The browser receives one script tag with no module boundaries.
This means:

- E2E tests interact with the compiled bundle, not individual `.ts` files
- Adding or removing `.ts` files has zero effect on test selectors, DOM structure, or runtime behavior
- The only observable output of this phase is `app/static/dist/main.js` — and it must be
  byte-functionally identical to the pre-extraction bundle

### Recommended New File Locations

```
app/static/src/ts/modules/
├── enrichment.ts          # EXISTING — trimmed to ~300 LOC polling orchestrator
├── verdict-compute.ts     # NEW — pure computation functions (~80 LOC)
├── row-factory.ts         # NEW — DOM row builders (~150 LOC)
├── cards.ts               # Unchanged
├── clipboard.ts           # Unchanged
├── export.ts              # Unchanged
├── filter.ts              # Unchanged
├── form.ts                # Unchanged
├── graph.ts               # Unchanged
├── settings.ts            # Unchanged
└── ui.ts                  # Unchanged
```

Both new files live in `modules/` alongside `enrichment.ts`. They are NOT `types/` files
(they contain logic) and NOT `utils/` files (they are domain-specific). The `modules/` pattern
is already established for all behavioral code.

### Pattern 1: Pure Extraction — verdict-compute.ts

**What:** Move computation functions with zero dependencies and zero DOM access.
**When to use:** Any function that takes plain data and returns plain data belongs here.

Functions to extract from `enrichment.ts`:

| Function | Lines | Inputs | Output | DOM access? |
|----------|-------|--------|--------|-------------|
| `computeWorstVerdict` | 95-102 | `VerdictEntry[]` | `VerdictKey` | No |
| `computeConsensus` | 108-122 | `VerdictEntry[]` | `{flagged, responded}` | No |
| `computeAttribution` | 139-159 | `VerdictEntry[]` | `{provider, text}` | No |
| `findWorstEntry` | 519-532 | `VerdictEntry[]` | `VerdictEntry | undefined` | No |
| `consensusBadgeClass` | 128-132 | `number` | `string` | No |

The `VerdictEntry` interface must also move to `verdict-compute.ts` because it is the primary
input type for all five functions. It is currently private to `enrichment.ts` — making it
exported is required since `enrichment.ts` and `row-factory.ts` both need it.

`verdictSeverityIndex` is NOT extracted — it lives in `types/ioc.ts` where it belongs.
`computeAttribution` calls `verdictSeverityIndex` from `types/ioc.ts`, so `verdict-compute.ts`
imports from `../types/ioc`.

```typescript
// Source: enrichment.ts lines 95-159 (to be moved verbatim)
// app/static/src/ts/modules/verdict-compute.ts

import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";

export interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
  detectionCount: number;
  totalEngines: number;
  statText: string;
}

export function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey { ... }
export function computeConsensus(entries: VerdictEntry[]): { flagged: number; responded: number } { ... }
export function computeAttribution(entries: VerdictEntry[]): { provider: string; text: string } { ... }
export function findWorstEntry(entries: VerdictEntry[]): VerdictEntry | undefined { ... }
export function consensusBadgeClass(flagged: number): string { ... }
```

### Pattern 2: DOM Row Factory — row-factory.ts

**What:** Move all DOM-construction code and the `CONTEXT_PROVIDERS` set.
**When to use:** Any function that calls `document.createElement` belongs here.

Functions to extract:

| Function | Lines | Purpose |
|----------|-------|---------|
| `CONTEXT_PROVIDERS` (set) | 315 | Provider routing constant |
| `PROVIDER_CONTEXT_FIELDS` (const) | 233-309 | Field definitions per provider |
| `ContextFieldDef` (interface) | 227-231 | Type for field definitions |
| `createLabeledField` | 321-331 | Build labeled span wrapper |
| `createContextFields` | 338-376 | Build context field container |
| `createContextRow` | 384-411 | Build context-only provider row |
| `createDetailRow` | 417-461 | Build verdict provider row |
| `updateSummaryRow` | 188-222 | Build/update summary row |
| `getOrCreateSummaryRow` | 165-181 | Get or create summary row element |

`formatDate` and `formatRelativeTime` are utility functions currently in `enrichment.ts`
that are called only from row-construction code. They belong in `row-factory.ts` as private
helpers.

The unified `createProviderRow(result, kind, statText)` signature described in the success
criteria is NOT required for Phase 2 — that would be a refactor. Phase 2 is extraction only.
The planner should note: the success criteria says `row-factory.ts` has `createProviderRow(result, kind, statText)` as a unified API. This is a new signature that wraps `createDetailRow` and `createContextRow`. The implementation should:
1. Extract both functions verbatim into `row-factory.ts`
2. Add a thin `createProviderRow` wrapper that dispatches based on whether the provider is in `CONTEXT_PROVIDERS`

The wrapper keeps the success criteria satisfied without changing behavior.

```typescript
// Unified dispatcher (new code, thin wrapper — not a refactor of internals)
export function createProviderRow(
  result: EnrichmentResultItem,
  kind: "context" | "detail",
  statText: string
): HTMLElement {
  if (kind === "context") {
    return createContextRow(result);
  }
  return createDetailRow(result.provider, result.verdict, statText, result);
}
```

Note: `createDetailRow` takes `(provider, verdict, statText, result?)` — the `kind` parameter
dispatches between the two existing functions. `enrichment.ts` callers can migrate to
`createProviderRow` or keep calling the individual functions directly; both work since both
are exported.

### Pattern 3: Trimmed enrichment.ts — State Owner + Polling Orchestrator

After extraction, `enrichment.ts` retains:

- `sortTimers` and `allResults` module state
- `sortDetailRows()` — DOM sort function (uses the state map)
- `findCopyButtonForIoc()` — DOM query helper
- `updateCopyButtonWorstVerdict()` — DOM mutation
- `updateProgressBar()`, `updatePendingIndicator()`, `showEnrichWarning()`, `markEnrichmentComplete()` — UI state functions
- `wireExpandToggles()` — event wiring
- `initExportButton()` — event wiring
- `renderEnrichmentResult()` — the main result handler (orchestrator)
- `init()` — public entry point

The imports change from internal definitions to cross-module imports:

```typescript
// New imports for enrichment.ts after extraction
import { VerdictEntry, computeWorstVerdict, computeConsensus, computeAttribution,
         findWorstEntry, consensusBadgeClass } from "./verdict-compute";
import { CONTEXT_PROVIDERS, createContextRow, createDetailRow, createProviderRow,
         updateSummaryRow } from "./row-factory";
```

### Anti-Patterns to Avoid

- **Refactor while extracting:** Do not rename functions, change signatures, or improve code while moving it. Zero changes to logic.
- **Partial extraction:** Do not leave some functions in `enrichment.ts` and some in the new file if they are tightly coupled. `CONTEXT_PROVIDERS` must move with `createContextRow` — they are one logical unit.
- **Merging the build step with the extraction:** Run `make typecheck && make js-dev` after EACH file addition, before trimming `enrichment.ts`. This catches import errors immediately.
- **Moving VerdictEntry without updating all consumers:** `VerdictEntry` is used in `enrichment.ts` function signatures after extraction. Update all references when the interface moves.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module resolution for IIFE | Custom namespace/global wrapping | esbuild `--bundle` | esbuild resolves all TypeScript imports into the bundle automatically; no runtime module system needed |
| Circular import detection | Manual dependency graph | `tsc --noEmit` + esbuild build | TypeScript and esbuild both error on circular imports immediately |
| Test isolation for extracted modules | Unit test harnesses for pure TS functions | The existing E2E suite | E2E tests validate behavior; the extraction goal is behavioral identity, not new unit test coverage |

**Key insight:** The IIFE output format means there is no "module boundary" in the compiled output. Any TypeScript import reorganization that compiles cleanly produces an equivalent bundle. The E2E tests are the ground truth — if they pass, the extraction is correct.

---

## Common Pitfalls

### Pitfall 1: Forgetting VerdictEntry is used by both extracted modules

**What goes wrong:** `VerdictEntry` starts in `enrichment.ts`. After moving it to `verdict-compute.ts`,
`row-factory.ts` also needs it (the row builders take `VerdictEntry` fields as parameters indirectly
through `EnrichmentItem`). But `createDetailRow` takes `(provider, verdict, statText, result?)` —
`VerdictEntry` is NOT directly in its signature. The accumulation side (`renderEnrichmentResult`
pushing into `iocVerdicts`) stays in `enrichment.ts`. Only `verdict-compute.ts` and `enrichment.ts`
need `VerdictEntry` directly.

**How to avoid:** Map the type dependencies before moving any code. `VerdictEntry` is needed by:
- `verdict-compute.ts` (all five functions take/return it)
- `enrichment.ts` (the `iocVerdicts` record and `renderEnrichmentResult` body)
`row-factory.ts` does NOT need `VerdictEntry` — `updateSummaryRow` takes
`Record<string, VerdictEntry[]>` which requires the import.

**Correction:** `updateSummaryRow` takes `iocVerdicts: Record<string, VerdictEntry[]>` as a
parameter, so `row-factory.ts` DOES need to import `VerdictEntry` from `verdict-compute.ts`.
The dependency graph is: `row-factory.ts` → `verdict-compute.ts` → `types/ioc.ts`.

### Pitfall 2: Circular import between row-factory.ts and enrichment.ts

**What goes wrong:** `updateSummaryRow` is called from `renderEnrichmentResult` in `enrichment.ts`.
If `updateSummaryRow` is in `row-factory.ts` AND `row-factory.ts` imports anything from `enrichment.ts`,
there is a circular dependency.

**How to avoid:** Verify the dependency direction is one-way:
```
enrichment.ts → verdict-compute.ts (pure functions)
enrichment.ts → row-factory.ts     (DOM builders)
row-factory.ts → verdict-compute.ts (VerdictEntry type)
row-factory.ts → types/api.ts       (EnrichmentResultItem)
row-factory.ts → types/ioc.ts       (VERDICT_LABELS, VerdictKey)
verdict-compute.ts → types/ioc.ts   (verdictSeverityIndex, VerdictKey)
```

`row-factory.ts` must NOT import from `enrichment.ts`. If a function needs something from
`enrichment.ts`, it must either be passed as a parameter or moved to a shared module.
In this case, `updateSummaryRow` calls `computeWorstVerdict`, `computeAttribution`,
`computeConsensus` — all of which should be in `verdict-compute.ts`, so `row-factory.ts`
imports `verdict-compute.ts` directly. No circular dependency.

**Warning signs:** `tsc --noEmit` emits "TS2442: Circular reference" or esbuild hangs.

### Pitfall 3: noUncheckedIndexedAccess strictness on VerdictEntry lookups

**What goes wrong:** `tsconfig.json` has `"noUncheckedIndexedAccess": true`. After extracting
`VerdictEntry` and marking `iocVerdicts` as `Record<string, VerdictEntry[]>`, any access like
`iocVerdicts[result.ioc_value]` returns `VerdictEntry[] | undefined`. Functions like
`computeWorstVerdict(iocVerdicts[result.ioc_value])` will fail to compile.

**How to avoid:** The existing code already handles this with null-coalescing (`?? []`).
When moving code, preserve the existing null-safety patterns exactly:
```typescript
// Current pattern (already correct — preserve verbatim):
entries.push({ ... });
iocVerdicts[result.ioc_value] = entries;
const worstVerdict = computeWorstVerdict(iocVerdicts[result.ioc_value] ?? []);
```
Do not "simplify" these patterns during extraction.

### Pitfall 4: The build does not automatically recompile

**What goes wrong:** Changes to `enrichment.ts` and new file additions are written to disk, but
the developer verifies against the previous `main.js` build.

**How to avoid:** Always run `make js-dev` after each file creation and after each trim of
`enrichment.ts`. The E2E test infrastructure runs the live Flask app which serves the compiled
`main.js` from `app/static/dist/` — stale builds produce false negatives.

### Pitfall 5: updateSummaryRow calls computeWorstVerdict/computeConsensus/computeAttribution

**What goes wrong:** If `updateSummaryRow` moves to `row-factory.ts` but the compute functions
remain temporarily in `enrichment.ts`, the build fails until both moves happen together or the
compute functions are extracted first.

**How to avoid:** Extraction order matters. Extract in this sequence:
1. `verdict-compute.ts` first (no dependencies on other new files)
2. `row-factory.ts` second (depends on `verdict-compute.ts`)
3. Trim `enrichment.ts` last (now imports from both new files)

This is the safest extraction order — each step produces a compilable state.

---

## Code Examples

### Import Pattern for verdict-compute.ts

```typescript
// Source: enrichment.ts current imports, adapted for new module
// app/static/src/ts/modules/verdict-compute.ts
import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";

export interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
  detectionCount: number;
  totalEngines: number;
  statText: string;
}
```

### Import Pattern for row-factory.ts

```typescript
// app/static/src/ts/modules/row-factory.ts
import type { EnrichmentResultItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { VERDICT_LABELS } from "../types/ioc";
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict, computeConsensus, computeAttribution,
         consensusBadgeClass } from "./verdict-compute";
```

### Import additions for enrichment.ts after extraction

```typescript
// New imports added to enrichment.ts (replaces inline definitions)
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict, findWorstEntry } from "./verdict-compute";
import { CONTEXT_PROVIDERS, createContextRow, createDetailRow,
         updateSummaryRow } from "./row-factory";
```

### Build verification sequence

```bash
# After adding verdict-compute.ts:
tsc --noEmit && make js-dev

# After adding row-factory.ts:
tsc --noEmit && make js-dev

# After trimming enrichment.ts:
tsc --noEmit && make js-dev && pytest tests/ -m e2e --tb=short
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single monolith `main.js` | TypeScript modules + esbuild bundle | Prior refactor (v7.0 partial) | Already modularized; this phase completes the pattern |
| `main.js` global functions | Module-scoped functions with explicit exports | Prior refactor | No global namespace pollution — esbuild IIFE wraps everything |

**No deprecated patterns in scope.** The TypeScript + esbuild + IIFE stack is already the
current architecture. Phase 2 is fully within the established pattern.

---

## Open Questions

1. **Should `formatDate` and `formatRelativeTime` move to `utils/dom.ts` or stay in `row-factory.ts`?**
   - What we know: Both functions are currently in `enrichment.ts`. They are only called from
     row-building code (`createContextRow`, `createDetailRow`). They contain no DOM access.
   - What's unclear: Are they general utilities or domain-specific row helpers?
   - Recommendation: Move to `row-factory.ts` as private helpers. They are exclusively used
     by row construction and are not general DOM utilities. `utils/dom.ts` is for cross-module
     DOM utilities (like `attr()`), not domain-specific formatters.

2. **Does the `createProviderRow` unified wrapper belong in Phase 2 or Phase 3?**
   - What we know: The success criteria explicitly names `createProviderRow(result, kind, statText)`
     as the public API for `row-factory.ts`. Phase 3 (Visual Redesign) will call this function
     when changing row appearance.
   - What's unclear: Whether a thin dispatcher wrapper counts as "zero behavioral change" or
     introduces risk.
   - Recommendation: Include the wrapper in Phase 2 as a thin dispatcher. The wrapper contains
     no logic — it only routes between the two existing functions. Phase 3 then has a stable
     API to target.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + playwright-pytest (E2E) |
| Config file | `tests/e2e/conftest.py` |
| Quick run command | `pytest tests/ -m e2e --tb=short -q` |
| Full suite command | `pytest tests/ -m e2e --tb=short` |

### Phase Requirements → Test Map

This phase has no requirement IDs from REQUIREMENTS.md (it is an architectural refactor).
The test gate is behavioral identity: all 91 E2E tests must pass unchanged.

| Behavior | Test Type | Automated Command | Status |
|----------|-----------|-------------------|--------|
| E2E behavioral identity after extraction | E2E suite | `pytest tests/ -m e2e --tb=short` | Existing — 91 tests |
| TypeScript type safety of extracted modules | Typecheck | `tsc --noEmit` | Existing |
| Bundle compiles without errors | Build | `make js-dev` | Existing |

### Sampling Rate
- **Per file creation (verdict-compute.ts, row-factory.ts):** `tsc --noEmit && make js-dev`
- **After each trim of enrichment.ts:** `tsc --noEmit && make js-dev`
- **Phase gate (after all extractions):** `pytest tests/ -m e2e --tb=short` — 91 passed required

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. No new test files are needed.
The E2E suite validates behavioral identity. TypeScript strict mode validates type safety.

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `enrichment.ts` (928 LOC — complete function inventory)
- Direct code reading: `tsconfig.json` — strict, noUncheckedIndexedAccess, Bundler moduleResolution
- Direct code reading: `Makefile` — esbuild 0.27.3, `--format=iife --bundle --platform=browser`
- Direct code reading: `main.ts` — single entry point, all modules imported here
- Direct code reading: `types/ioc.ts`, `types/api.ts`, `utils/dom.ts` — existing type infrastructure
- Direct code reading: `modules/cards.ts` — established module pattern for reference
- Direct code reading: Phase 1 `CSS-CONTRACTS.md` — locked class names that must not change

### Secondary (MEDIUM confidence)
- E2E test count confirmed: `pytest --collect-only -m e2e` → 91 collected (verified live)
- esbuild IIFE behavior: documented in Makefile + confirmed by existing working bundle

### Tertiary (LOW confidence — none for this phase)
The technical domain is fully covered by direct code inspection. No speculative findings.

---

## Metadata

**Confidence breakdown:**
- Function inventory (what to move): HIGH — read all 928 lines directly
- Dependency graph (import order): HIGH — traced all imports in enrichment.ts manually
- Build system behavior: HIGH — Makefile read directly, esbuild IIFE is the established pattern
- Circular import risk: HIGH — mapped dependency graph completely
- noUncheckedIndexedAccess pitfalls: HIGH — tsconfig read, patterns verified in existing code

**Research date:** 2026-03-17
**Valid until:** Stable (esbuild and TypeScript versions are locked in tools/ and tsconfig.json)

---

## Complete Function Inventory

Full accounting of every function in `enrichment.ts` (928 LOC) and its destination after extraction.

### Moves to verdict-compute.ts (~80 LOC)

| Function/Const | Lines | Type | Has DOM? |
|----------------|-------|------|----------|
| `VerdictEntry` (interface) | 34-41 | Type | No |
| `computeWorstVerdict` | 95-102 | Pure fn | No |
| `computeConsensus` | 108-122 | Pure fn | No |
| `consensusBadgeClass` | 128-132 | Pure fn | No |
| `computeAttribution` | 139-159 | Pure fn | No |
| `findWorstEntry` | 519-532 | Pure fn | No |

### Moves to row-factory.ts (~150 LOC)

| Function/Const | Lines | Type | Has DOM? |
|----------------|-------|------|----------|
| `ContextFieldDef` (interface) | 227-231 | Type | No |
| `PROVIDER_CONTEXT_FIELDS` | 233-309 | Const | No |
| `CONTEXT_PROVIDERS` (Set) | 315 | Const | No |
| `formatDate` | 58-65 | Helper | No |
| `formatRelativeTime` | 71-84 | Helper | No |
| `createLabeledField` | 321-331 | DOM builder | Yes |
| `createContextFields` | 338-376 | DOM builder | Yes |
| `createContextRow` | 384-411 | DOM builder | Yes |
| `createDetailRow` | 417-461 | DOM builder | Yes |
| `getOrCreateSummaryRow` | 165-181 | DOM builder | Yes |
| `updateSummaryRow` | 188-222 | DOM builder | Yes |
| `createProviderRow` (NEW wrapper) | — | Dispatcher | No |

### Stays in enrichment.ts (~300 LOC)

| Function/Const | Lines | Type | Notes |
|----------------|-------|------|-------|
| `sortTimers` | 46 | State | Per-IOC debounce timers |
| `allResults` | 49 | State | Export accumulator |
| `sortDetailRows` | 468-498 | DOM sort | Uses sortTimers state |
| `findCopyButtonForIoc` | 504-513 | DOM query | |
| `updateCopyButtonWorstVerdict` | 539-550 | DOM mutation | |
| `updateProgressBar` | 556-564 | DOM mutation | |
| `updatePendingIndicator` | 572-601 | DOM mutation | |
| `showEnrichWarning` | 607-613 | DOM mutation | |
| `markEnrichmentComplete` | 620-633 | DOM mutation | |
| `wireExpandToggles` | 777-788 | Event wiring | |
| `initExportButton` | 795-827 | Event wiring | |
| `renderEnrichmentResult` | 647-769 | Orchestrator | Main result handler |
| `init` | 847-927 | Public API | Exported entry point |