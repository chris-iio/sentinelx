# Project Research Summary

**Project:** SentinelX v1.1 Results Page Redesign
**Domain:** Multi-source threat intelligence aggregation UI — presentation layer refinement
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

SentinelX v1.1 is a presentation-only redesign of a working SOC triage tool. The codebase ships 14 enrichment providers, per-IOC detail pages, a full filter bar, and 848+ tests. The core problem is not missing data or features — it is that 14 provider rows displayed in a flat accordion feel like 14 separate search results stapled together rather than one unified intelligence report. Research into how VirusTotal, Hybrid Analysis, Shodan, IntelOwl, and URLScan solve this same problem yields a clear consensus: separate verdict assessment from contextual intelligence, group findings by signal type rather than by source name, and make the synthesized judgment the most visually dominant element in each card.

The recommended approach is a three-section accordion structure — Reputation (verdict-producing providers), Infrastructure Context (CONTEXT_PROVIDERS), and No Data (collapsed by default) — combined with a promoted worst-verdict headline element and a verdict breakdown micro-bar replacing the current text consensus badge. All of this is achievable without new Python routes, new TypeScript modules beyond two planned extractions (`verdict-compute.ts`, `row-factory.ts`), or any new libraries. The full native CSS toolbox (CSS Grid subgrid, `@container` queries, `@starting-style`, View Transitions API) is available at the current browser target, and the existing motion primitive system (`--card-index` stagger, `fadeSlideUp`, shimmer skeleton) is already sufficient.

The key risk is the existing test surface: 91 E2E tests contain 20+ hard-coded CSS class selectors, and the TypeScript modules rely on a documented DOM attribute contract (`data-ioc-value`, `data-ioc-type`, `data-verdict` on the `.ioc-card` root element). Any template restructuring that renames CSS classes or moves these attributes will cause silent failures. The mitigation is to establish preservation contracts before touching any template and run the full E2E suite after every template change — not at the end.

## Key Findings

### Recommended Stack

The existing stack is fully sufficient. No new libraries, no npm packages, no new standalone binaries are required. TypeScript 5.8, esbuild 0.27.3, Tailwind CSS v3.4.17 standalone, and the existing `input.css` design system handle everything the redesign needs.

The relevant CSS capabilities are native browser features already available at the es2022 build target: CSS Grid subgrid (97%+ support) for aligned card sections across the grid, `@container` queries (95%+ support) for card-internal layout adaptation, `@starting-style` (Chrome 117+, Firefox 129+, Safari 17.5+) for zero-JS provider row entry animations, and `document.startViewTransition()` (Baseline Oct 2025) for animated card reordering. Scroll-driven `animation-timeline: view()` is explicitly deferred — Firefox does not support it as of March 2026; use `IntersectionObserver` instead.

**Core technologies:**
- TypeScript 5.8: DOM manipulation, polling, card reordering — already proven across 13 modules
- esbuild 0.27.3: compiles to single IIFE bundle; `--target=es2022` enables all needed native APIs
- Tailwind CSS v3.4.17 standalone: utility classes; no Node.js dependency; v4 upgrade is a follow-on milestone, not this one
- Custom CSS (`input.css`): motion primitives, design tokens, component classes — redesign extends, does not replace

### Expected Features

Research into VirusTotal, Hybrid Analysis, Shodan, IntelOwl, and URLScan reveals consistent patterns: separate verdict providers from context providers, make the synthesized judgment visually dominant, and suppress zero-data rows as visual noise. These platforms all treat source as an attribute within a category group, not as the organizing principle.

**Must have (table stakes — P1 for v1.1):**
- Worst-verdict as report headline — make the verdict badge the dominant element in the card header (CSS-only, highest ROI of any single change)
- Category-grouped provider sections — Reputation / Infrastructure Context / No Data structure (backbone change from which all other improvements follow)
- No-data section collapsed by default — removes flat visual noise from zero-data provider rows
- Verdict breakdown micro-bar — visual malicious/suspicious/clean/no-data count replaces `[2/5]` text badge
- Provider category labels — distinct visual treatment for Reputation vs Infrastructure sections

**Should have (differentiators — P2 for v1.1.x):**
- Inline context summary always visible in card header — 2-3 key fields (GeoIP country, ASN org) without requiring accordion expansion
- Staleness indicator on summary row — `cached_at` already exists in `EnrichmentResultItem`; surface it
- Scan date on summary row — `scan_date` already in the data model; display it

**Defer (v1.2+):**
- Per-category expand/collapse toggle — collapse Infrastructure for clean IOCs
- IOC card sort by IOC type as alternative to severity sort
- Tailwind v4 upgrade — natural follow-on cleanup milestone after v1.1 ships

**Anti-features (do not implement):**
- Composite threat score — conflicts with SentinelX "never invent scores" design philosophy
- Tabs per IOC card — breaks at-a-glance comparison across IOCs; accordion is correct for this use case
- Auto-expand all cards — 140 rows simultaneously with 10 IOCs is catastrophic for cognitive load
- Inline verdict override / annotations — removed in v7.0 for good reasons; do not reintroduce
- Any new Python routes or TypeScript functions not driven by the visual restructuring — v1.1 is refinement only

### Architecture Approach

The redesign requires two TypeScript module extractions from `enrichment.ts` (currently 928 LOC) before any visual work begins. These extractions make the visual redesign isolated to `row-factory.ts` and `input.css` — without them, every row visual change requires touching an interleaved 928-LOC file where computation and DOM mutation are entangled.

The key architectural seam is the existing `CONTEXT_PROVIDERS` set and the rendering fork in `renderEnrichmentResult`. This fork correctly separates context rows from verdict rows today; the redesign promotes this distinction into the visual structure without changing any backend data model.

**Major components:**
1. `verdict-compute.ts` (NEW, ~80 LOC) — pure functions: `computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry`; no DOM access, no side effects; extracted from `enrichment.ts`
2. `row-factory.ts` (NEW, ~150 LOC) — unified `createProviderRow(result, kind, statText)` with `RowKind = "verdict" | "context"` discriminant; owns `CONTEXT_PROVIDERS` set and all row-building DOM code
3. `enrichment.ts` (MODIFIED, ~300 LOC after extraction) — polling orchestrator and state owner; calls into new modules; continues to own `iocVerdicts`, `iocResultCounts`, `allResults`, `sortTimers`
4. `input.css` (MAJOR CSS CHANGES) — new component CSS for redesigned row, card, and summary layout; existing motion primitives preserved
5. Templates: `_ioc_card.html`, `_enrichment_slot.html` — HTML shell changes; all `data-*` attribute contracts preserved verbatim

**Key constraints that must not change:**
- State stays in `enrichment.ts` — new helper modules receive values as parameters; no shared state store
- No backend changes — `rowKindFor(result.provider)` derives kind at render time using the existing `CONTEXT_PROVIDERS` set; row classification is a display concern, not a data concern
- `createElement + textContent` only — SEC-08 hard constraint; `innerHTML` and `insertAdjacentHTML` are prohibited throughout

### Critical Pitfalls

1. **CSS class rename breaks 91 E2E tests silently** — E2E page object (`tests/e2e/pages/results_page.py`) has 20+ hard-coded class selectors; failures manifest as timeout errors (looks like a network problem, not a selector mismatch). Prevention: two-class strategy — keep existing class as test anchor with no visual styles, add new class for visual redesign; or migrate page object to `data-testid` anchors before renaming any class.

2. **`data-*` attribute contract broken by template restructuring** — `filter.ts`, `cards.ts`, and `enrichment.ts` all read/write `data-ioc-value`, `data-ioc-type`, `data-verdict` on the `.ioc-card` root element. Moving these to a wrapper or child element silently breaks filtering, verdict updates, and card sorting. Prevention: treat these attributes as an interface contract before any template restructuring begins.

3. **Scope creep converts refinement into feature work** — v1.1 is refinement-only; any change requiring new Jinja context variables, new TypeScript functions, or a growing unit test count has crossed the scope boundary. Prevention: maintain a deferred features list; anything not achievable within existing route context and TypeScript module signatures goes on the list.

4. **Information density regression in pursuit of "cleaner" design** — SOC analysts scan, not browse; consumer web design patterns (whitespace, hover reveals, collapsed defaults) force more clicks per IOC and multiply across a 50-IOC triage session. Prevention: write information density acceptance criteria (IOC value fully visible, verdict label always visible, consensus count not hover-only) before touching any CSS.

5. **`innerHTML` introduced during row-factory refactoring** — SEC-08 is a hard constraint; provider names, IOC values, and `raw_stats` arrive from untrusted API responses. Prevention: `createElement + textContent` is the only permitted DOM construction pattern; run `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` as a pre-merge gate.

## Implications for Roadmap

Based on combined research, the redesign decomposes cleanly into four sequential phases. The ordering is non-negotiable: each phase creates the stable foundation the next phase requires.

### Phase 1: Foundation and Contracts

**Rationale:** Establish all preservation contracts before a single line of visual code changes. Pitfall research shows E2E failures, data attribute breaks, and scope drift all originate from skipping this setup. This phase has no visual output but eliminates the highest-risk failure modes upfront.

**Delivers:** Pre-merge checklist with CSS class preservation rules, data attribute contracts documented in code comments, information density acceptance criteria written out, CSS layer ownership rule established (component classes own all visual properties for existing elements; Tailwind utilities for new layout structures only), accessibility attribute catalog (`aria-*`, `role`, `id` per element), deferred features list initialized.

**Addresses:** Pitfalls 1 (E2E class contract), 2 (data attribute contract), 4 (scope discipline), 5 (density requirements), 6 (CSS specificity), 7 (accessibility)

**Research flag:** None — standard pre-refactor discipline. Skip `/gsd:research-phase`.

---

### Phase 2: TypeScript Module Extractions

**Rationale:** Extract `verdict-compute.ts` and `row-factory.ts` from `enrichment.ts` before any visual redesign. Architecture research is unambiguous: redesigning rows while computation and rendering are interleaved means touching everything simultaneously. Extraction first isolates the visual redesign to `row-factory.ts` and `input.css` only.

**Delivers:** `verdict-compute.ts` (pure computation, no DOM, ~80 LOC), `row-factory.ts` (unified `createProviderRow` with `RowKind` discriminant, ~150 LOC), `enrichment.ts` trimmed to ~300 LOC orchestrator. Zero behavioral change — existing E2E suite passes unchanged after this phase.

**Addresses:** Architecture "Separate Computation from DOM Mutation" pattern; enables Phase 3 to be visually isolated with compiler verification

**Test gate:** `tsc` compilation passes; all 91 E2E tests pass unchanged; all provider rows render with correct verdict CSS classes.

**Research flag:** None — mechanical extractions with compiler verification. Skip `/gsd:research-phase`.

---

### Phase 3: Visual Redesign — CSS and Row Structure

**Rationale:** With `row-factory.ts` extracted, all visual changes to rows are isolated to one file. CSS changes in `input.css` carry no TypeScript risk. This is the highest creative content of the milestone and the phase that directly addresses the "14 results stapled together" problem.

**Delivers:** Category-grouped provider sections (Reputation / Infrastructure Context / No Data) in `row-factory.ts` and `input.css`, worst-verdict as headline element (CSS sizing in `.ioc-card-header`), verdict breakdown micro-bar (additive JS in `updateSummaryRow` + CSS), no-data section collapsed by default, provider category labels/icons, `@starting-style` entry animation for provider rows, `document.startViewTransition()` wrapping `doSortCards()` for animated card reorder.

**Addresses:** All P1 features from FEATURES.md; uses CSS Grid subgrid, `@container` queries, `@starting-style`, View Transitions API — all in existing stack

**Avoids:** Pitfall 5 (information density), Pitfall 6 (CSS specificity — component classes own existing element properties)

**Test gate:** E2E suite passes; visual inspection of all verdict states (malicious, suspicious, clean, known_good, no_data, error) and all context providers; information density acceptance criteria verified.

**Research flag:** None — CSS patterns verified with HIGH confidence against MDN/caniuse. Skip `/gsd:research-phase`.

---

### Phase 4: HTML Template Restructuring

**Rationale:** HTML shell changes come last because: (a) CSS must be finalized first so template structure reflects confirmed layout decisions, (b) template changes carry the highest risk of breaking the DOM attribute contract — doing them last minimizes time with a broken contract.

**Delivers:** Updated `_ioc_card.html` and `_enrichment_slot.html` for new visual design, all `data-*` attributes preserved on `.ioc-card` root element, detail link Jinja expression preserved verbatim (`url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)`), all `aria-*` and `role` attributes preserved.

**Addresses:** Pitfall 3 (detail link `<path:>` contract), Pitfall 7 (accessibility attributes)

**Pre-merge gate:** Full DOM attribute contract checklist; URL IOC detail link smoke test (`/ioc/url/https://evil.com/beacon` returns 200); full E2E suite at zero failures; `grep` for `innerHTML`.

**Research flag:** None — HTML restructuring follows documented contracts. Skip `/gsd:research-phase`.

---

### Phase 5 (conditional): Inline Context Summary

**Rationale:** The inline context summary (always-visible GeoIP country + ASN org in card header) is a P2 feature architecturally independent of the P1 category grouping changes but higher-complexity. It requires `enrichment.ts` to route context provider results into a new DOM slot above the accordion rather than only into the expanded details container. Execute this phase only if Phases 3-4 deliver cleanly within scope.

**Delivers:** 2-3 key context fields visible in card header without requiring accordion expansion; staleness indicator for cached results in summary row; scan date on summary row.

**Addresses:** P2 features from FEATURES.md (inline context summary, staleness indicator, scan date)

**Research flag:** LOW complexity, but the timing dependency needs targeted analysis before implementation. Context providers may arrive after the card's initial summary row render; confirm whether `updatePendingIndicator` handles this correctly for the new inline slot.

---

### Phase Ordering Rationale

- Phase 1 must be first: contract violations are the most expensive failure mode; establish the insurance before doing any work.
- Phase 2 before Phase 3: the 928-LOC `enrichment.ts` monolith makes visual isolation impossible without extraction; it is the necessary precondition for the redesign.
- Phase 3 (CSS/JS) before Phase 4 (HTML): once CSS is stable, template changes are mechanical; reversing this order means iterating HTML structure while CSS is still changing.
- Phase 5 conditional: avoids forcing scope expansion on the core redesign; inline context summary is achievable but not required to solve the "14 results stapled together" problem.

### Research Flags

Phases needing deeper targeted research during planning:
- **Phase 5 (Inline Context Summary):** Timing dependency — context providers may complete after the card's initial summary row render; needs targeted analysis of enrichment polling flow before implementation to confirm whether enrichment.ts handles partial results correctly for the new inline DOM slot.

Phases with standard patterns (skip `/gsd:research-phase`):
- **Phase 1:** Pre-refactor contract documentation — standard discipline; no unknowns.
- **Phase 2:** TypeScript module extraction — mechanical with compiler verification; extraction boundaries are clear.
- **Phase 3:** CSS patterns all verified with HIGH confidence against MDN/caniuse and the existing codebase.
- **Phase 4:** HTML template restructuring — follows documented DOM attribute contracts.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing codebase directly inspected; CSS feature browser support verified against MDN/caniuse and Can I Use; all native API targets confirmed at the es2022 build target |
| Features | HIGH | Primary sources: VirusTotal docs, live Shodan and Hybrid Analysis inspection, IntelOwl official docs; design recommendations have strong cross-platform consensus from five independent platforms |
| Architecture | HIGH | Full source code review of all 13 TypeScript modules and 6 templates; extraction boundaries are mechanically verifiable with `tsc`; DOM attribute contracts directly confirmed from E2E test selectors |
| Pitfalls | HIGH | Derived entirely from direct codebase inspection (E2E selectors, TypeScript dependency graph, CSS layer structure); not theoretical — these are structural facts about the existing system with recovery paths |

**Overall confidence:** HIGH

### Gaps to Address

- **Inline context summary timing (Phase 5):** When a context provider result arrives via polling, the card may already have rendered its summary row with no context slot. Whether `enrichment.ts` handles writing into a new inline context slot correctly for partially-completed enrichment jobs needs verification during Phase 5 planning — not a blocker for Phases 1-4.

- **Verdict micro-bar animation interaction (Phase 3):** Whether animating the bar fill (width transition as provider results accumulate) conflicts with the `sortCardsBySeverity` debounce needs a quick prototype check early in Phase 3. The fix is simple if it occurs (skip animation during active sort), but worth verifying before committing to the bar animation approach.

- **Tailwind standalone scanner content glob (Phase 3-4):** If new utility classes are added in redesigned templates, confirm they are included in the Tailwind standalone scanner's content configuration. This is a known integration gotcha — utility classes added to templates not in the scanner glob silently drop from `dist/style.css`.

## Sources

### Primary (HIGH confidence)
- SentinelX codebase direct inspection: `app/static/src/ts/modules/enrichment.ts` (928 LOC), `cards.ts`, `filter.ts`, `types/api.ts`, `types/ioc.ts`, `utils/dom.ts`, `main.ts`
- SentinelX templates: `results.html`, `_ioc_card.html`, `_enrichment_slot.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `ioc_detail.html`
- SentinelX E2E test selectors: `tests/e2e/pages/results_page.py`, `test_results_page.py`, `test_extraction.py`, `test_copy_buttons.py`
- SentinelX CSS: `app/static/src/input.css` (design tokens, keyframes, component classes)
- [View Transition API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) — API shape, browser support
- [What's new in view transitions (2025) — Chrome Developers](https://developer.chrome.com/blog/view-transitions-in-2025) — same-document transitions, Baseline Oct 2025 confirmed
- [VirusTotal Reports Documentation](https://docs.virustotal.com/docs/results-reports) — tab structure, domain/IP vs file/URL report information architecture
- [IntelOwl Usage Documentation](https://intelowlproject.github.io/docs/IntelOwl/usage/) — DataModel synthesis pattern, Visualizer aggregation
- [Hybrid Analysis Sample Report](https://hybrid-analysis.com/sample/b558f0b1444be5df69027315f7aad563c54a3f791cebbb96a56fce7e5176f8f5/) — live Malicious/Suspicious/Informative grouping inspection
- [Shodan Host Page](https://www.shodan.io/host/203.185.191.41) — live inspection of category-first information architecture
- [animation-timeline: view() — Can I use](https://caniuse.com/mdn-css_properties_animation-timeline_view) — 82.81% global support, Firefox flag-only as of March 2026

### Secondary (MEDIUM confidence)
- [Tailwind CSS v4.0 release post](https://tailwindcss.com/blog/tailwindcss-v4) — v4 CSS feature set, `@theme` config model
- [Tailwind CSS v4 standalone CLI — GitHub Discussion #17638](https://github.com/tailwindlabs/tailwindcss/discussions/17638) — v4.1.3 standalone binary confirmed
- [The New CSS Layout Toolbox — Medium Oct 2025](https://medium.com/@kedarbpatil07/the-new-css-layout-toolbox-subgrid-container-queries-and-more-41cf94ebf821) — subgrid 97%+ global support
- [URLScan.io About](https://urlscan.io/about/) — "digestible chunks, analyst-first approach" design philosophy
- [Rearrange / Animate CSS Grid Layouts with the View Transition API — Bram.us](https://www.bram.us/2023/05/09/rearrange-animate-css-grid-layouts-with-the-view-transition-api/) — grid reorder + View Transitions implementation pattern

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*

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

# Stack Research

**Domain:** Results page redesign — multi-source aggregation UI, CSS layout, animation
**Milestone:** v1.1 Results Page Redesign
**Researched:** 2026-03-16
**Confidence:** HIGH (existing stack verified from codebase; CSS feature support verified against
official MDN/caniuse; Tailwind v4 standalone verified from GitHub Discussions)

---

## Context: Presentation Refinement Only

The existing stack is locked and ships. This document answers one question: **what, if anything,
does the v1.1 results page redesign require beyond what already exists?**

**Existing baseline (do not re-evaluate):**

| Tool | Version | How Used |
|------|---------|----------|
| TypeScript | 5.8 | 13 modules, strict mode, IIFE output via esbuild |
| esbuild | 0.27.3 | Standalone binary, `--target=es2022`, bundles to `dist/main.js` |
| Tailwind CSS | v3.4.17 | Standalone binary (no Node.js), utility classes in templates |
| Custom CSS | input.css (58KB) | Design tokens, keyframes, component classes |
| Jinja2 | Flask 3.1 | Server-side templates, partials, macros |

The CSS design system already has: `--ease-out-expo`, `--ease-out-quart`, `--duration-fast/normal/slow`,
`fadeSlideUp`, `fadeIn`, `slideInFade`, `slideOutFade` keyframes, shimmer-line loading skeleton,
`--card-index` stagger via CSS custom property, verdict color triples, zinc hierarchy tokens.

---

## Verdict: Current Stack Is Sufficient — No New Libraries Required

The redesign can achieve everything it needs through:
1. CSS features already available in the current `input.css` pipeline (Tailwind + custom)
2. ES2022 vanilla TypeScript (already compiled by esbuild)
3. Native browser APIs that ship in all modern browsers

No npm packages, no new standalone binaries, no new Python dependencies.

---

## Recommended Stack

### Core Technologies (unchanged)

| Technology | Version | Purpose | Why Sufficient |
|------------|---------|---------|---------------|
| TypeScript | 5.8 | DOM manipulation, enrichment polling, card reordering | Already handles all dynamic behavior; 13 modules prove the architecture scales |
| esbuild | 0.27.3 | Compiles TS to single IIFE bundle | `--target=es2022` enables all native APIs needed (View Transitions, CSS custom properties) |
| Tailwind CSS | v3.4.17 standalone | Utility classes for layout adjustments | Generates only used classes; CSS Grid/Flexbox utilities are comprehensive |
| Custom CSS (input.css) | — | Design tokens, component classes, keyframes | Already has motion primitives; redesign extends existing keyframes, not replaces them |

### CSS Capabilities to Leverage (Already Available, No New Setup)

These are native CSS features available in the current browser target (Chrome/Edge/Firefox/Safari modern).
They require zero new tools — just new CSS rules in `input.css`.

| Technique | Availability | Purpose in Redesign | Confidence |
|-----------|-------------|---------------------|------------|
| CSS Grid subgrid | Baseline (97%+ support) | Align card sections (header, enrichment zone, footer) across the card grid without JavaScript — headers stay level, stat rows align across cards | HIGH — Chrome 117+, Firefox 71+, Safari 16+ |
| CSS `@container` queries | Baseline (95%+ support) | Cards adapt their internal layout based on their allocated width, not viewport — handles wide vs narrow grid slots without media query hacks | HIGH — Chrome 106+, Firefox 110+, Safari 16+ |
| `view-transition-name` + `document.startViewTransition()` | Baseline Newly Available Oct 2025 | Animate card reordering (sort by severity) so cards glide to their new positions instead of teleporting — same-document transitions work in Chrome 111+, Firefox 133+, Safari 18+ | HIGH for same-document transitions |
| CSS `animation-timeline: view()` (scroll-driven) | ~83% global support, Safari 26+ only | Animate cards entering the viewport — LOW PRIORITY, only suitable as progressive enhancement because Firefox does not support it as of March 2026 | MEDIUM — skip for MVP, add with `@supports` guard later |
| `@starting-style` (entry animation) | Chrome 117+, Firefox 129+, Safari 17.5+ | Animate new detail rows appearing — triggers animation only on element insertion, not every render | HIGH — better than existing JS-managed `fadeSlideUp` for dynamically added rows |
| CSS `color-mix()` | Baseline (95%+ support) | Derive hover/focus states from verdict color tokens without hardcoding more hex values | HIGH |
| CSS `transition: grid-template-rows` | Modern browsers | Animate the expand/collapse of `.enrichment-details` with `grid-template-rows: 0fr` → `1fr` trick — smoother than `max-height` hacks | HIGH — known pattern, works in all modern browsers |

### View Transitions for Card Sort Animation

The existing `doSortCards()` in `cards.ts` re-appends DOM nodes synchronously — cards teleport to
new positions. Wrapping this in `document.startViewTransition()` with `view-transition-name`
CSS properties on each card produces animated FLIP-style movement:

```typescript
// In cards.ts — replace doSortCards() body with:
if ('startViewTransition' in document) {
  document.startViewTransition(() => doSortCards());
} else {
  doSortCards(); // graceful fallback — existing behavior
}
```

This requires assigning `view-transition-name` values. The `--card-index` CSS custom property
pattern already in `ui.ts` provides a template: assign names dynamically from TypeScript using
`card.style.setProperty('view-transition-name', 'ioc-card-' + CSS.escape(iocValue))`.

No new library. Zero bundle size impact. Graceful degradation is built-in — browsers without
support just execute the DOM change without animation.

**Browser support:** Chrome 111+, Edge 111+, Firefox 133+ (Baseline Oct 2025), Safari 18+.
HIGH confidence this is safe for production use.

### `@starting-style` for Provider Row Entry Animation

The current `enrichment.ts` appends provider detail rows with `detailsContainer.appendChild(row)`.
These rows appear instantly. Adding an entry animation requires either a JavaScript class-toggle
trick or `@starting-style`, which specifies the initial painted state when an element is first
inserted:

```css
.provider-detail-row {
  transition: opacity 200ms var(--ease-out-quart), transform 200ms var(--ease-out-quart);
  opacity: 1;
  transform: translateY(0);
}

@starting-style {
  .provider-detail-row {
    opacity: 0;
    transform: translateY(4px);
  }
}
```

No TypeScript changes required. The CSS handles it automatically on element insertion.
Browser support: Chrome 117+, Firefox 129+, Safari 17.5+ — effectively all modern browsers.

### Grid Layout for Multi-Source Presentation

The current `.ioc-cards-grid` uses CSS Grid (from the existing `ioc-cards-grid` class in `input.css`).
For the redesign, the key layout technique is **subgrid** inside each card:

```css
.ioc-card {
  display: grid;
  grid-template-rows: auto auto 1fr; /* header / original / enrichment */
}

/* When cards are in a grid row: subgrid aligns sections across columns */
.ioc-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
}
```

Subgrid lets the enrichment slot expand uniformly within a row — the "meta-search engine" feel
where all cards in a row feel like a coherent table rather than independent boxes.

### Supporting Browser APIs (Already Available at es2022 Target)

| API | Purpose | Notes |
|-----|---------|-------|
| `Intersection Observer` | Lazy-reveal card stagger animations as analyst scrolls | Already in all modern browsers; use instead of scroll-driven CSS animations (better Firefox support) |
| `CSS.escape()` | Safe dynamic CSS selector construction | Already used in `cards.ts` — continue the pattern |
| `document.startViewTransition()` | Card sort animation | Wrap existing `doSortCards()` call |
| `ResizeObserver` | Detect card width changes for container query fallback | Available in all modern browsers if polyfill needed |

---

## Tailwind CSS v4 Consideration

**Verdict: stay on Tailwind v3.4.17 for this milestone.**

Tailwind v4 is available as a standalone binary (confirmed at v4.1.3 from GitHub releases).
The v4 config model shifts from `tailwind.config.js` to `@theme {}` in CSS — a meaningful
migration requiring changes to `input.css` and removal of `tailwind.config.js`.

**Why not v4 for v1.1:**

1. The v3 → v4 migration is a separate task with its own regression surface — utility class
   names changed in some cases; existing `input.css` uses `@tailwind base/components/utilities`
   directives that v4 replaces with `@import "tailwindcss"`.
2. The CSS features needed for the redesign (`container queries`, `subgrid`, `@starting-style`,
   View Transitions) are all native browser features — they do not require Tailwind v4.
3. v4 does add useful utilities (native container query variants `@sm:`, `@lg:`, `@container`
   shorthand) but the project already has full `@container` support through custom CSS.

**Upgrade path:** Tailwind v4 is a natural follow-on for a cleanup milestone after v1.1 ships.
The redesigned CSS will be easier to migrate than the current accumulation of v3 workarounds.

---

## What NOT to Add

| Avoid | Why | What to Use Instead |
|-------|-----|---------------------|
| Chart.js / D3.js / any data viz library | The "data visualization" need for a results page is narrow: conviction bars, engine counts. CSS-only progress bars (width: percentage; background: verdict color) cover 100% of the use case. A 100KB chart library is disproportionate. | CSS `width` percentages + custom properties |
| Framer Motion / GSAP / Anime.js | Animation library for vanilla TS makes no sense. These target React/component frameworks. GSAP is 60KB+. | CSS `@starting-style`, View Transitions API, `transition` property |
| Motion One (JS animation library) | Lower overhead than GSAP but still adds bundle size for capabilities CSS now handles natively. | Native CSS transitions and `@starting-style` |
| Alpine.js / Htmx | Reactive micro-frameworks would require restructuring the existing 13-module TypeScript pattern. High migration cost, no gain for a refinement milestone. | Existing vanilla TS modules |
| Intersection Observer polyfill | Not needed — all modern browsers support it natively. The app is desktop-only, analyst workstations run current browsers. | Native Intersection Observer |
| CSS scroll-driven animations (`animation-timeline: view()`) as primary mechanism | Firefox does not support this as of March 2026 (available only under a flag). Safari only in v26 (beta as of research date). 82% support is not sufficient for a production feature that analysts depend on. | Intersection Observer API in TypeScript — 98%+ support, identical visual result |
| `view-transition-class` (new 2025 feature) | Chrome 139+ only as of March 2026. Too new for production use. | Plain `view-transition-name` per element |
| React / Vue / Svelte | Out of scope per PROJECT.md. The vanilla TS architecture handles this complexity. | Vanilla TypeScript |

---

## Animation Strategy Summary

The redesign has three distinct animation contexts:

| Context | Technique | Rationale |
|---------|-----------|-----------|
| Card entry (page load) | Existing `--card-index` stagger + `fadeSlideUp` keyframe | Already works. Keep as-is. |
| Provider row entry (enrichment arrives) | `@starting-style` CSS rule on `.provider-detail-row` | Zero JS change. Browser animates on element insertion automatically. |
| Card reorder (sort by severity) | `document.startViewTransition()` wrapping `doSortCards()` | 3 lines of TypeScript. FLIP-style animation. Graceful degradation built-in. |
| Shimmer loading skeleton | Already implemented (`shimmer-line` classes) | Keep. Appears before first provider result arrives. |
| Expand/collapse enrichment details | `grid-template-rows: 0fr / 1fr` transition | Replace existing `max-height` approach if used; grid-rows is smoother and avoids flash. |

---

## Build Tool Versions to Keep

| Tool | Current | Upgrade? | Reason |
|------|---------|---------|--------|
| esbuild | 0.27.3 | No | Current, stable. `--target=es2022` already enables View Transitions API. |
| Tailwind CSS standalone | v3.4.17 | No (this milestone) | v4 migration is separate work. |
| tsc | (project version) | No | TypeScript 5.8 supports all needed syntax. |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Native `document.startViewTransition()` | GSAP FLIP plugin | Only if GSAP is already in the project and you need IE/older browser support |
| `@starting-style` CSS | JS class-toggle + `requestAnimationFrame` trick | Only in projects that still support Firefox 128 or Safari 17.4 |
| CSS Grid subgrid | JavaScript layout synchronization | Only if subgrid is genuinely unavailable (pre-2023 browsers) — not applicable to analyst workstations |
| Intersection Observer for lazy stagger | `animation-timeline: view()` | Use the CSS approach once Firefox ships it without a flag (tentative: Firefox 136+, currently flag-only) |

---

## Version Compatibility

| Feature | Chrome | Firefox | Safari | Notes |
|---------|--------|---------|--------|-------|
| CSS Grid subgrid | 117+ | 71+ | 16+ | Safe — all modern browsers |
| CSS Container queries | 106+ | 110+ | 16+ | Safe — all modern browsers |
| `@starting-style` | 117+ | 129+ | 17.5+ | Safe — all modern browsers |
| `document.startViewTransition()` | 111+ | 133+ | 18+ | Safe — Baseline Oct 2025 |
| `animation-timeline: view()` | 115+ | flag only | 26+ | NOT safe for MVP — use IntersectionObserver instead |
| `color-mix()` | 111+ | 113+ | 16.2+ | Safe |
| `CSS.escape()` | 46+ | 31+ | 8+ | Already used in codebase |

---

## Sources

- [Tailwind CSS v4 standalone CLI — GitHub Discussion #17638](https://github.com/tailwindlabs/tailwindcss/discussions/17638)
  v4.1.3 standalone binary confirmed. v3→v4 migration model documented. MEDIUM confidence on migration scope.
- [Tailwind CSS v4.0 release post](https://tailwindcss.com/blog/tailwindcss-v4)
  v4 CSS feature set confirmed (`@theme`, `@container` native utilities, `starting:` variant). HIGH confidence.
- [What's new in view transitions (2025 update) — Chrome Developers](https://developer.chrome.com/blog/view-transitions-in-2025)
  Same-document view transitions browser support, `match-element` auto-naming, scoped transitions. HIGH confidence.
- [View Transition API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API)
  API shape, `document.startViewTransition()` method signature. HIGH confidence.
- [animation-timeline: view() — Can I use](https://caniuse.com/mdn-css_properties_animation-timeline_view)
  82.81% global support. Safari iOS 26+ only. Firefox flag-only as of research date. HIGH confidence on support numbers.
- [CSS scroll-driven animations — MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations)
  `animation-timeline: view()` syntax and `@supports` feature detection pattern. HIGH confidence.
- [The New CSS Layout Toolbox: subgrid, container queries — Medium Oct 2025](https://medium.com/@kedarbpatil07/the-new-css-layout-toolbox-subgrid-container-queries-and-more-41cf94ebf821)
  Subgrid 97%+ global support confirmed. MEDIUM confidence (secondary source).
- [Rearrange / Animate CSS Grid Layouts with the View Transition API — Bram.us](https://www.bram.us/2023/05/09/rearrange-animate-css-grid-layouts-with-the-view-transition-api/)
  Grid reorder + View Transitions API pattern. HIGH confidence — direct implementation reference.
- SentinelX codebase: `app/static/src/input.css`, `Makefile`, `app/static/src/ts/modules/cards.ts`,
  `app/static/src/ts/modules/ui.ts`, `app/static/src/ts/modules/enrichment.ts`
  Existing motion tokens, keyframes, stagger implementation, doSortCards() function. HIGH confidence.

---

*Stack research for: SentinelX v1.1 Results Page Redesign*
*Researched: 2026-03-16*

# Feature Research

**Domain:** Threat intelligence results page — multi-source aggregation, unified presentation
**Milestone:** v1.1 Results Page Redesign
**Researched:** 2026-03-16
**Confidence:** HIGH (platform patterns from official docs + direct inspection); MEDIUM (specific
implementation approaches, comparative analysis based on public documentation)

---

## Context: This Is a Presentation Redesign, Not a Feature Addition

The app already ships 14 providers, per-IOC detail pages, export, bulk input, cache, filter bar,
and verdict dashboard. The problem is not missing data — it is how that data is presented.

Current state: 14 provider rows (verdict badge + attribution + stat text + context fields) displayed
inside an expandable accordion per IOC card. Summary row shows worst verdict + consensus badge.
Context providers (IP Context, DNS Records, Cert History, ThreatMiner, ASN Intel) are pinned to top
of the expanded section. All other providers are sorted by severity descending.

The problem statement: "results feel like 14 separate search results stapled together, not one
cohesive report. Information isn't uniform across providers. Mix of verdicts, context rows, no-data
rows feels disjointed."

This research answers: what design patterns do the best threat intelligence platforms use to make
multi-source results feel like one unified answer?

---

## How the Best Platforms Solve This

### VirusTotal: Separation by Information Type, Not Source

VirusTotal's core architectural insight is that different questions deserve different views, and
sources should be subordinate to those views. Their tab structure for file/URL reports:

- **Summary header** (always visible): Detection ratio ("X / Y" flagged), community score, hash,
  timestamp, tags. This is the unified answer at a glance.
- **Detection tab**: Partner verdict grid — all vendor results in one flat table, grouped by
  verdict category (malicious / suspicious / clean / undetected). Sources appear as rows within
  categories, not as the organizational unit.
- **Details tab**: Metadata (file properties, HTTP headers, DNS records) — type-specific context
  separated from reputation judgments.
- **Relations tab**: Relationships and pivots — all IOC-to-IOC connections independent of which
  source found them.
- **Community tab**: Analyst notes and votes — separated from automated signals.

Key lesson: **verdict assessment** and **contextual intelligence** and **relationships** are
fundamentally different kinds of information and should never be mixed in the same section.

Domain/IP reports in VirusTotal intentionally omit partner verdicts (because vendors don't rate IPs
as "malicious" the same way they rate files). Instead they show pure context — passive DNS, WHOIS,
ASN, communicating files. This distinction between IOC types is a critical design principle.

### Hybrid Analysis: Severity-First, Source-Secondary

Hybrid Analysis leads with a **threat score** (e.g., 66/100) and an **AV detection rate** (e.g.,
9%) in the header — the synthesized judgment — before any source is named. Then it groups findings
into **Malicious Indicators** / **Suspicious Indicators** / **Informative Indicators** with counts.
Within each group, items show their source type (Static Parser, API Call, Registry Access) as an
attribute, not the organizing principle.

The MITRE ATT&CK matrix section organizes tactics/techniques without naming which analyzer found
each — the framework is the organizing lens, not the tool.

Key lesson: **group by threat signal type** (malicious / suspicious / informative / context), not
by provider name. Provider is an attribute within a group, not a section header.

### Shodan: Category-First, Drill-Down Architecture

Shodan's host page opens with a **General Information block** (location, org, ISP, ASN) — a single
unified identity section that collapses all provider outputs for that category. Then **Web
Technologies** as a second block. Then **Open Ports** as navigable tab anchors.

Each port section reveals nested detail (SSL cert, banners, service identification, vulnerability
CVEs) via sequential drill-down. The user never sees "nginx reports X, Shodan reports Y" — they see
a unified answer for the port with all data synthesized under one heading.

Key lesson: **group by topic/category** (identity, network, reputation, behavior), not by data
source. Multiple sources feeding the same category should appear together under that category.

### IntelOwl: DataModel Synthesis

IntelOwl v6.2+ introduced "DataModels" that normalize all analyzer outputs into standardized keys
before display. Instead of showing OTX's response format next to ThreatFox's response format, both
are mapped to `{ ip_reputation, asn, last_seen, associated_malware }` and displayed uniformly.

Their "Visualizers" aggregate across multiple analyzers (e.g., "DNS Visualizer aggregates all DNS
analyzer reports") so the display unit is the topic, not the tool.

Key lesson: **normalize provider output to domain fields** before display. "Reputation" means the
same thing whether it comes from AbuseIPDB or GreyNoise — the label should match, not the provider
name.

### URLScan.io: Context First, Security Second

URLScan organizes scan results as: infrastructure (IPs/domains/technologies found) → statistics
(counts, protocols) → enrichment (geolocation, ASN, rankings) → security verdicts (threat
analysis, community). Context establishes what something IS before the verdict establishes whether
it's BAD.

Key lesson: **establish identity before making judgment**. Show "this IP is in US-East, owned by
Hetzner, serving port 443 with Nginx" before "3 providers flagged this as malicious."

---

## Feature Landscape

### Table Stakes (Analysts Expect These)

Features that any analyst would expect from a unified threat intelligence results view.
Missing these makes the redesign feel superficial.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Verdict-first summary per IOC | Every serious TI platform leads with the judgment — analyst should know malicious/clean before reading any detail | LOW | Already exists as worst-verdict badge; needs better visual hierarchy/prominence |
| Clear visual separation of verdict vs context providers | VirusTotal, Shodan, URLScan all separate "reputation signals" from "contextual data" — mixing them creates confusion | MEDIUM | Currently all rows in one flat list; context providers pinned to top but visually identical to verdict rows |
| Grouped provider display by category | Hybrid Analysis, Shodan group signals by type (malicious / suspicious / informative / context) not by source name | MEDIUM | Currently: flat list sorted by severity. Needed: category sections with counts per section |
| Provider count shown in summary ("3/9 flagged") | VT shows "X/Y engines"; HA shows AV detection rate — analysts want denominator, not just numerator | LOW | Consensus badge `[2/5]` partially does this; needs to be more prominent and readable |
| Empty/no-data state clearly separated from clean verdict | A provider that has no record ≠ a provider that checked and found nothing | LOW | Currently both map to `no_data` label; "checked and clean" vs "no record found" are different signals |
| Context fields readable without expanding details | Shodan shows key fields (open ports, vulns) inline on the search results card — critical context should not require expansion | MEDIUM | Currently context fields (GeoIP, ASN, ports) are hidden in expanded accordion; minimal context should always be visible |
| IOC type badge clearly visible | Every platform distinguishes IP / domain / URL / hash — different types have different signals, the analyst must know which they're looking at | LOW | Already implemented; needs consistent prominent placement |
| Scan date or data freshness indicator | Analysts care whether VirusTotal result is from today or 6 months ago; stale data changes the verdict meaning | LOW | `scan_date` is already in `EnrichmentResultItem`; not currently surfaced in summary row |

### Differentiators (What Makes This Feel Like One Report)

Features that go beyond "list of provider results" toward "unified intelligence report."
These are the features that make the difference between 14 results stapled together and one answer.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Category-grouped provider sections | Show verdict-producing providers in one section ("Reputation"), context providers in another ("Infrastructure"), zero-data providers collapsed or in a third section ("No Data") — matching Hybrid Analysis / VirusTotal pattern | MEDIUM | Requires template redesign of enrichment-details; existing CONTEXT_PROVIDERS set is the seed for this grouping |
| Inline context summary always visible | Show 2-3 key context fields (GeoIP country, ASN org, open port count) directly in the IOC card header without requiring expansion — the "at a glance" context that establishes identity before judgment | MEDIUM | Requires context providers to complete before card renders context line; may need to wait for first context result |
| Verdict breakdown micro-bar | Visual "3 malicious / 2 suspicious / 4 clean / 5 no data" bar within each IOC card — matches Hybrid Analysis's "Malicious/Suspicious/Informative" count approach; richer than current `[2/5]` text badge | MEDIUM | Client-side, requires count tracking already in iocVerdicts; pure CSS/DOM addition |
| Provider category icons/labels | Distinct visual treatment for reputation providers (flag icon) vs infrastructure context (server icon) vs passive intel (clock icon) — reinforces that different rows answer different questions | LOW | CSS token + icon addition; high visual impact for low implementation cost |
| "No data" section collapsed by default | Move all no-data providers into a collapsed section ("5 providers had no record") rather than showing them as flat rows equal to providers with actual findings | LOW | Currently no-data rows appear in the same sorted list; separating them reduces visual noise significantly |
| Worst-verdict summary as report headline | Make the worst-verdict badge the dominant visual element in the IOC card — current badge is 12-16px text in a row; should be the first thing the eye goes to (size hierarchy matching VT's large X/Y detection ratio) | LOW | CSS change to verdict-label/verdict-badge sizing in ioc-card-header; high impact, low cost |
| Staleness indicator on cached results | Show "data from 4h ago" on summary row when result was served from cache — matches VT's timestamp-in-summary approach; tells analyst whether to trust the verdict or re-query | LOW | `cached_at` field already exists in EnrichmentResultItem and is shown in expanded detail rows; surface in summary row |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Composite threat score (e.g., "74/100") | Feels like a unified answer; analysts want one number | Hides the reasoning; obscures which providers drove the score; SentinelX's core design philosophy is transparency — "never invent scores"; composite scores require calibration that doesn't exist here | Use verdict breakdown bar (malicious count / responded count) — visual but not invented |
| Provider logo/branding in rows | Looks professional, easier to recognize at a glance | Significantly increases page weight (14 logos × number of IOCs); logos require licensing verification; textContent-only DOM rule makes inline SVG complex | Use consistent provider name abbreviations with color-coded category badges |
| Auto-expand all IOC cards | Analyst wants everything visible immediately | 10 IOCs × 14 providers = 140 rows visible simultaneously; catastrophic for scan time and cognitive load | Expand only the highest-severity IOC by default; let analyst expand others on demand |
| Tabs instead of accordion | VT uses tabs; tabs look modern | For a card-per-IOC layout, tabs would require tab state per card (complex JS) and break the at-a-glance comparison across IOCs; accordion lets all IOCs remain scannable simultaneously | Keep accordion; improve category sections within the accordion |
| Inline verdict editing / analyst override | Analyst wants to mark "VT says clean but I disagree" | Annotations were removed in v7.0 for good reason — couples triage tool to case management; introduces mutable state; conflicts with cache invalidation model | Direct analysts to their TIP/SIEM for case notes; detail page already exists for deep investigation |
| Real-time confidence scoring across providers | Weight providers by reputation (VT = high trust, unknown = low trust) | Requires maintaining a trust model that goes stale as providers change quality; creates false precision; different providers answer different questions (AbuseIPDB answers "is this reported" not "is this malicious") | Show provider category (reputation vs passive intel) as context so analyst applies their own mental weights |
| Progressive disclosure with infinite scroll | Modern UX pattern; avoids long pages | IOC triage is a compare-all-IOCs task, not a read-one-article task; infinite scroll breaks the analyst's mental model of "I have N IOCs to triage" | Show all IOC cards, keep cards compact, use filter bar to reduce visible set |

---

## Feature Dependencies

```
Category-Grouped Provider Sections
    requires──> CONTEXT_PROVIDERS set (already exists in enrichment.ts)
    requires──> verdict count tracking per category (iocVerdicts already tracks this)
    requires──> template redesign of .enrichment-details container
    enables──> "No Data" section collapsed by default (trivially add third group)
    enables──> Provider category icons/labels (apply per group, not per row)

Inline Context Summary (always visible)
    requires──> context provider results arrive before card renders full summary
    requires──> IOC card template change (new .ioc-context-inline slot)
    depends on──> enrichment.ts routing context vs verdict results differently
    conflicts with──> showing nothing until all providers complete (current behavior)

Verdict Breakdown Micro-Bar
    requires──> per-verdict count tracking (iocVerdicts already has this data)
    requires──> CSS bar component
    enhances──> Worst-verdict summary as report headline
    replaces──> current [flagged/responded] consensus badge (same data, better display)

Worst-Verdict as Report Headline
    requires──> CSS hierarchy change in .ioc-card-header
    is independent of──> grouped sections (works immediately as CSS-only change)

Staleness Indicator on Summary Row
    requires──> cached_at already in EnrichmentResultItem (already exists)
    requires──> updateSummaryRow() to surface cached_at when all results are from cache
    is independent of──> category grouping

No-Data Section Collapsed by Default
    requires──> Category-Grouped Provider Sections (no_data is a group)
    is a low-cost win once grouping exists
```

### Dependency Notes

- **Grouping is the backbone change.** Most differentiators become simple once the three-section
  structure (Reputation / Infrastructure Context / No Data) exists. Category icons, collapsed
  no-data section, and section-level counts all follow from grouping.

- **Inline context summary is independent of grouping** but higher-complexity. It requires
  enrichment.ts to write context fields into a new DOM slot in the card header (above the accordion)
  rather than only into the expanded details container.

- **Worst-verdict as headline is purely CSS.** No JS changes required — make the existing
  `.verdict-label` in `.ioc-card-header` significantly larger (24-28px vs current 12-14px).
  Highest impact-to-cost ratio of any change.

- **Verdict breakdown bar is purely additive JS.** The `iocVerdicts` data structure already
  accumulates every verdict entry. Computing counts by verdict type and rendering a bar is a
  `updateSummaryRow()` change + CSS addition.

---

## MVP Definition (v1.1)

### Launch With (v1.1 Core)

Minimum changes that address the "14 separate results stapled together" problem.

- [ ] Worst-verdict as report headline — make verdict badge the dominant element in card header
  (CSS sizing change, zero JS changes, highest ROI)
- [ ] Category-grouped provider sections — Reputation section (verdict-producing providers) /
  Infrastructure Context section (CONTEXT_PROVIDERS) / No Data section (collapsed by default)
- [ ] Verdict breakdown micro-bar — visual count of malicious/suspicious/clean/no-data providers
  (replaces `[2/5]` consensus text badge with visual representation)
- [ ] No-data section collapsed by default — removes visual noise from flat provider list
- [ ] Provider category labels — distinct label/icon for "Reputation" vs "Infrastructure" sections

### Add After Validation (v1.1.x)

Features to add once core restructure is working and tested.

- [ ] Inline context summary — once grouping is stable, surface 2-3 key context fields directly
  in card header (GeoIP country + ASN org for IPs; creation age for domains)
- [ ] Staleness indicator in summary row — surface `cached_at` when data is not fresh
- [ ] Scan date on summary row — show most recent scan date from verdict providers

### Future Consideration (v1.2+)

- [ ] Per-category expand/collapse toggle — collapse "Infrastructure" section by default for
  clean IOCs where context adds noise
- [ ] IOC card sort by IOC type (group all IPs together, then domains, etc.) as an alternative
  to current severity sort — useful for bulk input with mixed IOC types

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Worst-verdict as report headline (CSS only) | HIGH — first thing analyst reads | LOW — CSS sizing | P1 |
| Category-grouped provider sections | HIGH — eliminates "14 results" feel | MEDIUM — JS + template | P1 |
| No-data section collapsed by default | HIGH — reduces noise immediately | LOW — CSS default state | P1 |
| Verdict breakdown micro-bar | MEDIUM — richer than text badge | MEDIUM — JS count + CSS bar | P1 |
| Provider category labels/icons | MEDIUM — reinforces information structure | LOW — CSS tokens | P2 |
| Inline context summary (always visible) | MEDIUM — eliminates mandatory expand for context | HIGH — new DOM slot, enrichment.ts change | P2 |
| Staleness indicator on summary row | LOW-MEDIUM — data freshness matters for verdict trust | LOW — cached_at already available | P2 |
| Scan date on summary row | LOW — detail-level info | LOW — scan_date already available | P3 |

**Priority key:**
- P1: Must have for v1.1 — directly addresses the "stapled together" problem
- P2: Should have — improves information coherence and context visibility
- P3: Nice to have — polish

---

## Competitor Feature Analysis

How the best platforms handle the specific problems SentinelX currently exhibits.

| Problem | VirusTotal Approach | Hybrid Analysis Approach | Our Approach (v1.1) |
|---------|---------------------|--------------------------|---------------------|
| 14 sources feel separate | Tabs separate verdict / metadata / relations / community — verdict is the primary tab | Group by signal type (malicious / suspicious / informative), not by source | Three-section accordion: Reputation / Infrastructure Context / No Data |
| Context vs verdict mixed | Domain/IP reports have zero vendor verdicts — pure context only; file reports have zero context in detection tab | Indicators section separates malicious / suspicious / informative rows | CONTEXT_PROVIDERS rendered in their own section, visually distinct from verdict section |
| Verdict clarity | Large X/Y ratio in header is the dominant visual element | Threat score + AV detection rate in header before any source details | Worst-verdict badge promoted to dominant headline element in card |
| No-data providers as noise | Not shown — VirusTotal only lists engines that returned a result | Informative indicators section separates low-signal results | No-data section collapsed by default with count shown ("5 had no record") |
| Context fields buried | Details tab separate from detection; always shown by default | Informative indicators always visible in summary | Inline context summary (2-3 fields) always visible in card header |

---

## Sources

- [VirusTotal Reports Documentation](https://docs.virustotal.com/docs/results-reports) — Official
  tab structure, field names, domain/IP vs file/URL report differences (HIGH confidence)
- [Shodan Host Page](https://www.shodan.io/host/203.185.191.41) — Live inspection of Shodan host
  report information architecture (HIGH confidence — direct observation)
- [IntelOwl Usage Documentation](https://intelowlproject.github.io/docs/IntelOwl/usage/) — DataModel
  synthesis approach, Visualizer aggregation pattern (HIGH confidence — official docs)
- [Hybrid Analysis Sample Report](https://hybrid-analysis.com/sample/b558f0b1444be5df69027315f7aad563c54a3f791cebbb96a56fce7e5176f8f5/) —
  Live inspection of Malicious/Suspicious/Informative indicator grouping (HIGH confidence)
- [ANY.RUN Malware Analysis Report blog](https://any.run/cybersecurity-blog/malware-analysis-report/) —
  ANY.RUN report section structure and hierarchy (MEDIUM confidence — marketing blog)
- [URLScan.io About](https://urlscan.io/about/) — "digestible chunks, analyst-first approach"
  design philosophy (MEDIUM confidence — official but brief)
- [SentinelX enrichment.ts](../app/static/src/ts/modules/enrichment.ts) — Current implementation
  of summary row, consensus badge, context row, detail row, sort logic (HIGH confidence — source)
- [SentinelX _ioc_card.html / _enrichment_slot.html templates](../app/templates/partials/) —
  Current DOM structure (HIGH confidence — source)

---

*Feature research for: SentinelX v1.1 Results Page Redesign*
*Researched: 2026-03-16*

# Pitfalls Research

**Domain:** UI redesign of an existing multi-provider threat intelligence results page
**Researched:** 2026-03-16
**Confidence:** HIGH — based on direct codebase inspection of all E2E tests, page object selectors, TypeScript modules, Jinja templates, and CSS. No external verification needed; pitfalls are structural facts about this specific codebase.

---

## Context: What This Research Covers

SentinelX v1.1 redesigns the results page of a working, tested SOC tool. The goal is cohesive visual
presentation — not new features. The existing system has:

- **91 E2E tests** using Playwright Page Object Model with hard-coded CSS class selectors
- **757+ unit/integration tests** covering enrichment logic, routes, and rendering
- **13 TypeScript modules** compiled by esbuild into a single IIFE bundle
- **Security constraint SEC-08**: all DOM construction uses `createElement + textContent`, never `innerHTML`
- **Tailwind CSS standalone** (no PostCSS, no npm) generating from `app/static/src/input.css`
- A **detail page URL contract** (`/ioc/<type>/<path:value>`) used in the card template

The pitfalls below are calibrated for redesign-without-new-features on this exact system.

---

## Critical Pitfalls

### Pitfall 1: CSS Class Rename Breaks E2E Tests Silently

**What goes wrong:**
The E2E page object (`tests/e2e/pages/results_page.py`) contains 20+ hard-coded CSS class selectors.
If any of these classes are renamed, removed, or restructured as part of the visual redesign, the
corresponding Playwright locator returns zero elements — and the test fails with a timeout rather
than a clear "class not found" error. The failure mode looks like a network or timing problem, not
a selector mismatch, which wastes debugging time.

The locked selectors are:
- `.ioc-card`, `.ioc-card[data-ioc-type]`, `.ioc-card[data-verdict]`, `.ioc-card:visible`
- `.ioc-value`, `.ioc-type-badge`, `.ioc-original`, `.verdict-label`, `.copy-btn`
- `.filter-bar-wrapper`, `.filter-verdict-buttons .filter-btn`, `.filter-type-pills .filter-pill`
- `.filter-search-input`, `.filter-btn--active`, `.filter-pill--active`
- `.ioc-cards-grid` (via `#ioc-cards-grid` locator in `test_extraction.py`)
- `.results-summary .ioc-count`, `.mode-indicator`, `.back-link`, `.empty-state`, `.empty-state-body`
- `#verdict-dashboard`, `.verdict-kpi-card[data-verdict]`, `.provider-coverage-row`
- `.enrichment-slot`, `.enrichment-slot--loaded`, `.chevron-toggle`, `.enrichment-details`

The E2E test for sticky positioning reads computed style directly:
```python
page.evaluate("() => window.getComputedStyle(document.querySelector('.filter-bar-wrapper')).position")
```
This fails if `.filter-bar-wrapper` is renamed or if the sticky class is moved to a child element.

**Why it happens:**
Visual redesigns naturally want to rename classes to reflect new semantic intent (e.g., rename
`.ioc-card` to `.result-card`, rename `.ioc-value` to `.indicator-value`). The developer changes the
template and CSS simultaneously and everything looks correct visually — but E2E tests fail because
the page object still uses the old class names.

**How to avoid:**
Establish a two-class strategy: keep the existing semantic class as a "test anchor" that carries
no visual styles, and add a new class for the visual redesign. Example:
```html
<div class="ioc-card result-card-v2" data-ioc-value="...">
```
The test selects `.ioc-card`; the CSS styles `.result-card-v2`. Alternatively, use `data-testid`
attributes as dedicated test hooks that are immune to CSS renaming. Update the page object to use
`data-testid` selectors before renaming any CSS classes.

**Warning signs:**
- E2E tests suddenly fail with timeout errors after template changes
- `test_filter_bar_has_sticky_position` fails without a Flask error
- `test_cards_have_verdict_labels` reports 0 elements found

**Phase to address:**
Phase 1 of redesign — establish the CSS class preservation contract before touching any template.
Run the full E2E suite after every template change, not just at the end.

---

### Pitfall 2: `data-*` Attribute Contract Broken by Template Restructuring

**What goes wrong:**
The filter logic in `filter.ts` reads `data-verdict`, `data-ioc-type`, and `data-ioc-value` from
`.ioc-card` elements. The enrichment polling in `enrichment.ts` and `cards.ts` reads and writes
`data-verdict`. The E2E tests assert on the values of these attributes directly:

```python
assert visible.get_attribute("data-ioc-value") == "8.8.8.8"
card.get_attribute("data-verdict")  # asserted == "no_data"
```

If the redesign moves these attributes to a wrapper or child element (even while keeping the classes),
the JavaScript breaks silently — filter still runs but matches against empty strings, so all cards
show/hide incorrectly — and E2E tests assert on None instead of the value.

`cards.ts:findCardForIoc()` uses `document.querySelector('.ioc-card[data-ioc-value="..."]')`.
Moving `data-ioc-value` off the `.ioc-card` root element breaks verdict updates and card sorting.

**Why it happens:**
Template restructuring for visual purposes (adding wrapper divs, moving elements into a new grid
layout) does not obviously affect JavaScript behavior. The developer tests visually, sees the card
render correctly, and ships — but the JavaScript was silently reading from elements that no longer
have the expected attributes.

**How to avoid:**
Treat `data-ioc-value`, `data-ioc-type`, and `data-verdict` on `.ioc-card` as an interface contract,
not implementation details. Document them explicitly:
```
CONTRACT: .ioc-card root element MUST carry:
  data-ioc-value="{normalized_ioc_value}"
  data-ioc-type="{ioc_type}"
  data-verdict="{verdict_key}"
These attributes are read by filter.ts, cards.ts, and enrichment.ts.
Moving them to a child element will silently break filtering and verdict updates.
```
Add a unit test that asserts these attributes exist on the root `.ioc-card` element.

**Warning signs:**
- Filter bar buttons have no visual effect after template changes
- Verdict badges never update during enrichment
- Cards always appear/disappear in groups rather than individually

**Phase to address:**
Phase 1 — document the data attribute contract before any template restructuring.

---

### Pitfall 3: Detail Page Link Contract Broken by IOC Value Encoding Change

**What goes wrong:**
Every IOC card contains a "Detail" link generated by Jinja:
```jinja
href="{{ url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value) }}"
```
The route uses `<path:ioc_value>` to handle URL IOCs containing slashes. This is a load-bearing
design decision. If the redesign changes how IOC values are displayed or encoded in the template
(e.g., wrapping values in a different element, applying URL encoding in the template rather than
letting Flask handle it, or changing how `ioc.value` is passed), the generated URL may no longer
match the route pattern.

Additionally, `enrichment.ts:findCopyButtonForIoc()` iterates `.copy-btn` elements and matches
`data-value` attributes against the IOC value string. If the copy button is restructured or its
`data-value` attribute is removed during visual cleanup, clipboard copy silently stops working.

**Why it happens:**
`url_for()` looks simple — it just generates a URL. Developers may not realize that the `<path:>`
converter is doing special work for URL-type IOCs (`https://evil.com/path/here`), or that changing
how `ioc.value` flows through the template can break URL generation for edge cases.

**How to avoid:**
Never modify the Jinja expression generating the detail link. The exact form:
```jinja
url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)
```
must be preserved verbatim. Run the URL IOC test from `test_ioc_detail_routes.py` (the
`/ioc/url/https://evil.com/beacon` case) as a smoke test after any template change.

**Warning signs:**
- Detail links for URL-type IOCs return 404
- `test_ioc_detail_routes.py::test_path_converter_handles_url_ioc` fails
- Copy button no longer copies anything after enrichment

**Phase to address:**
Before any template work — preserve the link generation expression and add it to the pre-merge
checklist.

---

### Pitfall 4: Scope Creep Converts a Refinement Milestone into a Feature Milestone

**What goes wrong:**
While redesigning the visual presentation, it becomes tempting to "while I'm here" add new features:
provider grouping by category, collapsible IOC type sections, a summary stats panel, dark/light
mode toggle, annotation-style inline notes, or animated transitions. Each individual addition looks
small, but collectively they add features that:
1. Need new tests written (which requires understanding the feature, not just visual tweaks)
2. Change the data model or routing (which requires backend work)
3. Extend the timeline beyond the stated scope
4. Risk introducing new bugs into a previously stable system

The v1.1 milestone explicitly states: "New features — v1.1 is refinement only." This constraint
exists because the test suite is calibrated to the current behavior. Adding features while redesigning
means updating tests at the same time as changing visual structure — two moving targets simultaneously.

**Why it happens:**
Redesigns offer high creative leverage. Every element is already being touched, so "just add X while
I'm here" feels efficient. The cognitive load of working in a file makes each incremental addition
feel free. It isn't — each addition has a tail cost in testing, documentation, and future maintenance.

**How to avoid:**
Maintain a "deferred features" list. Every idea that goes beyond visual restructuring gets added to
the list, not implemented. The definition of "visual restructuring" is: change that does not require
new Python routes, new TypeScript functions, new template variables, or new test cases. Review the
deferred list at the end of the milestone for a future roadmap item.

**Warning signs:**
- Template starts receiving new Jinja context variables not in the current route
- New TypeScript functions are being written (not modified) during the redesign
- The unit test count is growing, not just the E2E count being updated

**Phase to address:**
Every phase — carry the deferred features list at all times.

---

### Pitfall 5: Information Density Regression in Pursuit of "Cleaner" Design

**What goes wrong:**
SOC analysts use information density deliberately. The current card shows, in one visible state:
IOC value, type badge, verdict label, copy button, detail link, and (when present) the defanged
original. The enrichment slot shows the worst verdict badge, attribution text, and consensus badge
simultaneously before the analyst expands it. Redesigns that reduce visible information to achieve
a "cleaner" aesthetic force analysts to click to see what was previously scannable. Each additional
click per IOC multiplies across a 50-IOC triage session.

Specific information density losses to avoid:
- Removing the verdict label from the card header (visible before enrichment completes)
- Hiding the consensus badge `[3/5]` behind a hover state
- Moving the IOC type badge to a collapsed section
- Replacing the provider-count "3 providers still loading..." with a generic spinner
- Abbreviating or truncating the IOC value in the card header

**Why it happens:**
Designer instinct and general web design patterns optimize for whitespace and minimal visible
information. These patterns apply to consumer apps where users browse. This app is a professional
tool where analysts scan. The aesthetic goal ("cleaner") conflicts with the functional goal ("faster
triage"). Without SOC analyst user testing, the designer defaults to general web aesthetics.

**How to avoid:**
Define information density requirements before redesigning:
1. The IOC value must be fully visible without expansion (no truncation for typical lengths)
2. The verdict label must be visible on the card header before enrichment completes
3. The consensus badge must be visible without hover in the summary row
4. The provider count / "still loading" text must be visible per-card

Treat these as acceptance criteria. Verify each after every visual iteration.

**Warning signs:**
- Card header has fewer visible elements than before the redesign
- Analyst workflow requires more clicks to triage the same set of IOCs
- Information moved to "hover" or "expanded" states was previously always-visible

**Phase to address:**
Phase 1 — write the information density requirements before touching the CSS. Treat them as
non-negotiable acceptance criteria.

---

### Pitfall 6: CSS Specificity Wars Between Tailwind Utilities and BEM Component Classes

**What goes wrong:**
The project uses both Tailwind utility classes (from `input.css` via `@layer utilities`) and
hand-written BEM-style component classes (`.ioc-card`, `.verdict-label`, `.filter-btn`). During
a redesign, adding Tailwind utilities directly to the same elements as the existing component
classes creates specificity conflicts:

1. `@layer components` vs `@layer utilities` — utilities win by default in Tailwind's cascade
2. Adding `!important` to override component styles with utilities propagates everywhere
3. Mixing concerns: the component class handles layout/color/transition while utilities handle
   spacing/typography, with no clear boundary

The existing CSS uses `@layer` blocks in `input.css`. Adding utilities inline in the template
means the compiled `dist/style.css` may not include them if the Tailwind standalone scanner
doesn't find them in the scanned files.

**Why it happens:**
Tailwind's utility-first approach makes quick visual changes easy. Adding `px-4 py-2 rounded-lg`
to a card element works instantly. But when the component class already defines padding and
border-radius, the interaction between the two is unpredictable. Developers add `!important` to
utilities to "fix" overrides, creating a specificity debt that compounds with each iteration.

**How to avoid:**
Follow a single-layer rule for each component: either the component class owns all visual properties,
or Tailwind utilities own them — never both on the same element for the same properties. For this
redesign, the cleanest approach is to update the hand-written component classes in `input.css` and
reserve Tailwind utilities for new layout structures only. Avoid adding Tailwind utilities to
existing elements that already have component classes controlling the same property.

**Warning signs:**
- Adding `!important` to Tailwind utilities to override component class styles
- Same property (e.g., `padding`) defined in both the component class and a Tailwind utility on
  the same element
- `dist/style.css` does not reflect changes made in inline utility classes in templates

**Phase to address:**
CSS architecture decision in Phase 1 — establish which layer owns what before modifying any styles.

---

### Pitfall 7: Accessibility Regressions From Visual Restructuring

**What goes wrong:**
The existing templates have specific accessibility attributes that tests verify:
- Copy buttons: `aria-label="Copy {ioc.value}"` — verified by `test_copy_button_has_aria_label`
- Mode toggle: `aria-pressed` — verified by E2E tests
- Chevron toggle: `aria-expanded="false"` — in `_enrichment_slot.html`, wired by `enrichment.ts`
- Verdict KPI cards: `role="button" tabindex="0"` — keyboard clickable for filter-by-verdict
- Filter search input: `id="filter-search-input"` — referenced by `filter.ts` via `getElementById`

If visual restructuring moves elements, changes element types (e.g., `<div>` to `<span>`), removes
landmark roles, or strips `aria-*` attributes during cleanup, the result is:
1. Screen readers lose context
2. JavaScript wiring breaks (`filter.ts` searches `getElementById("filter-search-input")`)
3. Keyboard navigation fails for the verdict dashboard

The filter search input is doubly coupled: the `id="filter-search-input"` is used by `filter.ts`
(JavaScript) AND the class `.filter-search-input` is used by the E2E page object. Both must be
preserved.

**Why it happens:**
Visual redesigns focus on what's visible. Accessibility attributes are invisible and frequently
stripped during template cleanup as "extra noise." Developers who don't use screen readers or
keyboard navigation do not notice the regression.

**How to avoid:**
Before any template change, catalog every `aria-*`, `role=`, `tabindex`, and `id` attribute in the
results-page templates. Mark each as "JavaScript-coupled", "test-coupled", or "accessibility-only".
Never remove an attribute without checking all three categories. Run the E2E aria label tests
after every template iteration.

**Warning signs:**
- `test_copy_button_has_aria_label` fails
- Filter search input stops responding to typing (JavaScript can't find the element by ID)
- Verdict dashboard KPI cards are not keyboard-focusable

**Phase to address:**
Before template restructuring — audit and catalog all semantic attributes. Include accessibility
verification in the phase acceptance criteria.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Rename CSS classes without updating E2E page objects | Visual redesign feels clean | All filter/copy/navigation E2E tests fail; silent timeout errors | Never — update page object alongside template |
| Move `data-verdict` to a child element for layout reasons | Cleaner card structure | `filter.ts` and `cards.ts` break silently; verdict updates stop working | Never — data attributes on `.ioc-card` root are a contract |
| Add Tailwind utilities on top of existing component classes | Quick visual iteration | Specificity conflicts; `!important` debt; unclear ownership | Only for new elements with no existing component class |
| Copy visual design patterns from consumer apps | Aesthetically polished | Reduced information density; analysts need more clicks per IOC | Only when analyst-facing density requirements are met first |
| Defer E2E test runs to end of redesign phase | Faster iteration | Accumulate multiple breaking changes; harder to isolate regression source | Never — run E2E after each template change |
| Strip "redundant" `id=` or `aria-` attributes during cleanup | Cleaner HTML | JavaScript wiring breaks (`getElementById` fails); accessibility regressions | Never — audit before removing any `id` or `aria-*` |

---

## Integration Gotchas

Common mistakes when modifying the results page in this specific architecture.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Jinja + TypeScript coupling | Renaming a Jinja template variable breaks the JS data attribute read | Treat `data-job-id`, `data-mode`, `data-provider-counts` on `.page-results` as a contract between Flask route and `enrichment.ts:init()` |
| esbuild IIFE bundle | Adding a new TypeScript module without updating `main.ts` init call | `main.ts` calls `init()` for each module; new modules must be registered there or they never execute |
| Tailwind standalone CLI | Adding utility classes in templates that are not scanned | Tailwind standalone scans files listed in its config; ensure templates are included in the content glob |
| `filter.ts` querySelector scope | Moving `.ioc-card` elements outside `#filter-root` | `filter.ts` queries `filterRoot.querySelectorAll(".ioc-card")` — cards outside `#filter-root` are invisible to the filter |
| `enrichment.ts` chevron wiring | Adding new `.enrichment-details` containers with different structure | `wireExpandToggles()` expects `.chevron-toggle` followed by `.enrichment-details` as `nextElementSibling` — structural adjacency is required |
| `cards.ts` CSS.escape selector | IOC values with special characters in `data-ioc-value` | `findCardForIoc()` uses `CSS.escape()` correctly — preserve this pattern; do not change the attribute to an encoded form |

---

## Performance Traps

Patterns that work at small scale but become visible problems with 14 providers across multiple IOCs.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Expensive CSS transitions on cards | Page feels sluggish when 14 providers update 10+ cards simultaneously | Use `will-change: transform` sparingly; avoid transitions on frequently-mutated properties like `border-color` | With 10+ IOCs in online mode; each provider result triggers a card update |
| CSS animations triggered on every verdict update | Cards "flash" as each provider result arrives; visual noise | Gate animation to initial card appearance only (the existing `animation-delay` pattern does this correctly) | From first online enrichment run |
| `sortCardsBySeverity()` triggers a layout reflow | Cards re-order visually mid-enrichment; disorienting | Debounce is already implemented (100ms); do not remove it during cleanup | If debounce is removed, every provider result triggers a DOM reorder |
| Filter reapplication not triggered after DOM changes | Cards added after page load (new IOC types) may not be subject to active filters | `applyFilter()` must be called after any dynamic DOM change that adds `.ioc-card` elements | If redesign adds lazy-loaded card groups |
| Heavy CSS selectors on card grid | Painting performance degrades with many cards | Avoid attribute selectors on inner elements (`.ioc-card .enrichment-slot[data-state="loaded"]`); prefer class selectors | Visible at 20+ IOCs with active enrichment |

---

## Security Mistakes

Domain-specific security issues in the context of this redesign.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Introducing `innerHTML` during visual restructuring | XSS — API responses (IOC values, provider names, stat text) reach the DOM unsanitized | The entire `enrichment.ts` uses `createElement + textContent` (SEC-08). Never replace this with template literals or `innerHTML` for "convenience" during refactoring |
| Using `insertAdjacentHTML` as "safe innerHTML" | Same XSS risk as `innerHTML` | `insertAdjacentHTML` parses HTML; it is not safe for untrusted content. Only `createElement + textContent` is permitted |
| Exposing IOC values in URL fragments for visual effects | Fragment state visible in browser history | Existing architecture does not use fragments for state; do not introduce them during redesign |
| Weakening CSP to allow inline styles added during redesign | Inline `style=` attributes could allow style injection | If a visual effect requires inline `style=`, ensure it uses JavaScript to set `element.style.property = value` (not `innerHTML`), which is CSP-safe |

---

## UX Pitfalls

Common user experience mistakes when redesigning a professional triage tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Making verdict colors "softer" for aesthetics | Malicious and suspicious verdicts become hard to distinguish at a glance | Verdict colors are functional, not decorative — keep high-contrast for malicious (red) and suspicious (amber) |
| Removing the "NO DATA" default verdict label before enrichment | Analyst cannot tell if a card failed to load or simply has no data | The `no_data` verdict label serves as a loading state placeholder — preserve it |
| Collapsing the filter bar into a hamburger/dropdown | Filter-by-type and search require more clicks per triage session | The filter bar is used on every session; it must be always-visible (the existing sticky pattern is correct) |
| Adding hover-only tooltips for IOC type badges | Badge meaning is not discoverable for keyboard users or during fast scanning | Abbreviations (IPV4, SHA256) are already standard; if tooltip added, use `<title>` or `aria-label` not CSS-only hover |
| Reordering card elements so Copy precedes the IOC value | Breaks analyst scanning pattern (value first, actions second) | The existing order — value, type, verdict, copy, detail — follows triage priority; preserve it |
| Making the verdict dashboard KPI cards into a collapsed accordion | Removes the at-a-glance summary that makes online mode valuable | The verdict dashboard is always-visible for a reason; collapsing it removes its primary value |

---

## "Looks Done But Isn't" Checklist

Things that appear complete visually but are missing critical pieces.

- [ ] **CSS classes preserved:** Run E2E suite; all 91 tests pass. Zero selector timeouts.
- [ ] **`data-*` contracts:** `.ioc-card` root element carries `data-ioc-value`, `data-ioc-type`, `data-verdict`. Verified by `test_cards_have_data_verdict_attribute` passing.
- [ ] **Filter bar sticky:** `window.getComputedStyle(document.querySelector('.filter-bar-wrapper')).position === 'sticky'`. Verified by `test_filter_bar_has_sticky_position`.
- [ ] **Detail links:** URL IOCs (`https://evil.com/path`) produce working detail page links. Verified by navigating a URL-type IOC's detail link.
- [ ] **Copy button aria-label:** `aria-label="Copy {ioc.value}"` present on every copy button. Verified by `test_copy_button_has_aria_label`.
- [ ] **Filter search ID:** `id="filter-search-input"` on the search input — both test-coupled and JavaScript-coupled. Verify by typing in search and confirming filter applies.
- [ ] **Verdict dashboard:** `#verdict-dashboard` present in online mode, absent in offline mode. Verified by `test_online_mode_shows_verdict_dashboard` and `test_offline_mode_hides_verdict_dashboard`.
- [ ] **`#filter-root` contains all cards:** All `.ioc-card` elements are descendants of `#filter-root`. Verify filtering still works for all card types.
- [ ] **Accessibility:** Verdict KPI cards have `role="button" tabindex="0"`. Chevron toggles have `aria-expanded`. Verify by keyboard-tabbing through the page.
- [ ] **SEC-08 preserved:** No `innerHTML` or `insertAdjacentHTML` introduced. Run `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — should return zero results.
- [ ] **Information density:** Verdict label, IOC value (full), and type badge visible without any click or hover on every card in offline mode. Verify by visual inspection with 5 IOCs.
- [ ] **No new features:** Template variable list in the route matches the redesigned template's variable usage. No new Python context variables added. Run `grep -n "{{ " app/templates/results.html app/templates/partials/*.html` and compare to route context.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| E2E tests fail after CSS class rename | MEDIUM | Identify renamed class; either revert rename or add old class as secondary class on element; rerun E2E |
| Data attribute moved off `.ioc-card` root; filter broken | MEDIUM | Move attribute back to root; check `data-ioc-value`, `data-ioc-type`, `data-verdict` are all on the `.ioc-card` element; rerun unit tests for filter |
| Detail link broken for URL-type IOCs | LOW | Restore verbatim `url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)` in `_ioc_card.html`; test with URL IOC |
| Scope crept into new feature | MEDIUM | Extract the feature addition into a separate commit, revert from current branch, add to deferred features list; redesign branch should contain only visual changes |
| Information density regression found in UAT | MEDIUM | Identify which elements moved to collapsed/hover state; restore to always-visible; this is a design revision, not a code bug |
| CSS specificity conflict causes visual breakage | LOW | Remove utility classes from conflicted element; update the component class in `input.css` instead; rebuild CSS |
| `innerHTML` introduced during refactoring | HIGH — security | Revert the change immediately; re-implement using `createElement + textContent` pattern; run `grep -rn "innerHTML" app/static/src/ts/` to confirm no other occurrences |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CSS class rename breaks E2E tests (Pitfall 1) | Phase 1 — establish class preservation contract before any template edits | Run full 91-test E2E suite; zero failures |
| `data-*` contract broken (Pitfall 2) | Phase 1 — document data attribute contract in a code comment; add unit test | `test_cards_have_data_verdict_attribute` and `test_cards_have_data_ioc_value_attribute` pass |
| Detail page link contract broken (Pitfall 3) | Phase 1 — add URL IOC smoke test to pre-merge checklist | `/ioc/url/https://evil.com/beacon` returns 200; `test_path_converter_handles_url_ioc` passes |
| Scope creep (Pitfall 4) | Every phase — maintain deferred features list; PR description must state "no new features" | Route context variables unchanged; no new TypeScript functions; test count does not grow |
| Information density regression (Pitfall 5) | Phase 1 — write density requirements as acceptance criteria before CSS changes | Visual checklist: verdict label visible, IOC value untruncated, consensus badge visible, all on card without expansion |
| Tailwind/BEM specificity war (Pitfall 6) | Phase 1 CSS architecture decision — single-layer ownership rule established before styling | No `!important` in redesigned CSS; `dist/style.css` reflects all intended visual changes |
| Accessibility regressions (Pitfall 7) | Before template restructuring — catalog all `aria-*`/`role`/`id` attributes | `test_copy_button_has_aria_label`, `aria-expanded` on chevron, `role="button"` on KPI cards all verified |

---

## Sources

- Direct inspection: `tests/e2e/pages/results_page.py` (all CSS selectors the redesign must preserve)
- Direct inspection: `tests/e2e/test_results_page.py` (FILTER-01 through FILTER-04 tests with exact selector dependencies)
- Direct inspection: `tests/e2e/test_extraction.py` (structural attribute tests)
- Direct inspection: `tests/e2e/test_copy_buttons.py` (aria-label contract)
- Direct inspection: `app/templates/partials/_ioc_card.html` (data attribute layout and link generation)
- Direct inspection: `app/templates/partials/_filter_bar.html` (filter bar structure and IDs)
- Direct inspection: `app/templates/partials/_verdict_dashboard.html` (KPI card structure)
- Direct inspection: `app/static/src/ts/modules/filter.ts` (querySelector dependencies on `#filter-root`)
- Direct inspection: `app/static/src/ts/modules/cards.ts` (`findCardForIoc` data attribute contract)
- Direct inspection: `app/static/src/ts/modules/enrichment.ts` (chevron adjacency requirement, SEC-08 pattern)
- Direct inspection: `app/static/src/input.css` (existing CSS layers and component class ownership)
- Direct inspection: `app/templates/ioc_detail.html` (CSS-only tab pattern, `<path:>` URL contract)
- Project constraints: `PROJECT.md` — "New features — v1.1 is refinement only"

---

*Pitfalls research for: SentinelX v1.1 Results Page Redesign — redesigning existing multi-provider threat intel UI*
*Researched: 2026-03-16*

# Design Inspiration: SentinelX v1.2 Modern UI Redesign

**Domain:** Security tool UI — IOC triage for SOC analysts
**Researched:** 2026-02-25
**Overall confidence:** HIGH (grounded in verified design systems + real tool analysis)

---

## Executive Summary

SentinelX needs to look like it belongs alongside GreyNoise, Snyk, and Vercel — not like a Flask dev prototype. The gap between "functional tool" and "premium product" lives in four areas: surface layering, typography weight and spacing, component polish (badges, status dots, transitions), and empty/loading state craftsmanship.

The target aesthetic is **Linear-meets-GreyNoise**: near-monochromatic dark zinc background, emerald/teal accent for the security-domain accent color, crisp Inter typography at precise weights, and verdict badges with intentional semantic color coding. Every surface should feel slightly elevated from the one behind it — background → card → popover — each distinguished by a 4-8% lightness step, not a dramatic color change.

This is achievable in Tailwind CSS without a full component framework rewrite. The existing Alpine.js + vanilla JS frontend is the right architecture. What changes is the CSS design token system and component-level class choices.

---

## 1. Security Tool UI Pattern Analysis

### What premium security tools share

Research across GreyNoise Visualizer, Snyk, and CrowdStrike Falcon reveals consistent patterns:

**Near-monochromatic dark foundations**
- Backgrounds: `#0a0a0a` to `#121212` (near-black, not pure black)
- Surface 1 (page): `#0d0d0d`–`#111113`
- Surface 2 (cards): `#161618`–`#1c1c1e`
- Surface 3 (inputs, nested): `#1e1e21`–`#222225`
- Borders: `rgba(255,255,255, 0.08)`–`rgba(255,255,255, 0.12)` (barely visible white at 8–12% opacity)

**Semantic accent color = trust signal**
GreyNoise uses cyan (`#11e4e4`) as its primary interactive color. This is a deliberate choice: in security contexts, cyan/teal/emerald signals "active intelligence" rather than the "alert" red or "passive" blue of enterprise software. For SentinelX, emerald (`#10b981`) and teal (`#14b8a6`) fit this role perfectly.

**Verdict color coding is universal**
All security platforms studied use the same four-color verdict system:
- MALICIOUS / CRITICAL: Red — `#ef4444` or `#f14150`
- SUSPICIOUS / HIGH: Amber/Orange — `#f59e0b` or `#eea11b`
- CLEAN / SAFE: Green/Emerald — `#10b981` or `#22c55e`
- NO RECORD / UNKNOWN: Zinc/Gray — `#71717a` or `#94a3b8`

This matches VMRay's and Snyk's verdict systems. It's a learned pattern for analysts. Do not deviate.

**Typography: monospace for data, sans-serif for labels**
GreyNoise uses Inconsolata for IP addresses, hashes, and domains — treating them as data artifacts. Labels, headings, and navigation use Inter. SentinelX should follow this: all IOC values (IPs, domains, hashes, URLs) in a monospace font; all metadata and UI chrome in Inter.

**Information density without clutter**
Security analysts read dense data. The pattern is: tight card grids, small font sizes (12–13px for metadata), generous whitespace only at page level. Linear's 8px spacing scale (8, 16, 24, 32, 48, 64px) applied consistently achieves this.

---

## 2. Linear Design Patterns (Concrete)

Source: Linear's own redesign blog + linear.style CSS analysis.

### Color System

Linear uses LCH color space but maps to near-neutral zinc values:

```
Dark mode CSS variables (approximated to hex):
--background:    #111113  (zinc-900 equivalent)
--surface:       #1b1b1e  (between zinc-800 and zinc-900)
--alt-bg:        #222225  (zinc-800 equivalent)
--border:        rgba(255,255,255,0.08)
--text-primary:  #f4f4f5  (zinc-100)
--text-secondary:#a1a1aa  (zinc-400)
--text-muted:    #71717a  (zinc-500)
--accent:        #848CD0  (light purple in Linear; swap for emerald in SentinelX)
```

### Typography

- **Font**: Inter for body, Inter Display for headings (heavier optical weight at large sizes)
- **Body**: 13–14px, weight 400, letter-spacing: -0.01em
- **Labels/metadata**: 11–12px, weight 500, letter-spacing: 0.02em (slightly wider, uppercase optional)
- **Headings**: 16–20px, weight 600, letter-spacing: -0.02em
- **Data values (monospace)**: 12–13px JetBrains Mono or similar

### Spacing System

Linear uses an 8px base scale:
- `4px` — tight internal padding (icon gaps, badge padding)
- `8px` — standard gap between inline elements
- `12px` — card internal padding small
- `16px` — standard component padding
- `24px` — section spacing
- `32px` — card-to-card gap in grids
- `48px` — major section breaks
- `64px` — page-level padding

### Borders and Cards

- Border radius: `6px` for cards, `4px` for smaller elements, `999px` for badges/pills
- Card border: `1px solid rgba(255,255,255,0.08)`
- Card background: slightly lighter than page (4–6% lighter in perceptual lightness)
- No dramatic drop shadows on dark backgrounds — shadows read as glow artifacts
- Instead: subtle inset highlight `box-shadow: inset 0 1px 0 rgba(255,255,255,0.06)` gives cards a top-edge highlight

### Micro-interactions

- Hover state: background transitions to 2–4% lighter surface, `150ms ease-out`
- Focus ring: `2px offset, 2px solid currentColor` (matches accent color)
- Transitions: only on `background-color`, `color`, `border-color`, `opacity` — never on `width/height` (layout thrash)
- Click: `scale(0.98)` via `transform`, `80ms ease-in`

---

## 3. Vercel Geist Design Patterns (Concrete)

Source: Verified Geist design system CSS variables from community analysis.

### Color Tokens (Dark Mode)

```css
/* Geist dark mode verified values */
--geist-background:  #000000  (pure black — Vercel leans harder dark than Linear)
--geist-foreground:  #ffffff
--accents-1:         #111111  (lightest surface)
--accents-2:         #1a1a1a  (card surface)
--accents-3:         #333333  (muted elements)
--accents-4:         #444444
--accents-5:         #666666  (secondary text)
--accents-6:         #888888  (muted text)
--accents-7:         #999999
--accents-8:         #fafafa  (near white, used for subtle borders)
--geist-success:     #0070f3  (blue — not green; Vercel uses blue for "success")
--geist-error:       #ff0000
--geist-warning:     #f5a623
--geist-cyan:        #50e3c2  (used for status indicators)
```

Note: Vercel uses blue for "success" (deployment ready), which is a developer-tool convention. **SentinelX should use the security-domain convention instead: emerald green for CLEAN verdicts** since analysts expect red/green for threat/no-threat.

### Card Design

Vercel cards use:
- Background: `#111` on `#000` background
- Border: `1px solid #333` (about 20% white opacity equivalent)
- Border radius: `8px`
- No shadows — pure border + background distinction
- Hover: border color shifts to `#555`

### Status Indicators

Vercel's status dot component uses a `6px` diameter circle with:
- READY (success): `#50e3c2` (teal/cyan)
- ERROR: `#ff0000`
- BUILDING: pulsing amber `#f5a623`
- QUEUED: `#888888` (gray)

The "building" pulse animation is `scale(1)` → `scale(1.5)` with `opacity(1)` → `opacity(0)`, `1.5s ease-in-out infinite`. This is the standard "loading ping" pattern and directly applicable to SentinelX's enrichment-in-progress state.

---

## 4. Color System for SentinelX

### Recommended Palette

Using Tailwind v3 hex values as the source of truth (verified):

```
ZINC SCALE (foundation):
zinc-950: #09090b   ← page background
zinc-900: #18181b   ← primary card background
zinc-800: #27272a   ← input background, secondary surfaces
zinc-700: #3f3f46   ← active/hover states, dividers
zinc-600: #52525b   ← borders (can also use as rgba)
zinc-500: #71717a   ← muted text, disabled
zinc-400: #a1a1aa   ← secondary text, labels
zinc-300: #d4d4d8   ← primary text (softer than white)
zinc-100: #f4f4f5   ← headings, high-emphasis text
zinc-50:  #fafafa   ← pure white equivalent accents

EMERALD SCALE (primary accent — security domain "safe"):
emerald-950: #022c22
emerald-900: #064e3b
emerald-800: #065f46
emerald-700: #047857  ← badge background (dark)
emerald-600: #059669  ← badge border, secondary CTA
emerald-500: #10b981  ← primary accent, CLEAN verdict badge text
emerald-400: #34d399  ← hover state on emerald elements
emerald-300: #6ee7b7  ← text on dark emerald backgrounds
emerald-100: #d1fae5  ← very light emerald for subtle highlights

TEAL SCALE (secondary accent — interactive elements):
teal-600: #0d9488
teal-500: #14b8a6  ← interactive highlights, focus rings
teal-400: #2dd4bf  ← hover on interactive teal elements
teal-300: #5eead4  ← bright teal for active states

STATUS PALETTE (semantic, do not modify):
red-500:    #ef4444  ← MALICIOUS verdict
red-400:    #f87171  ← MALICIOUS badge text on dark bg
red-950:    #450a0a  ← MALICIOUS badge background
amber-500:  #f59e0b  ← SUSPICIOUS verdict
amber-400:  #fbbf24  ← SUSPICIOUS badge text
amber-950:  #451a03  ← SUSPICIOUS badge background
emerald-500:#10b981  ← CLEAN verdict
emerald-950:#022c22  ← CLEAN badge background
zinc-400:   #a1a1aa  ← NO RECORD verdict text
zinc-800:   #27272a  ← NO RECORD badge background
```

### CSS Variable Architecture

```css
:root {
  /* Surfaces — 4 layers */
  --surface-base:    #09090b;  /* zinc-950 — page */
  --surface-1:       #18181b;  /* zinc-900 — primary cards */
  --surface-2:       #27272a;  /* zinc-800 — inputs, nested cards */
  --surface-3:       #3f3f46;  /* zinc-700 — hover states */

  /* Borders */
  --border-subtle:   rgba(255,255,255,0.06);  /* barely visible */
  --border-default:  rgba(255,255,255,0.10);  /* standard card border */
  --border-emphasis: rgba(255,255,255,0.18);  /* hover/focus border */

  /* Text hierarchy — 4 levels */
  --text-primary:    #f4f4f5;  /* zinc-100 — headings */
  --text-secondary:  #d4d4d8;  /* zinc-300 — body text */
  --text-tertiary:   #a1a1aa;  /* zinc-400 — labels, metadata */
  --text-muted:      #71717a;  /* zinc-500 — disabled, placeholders */

  /* Accent */
  --accent:          #10b981;  /* emerald-500 */
  --accent-hover:    #34d399;  /* emerald-400 */
  --accent-subtle:   #022c22;  /* emerald-950 — bg for accent regions */
  --accent-border:   #047857;  /* emerald-700 — border for accent regions */

  /* Interactive secondary */
  --interactive:     #14b8a6;  /* teal-500 */
  --interactive-hover:#2dd4bf; /* teal-400 */

  /* Verdicts */
  --verdict-malicious-text:  #f87171;  /* red-400 */
  --verdict-malicious-bg:    #450a0a;  /* red-950 */
  --verdict-malicious-border:#ef4444;  /* red-500 */
  --verdict-suspicious-text: #fbbf24;  /* amber-400 */
  --verdict-suspicious-bg:   #451a03;  /* amber-950 */
  --verdict-suspicious-border:#f59e0b; /* amber-500 */
  --verdict-clean-text:      #34d399;  /* emerald-400 */
  --verdict-clean-bg:        #022c22;  /* emerald-950 */
  --verdict-clean-border:    #10b981;  /* emerald-500 */
  --verdict-norecord-text:   #a1a1aa;  /* zinc-400 */
  --verdict-norecord-bg:     #27272a;  /* zinc-800 */
  --verdict-norecord-border: #3f3f46;  /* zinc-700 */
}
```

---

## 5. Typography System

### Font Stack

```css
--font-sans: 'Inter', 'Inter var', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Menlo', monospace;
```

**Why Inter:** Linear, Vercel, and Linear-style SaaS universally use Inter. It was designed for screen readability, has a tall x-height (great for dense data), and 9 weights for fine-grained hierarchy. Available free from Google Fonts or via local hosting.

**Why JetBrains Mono for IOC values:** IP addresses, hashes, domains, and URLs are data artifacts — treating them as code with a monospace font creates instant visual distinction between "label" and "value", which is critical for analyst scanning speed.

### Scale

```
--text-xs:    11px / 1.4  weight: 500   letter-spacing: 0.04em   (labels, badges)
--text-sm:    12px / 1.5  weight: 400   letter-spacing: 0.01em   (metadata, secondary)
--text-base:  13px / 1.6  weight: 400   letter-spacing: 0      (body, card content)
--text-md:    14px / 1.5  weight: 500   letter-spacing: -0.01em  (card titles)
--text-lg:    16px / 1.4  weight: 600   letter-spacing: -0.015em (section headers)
--text-xl:    20px / 1.3  weight: 600   letter-spacing: -0.02em  (page title)
--text-2xl:   24px / 1.2  weight: 700   letter-spacing: -0.025em (hero heading)
```

### Text Hierarchy in Practice

```
Page title:        24px, weight 700, zinc-100, -0.025em
Section heading:   16px, weight 600, zinc-100, -0.015em
Card title:        14px, weight 500, zinc-300, -0.01em
Body / meta:       13px, weight 400, zinc-400
Labels (ALL CAPS): 11px, weight 500, zinc-500, 0.06em (uppercase tracking)
IOC values:        13px JetBrains Mono, weight 400, zinc-300
Muted / disabled:  12px, weight 400, zinc-600
```

The uppercase + wide-tracking pattern for labels (`MALICIOUS`, `IPv4`, `HASH`, `PROVIDER`) is universally used in security tools. It signals "system classification" vs "human content".

---

## 6. Component Gallery — Premium Signals

### 6.1 Verdict Badge (Pill)

```html
<!-- MALICIOUS example -->
<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold
             tracking-wide uppercase
             bg-red-950 text-red-400 border border-red-800/50">
  <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
  MALICIOUS
</span>
```

Key specs:
- Shape: `border-radius: 9999px` (full pill)
- Padding: `4px 8px` (py-0.5 px-2)
- Font: 11px, weight 600, uppercase, letter-spacing 0.04em
- Leading dot: 6px circle in the pure status color
- Background: 950 shade (very dark tint)
- Text: 400 shade (readable on dark bg)
- Border: 800 shade at 50% opacity

Apply same pattern for all four verdict states using the palette above.

### 6.2 Status Indicator Dot (Loading)

For enrichment in-progress (Vercel-style status dot):

```css
/* Pulsing dot for "querying" state */
.status-loading {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #14b8a6;  /* teal-500 */
  position: relative;
}
.status-loading::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: inherit;
  animation: ping 1.2s cubic-bezier(0,0,0.2,1) infinite;
}
@keyframes ping {
  75%, 100% { transform: scale(2); opacity: 0; }
}
```

### 6.3 IOC Type Badge (Inline Tag)

For distinguishing IPv4, Domain, Hash, URL, CVE:

```html
<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono
             font-medium bg-zinc-800 text-zinc-400 border border-zinc-700/60">
  IPv4
</span>
```

These should be small (not pill — rectangular with 4px radius) and use a monospace font to feel like terminal type labels.

### 6.4 Card Component (IOC Result Card)

```
Anatomy from top to bottom:
┌─────────────────────────────────────────────┐ ← border: 1px solid rgba(255,255,255,0.08)
│ ████ [IOC type badge]    [verdict badge] ░░ │ ← card header: surface-2, px-4 py-3
│─────────────────────────────────────────────│ ← divider: 1px solid rgba(255,255,255,0.06)
│ [monospace IOC value]                       │ ← surface-1, px-4 py-3
│─────────────────────────────────────────────│
│ Provider results (3 rows)                   │ ← px-4 py-2, smaller text
└─────────────────────────────────────────────┘

- Border radius: 8px
- Background: zinc-900 (#18181b)
- Top header region: slightly darker zinc-800 bg OR accent left border for severity
- Left border accent: 3px solid [verdict color] (Carbon Design System pattern)
- No drop shadow (use border only)
- Hover: border-color shifts to rgba(255,255,255,0.16)
- Transition: border-color 150ms ease-out
```

The **left accent border** (3px colored bar on the card's left edge) is the Carbon Design System pattern for severity indication. It communicates verdict at a glance even before reading the badge. Use it on result cards.

### 6.5 Skeleton Loader

For the moment between submit and results appearing:

```css
.skeleton {
  background: linear-gradient(
    90deg,
    #27272a 25%,
    #3f3f46 37%,
    #27272a 63%
  );
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}
@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
```

Show 3–5 skeleton card placeholders during enrichment loading. This communicates "results are coming" better than a spinner.

### 6.6 Toast Notification

```
Position: bottom-right, 16px from edge
Size: min-width 280px, max-width 360px
Background: zinc-800 (#27272a)
Border: 1px solid rgba(255,255,255,0.12)
Border radius: 8px
Shadow: 0 4px 16px rgba(0,0,0,0.6)  ← shadows read well on very dark UIs
Left border: 3px solid [success/error/info color]
Font: 13px Inter, zinc-300
Duration: 4000ms auto-dismiss
Animation: slide in from right, 200ms ease-out; slide out right, 150ms ease-in
```

### 6.7 Filter Bar (Results Page)

```
Position: sticky top-0 (stays visible while scrolling)
Background: zinc-950/95 with backdrop-filter: blur(12px)  ← glassmorphism nav
Border-bottom: 1px solid rgba(255,255,255,0.08)
Height: 48px
Padding: 0 24px

Filter pills: rounded-md (not full pill), 6px radius
Active filter: bg-zinc-800 border-zinc-600 text-zinc-100
Inactive filter: bg-transparent border-transparent text-zinc-400
Hover: border-zinc-700 text-zinc-300
```

The sticky blurred filter bar is the definitive "this is a premium product" signal. Linear uses it for sidebar nav, Vercel uses it for deployment filters, Netlify uses it for their dashboard.

---

## 7. Empty State Design

### Philosophy
Security-context empty states should communicate **readiness**, not absence. The input page before a scan, the results page with no filters matching — both need purposeful messaging.

### Recommended Pattern (Input Page — Pre-Scan)

```
NO ILLUSTRATION (decorative art on security tools feels incongruous)
Instead:
- Subtle terminal-style monospace text OR
- Simple geometric icon (shield, search, terminal cursor)
- Centered in the textarea focus area

Message pattern:
  [Icon — 24px, zinc-600]
  "Paste intelligence text to begin triage"
  [12px, zinc-500, centered]
```

### Recommended Pattern (Results — No Matches)

```
- Centered vertically in results area
- Icon: zinc-600 (not colored)
- Title: "No IOCs match current filters"  [14px, zinc-400, weight 500]
- Subtitle: "Clear filters to see all [N] extracted indicators"  [12px, zinc-500]
- CTA: "Clear all filters"  [text button, emerald-500, 13px]
```

Linear and Notion both use monochrome, minimal empty states — no illustrations, just purposeful copy and a single CTA. This is the correct pattern for tool UIs (not marketing sites).

---

## 8. Specific Recommendations per Page

### 8.1 INPUT PAGE

**Goal:** Feel like a focused, professional intake terminal.

```
Layout:
- Max-width: 720px centered
- Page background: zinc-950 (#09090b)
- Generous vertical centering (form vertically centered in viewport)

Header section:
- App name: "SentinelX" — 20px Inter, weight 700, zinc-100, letter-spacing -0.02em
- Subtitle: "IOC Extraction & Enrichment" — 13px, zinc-400
- Right-aligned: version badge (zinc-700 bg, zinc-400 text) + mode status dot

Textarea:
- Background: zinc-900 (#18181b)
- Border: 1px solid rgba(255,255,255,0.08)
- Border-radius: 8px
- Focus border: 1px solid teal-600 (#0d9488) with box-shadow: 0 0 0 3px rgba(14,165,233,0.15)
- Font: 13px JetBrains Mono — text is already "code-like data"
- Placeholder: zinc-600, "Paste alert text, email headers, threat reports..."
- Min-height: 240px

Toggle (Offline/Online mode):
- Track: zinc-700 (OFF) / emerald-700 (ON)
- Thumb: white circle, 2px shadow
- Label: "Offline" / "Online" — 13px, zinc-300, weight 500
- Online mode: show a teal status dot to the right of "Online"

Submit button:
- Background: emerald-600 (#059669) default / emerald-500 hover
- Text: white, 14px, weight 600
- Border-radius: 6px
- Padding: 10px 24px
- Transition: background 120ms ease, transform 80ms ease
- Active: scale(0.98)
- Disabled (no input): zinc-800 bg, zinc-600 text, cursor not-allowed
```

**Contextual submit button text (already implemented — maintain this):**
- 0 chars: "Paste text to analyze" (disabled)
- Offline mode: "Extract IOCs"
- Online mode: "Extract & Enrich"

### 8.2 RESULTS PAGE

**Goal:** Dense, scannable intelligence report. Not a pretty dashboard — an analyst's terminal.

```
Page layout:
- Max-width: 1200px
- Two-column: sidebar summary (280px) + main card grid

Sticky filter bar:
- height: 48px, backdrop-blur: 12px, bg: zinc-950/95
- Filter chips: verdict filter (ALL / MALICIOUS / SUSPICIOUS / CLEAN / NO RECORD)
  + type filter (ALL / IPv4 / Domain / URL / Hash / CVE)
- Search input: 200px wide, inline in filter bar, zinc-800 bg, teal focus ring
- Result count: "Showing 12 of 47 IOCs" — zinc-500, 12px, right-aligned

Summary dashboard (sidebar):
- Card: zinc-900, border rgba(255,255,255,0.08), border-radius 8px
- Title: "Scan Summary" — 13px, zinc-400, uppercase, weight 500, tracking wide
- Stats: large number (24px, weight 700) + label (11px, zinc-500)
- Color-coded counts: red-400, amber-400, emerald-400, zinc-400 for verdict counts

IOC result cards:
- Grid: 1 column (full width of main area)
- Card: zinc-900, border rgba(255,255,255,0.08), border-radius 8px
- Left border accent: 3px solid [verdict color — red/amber/emerald/zinc]
- Header row (px-4 py-3):
    - [IOC type tag] [monospace IOC value — zinc-200] [verdict badge right-aligned]
- Divider: 1px solid rgba(255,255,255,0.06)
- Provider section (px-4 py-3):
    - 3 columns for providers: [provider name] [timestamp] [verdict pill]
    - Provider name: 11px, zinc-500, uppercase
    - Verdict text: emerald/red/amber/zinc appropriate color
    - Timestamp: 11px, zinc-600, monospace

Enrichment loading state:
- Show skeleton cards (shimmer animation)
- Status: teal pulsing dot + "Querying providers..." text
```

**Card left border verdict accent is the highest-impact single change.** An analyst scanning 30 IOCs can immediately see the 3 red-bordered cards without reading any text.

### 8.3 SETTINGS PAGE

**Goal:** Clean, professional configuration form. Not a cluttered admin panel.

```
Layout:
- Max-width: 560px centered
- Single column

Header:
- "Settings" — 20px, weight 600, zinc-100
- "API key configuration" — 13px, zinc-400

Form groups (each provider):
Provider name row:
  - Icon (optional: provider logo or generic key icon, 16px, zinc-500)
  - Provider name: 14px, weight 500, zinc-200
  - Status badge: "Configured" (emerald) or "Not configured" (zinc-600 text)

Input:
  - Label: 12px, zinc-400, weight 500 (above input)
  - Input: zinc-800 bg, border rgba(255,255,255,0.1), border-radius 6px, 40px height
  - Font: 13px JetBrains Mono (API keys are code artifacts)
  - Type: password (show/hide toggle — eye icon, zinc-500)
  - Placeholder: "••••••••••••••••" or "VT-XXXXXXXXXXXXXXXX" pattern hint
  - Focus: teal ring (2px solid teal-500, 2px offset)
  - Saved state: green checkmark appears at right, "Saved" 11px text emerald-500

Sections:
  - Divider between providers: 1px solid rgba(255,255,255,0.06)
  - Optional: info callout for public APIs (MalwareBazaar, ThreatFox):
    bg: zinc-900, border: rgba(255,255,255,0.06), text: zinc-400, 12px
    "No configuration required — public API"
```

---

## 9. Animation and Transition Reference

### Approved transitions (all GPU-accelerated):

```css
/* Standard interactive */
transition: background-color 150ms ease-out, border-color 150ms ease-out, color 150ms ease-out;

/* Button press */
transition: transform 80ms ease-in, background-color 120ms ease-out;
transform: scale(0.98); /* active state */

/* Toast slide in */
animation: slideInRight 200ms cubic-bezier(0.16, 1, 0.3, 1);
@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

/* Skeleton shimmer (1.4s, subtle) */
animation: shimmer 1.4s ease infinite;

/* Status dot pulse (1.2s, for enrichment loading) */
animation: ping 1.2s cubic-bezier(0,0,0.2,1) infinite;

/* Verdict badge reveal (when results arrive) */
animation: fadeIn 200ms ease-out;
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**Never animate:** `width`, `height`, `max-height`, `top`, `left` (layout properties — cause reflow)
**Always animate:** `transform`, `opacity`, `background-color`, `border-color`, `color`

---

## 10. Typography Accessibility on Dark

WCAG AA requires 4.5:1 contrast for normal text, 3:1 for large text.

| Use | Color | On Background | Approximate Ratio | Pass? |
|-----|-------|--------------|-------------------|-------|
| Headings | zinc-100 (#f4f4f5) | zinc-950 (#09090b) | ~18:1 | AA+ |
| Body | zinc-300 (#d4d4d8) | zinc-950 (#09090b) | ~12:1 | AA+ |
| Secondary | zinc-400 (#a1a1aa) | zinc-950 (#09090b) | ~7:1 | AA |
| Muted | zinc-500 (#71717a) | zinc-950 (#09090b) | ~4.5:1 | AA (borderline) |
| Placeholders | zinc-600 (#52525b) | zinc-900 (#18181b) | ~2.5:1 | Fails AA |

**Action:** Placeholders should use zinc-500 on zinc-900 backgrounds (not zinc-600). Increase placeholder color to maintain at least 3:1.

---

## 11. What NOT to Do (Anti-Patterns)

| Anti-Pattern | Why It Fails | What to Do Instead |
|---|---|---|
| Pure black (#000) page background | Too stark, card elevation impossible | Use zinc-950 (#09090b) |
| Pure white text on dark | Eye strain, "overdone terminal" look | zinc-100 (#f4f4f5) for headings |
| Generic blue for all accents | Corporate enterprise feel | Emerald/teal for security domain signal |
| Illustrations in empty states | Incongruous with analyst tool UX | Minimal icon + purposeful copy |
| Combined/numeric threat scores | Obfuscates data, analysts hate this | Raw verdict labels per provider (already SentinelX's design) |
| Glassmorphism on cards | Readability sacrifice, trendy → dated | Glassmorphism only on sticky overlays (filter bar, modals) |
| Animated gradients on backgrounds | Distracting during analysis | Static surface layers only |
| Drop shadows on dark bg | Appear as glow artifacts | Use borders + background-color distinction |
| Sans-serif for IOC values | Values look like labels, not data | Monospace for all IOC values |
| Spinner for enrichment loading | No progress feedback | Skeleton cards + status text + status dot |

---

## 12. Reference Products Summary

| Product | What to Steal | Color | Typography | Component |
|---------|--------------|-------|------------|-----------|
| **GreyNoise Visualizer** | Monospace-first data display, cyan/teal as primary interactive | `#121212` bg, `#11e4e4` accent | Inconsolata + Inter | Dense IP lookup cards |
| **Linear** | 8px spacing scale, surface layering, LCH-based neutral palette | zinc-equivalent bg, violet accent | Inter + Inter Display | Card borders, sidebar density |
| **Vercel Geist** | Status dot (pulsing), sticky blurred nav bar, deployment-state badges | `#000` bg, `#50e3c2` teal status | Inter | Status indicators, filter bars |
| **Snyk** | Verdict severity badges (Critical/High/Medium/Low), issue card layout | Dark navy, red/amber severity | Inter | Severity badge system |
| **CrowdStrike Falcon** | Widget-based dashboard, dark neutral canvas | `#1a1a2e` deep navy bg | Sans-serif headings | Dashboard cards |
| **Carbon Design System** | Top-border/left-border severity pattern on cards | `#24a148` green, `#da1e28` red | IBM Plex Sans | Status indicator cards |

---

## Sources

- [Linear UI Redesign — linear.app/now](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [Linear Design: LogRocket analysis](https://blog.logrocket.com/ux-design/linear-design/)
- [Linear Changelog March 2024](https://linear.app/changelog/2024-03-20-new-linear-ui)
- [Vercel Geist CSS Variables — community analysis](https://github.com/2nthony/vercel-css-vars)
- [Tailwind CSS Color Scales v3 (verified hex values)](https://v3.tailwindcss.com/docs/customizing-colors)
- [shadcn/ui Theming — dark mode CSS variables](https://ui.shadcn.com/docs/theming)
- [Carbon Design System — Status Indicator Pattern](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- [VMRay Verdict System design](https://www.vmray.com/cyber-security-blog/explained-vmray-verdict-system/)
- [GreyNoise Visualizer](https://viz.greynoise.io/)
- [Cyber security color palettes with hex values](https://produkto.io/color-palettes/cyber-security)
- [Skeleton loader shimmer pattern](https://frontend-hero.com/how-to-create-skeleton-loader)
- [CSS Transitions reference — Josh W. Comeau](https://www.joshwcomeau.com/animation/css-transitions/)
- [Command palette UX patterns — Mobbin](https://mobbin.com/glossary/command-palette)
- [Dark mode design guide — UI Deploy](https://ui-deploy.com/blog/complete-dark-mode-design-guide-ui-patterns-and-implementation-best-practices-2025)