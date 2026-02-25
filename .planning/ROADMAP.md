# Roadmap: oneshot-ioc

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-24)
- 🔲 **v1.1 UX Overhaul** — Phases 6-10 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-24</summary>

- [x] Phase 1: Foundation and Offline Pipeline (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Core Enrichment (4/4 plans) — completed 2026-02-21
- [x] Phase 3: Additional TI Providers (3/3 plans) — completed 2026-02-21
- [x] Phase 3.1: Integration Fixes and Git Hygiene (1/1 plan) — completed 2026-02-22 *(INSERTED)*
- [x] Phase 4: UX Polish and Security Verification (2/2 plans) — completed 2026-02-24

Full details: `milestones/v1.0-ROADMAP.md`

</details>

### v1.1 UX Overhaul (Phases 6-10)

- [ ] **Phase 6: Foundation — Tailwind + Alpine + Card Layout** - Set up Tailwind CLI and Alpine.js, rewrite results page from table to card layout with summary dashboard
- [x] **Phase 7: Filtering & Search** - Verdict filter bar, IOC type pills, text search, sticky filters, grouped-by-type toggle (completed 2026-02-25)
- [ ] **Phase 8: Input Page Polish** - Toggle switch, paste feedback, contextual submit button, larger textarea
- [ ] **Phase 9: Export & Copy Enhancements** - Export dropdown (text/JSON/CSV), structured clipboard, bulk selection, copy selected
- [ ] **Phase 10: Settings & Polish** - Test connection button, accessibility audit, performance verification, final E2E pass

## Phase Details

### Phase 6: Foundation — Tailwind + Alpine + Card Layout
**Goal**: Results page displays IOCs as severity-sorted cards with a summary dashboard, powered by Tailwind CSS and Alpine.js, with all E2E tests passing on the new layout
**Depends on**: v1.0 complete (Phase 4)
**Requirements**: LAYOUT-01, LAYOUT-02, LAYOUT-03, LAYOUT-04, LAYOUT-05
**Success Criteria** (what must be TRUE):
  1. Tailwind CSS standalone CLI is integrated into the build process (Makefile target) and generates production CSS
  2. Alpine.js CSP build loads from `/static/` without CSP violations — verified by browser console check
  3. Results page displays each IOC as a card with: value, type badge, verdict label, and provider details
  4. Cards are sorted by verdict severity: malicious → suspicious → clean → no data
  5. Summary dashboard at top shows clickable verdict count badges with correct totals
  6. E2E tests pass with updated page object selectors targeting the new card layout
Plans:

### Phase 7: Filtering & Search
**Goal**: Analyst can instantly narrow results by verdict, IOC type, or text search — reducing visual noise from 50+ IOCs to just the ones that matter
**Depends on**: Phase 6
**Requirements**: FILTER-01, FILTER-02, FILTER-03, FILTER-04
**Success Criteria** (what must be TRUE):
  1. Clicking "Malicious" in the verdict filter bar shows only malicious IOC cards, hiding all others
  2. IOC type pills only appear for types present in current results (no phantom pills)
  3. Typing in the search box filters cards in real-time (<100ms response) by IOC value substring match
  4. Filter bar remains visible (sticky) when scrolling through 50+ cards
  5. Dashboard verdict badges act as filter shortcuts — clicking one applies the corresponding verdict filter
**Plans:** 2/2 plans complete
Plans:
- [ ] 07-01-PLAN.md — Alpine filter component + filter bar HTML + CSS + safelist
- [ ] 07-02-PLAN.md — E2E tests for filter interactions + visual verification

### Phase 8: Input Page Polish
**Goal**: Input page communicates mode clearly and provides immediate feedback on paste actions, reducing analyst confusion about what will happen when they submit
**Depends on**: Phase 6 (needs Tailwind/Alpine foundation)
**Requirements**: INPUT-01, INPUT-02, INPUT-03
**Success Criteria** (what must be TRUE):
  1. Mode selector is a toggle switch (not dropdown) with clear "Offline" / "Online" labels and visual state
  2. Pasting text into the textarea shows "N characters pasted" feedback near the input
  3. Submit button reads "Extract IOCs" in offline mode and "Extract & Enrich" in online mode, updating reactively on toggle
**Plans:** 1/2 plans executed
Plans:
- [ ] 08-01-PLAN.md — Toggle switch, paste feedback, reactive submit label (HTML + CSS + JS)
- [ ] 08-02-PLAN.md — E2E test updates + human visual verification

### Phase 9: Export & Copy Enhancements
**Goal**: Analyst can export triage results in multiple formats and selectively copy IOCs, eliminating manual copy-paste into reports
**Depends on**: Phase 6 (needs card layout with checkboxes)
**Requirements**: EXPORT-01, EXPORT-02, EXPORT-03, EXPORT-04
**Success Criteria** (what must be TRUE):
  1. Export dropdown offers three options: Copy to clipboard (text), Download JSON, Download CSV
  2. Clipboard copy produces structured text with headers (IOC, Type, Verdict, Provider Details) not raw dump
  3. Each IOC card has a checkbox; "Select All" and "Copy Selected" buttons appear when any box is checked
  4. Bulk operations respect the current filter — "Select All" selects only visible (filtered) cards
  5. Downloaded JSON contains all enrichment data; CSV contains flattened summary fields
Plans:

### Phase 10: Settings & Polish
**Goal**: Settings page validates API configuration, all UI elements are keyboard-accessible with ARIA labels, and the app performs smoothly at scale
**Depends on**: Phase 9 (all features complete)
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):
  1. "Test Connection" button in settings sends a lightweight VT API call and shows success/failure feedback
  2. All interactive elements (cards, filters, buttons, toggles, checkboxes) are keyboard-navigable with visible focus indicators
  3. Screen reader can navigate results: ARIA labels on cards, filters, and export controls
  4. Results page with 100+ IOC cards renders without jank and filters respond in <100ms
  5. Full E2E test suite passes covering the complete v1.1 feature set
Plans:

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8 → 9 → 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Offline Pipeline | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Core Enrichment | v1.0 | 4/4 | Complete | 2026-02-21 |
| 3. Additional TI Providers | v1.0 | 3/3 | Complete | 2026-02-21 |
| 3.1. Integration Fixes and Git Hygiene | v1.0 | 1/1 | Complete | 2026-02-22 |
| 4. UX Polish and Security Verification | v1.0 | 2/2 | Complete | 2026-02-24 |
| 6. Foundation — Tailwind + Alpine + Card Layout | v1.1 | 0/? | Pending | — |
| 7. Filtering & Search | 2/2 | Complete   | 2026-02-25 | — |
| 8. Input Page Polish | 1/2 | In Progress|  | — |
| 9. Export & Copy Enhancements | v1.1 | 0/? | Pending | — |
| 10. Settings & Polish | v1.1 | 0/? | Pending | — |
