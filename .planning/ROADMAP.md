# Roadmap: oneshot-ioc

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-24)
- ✅ **v1.1 UX Overhaul** — Phases 6-8 (shipped 2026-02-25, reduced scope)
- 📋 **v1.2 Modern UI Redesign** — Phases 11-14 (planned)

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

<details>
<summary>✅ v1.1 UX Overhaul (Phases 6-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 6: Foundation — Tailwind + Alpine + Card Layout — completed 2026-02-24
- [x] Phase 7: Filtering & Search — completed 2026-02-25
- [x] Phase 8: Input Page Polish — completed 2026-02-25

Phases 9-10 dropped: EXPORT and POLISH requirements superseded by v1.2 full redesign.

Full details: `milestones/v1.1-ROADMAP.md`

</details>

### v1.2 Modern UI Redesign (Phases 11-14)

- [x] **Phase 11: Foundation — Design Tokens & Base CSS** - Establish verified zinc/emerald/teal token system, self-host Inter Variable and JetBrains Mono fonts, configure dark-first CSS infrastructure with WCAG AA verified contrast
- [ ] **Phase 12: Shared Component Elevation** - Unify verdict badges, standardize focus rings, elevate buttons and form elements, create icon macro, redesign header/footer
- [ ] **Phase 13: Results Page Redesign** - Extract Jinja2 template partials, add card hover elevation, dot indicators, shimmer skeleton loader, KPI dashboard, empty state, and search icon
- [ ] **Phase 14: Input & Settings Page Redesign** - Refine textarea and submit button, upgrade mode toggle, animate paste feedback, redesign settings with section cards and monospace API key field

## Phase Details

### Phase 11: Foundation — Design Tokens & Base CSS
**Goal**: A verified dark-first design token system is in place — every color token passes WCAG AA contrast, Inter Variable and JetBrains Mono load from static fonts, and browser dark-mode signals are correct — with no structural template changes yet
**Depends on**: v1.1 complete (Phase 8)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08
**Success Criteria** (what must be TRUE):
  1. All IOC value displays render in JetBrains Mono Variable (verifiable by inspecting font-family in DevTools on any results page IOC)
  2. All UI chrome text renders in Inter Variable (verifiable by inspecting font-family on the input page label or header)
  3. Every text/background token pair in the design system passes WCAG AA: 4.5:1 for normal text, 3:1 for UI components (verified via contrast checker against documented token values)
  4. Pasting into the settings API key field then refreshing does not produce a yellow autofill flash — the field stays dark zinc
  5. Browser scrollbar and native form controls render in dark mode (no light scrollbar on dark background in any OS-level dark-aware browser)
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md — Font infrastructure (download + @font-face + preload), base.html dark-mode meta, Tailwind config (darkMode + forms plugin)
- [x] 11-02-PLAN.md — Design token rewrite (zinc/emerald/teal :root), component rule migration to verdict triples, autofill override, typography scale
- [x] 11-03-PLAN.md — WCAG AA contrast verification (automated + human visual checkpoint)

### Phase 12: Shared Component Elevation
**Goal**: All shared UI primitives — verdict badges, buttons, focus rings, form elements, header/footer, icon macro — are elevated to the target design system so every subsequent page starts from a consistent premium baseline
**Depends on**: Phase 11
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07
**Success Criteria** (what must be TRUE):
  1. All five verdict badge states (malicious, suspicious, clean, no record, pending) use the tinted-background + colored-border + colored-text pattern — the solid amber suspicious badge is gone
  2. Every interactive element (buttons, filter pills, toggle, search input, links) shows a visible 2px teal outline on keyboard focus — no element has an invisible or box-shadow-only focus indicator
  3. Primary (emerald), secondary (zinc), and ghost button variants are visually distinct with hover and disabled states that are observable without DevTools
  4. The sticky filter bar has a frosted-glass blur effect visible when scrolling past cards (content visible through the blurred bar background)
  5. Header and footer use Inter Variable at the correct weight hierarchy with emerald accent treatment on the brand name
**Plans**: TBD

Plans:

### Phase 13: Results Page Redesign
**Goal**: The results page is refactored into Jinja2 template partials and elevated to the target visual design — card hover elevation, dot type indicators, shimmer skeleton, KPI dashboard, empty state, and search icon prefix all in place
**Depends on**: Phase 12
**Requirements**: RESULTS-01, RESULTS-02, RESULTS-03, RESULTS-04, RESULTS-05, RESULTS-06, RESULTS-07, RESULTS-08
**Success Criteria** (what must be TRUE):
  1. All existing Playwright E2E tests pass after template partial extraction (before any visual changes) — `_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, and `_enrichment_slot.html` exist as separate partial files
  2. Hovering an IOC card produces a visible lift effect (card moves up slightly with shadow) within 150ms
  3. Each IOC type badge shows a small colored dot before the type label, distinguishable without reading the text
  4. When no IOCs are found in results, a centered shield/search icon with "No IOCs detected" headline and supported-types body text is displayed instead of an empty list
  5. During enrichment loading, each pending card shows animated shimmer rectangles instead of a spinner — the animation is smooth and does not jank during scroll
  6. The verdict stat dashboard displays four KPI cards with large monospace numbers and colored top borders, not inline pills
**Plans**: TBD

Plans:

### Phase 14: Input & Settings Page Redesign
**Goal**: The input page and settings page are visually consistent with the v1.2 design system — refined textarea, mode-aware submit button, upgraded toggle, animated paste feedback, and Vercel-style settings section cards with monospace API key field
**Depends on**: Phase 13
**Requirements**: PAGE-01, PAGE-02, PAGE-03, PAGE-04, PAGE-05, PAGE-06
**Success Criteria** (what must be TRUE):
  1. The submit button is emerald when Online mode is active and zinc (secondary) when Offline mode is active, updating instantly on toggle without page reload
  2. Pasting text into the textarea triggers a character count notification that appears and fades out via CSS animation (not an abrupt show/hide)
  3. The settings page displays each section in a bordered card with the section name on the left and any action button on the right of a header row
  4. The API key input field renders in JetBrains Mono with a show/hide toggle button and a "Configured" or "Not configured" status badge that reflects actual key presence
**Plans**: TBD

Plans:

## Progress

**Execution Order:**
Phases execute in numeric order: 11 → 12 → 13 → 14

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Offline Pipeline | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Core Enrichment | v1.0 | 4/4 | Complete | 2026-02-21 |
| 3. Additional TI Providers | v1.0 | 3/3 | Complete | 2026-02-21 |
| 3.1. Integration Fixes and Git Hygiene | v1.0 | 1/1 | Complete | 2026-02-22 |
| 4. UX Polish and Security Verification | v1.0 | 2/2 | Complete | 2026-02-24 |
| 6. Foundation — Tailwind + Alpine + Card Layout | v1.1 | 0/? | Complete | 2026-02-24 |
| 7. Filtering & Search | v1.1 | 2/2 | Complete | 2026-02-25 |
| 8. Input Page Polish | v1.1 | 2/2 | Complete | 2026-02-25 |
| 11. Foundation — Design Tokens & Base CSS | v1.2 | 3/3 | Complete | 2026-02-28 |
| 12. Shared Component Elevation | v1.2 | 0/? | Not started | — |
| 13. Results Page Redesign | v1.2 | 0/? | Not started | — |
| 14. Input & Settings Page Redesign | v1.2 | 0/? | Not started | — |
