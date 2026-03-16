# Roadmap: SentinelX

## Milestones

- ✅ **v1.0 Foundation** — All prior work (shipped 2026-03-14)
- 🚧 **v1.1 Results Page Redesign** — Phases 1-5 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation — SHIPPED 2026-03-14</summary>

All prior milestones (v1.0 MVP through v7.0 partial) collapsed into v1.0 Foundation at version reset.
Includes: IOC extraction, 14 providers, results page, detail pages, cache, export, bulk input, ASN intel, relationship graphs, security hardening.

See `.planning/MILESTONES.md` for full internal milestone history.

</details>

### 🚧 v1.1 Results Page Redesign (In Progress)

**Milestone Goal:** Make 14 providers feel like one cohesive intelligence report instead of 14 separate search results stapled together.

## Phase Details

### Phase 1: Contracts and Foundation
**Goal**: All preservation contracts are documented and enforced before a single line of visual code changes
**Depends on**: Nothing (first phase)
**Requirements**: (none — foundation work that enables all other phases safely)
**Success Criteria** (what must be TRUE):
  1. Every CSS class used by E2E selectors is catalogued with a "do not rename" rule and the catalog is committed to the repo
  2. The `data-ioc-value`, `data-ioc-type`, and `data-verdict` attribute contract on `.ioc-card` is documented in code comments in the template
  3. Information density acceptance criteria are written out (IOC value visible, verdict label always visible, consensus count not hover-only)
  4. A CSS layer ownership rule exists: component classes own all visual properties for existing elements; Tailwind utilities for new layout structures only
**Plans**: 1 plan
Plans:
- [ ] 01-01-PLAN.md — CSS contract catalog, inline source annotations, and E2E baseline confirmation

### Phase 2: TypeScript Module Extractions
**Goal**: `enrichment.ts` is split into three focused modules with zero behavioral change — visual redesign work is now isolated to `row-factory.ts`
**Depends on**: Phase 1
**Requirements**: (none — architectural refactor that isolates the visual redesign)
**Success Criteria** (what must be TRUE):
  1. `verdict-compute.ts` exists (~80 LOC) with pure functions `computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry` and no DOM access
  2. `row-factory.ts` exists (~150 LOC) with unified `createProviderRow(result, kind, statText)` owning the `CONTEXT_PROVIDERS` set and all row-building DOM code
  3. `enrichment.ts` is trimmed to ~300 LOC as the polling orchestrator and state owner only
  4. All 91 E2E tests pass unchanged after extraction — zero behavioral change
**Plans**: TBD

### Phase 3: Visual Redesign
**Goal**: Provider rows display a clear visual hierarchy with verdict prominence, a breakdown micro-bar, category labels, and no-data rows collapsed by default
**Depends on**: Phase 2
**Requirements**: VIS-01, VIS-02, VIS-03, GRP-02
**Success Criteria** (what must be TRUE):
  1. The worst verdict badge is the dominant visual element in each IOC card header — noticeably larger and higher-contrast than provider row verdicts (VIS-01)
  2. The summary row shows a visual count bar of malicious/suspicious/clean/no-data providers — the `[2/5]` text consensus badge is gone and replaced by the micro-bar (VIS-02)
  3. Provider rows within the Reputation and Infrastructure sections display a distinct category label so analysts can tell at a glance which section they are reading (VIS-03)
  4. No-data providers are collapsed by default — only a count summary ("5 had no record") is visible without interaction (GRP-02)
  5. All 91 E2E tests pass; no information density regression (all content visible without hover)
**Plans**: TBD

### Phase 4: Template Restructuring
**Goal**: The HTML template delivers three explicit sections — Reputation, Infrastructure Context, No Data — as the structural backbone of each IOC card
**Depends on**: Phase 3
**Requirements**: GRP-01
**Success Criteria** (what must be TRUE):
  1. Each IOC card visibly organizes provider results under three labeled sections: Reputation, Infrastructure Context, and No Data (GRP-01)
  2. All `data-ioc-value`, `data-ioc-type`, and `data-verdict` attributes remain on the `.ioc-card` root element — filtering, verdict updates, and card sorting all function correctly
  3. URL IOC detail links resolve correctly — `/ioc/url/https://evil.com/beacon` returns 200 (the `<path:>` route contract is preserved)
  4. All 91 E2E tests pass at zero failures after template restructuring
**Plans**: TBD

### Phase 5: Context and Staleness
**Goal**: Key context fields and cache age are visible in the IOC card header without requiring any accordion expansion
**Depends on**: Phase 4
**Requirements**: CTX-01, CTX-02
**Success Criteria** (what must be TRUE):
  1. For IP IOCs, GeoIP country and ASN org are visible in the card header before the analyst expands any section (CTX-01)
  2. For domain IOCs, the registrar is visible in the card header before the analyst expands any section (CTX-01)
  3. IOC cards with cached results show a staleness indicator (e.g., "data from 4h ago") in the summary row without requiring any interaction (CTX-02)
  4. All 91 E2E tests pass; context fields degrade gracefully when data is unavailable (no layout shift, no blank UI slots)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Contracts and Foundation | 1/1 | Complete   | 2026-03-16 | - |
| 2. TypeScript Module Extractions | v1.1 | 0/TBD | Not started | - |
| 3. Visual Redesign | v1.1 | 0/TBD | Not started | - |
| 4. Template Restructuring | v1.1 | 0/TBD | Not started | - |
| 5. Context and Staleness | v1.1 | 0/TBD | Not started | - |
