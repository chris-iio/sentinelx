# Phase 22: Enrichment Module and Entry Point - Research

**Researched:** 2026-03-01
**Domain:** TypeScript module extraction — enrichment polling, main.ts entry point, template cleanup, original JS deletion
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOD-01 | `main.ts` imports and initializes all feature modules as the esbuild entry point | All six Phase 21 modules export `init()` — main.ts only needs to import them and wire DOMContentLoaded; pattern is identical to the existing placeholder |
| MOD-04 | Enrichment polling module: fetch loop, progress bar, result rendering, warning banner | Full enrichment logic (lines 316-643 in main.js) is mapped and typed; all dependent APIs (cards, clipboard, types) are already exported |
| SAFE-03 | Original `main.js` deleted after migration verified complete | `app/static/main.js` exists at 835 lines; deletion is a `git rm` after the TypeScript bundle is confirmed working |
| SAFE-04 | `base.html` script tag updated to reference `dist/main.js` | `base.html` currently loads BOTH `dist/main.js` (line 35) AND `main.js` (line 36) — SAFE-04 means removing the `main.js` line (the `dist/main.js` line already exists) |
</phase_requirements>

---

## Summary

Phase 22 completes the TypeScript migration by implementing two remaining items: the complex `enrichment.ts` module (~250 lines of logic) and the real `main.ts` entry point that wires all modules together. The phase also performs two cleanup operations: removing the duplicate `main.js` script tag from `base.html` and deleting the original `app/static/main.js` file from the repository.

The technical foundation is fully in place. All type definitions (`EnrichmentItem`, `EnrichmentStatus`, `VerdictKey`, `IOC_PROVIDER_COUNTS`, `VERDICT_LABELS`) are defined in `types/`. All dependent module APIs (`updateCardVerdict`, `updateDashboardCounts`, `sortCardsBySeverity`, `findCardForIoc` from `cards.ts`; `writeToClipboard` from `clipboard.ts`; `attr` from `utils/dom.ts`) are already exported. The six Phase 21 modules each export a single `init()` function. The build pipeline (`make js`) is operational and produces `dist/main.js`.

The enrichment module is complex because it manages mutable state that spans multiple render calls (the `rendered` dedup map, `iocVerdicts` accumulator, `iocResultCounts` counter). These require typed interfaces to satisfy `strict: true` and `noUncheckedIndexedAccess`. The critical constraint is zero behavioral change — the TypeScript port must produce byte-for-byte equivalent behavior to the original vanilla JS.

**Primary recommendation:** Extract `enrichment.ts` first (the hard part), then replace the `main.ts` placeholder, then clean up `base.html` and delete `main.js` as the final atomic step after verifying `dist/main.js` works.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | 5.8 (tsc binary) | Type checking | Already installed, tsconfig configured |
| esbuild | 0.27.3 (standalone binary) | Bundling to IIFE | Already installed, `make js` works |
| Browser Fetch API | Native | Enrichment polling HTTP calls | CSP-safe, no imports needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `types/ioc.ts` | Project | `VerdictKey`, `IocType`, `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` | Import for all verdict/type operations |
| `types/api.ts` | Project | `EnrichmentItem`, `EnrichmentResultItem`, `EnrichmentErrorItem`, `EnrichmentStatus` | Import for typed polling response |
| `utils/dom.ts` | Project | `attr()` helper | Import for all `getAttribute` calls |
| `modules/cards.ts` | Project | `updateCardVerdict`, `updateDashboardCounts`, `sortCardsBySeverity`, `findCardForIoc` | Import for card DOM mutations |
| `modules/clipboard.ts` | Project | `writeToClipboard` | Import for export button clipboard write |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Module-level state (rendered, iocVerdicts, iocResultCounts) | Class-based encapsulation | Class adds complexity with no benefit here; closure state is simpler and consistent with other modules |
| `Record<string, ...>` for accumulator | `Map<string, ...>` | `Map` is cleaner but `Record` matches the original JS pattern and works fine for string keys |

**Installation:** No new packages — all tooling already installed.

---

## Architecture Patterns

### Recommended Project Structure

The existing TypeScript tree after Phase 22 completes:

```
app/static/src/ts/
├── main.ts                    # Entry point — imports all modules, wires DOMContentLoaded
├── types/
│   ├── ioc.ts                 # VerdictKey, IocType, VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS
│   └── api.ts                 # EnrichmentItem, EnrichmentStatus (discriminated union)
├── utils/
│   └── dom.ts                 # attr() helper
└── modules/
    ├── enrichment.ts          # NEW: polling loop, progress, rendering, warning, export
    ├── form.ts                # Phase 21
    ├── clipboard.ts           # Phase 21
    ├── cards.ts               # Phase 21
    ├── filter.ts              # Phase 21
    ├── settings.ts            # Phase 21
    └── ui.ts                  # Phase 21
```

### Pattern 1: Module-Level Typed State with `Record<string, T>`

The enrichment polling loop maintains three mutable accumulators across interval ticks. These must be typed as `Record` interfaces, not `any`.

**What:** Typed accumulator state declared in the `initEnrichmentPolling` function scope, shared by the interval callback closure.

**When to use:** Any time enrichment result data must survive across multiple fetch() calls.

```typescript
// Source: typed translation of main.js lines 325-332

/** Per-IOC verdict entry — one per provider result for this IOC. */
interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
}

// Inside initEnrichmentPolling():
const rendered: Record<string, boolean> = {};
const iocVerdicts: Record<string, VerdictEntry[]> = {};
const iocResultCounts: Record<string, number> = {};
```

The `VerdictEntry` interface is a new local interface (not exported). It lives at the top of `enrichment.ts` since it's only used internally.

### Pattern 2: Discriminated Union Narrowing for EnrichmentItem

The polling response contains a union of result/error items. TypeScript narrows correctly on the `type` discriminant.

```typescript
// Source: typed translation of main.js lines 346-363 + renderEnrichmentResult()

function renderEnrichmentResult(
  result: EnrichmentItem,
  iocVerdicts: Record<string, VerdictEntry[]>,
  iocResultCounts: Record<string, number>
): void {
  // ...DOM lookup...

  let summaryText = "";
  let verdict: VerdictKey;

  if (result.type === "result") {
    // TypeScript narrows result to EnrichmentResultItem here
    verdict = result.verdict;
    // result.detection_count, result.total_engines, result.scan_date all available
  } else {
    // TypeScript narrows result to EnrichmentErrorItem here
    verdict = "error";
    // result.error available
  }
}
```

### Pattern 3: noUncheckedIndexedAccess — Defensive Access Pattern

`tsconfig.json` has `noUncheckedIndexedAccess: true`. Any `Record<string, T>` index returns `T | undefined`. Use nullish coalescing.

```typescript
// Source: pattern established in cards.ts (line 84)

// WRONG (TypeScript error under noUncheckedIndexedAccess):
iocResultCounts[result.ioc_value] + 1

// CORRECT:
iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;

// WRONG:
if (!iocVerdicts[result.ioc_value]) {
  iocVerdicts[result.ioc_value] = [];
}
iocVerdicts[result.ioc_value].push(...)  // still possibly undefined after if-check

// CORRECT:
const entries = iocVerdicts[result.ioc_value] ?? [];
iocVerdicts[result.ioc_value] = entries;
entries.push({ provider: result.provider, verdict, summaryText });
```

### Pattern 4: Timer Type — ReturnType<typeof setInterval>

The interval ID must use `ReturnType<typeof setInterval>`, matching the timer pattern from other modules.

```typescript
// Source: pattern from cards.ts line 16, form.ts line 12

// WRONG:
let intervalId: number = setInterval(...)

// CORRECT (consistent with project pattern):
let intervalId: ReturnType<typeof setInterval> | null = null;
// ...
intervalId = setInterval(function() { ... }, 750);
// ...
clearInterval(intervalId);
```

### Pattern 5: main.ts Entry Point

The entry point replaces the Phase 19 placeholder and mirrors the IIFE `init()` function in `main.js` lines 838-856.

```typescript
// Replaces the placeholder in app/static/src/ts/main.ts

import { init as initForm } from "./modules/form";
import { init as initClipboard } from "./modules/clipboard";
import { init as initCards } from "./modules/cards";
import { init as initFilter } from "./modules/filter";
import { init as initSettings } from "./modules/settings";
import { init as initUi } from "./modules/ui";
import { init as initEnrichment } from "./modules/enrichment";

function init(): void {
  initForm();
  initClipboard();
  initCards();
  initFilter();
  initEnrichment();
  initSettings();
  initUi();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
```

Note: esbuild IIFE format wraps all module code in an immediately-invoked function automatically — no manual IIFE wrapper needed in `main.ts`.

### Pattern 6: base.html Cleanup (SAFE-04)

`base.html` currently has TWO script tags (lines 35-36). SAFE-04 requires removing only the `main.js` line. The `dist/main.js` line already exists and must stay.

```html
<!-- CURRENT state (both lines present): -->
<script src="{{ url_for('static', filename='dist/main.js') }}" defer></script>
<script src="{{ url_for('static', filename='main.js') }}" defer></script>

<!-- AFTER Phase 22 (only dist/main.js remains): -->
<script src="{{ url_for('static', filename='dist/main.js') }}" defer></script>
```

### Anti-Patterns to Avoid

- **Non-null assertions (`!`):** All existing Phase 21 modules use `if (!el) return` guards. `enrichment.ts` must follow the same pattern — no `!` operator anywhere.
- **`any` type:** The accumulator maps `iocVerdicts` and `iocResultCounts` must be typed with explicit interfaces, not `any`.
- **Deleting `main.js` before verifying the bundle:** The deletion (SAFE-03) must happen after confirming the compiled `dist/main.js` is behaviorally equivalent. Sequence matters: implement → build → test → delete.
- **Removing both script tags simultaneously:** Only remove the `main.js` script tag. The `dist/main.js` tag must remain.
- **`VERDICT_LABELS[verdict]` direct access without fallback:** Under `noUncheckedIndexedAccess`, `Record<VerdictKey, string>` indexed with a `VerdictKey` is actually safe (known keys). But if the verdict comes from a runtime string cast, add a fallback: `VERDICT_LABELS[verdict] ?? verdict.toUpperCase()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verdict severity comparison | Custom severity comparison logic | `VERDICT_SEVERITY.indexOf(v)` from `types/ioc.ts` | Already implemented, typed as `readonly VerdictKey[]` |
| Card DOM lookup | Custom `querySelector` logic | `findCardForIoc()` from `cards.ts` | CSS.escape handled, type-safe |
| Clipboard write with feedback | Custom clipboard implementation | `writeToClipboard()` from `clipboard.ts` | Fallback copy covered, already tested |
| Dashboard count update | Custom count logic | `updateDashboardCounts()` from `cards.ts` | Already typed and tested |
| Card sort | Custom sort logic | `sortCardsBySeverity()` from `cards.ts` | Debounced, already typed |
| Card verdict update | Custom DOM mutation | `updateCardVerdict()` from `cards.ts` | CSS class management handled |

**Key insight:** Phase 21 was specifically designed to expose exactly the APIs that Phase 22 needs. The enrichment module is a consumer of the cards and clipboard modules — it should not re-implement any of their logic.

---

## Common Pitfalls

### Pitfall 1: noUncheckedIndexedAccess with Record accumulators

**What goes wrong:** TypeScript reports errors on `iocResultCounts[key] + 1` and `iocVerdicts[key].push(...)` because indexed access returns `T | undefined` even with `Record<string, T>`.

**Why it happens:** `noUncheckedIndexedAccess` treats all string-keyed index access as potentially undefined, even when the key was just assigned.

**How to avoid:** Always use nullish coalescing for reads: `(iocResultCounts[key] ?? 0) + 1`. For push operations, assign to a local: `const arr = iocVerdicts[key] ?? []; iocVerdicts[key] = arr; arr.push(item)`.

**Warning signs:** TypeScript error "Object is possibly 'undefined'" on accumulator read operations.

### Pitfall 2: Timer type mismatch with setInterval vs setTimeout

**What goes wrong:** Using `ReturnType<typeof setTimeout>` for the interval ID — while structurally compatible in browsers, it signals intent incorrectly and may confuse future readers.

**Why it happens:** Copy-paste from the setTimeout pattern used in other modules.

**How to avoid:** Use `ReturnType<typeof setInterval>` for the interval, consistent with the function used. The pattern `let intervalId: ReturnType<typeof setInterval>` mirrors how the modules handle timers.

**Warning signs:** Lint warning or code review noting semantic mismatch.

### Pitfall 3: Deleting main.js before bundle is verified working

**What goes wrong:** `dist/main.js` is compiled from the incomplete `main.ts` placeholder (just `export {}`). If `main.js` is deleted at the start of the phase rather than the end, the app breaks for the entire development period.

**Why it happens:** The deletion feels like "step 1" since it's listed as SAFE-03, but it's actually the final step.

**How to avoid:** Sequence is: implement enrichment.ts → implement main.ts → build → verify browser behavior → THEN delete main.js and remove the duplicate script tag.

**Warning signs:** App loads with no enrichment polling (silent failure because `dist/main.js` is the Phase 19 placeholder that does nothing).

### Pitfall 4: Both script tags running concurrently during development

**What goes wrong:** During Phase 22 development, `base.html` loads both `dist/main.js` (built from new TypeScript) and `main.js` (original). This means event listeners are registered twice — double polling, double filter wiring, etc.

**Why it happens:** The `dist/main.js` tag was added in Phase 19 plan 02, but `main.js` was not yet removed (that's SAFE-03/SAFE-04 in Phase 22).

**How to avoid:** Development testing should remove the `main.js` tag locally during development to isolate the TypeScript bundle. The phase plan should account for this: either temporarily comment out `main.js` during dev, or run final verification with both removed simultaneously as the last step.

**Warning signs:** Enrichment results appearing twice in cards, duplicate event listeners firing.

### Pitfall 5: formatDate with null scan_date under strict TypeScript

**What goes wrong:** `result.scan_date` in `EnrichmentResultItem` is typed `string | null`. Passing it directly to `formatDate(iso: string)` causes a type error.

**Why it happens:** The original JS `formatDate` accepted `null` implicitly; TypeScript enforces the parameter type.

**How to avoid:** Define `formatDate` as `(iso: string | null): string` — then the early return `if (!iso) return ""` satisfies the type check.

```typescript
function formatDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}
```

### Pitfall 6: IOC_PROVIDER_COUNTS indexed with runtime ioc_type string

**What goes wrong:** `result.ioc_type` is typed `string` (not `IocType`), but `IOC_PROVIDER_COUNTS` is `Record<IocType, number>`. Direct indexing causes a type error.

**Why it happens:** The API response `ioc_type` field could theoretically be any string — TypeScript won't let you index a `Record<IocType, number>` with `string`.

**How to avoid:** Either cast with a type guard, or use a safe access pattern:

```typescript
// Safe pattern — no type assertion needed
const totalExpected = Object.prototype.hasOwnProperty.call(IOC_PROVIDER_COUNTS, iocType)
  ? IOC_PROVIDER_COUNTS[iocType as IocType]
  : 0;
```

---

## Code Examples

### enrichment.ts Module Shell

```typescript
// app/static/src/ts/modules/enrichment.ts

import type { EnrichmentItem, EnrichmentStatus } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { VERDICT_LABELS, VERDICT_SEVERITY, IOC_PROVIDER_COUNTS } from "../types/ioc";
import { attr } from "../utils/dom";
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
import { writeToClipboard } from "./clipboard";

/** Per-provider verdict entry for a single IOC. Used in iocVerdicts accumulator. */
interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
}

export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  const jobId = attr(pageResults, "data-job-id");
  const mode = attr(pageResults, "data-mode");

  if (!jobId || mode !== "online") return;

  const rendered: Record<string, boolean> = {};
  const iocVerdicts: Record<string, VerdictEntry[]> = {};
  const iocResultCounts: Record<string, number> = {};

  const intervalId = setInterval(function () {
    fetch("/enrichment/status/" + jobId)
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json() as Promise<EnrichmentStatus>;
      })
      .then(function (data: EnrichmentStatus | null) {
        if (!data) return;
        // ... polling logic
      })
      .catch(function () {
        // Fetch error — silently continue
      });
  }, 750);
}
```

### Worst-Verdict Computation (Typed)

```typescript
// Typed translation of main.js computeWorstVerdict() lines 565-578

function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  if (entries.length === 0) return "no_data";
  let worst = entries[0];
  if (!worst) return "no_data"; // noUncheckedIndexedAccess guard
  for (let i = 1; i < entries.length; i++) {
    const entry = entries[i];
    if (!entry) continue;
    if (VERDICT_SEVERITY.indexOf(entry.verdict) > VERDICT_SEVERITY.indexOf(worst.verdict)) {
      worst = entry;
    }
  }
  return worst.verdict;
}
```

### findCopyButtonForIoc (Typed)

```typescript
// Typed translation of main.js findCopyButtonForIoc() lines 594-603

function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
  const btns = document.querySelectorAll<HTMLElement>(".copy-btn");
  for (const btn of btns) {
    if (attr(btn, "data-value") === iocValue) {
      return btn;
    }
  }
  return null;
}
```

### getOrCreateNodataSection (Typed)

```typescript
// Typed translation of main.js getOrCreateNodataSection() lines 408-427

function getOrCreateNodataSection(slot: HTMLElement): HTMLDetailsElement {
  const existing = slot.querySelector<HTMLDetailsElement>(".enrichment-nodata-section");
  if (existing) return existing;

  const details = document.createElement("details");
  details.className = "enrichment-nodata-section";

  const summary = document.createElement("summary");
  summary.className = "enrichment-nodata-summary";
  summary.textContent = "1 provider: no record";

  details.appendChild(summary);
  slot.appendChild(details);
  return details;
}
```

### initExportButton (inside init() or as helper)

```typescript
// Typed translation of main.js initExportButton() lines 636-666

function initExportButton(): void {
  const exportBtn = document.getElementById("export-btn");
  if (!exportBtn) return;

  exportBtn.addEventListener("click", function () {
    const lines: string[] = [];
    const iocCards = document.querySelectorAll<HTMLElement>(".ioc-card");

    iocCards.forEach(function (card) {
      const valueEl = card.querySelector<HTMLElement>(".ioc-value");
      if (!valueEl) return;
      const iocValue = (valueEl.textContent ?? "").trim();
      const copyBtn = findCopyButtonForIoc(iocValue);
      const enrichment = copyBtn ? attr(copyBtn, "data-enrichment") : "";
      lines.push(enrichment ? iocValue + " | " + enrichment : iocValue);
    });

    writeToClipboard(lines.join("\n"), exportBtn);
  });
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `var` with function-scoped closures | `const`/`let` with block scope | Phase 22 | Cleaner closure capture, no IIFE hoisting issues |
| `Object.prototype.hasOwnProperty.call(counts, v)` | Direct `Record<K,V>` access with nullish coalescing | Phase 22 | Type-safe, less ceremony |
| `Array.prototype.slice.call(nodeList)` | `Array.from(nodeList)` or `for...of` | Phase 22 | Native iteration, typed |
| Manual `for (var i = 0; ...)` loops | `forEach`, `for...of` | Phase 22 | Consistent with Phase 21 module style |

**Important:** The behavioral translation must be exact. The "state of the art" changes listed here are permissible modernizations (consistent with QUAL-01 which is future scope) but the critical constraint is zero functional regression.

---

## Phase 22 Execution Sequence

The four requirements have a dependency order that matters:

```
1. enrichment.ts    (MOD-04) — implement the complex module
2. main.ts          (MOD-01) — replace placeholder, import all 7 modules
3. make js          (verify)  — confirm bundle compiles with no errors
4. make typecheck   (verify)  — confirm zero TypeScript errors
5. base.html        (SAFE-04) — remove the main.js script tag (keep dist/main.js)
6. git rm main.js   (SAFE-03) — delete the original file last
```

Steps 5 and 6 are the "point of no return" — they remove the safety net. They must be the final actions after behavioral verification.

---

## Key Observations About the Enrichment Logic

The original enrichment section of `main.js` spans lines 205-643 (approximately 438 lines total including helpers that are shared with other modules). However:

- `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` (lines 205-228) move to `types/ioc.ts` — already done in Phase 20
- `verdictSeverity()` function (lines 230-233) is now `VERDICT_SEVERITY.indexOf()` — no separate function needed
- `findCardForIoc()`, `updateCardVerdict()`, `updateDashboardCounts()`, `sortCardsBySeverity()` (lines 236-314) move to `cards.ts` — already done in Phase 21
- `initCopyButtons()`, `writeToClipboard()`, `fallbackCopy()`, `showCopiedFeedback()` (lines 166-223) move to `clipboard.ts` — already done in Phase 21
- `initFilterBar()` (lines 677-788) moved to `filter.ts` — already done in Phase 21

What remains for `enrichment.ts`:
- `initEnrichmentPolling()` — the fetch loop with state accumulators
- `updateProgressBar()`
- `getOrCreateNodataSection()`
- `updateNodataSummary()`
- `updatePendingIndicator()`
- `renderEnrichmentResult()` — the main render function (calls into cards + clipboard)
- `computeWorstVerdict()`
- `updateCopyButtonWorstVerdict()`
- `findCopyButtonForIoc()`
- `formatDate()`
- `markEnrichmentComplete()`
- `showEnrichWarning()`
- `initExportButton()`

Estimated `enrichment.ts` size: approximately 250-300 lines (after removing the already-extracted helpers).

---

## Open Questions

1. **Double-loading during development**
   - What we know: `base.html` loads both `dist/main.js` and `main.js` concurrently during Phase 22 development
   - What's unclear: Whether the planner should handle this as a separate sub-step (temporarily remove `main.js` tag during dev) or handle it atomically at the end
   - Recommendation: Plan should note this and either (a) have the developer comment out `main.js` tag immediately when starting work, or (b) accept the doubled behavior during dev and verify only at the end

2. **`ioc_type` narrowing for IOC_PROVIDER_COUNTS**
   - What we know: `EnrichmentResultItem.ioc_type` is `string` (from API), but `IOC_PROVIDER_COUNTS` is `Record<IocType, number>`
   - What's unclear: Whether a runtime type guard is needed or a simple type assertion is acceptable
   - Recommendation: Use `hasOwnProperty` check as shown in the pitfalls section — it's the safest approach and avoids type assertions

---

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `/home/chris/projects/sentinelx/app/static/main.js` — enrichment logic (lines 205-643) fully reviewed
- Direct code analysis of all Phase 21 TypeScript modules (`form.ts`, `clipboard.ts`, `cards.ts`, `filter.ts`, `settings.ts`, `ui.ts`) — exported APIs inventoried
- Direct code analysis of `types/ioc.ts` and `types/api.ts` — all type definitions reviewed
- `tsconfig.json` — strict mode settings confirmed
- `Makefile` — build targets and entry point confirmed
- `app/templates/base.html` — dual script tag situation confirmed

### Secondary (MEDIUM confidence)
- TypeScript documentation on `noUncheckedIndexedAccess` behavior with `Record<string, T>` — general TypeScript knowledge, consistent with observed behavior in Phase 21 modules

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tooling is operational from Phases 19-21; no new dependencies
- Architecture: HIGH — direct code reading of source, no inference required
- Pitfalls: HIGH — noUncheckedIndexedAccess patterns verified by reading existing Phase 21 modules that already handle them
- Execution sequence: HIGH — logical dependency ordering, confirmed by reading base.html

**Research date:** 2026-03-01
**Valid until:** Until Phase 23 begins (this research will not become stale — it's based on static analysis of the codebase)
