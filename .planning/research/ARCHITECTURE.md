# Architecture Research

**Domain:** Results page redesign — TypeScript module integration (SentinelX v1.1)
**Researched:** 2026-03-16
**Confidence:** HIGH (full source code review, all modules and templates read directly)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Flask Template Layer                         │
│  results.html -> _ioc_card.html -> _enrichment_slot.html            │
│  (server-rendered shell; enrichment containers start empty)          │
├─────────────────────────────────────────────────────────────────────┤
│                      TypeScript Module Layer                         │
│  main.ts (init orchestrator — 8 modules in fixed init order)         │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│  enrichment  │    cards     │    filter    │  graph / export / etc  │
│  (928 LOC)   │  (136 LOC)   │  (143 LOC)   │  (no redesign impact)  │
│  - polling   │  - verdict   │  - filter    │                        │
│  - rendering │    update    │    state     │                        │
│  - summary   │  - dashboard │  - apply     │                        │
│  - detail    │    counts    │    filter    │                        │
│  - context   │  - sort      │              │                        │
│    row fork  │    cards     │              │                        │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
│                         Data Flow (API)                              │
│  GET /enrichment/status/<job_id> -> EnrichmentStatus JSON            │
│  (750ms polling interval, incremental delivery)                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Integration Points |
|-----------|---------------|-------------------|
| `enrichment.ts` | Polling loop, result rendering, summary row, detail rows, context rows, export button wiring | Calls `cards.ts` for all card mutations. Consumes `EnrichmentItem` from `types/api.ts`. Owns `iocVerdicts`, `iocResultCounts`, `allResults`, `sortTimers` state. |
| `cards.ts` | `updateCardVerdict`, `updateDashboardCounts`, `sortCardsBySeverity`, `findCardForIoc` | Called by `enrichment.ts`. Reads card DOM via `data-ioc-value` / `data-verdict` attributes. |
| `filter.ts` | Verdict/type/search filter state, show/hide cards, active-state sync with dashboard | Reads `.ioc-card[data-verdict]` and `.ioc-card[data-ioc-type]`. Completely independent of enrichment.ts. |
| `graph.ts` | SVG hub-and-spoke graph on detail page only | Reads `data-graph-nodes` / `data-graph-edges` from `#relationship-graph`. No dependency on enrichment.ts. |
| `export.ts` | JSON/CSV download, copy-all-IOCs | Called by `enrichment.ts` export button wiring. Consumes `allResults: EnrichmentItem[]`. |
| `types/api.ts` | `EnrichmentResultItem`, `EnrichmentErrorItem`, `EnrichmentItem`, `EnrichmentStatus` | Pure types — imported by `enrichment.ts` and `export.ts`. Stable API contract. |
| `types/ioc.ts` | `VerdictKey`, `VERDICT_LABELS`, `verdictSeverityIndex`, `getProviderCounts` | Imported by `enrichment.ts`, `cards.ts`. `getProviderCounts()` reads DOM attribute. |
| `utils/dom.ts` | `attr()` typed getAttribute wrapper | Imported by `enrichment.ts`, `cards.ts`, `filter.ts`. |

---

## The Critical Split: Verdict Rows vs Context Rows

This is the primary architectural seam for the redesign.

### Current Rendering Fork (enrichment.ts ~line 662)

```
renderEnrichmentResult(result)
    |
    ├── CONTEXT_PROVIDERS.has(result.provider)?
    │   YES:
    │   ├── remove spinner
    │   ├── createContextRow(result)       -> prepend to .enrichment-details
    │   ├── NO iocVerdicts accumulation
    │   ├── NO summary row update
    │   ├── NO card verdict / dashboard / sort
    │   └── return early
    │
    └── NO (verdict provider):
        ├── remove spinner
        ├── accumulate iocVerdicts[ioc_value]
        ├── createDetailRow(provider, verdict, statText, result)
        │                  -> append to .enrichment-details
        ├── sortDetailRows(detailsContainer, iocValue) [debounced 100ms]
        ├── updateSummaryRow(slot, iocValue, iocVerdicts)
        ├── updatePendingIndicator(slot, card, receivedCount)
        ├── updateCardVerdict(iocValue, worstVerdict)
        ├── updateDashboardCounts()
        ├── sortCardsBySeverity()
        └── updateCopyButtonWorstVerdict(iocValue, iocVerdicts)
```

**CONTEXT_PROVIDERS** (module-scope Set in enrichment.ts):
`"IP Context"`, `"DNS Records"`, `"Cert History"`, `"ThreatMiner"`, `"ASN Intel"`

Context rows: no verdict badge, pinned to top of details container after sort, purely informational, do not participate in consensus/attribution/worst-verdict computation.

### Can the Two Rendering Paths Be Unified?

**Yes — with a typed discriminant parameter, not structural changes to the data.**

The current `CONTEXT_PROVIDERS` set is the correct owner of this mapping (it is a display decision, not a data decision). The rendering fork can be unified into a single `createProviderRow(result, kind)` function where `kind: "verdict" | "context"` controls visual rendering. The fork logic moves from a `if/else` in `renderEnrichmentResult` to a `rowKind` parameter derivation before calling the unified factory.

This approach: no API contract changes, no backend changes, no changes to `types/api.ts`. The `CONTEXT_PROVIDERS` set stays as the source of truth; the two separate creation functions collapse into one. The benefit is that a visual redesign to rows only needs one place to change instead of two.

---

## DOM Attribute Contract

These attributes are read by TypeScript from server-rendered HTML. They are stable across the redesign. Any template change must preserve every attribute in this table.

| Element | Attribute | Consumer | Constraint |
|---------|-----------|----------|------------|
| `.page-results` | `data-job-id` | enrichment.ts init | Required for polling |
| `.page-results` | `data-mode` | enrichment.ts init | `"online"` / `"offline"` |
| `.page-results` | `data-provider-counts` | ioc.ts getProviderCounts() | JSON-encoded dict |
| `.ioc-card` | `data-ioc-value` | cards.ts findCardForIoc, filter.ts | CSS.escape used on read |
| `.ioc-card` | `data-ioc-type` | enrichment.ts updatePendingIndicator, filter.ts | IOC type string |
| `.ioc-card` | `data-verdict` | cards.ts updateCardVerdict, filter.ts, cards.ts sort | Written by updateCardVerdict |
| `.copy-btn` | `data-value` | enrichment.ts findCopyButtonForIoc | Must match ioc_value |
| `.copy-btn` | `data-enrichment` | enrichment.ts updateCopyButtonWorstVerdict | Written at runtime |
| `.enrichment-slot` | (class only) | enrichment.ts renderEnrichmentResult | `--loaded` class triggers chevron visibility |
| `.enrichment-details` | (class only) | enrichment.ts sortDetailRows, createContextRow | `is-open` class controls expand |
| `.chevron-toggle` | `aria-expanded` | enrichment.ts wireExpandToggles | Set on click |
| `[data-filter-verdict]` | attribute value | filter.ts | Verdict name string |
| `[data-filter-type]` | attribute value | filter.ts | IOC type string |
| `[data-verdict-count]` | attribute value | cards.ts updateDashboardCounts | Verdict name string |
| `#relationship-graph` | `data-graph-nodes`, `data-graph-edges` | graph.ts | JSON-encoded arrays |

---

## New Components Required

### New TypeScript Modules (extractions from enrichment.ts)

| Module | LOC | What It Contains | Why Extract |
|--------|-----|-----------------|-------------|
| `verdict-compute.ts` | ~80 | `VerdictEntry` interface, `computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry` | Pure functions with no DOM dependency — correct boundary, easy to test, enables enrichment.ts to focus on orchestration |
| `row-factory.ts` | ~150 | `createProviderRow(result, kind, statText)`, `createContextFields`, `createLabeledField`, `PROVIDER_CONTEXT_FIELDS`, `CONTEXT_PROVIDERS` | All row-building DOM code in one place — the redesign modifies this module only for visual changes |

These extractions are not optional cosmetics. `enrichment.ts` is 928 LOC and will grow during the redesign. Keeping computation mixed with DOM mutation makes it impossible to reason about one without the other.

### New TypeScript Module Public APIs (proposed)

```typescript
// verdict-compute.ts
export interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
  detectionCount: number;
  totalEngines: number;
  statText: string;
}
export function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey
export function computeConsensus(entries: VerdictEntry[]): { flagged: number; responded: number }
export function computeAttribution(entries: VerdictEntry[]): { provider: string; text: string }
export function findWorstEntry(entries: VerdictEntry[]): VerdictEntry | undefined

// row-factory.ts
export type RowKind = "verdict" | "context";
export function rowKindFor(provider: string): RowKind
export function createProviderRow(
  result: EnrichmentResultItem,
  kind: RowKind,
  statText: string      // pre-computed caller responsibility
): HTMLElement
export function createContextFields(result: EnrichmentResultItem): HTMLElement | null
export { CONTEXT_PROVIDERS }  // re-export for enrichment.ts use
```

### Modified Components

| Component | Change Type | What Changes | Risk Level |
|-----------|------------|-------------|------------|
| `enrichment.ts` | Refactor | Remove extracted functions, import from new modules, simplify `renderEnrichmentResult` dispatch | Medium — largest file, but extraction boundaries are mechanically clear |
| `_enrichment_slot.html` | Modify | Structure changes for redesigned summary row layout | Low — only renders a DOM shell |
| `_ioc_card.html` | Modify | Card header changes for new visual design | Low — preserve all `data-*` attributes |
| `results.html` | Possibly modify | New page-level sections if redesign requires them | Low |
| `input.css` | Major | New CSS for redesigned row, card, and summary components | Low risk — CSS-only changes |

### Unchanged Components

`filter.ts`, `graph.ts`, `export.ts`, `form.ts`, `clipboard.ts`, `settings.ts`, `ui.ts`, `types/api.ts`, `types/ioc.ts`, `utils/dom.ts`, `ioc_detail.html`, `main.ts` (no new module inits needed unless new modules need DOMContentLoaded wiring)

---

## Recommended Project Structure

No directory restructuring. The redesign adds new modules within the existing layout.

```
app/static/src/ts/
├── main.ts                     # Add imports for new modules if they export init()
├── modules/
│   ├── enrichment.ts           # MODIFY: trim to ~300 LOC, import from new modules
│   ├── verdict-compute.ts      # NEW: ~80 LOC pure computation
│   ├── row-factory.ts          # NEW: ~150 LOC unified row DOM builder
│   ├── cards.ts                # MINOR or NO CHANGE
│   ├── filter.ts               # NO CHANGE
│   ├── graph.ts                # NO CHANGE
│   ├── export.ts               # NO CHANGE
│   ├── form.ts                 # NO CHANGE
│   ├── clipboard.ts            # NO CHANGE
│   ├── settings.ts             # NO CHANGE
│   └── ui.ts                   # NO CHANGE
├── types/
│   ├── api.ts                  # NO CHANGE
│   └── ioc.ts                  # NO CHANGE
└── utils/
    └── dom.ts                  # NO CHANGE
```

---

## Architectural Patterns

### Pattern 1: Separate Computation from DOM Mutation

**What:** Pure functions that compute values (`computeWorstVerdict`, `computeConsensus`, `computeAttribution`) live in `verdict-compute.ts`. DOM mutation functions that act on those values live in `enrichment.ts` and `row-factory.ts`. Pure functions receive values as parameters — they do not touch the DOM.

**When to use:** Immediately as the first step of the redesign. `enrichment.ts` currently mixes both freely, which makes both harder to change.

**Trade-offs:** One extra file, but `enrichment.ts` becomes a clean orchestrator (~300 LOC) rather than a 928-LOC monolith where computation and rendering are interleaved.

**Example:**
```typescript
// verdict-compute.ts — no DOM imports, no side effects
export function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  if (entries.some((e) => e.verdict === "known_good")) return "known_good";
  const worst = findWorstEntry(entries);
  return worst ? worst.verdict : "no_data";
}
```

### Pattern 2: Unified Row Factory with RowKind Discriminant

**What:** A single `createProviderRow(result, kind, statText)` replaces the separate `createDetailRow` and `createContextRow` functions. Visual rendering diverges on `kind`, not on `CONTEXT_PROVIDERS.has(result.provider)` — that check happens once at the call site.

**When to use:** During the visual redesign. The redesign changes how rows look; having both types in one function means the visual changes happen in one place.

**Trade-offs:** Slightly more complex single function vs two simple functions. Worth it because the two-path design currently requires applying any row layout change in two places.

**Example:**
```typescript
// row-factory.ts
export function createProviderRow(
  result: EnrichmentResultItem,
  kind: RowKind,
  statText: string
): HTMLElement {
  const row = document.createElement("div");
  row.className = kind === "context"
    ? "provider-row provider-row--context"
    : "provider-row provider-row--verdict";
  row.setAttribute("data-verdict", kind === "context" ? "context" : result.verdict);
  // provider name: always
  // verdict badge: verdict rows only
  // stat text: verdict rows only
  // context fields: both kinds, prominence differs
  // cache badge: both kinds
  return row;
}
```

### Pattern 3: Module State Stays in enrichment.ts

**What:** `iocVerdicts`, `iocResultCounts`, `allResults`, and `sortTimers` remain module-private in `enrichment.ts`. New helper modules (`verdict-compute.ts`, `row-factory.ts`) receive values as parameters — they own no state.

**When to use:** Throughout the redesign. Do not create a shared state store.

**Trade-offs:** `enrichment.ts` remains the state owner for results rendering. This is correct — it is the right owner of this state for a single-page polling-based architecture.

---

## Data Flow

### Enrichment Result Flow (post-refactor)

```
Flask /enrichment/status/<job_id>
    | (750ms poll)
EnrichmentStatus { total, done, complete, results: EnrichmentItem[] }
    |
renderEnrichmentResult(result, iocVerdicts, iocResultCounts)
    |
    +-- spinner removal, slot --loaded class
    |
    +-- kind = rowKindFor(result.provider)    [from row-factory.ts]
    |
    +-- if kind === "context":
    |     createProviderRow(result, "context", "") -> prepend to .enrichment-details
    |     updatePendingIndicator(...)
    |     return
    |
    +-- if kind === "verdict":
          statText = buildStatText(result)     [local helper, stays in enrichment.ts]
          accumulate iocVerdicts[ioc_value]    [uses VerdictEntry from verdict-compute.ts]
          createProviderRow(result, "verdict", statText) -> append to .enrichment-details
          sortDetailRows(container, iocValue)  [debounced 100ms]
          updateSummaryRow(slot, iocValue, iocVerdicts)
          updatePendingIndicator(...)
          updateCardVerdict(iocValue, computeWorstVerdict(entries))
          updateDashboardCounts()
          sortCardsBySeverity()
          updateCopyButtonWorstVerdict(...)
```

### State Ownership Map

```
enrichment.ts (module-private)
├── iocVerdicts: Record<string, VerdictEntry[]>      -- per-IOC verdict history
├── iocResultCounts: Record<string, number>           -- for pending indicator
├── allResults: EnrichmentItem[]                      -- for export
├── sortTimers: Map<string, ReturnType<setTimeout>>   -- debounce per IOC
└── rendered: Record<string, boolean>                 -- dedup key per poll

cards.ts (module-private)
└── sortTimer: ReturnType<typeof setTimeout> | null   -- card sort debounce

filter.ts (closure-private inside init())
└── filterState: { verdict: string, type: string, search: string }
```

---

## Suggested Refactoring Order

This order minimizes breakage by ensuring each step has a stable foundation.

### Step 1: Extract verdict-compute.ts

**What to move:** `VerdictEntry` interface, `computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry`. Update `enrichment.ts` imports.

**Why first:** Zero behavioral change. These are pure functions with no DOM or module-state dependencies. Moving them is a mechanical extraction — copy, export, update imports. Reduces `enrichment.ts` by ~90 LOC.

**Downstream benefit:** Steps 2-4 operate on a smaller `enrichment.ts` where computation and mutation are no longer interleaved.

**Risk:** Negligible. TypeScript compiler catches any import errors.

**Test gate:** `tsc` compilation passes. All existing E2E tests pass unchanged.

### Step 2: Extract row-factory.ts

**What to move:** `createDetailRow`, `createContextRow`, `createLabeledField`, `createContextFields`, `PROVIDER_CONTEXT_FIELDS`, `CONTEXT_PROVIDERS`, `formatRelativeTime` (if shared). Expose unified `createProviderRow` and `rowKindFor`. Update `enrichment.ts` to call the new API.

**Why second:** Depends on Step 1 (`VerdictEntry` is now in `verdict-compute.ts`). After this step, `enrichment.ts` is reduced to ~300 LOC and handles only polling, orchestration, and state. The visual redesign in Steps 3-4 happens exclusively inside `row-factory.ts` and `input.css`.

**Risk:** Low. The rendering logic moves location but does not change behavior. Careful import wiring required.

**Test gate:** `tsc` compilation passes. E2E: provider rows render with correct verdict CSS classes, context rows appear above verdict rows, cache badges appear.

### Step 3: Redesign CSS (input.css)

**What:** Replace `.provider-detail-row` / `.provider-context-row` with new component CSS. Redesign `.ioc-summary-row` layout. Update card header styling if needed.

**Why third:** CSS-only change — zero TypeScript risk. Steps 1-2 mean all row class names are managed in `row-factory.ts`, giving a clean surface for the visual redesign.

**Risk:** Visual regression. Run E2E suite after every significant CSS block change.

**Test gate:** Visual inspection of all verdict states (malicious, suspicious, clean, known_good, no_data, error) and all context providers. E2E suite passes.

### Step 4: Redesign HTML Shell

**What:** Update `_ioc_card.html` and `_enrichment_slot.html` for the new visual design. Preserve every attribute in the DOM Attribute Contract table.

**Why fourth:** After CSS is finalized, HTML adjustments lock in the structure. Template changes are lower risk than TypeScript changes.

**Risk:** Breaking DOM attribute contracts. Use the contract table as a pre-commit checklist — every `data-*` attribute listed must survive unchanged.

**Test gate:** E2E suite — filter behavior, enrichment rendering, card sort, export all function correctly.

### Step 5 (optional): Extract summary.ts

**What:** Move `getOrCreateSummaryRow`, `updateSummaryRow`, `updatePendingIndicator`, `consensusBadgeClass` to a new `summary.ts` module.

**Why optional:** Only needed if `enrichment.ts` exceeds ~350 LOC after Steps 1-2. If the file is manageable, skip this step. The summary row functions are tightly coupled to `iocVerdicts` state anyway — extracting them without moving state adds complexity.

**Risk:** Low if done. Skip if not necessary.

---

## Integration Points

### enrichment.ts -> cards.ts (existing, stable, no change)

| Call | When | What It Does |
|------|------|-------------|
| `findCardForIoc(iocValue)` | Every result | Returns `HTMLElement \| null` by `data-ioc-value` |
| `updateCardVerdict(iocValue, worstVerdict)` | After iocVerdicts updated | Sets `data-verdict`, updates `.verdict-label` text + class |
| `updateDashboardCounts()` | After every verdict result | Counts all `.ioc-card[data-verdict]`, updates count elements |
| `sortCardsBySeverity()` | After every verdict result | Debounced 100ms, reorders card grid by worst verdict |

This interface is stable. The redesign does not need to change it.

### enrichment.ts -> verdict-compute.ts (new boundary)

`enrichment.ts` passes `iocVerdicts[ioc_value]` to pure functions and receives computed values back. No shared state, no DOM access in `verdict-compute.ts`.

### enrichment.ts -> row-factory.ts (new boundary)

`enrichment.ts` calls `rowKindFor(result.provider)` to determine kind, then calls `createProviderRow(result, kind, statText)`. The `statText` computation (the `if verdict === "malicious" ...` logic block) stays in `enrichment.ts` — it is caller context, not row-building logic.

### filter.ts <-> cards.ts (indirect, via DOM attributes — no change)

`filter.ts` reads `data-verdict` / `data-ioc-type` / `data-ioc-value` from cards. `cards.ts` writes `data-verdict`. This contract works through DOM attributes and must not be changed. CSS class names on cards can be renamed freely; attribute names must not be renamed.

### Detail Page (ioc_detail.html) — Separate System, No Impact

The detail page uses CSS-only tabs (radio inputs + adjacent sibling selectors). JavaScript has no involvement in tab switching. `graph.ts` renders the SVG relationship graph. The detail page is architecturally independent of the results page and is not part of the redesign scope.

---

## Anti-Patterns

### Anti-Pattern 1: Changing the Flask API Contract to Support the Redesign

**What people do:** Add a `row_kind` field to `EnrichmentResultItem` in the Flask JSON response so the frontend does not need `CONTEXT_PROVIDERS`.

**Why it's wrong:** The rendering decision is a display concern, not a data concern. The Python backend is stable and all 14 providers are working. A backend change requires changes to `app/routes.py`, `app/enrichment/models.py`, `types/api.ts`, and all existing tests.

**Do this instead:** Derive `row_kind` at render time via `rowKindFor(result.provider)` using the `CONTEXT_PROVIDERS` set in `row-factory.ts`. No backend changes.

### Anti-Pattern 2: Refactoring renderEnrichmentResult Before Extracting Pure Functions

**What people do:** Start the redesign by restructuring the rendering dispatch in `renderEnrichmentResult` while computation functions are still inline.

**Why it's wrong:** The computation functions (`computeWorstVerdict` etc.) are entangled with state management code. Refactoring rendering while computation is entangled means touching everything simultaneously.

**Do this instead:** Step 1 (extract `verdict-compute.ts`) takes ~15 minutes and makes all subsequent steps isolated. Never skip it.

### Anti-Pattern 3: Renaming data-* Attributes During HTML Redesign

**What people do:** Rename `.ioc-card[data-verdict]` to `.ioc-card[data-ioc-verdict]` for clarity during the HTML template redesign.

**Why it's wrong:** The `data-verdict` attribute is read by `cards.ts` (3 call sites), `filter.ts` (2 call sites), and written by `updateCardVerdict`. A rename requires coordinated changes in TypeScript, templates, and CSS in one atomic commit. If the rename is incomplete, the sort, filter, and dashboard all silently break.

**Do this instead:** Keep all `data-*` attribute names exactly as they are. Rename CSS class names freely; never rename `data-*` attributes without updating all consumers.

### Anti-Pattern 4: Using innerHTML in Redesigned Row Code

**What people do:** In the new `createProviderRow`, use template literals with `innerHTML` to build complex row HTML more concisely.

**Why it's wrong:** SEC-08 is a hard constraint for this codebase. Provider names, IOC values, verdict text, and `raw_stats` values all arrive from untrusted API responses. A single `innerHTML` with any of these values creates an XSS vector.

**Do this instead:** Continue the `createElement` + `textContent` pattern. For complex layouts, nest `createElement` calls. It is verbose but provably safe.

### Anti-Pattern 5: Moving iocVerdicts State Out of enrichment.ts

**What people do:** Create a shared `verdictStore.ts` module with module-level state so `verdict-compute.ts` can access it directly.

**Why it's wrong:** Shared module-level state creates hidden coupling. `enrichment.ts` is the correct owner of polling-session state — it is the only module that knows when a polling session starts and ends.

**Do this instead:** Pass `iocVerdicts` as a parameter to functions that need it. This is already the pattern in the current code (`renderEnrichmentResult(result, iocVerdicts, iocResultCounts)`) and should be preserved.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (1 analyst, 14 providers, ~50 IOCs/session) | No changes needed — polling approach is correct |
| More providers added | `CONTEXT_PROVIDERS` set and `PROVIDER_CONTEXT_FIELDS` map in `row-factory.ts` scale linearly |
| More IOCs (100+/session) | `sortCardsBySeverity` and `sortDetailRows` debouncing already handles this correctly |
| Framework adoption | Declared out of scope in PROJECT.md — vanilla TS is preferred |

---

## Sources

- Direct source code review (all files read for this research):
  - `app/static/src/ts/modules/enrichment.ts` (928 LOC)
  - `app/static/src/ts/modules/cards.ts` (136 LOC)
  - `app/static/src/ts/modules/filter.ts` (143 LOC)
  - `app/static/src/ts/modules/graph.ts`, `export.ts`
  - `app/static/src/ts/types/api.ts`, `types/ioc.ts`
  - `app/static/src/ts/utils/dom.ts`
  - `app/static/src/ts/main.ts`
- Template review:
  - `app/templates/results.html`
  - `app/templates/partials/_ioc_card.html`
  - `app/templates/partials/_enrichment_slot.html`
  - `app/templates/partials/_verdict_dashboard.html`
  - `app/templates/partials/_filter_bar.html`
  - `app/templates/ioc_detail.html`
- CSS review: `app/static/src/input.css` lines 1-100 (design tokens), 1083-1310 (enrichment slot styles)
- Project context: `.planning/PROJECT.md` (v1.1 milestone definition)
- No external sources consulted — this is a codebase analysis

---
*Architecture research for: SentinelX v1.1 Results Page Redesign — TypeScript module integration*
*Researched: 2026-03-16*
