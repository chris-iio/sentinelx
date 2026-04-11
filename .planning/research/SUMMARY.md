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
