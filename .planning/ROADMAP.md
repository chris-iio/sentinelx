# Roadmap: oneshot-ioc

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-24)
- ✅ **v1.1 UX Overhaul** — Phases 6-8 (shipped 2026-02-25, reduced scope)
- ✅ **v1.2 Modern UI Redesign** — Phases 11-12 (shipped; 13-14 superseded by v1.3)
- 📋 **v1.3 Visual Experience Overhaul** — Phases 15-17 (in progress)

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

<details>
<summary>✅ v1.2 Modern UI Redesign (Phases 11-12) — SHIPPED 2026-02-28</summary>

- [x] Phase 11: Foundation — Design Tokens & Base CSS (3/3 plans) — completed 2026-02-28
- [x] Phase 12: Shared Component Elevation (3/3 plans) — completed 2026-02-27

Phases 13-14 superseded by v1.3 Visual Experience Overhaul (broader scope). Phase 13 plan 01 (Jinja2 partial extraction) was completed and partials are in place.

</details>

### v1.3 Visual Experience Overhaul (Phases 15-17)

- [ ] **Phase 15: Results Page Visual Overhaul** - Card hover lift, staggered cascade animation, shimmer skeleton loader, KPI dashboard with monospace numbers, empty state, type badge dot indicators, search icon prefix, scroll-aware filter bar
- [ ] **Phase 16: Input Page and Global Motion** - Textarea focus glow, animated paste feedback, mode-aware submit button, input card depth, global CSS transitions, page load stagger, border glow on focus
- [ ] **Phase 17: Settings Page Polish** - Section cards with bordered layout, JetBrains Mono API key field with show/hide toggle, Configured/Not configured status badge

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
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md — Core CSS component elevation: verdict badge borders, global focus-visible ring, ghost button variant
- [x] 12-02-PLAN.md — Form element dark-theme styling and frosted-glass filter bar backdrop
- [x] 12-03-PLAN.md — Heroicons Jinja2 macro, header/footer redesign, visual verification checkpoint

### Phase 15: Results Page Visual Overhaul
**Goal**: The results page is a fully animated, visually rich experience — cards lift on hover, cascade in on load, shimmer during enrichment, show a KPI dashboard, handle empty state, and present type badges with dot indicators and a search field with icon prefix; the filter bar is scroll-aware
**Depends on**: Phase 12 (shared components), Jinja2 partials in place (from v1.2 Phase 13-01)
**Requirements**: RES-01, RES-02, RES-03, RES-04, RES-05, RES-06, RES-07, MOT-03
**Success Criteria** (what must be TRUE):
  1. Hovering any IOC card produces a visible upward lift (translateY + enhanced shadow) that begins within 150ms — observable without DevTools
  2. On page load, IOC cards animate in with a staggered cascade — each card visibly delayed from the previous by roughly 50ms, so the sequence is perceptible
  3. Each IOC type badge displays a small colored dot before the type label that distinguishes types without requiring the text to be read
  4. When no IOCs are found, the results area shows a centered icon with a "No IOCs detected" headline and a body line listing supported types — not an empty list or blank space
  5. During enrichment loading, pending IOC cards show animated shimmer rectangles (not a spinner) that animate smoothly without scroll jank
  6. The verdict stat area displays four KPI cards with large monospace numbers and colored top borders — inline pills are absent from this area
  7. The text search input has a magnifying glass icon visually inside the left edge of the field
  8. Scrolling the results page past the filter bar threshold gives the filter bar a visibly enhanced shadow/border treatment compared to its unscrolled state
**Plans**: TBD

Plans:

### Phase 16: Input Page and Global Motion
**Goal**: The input page is polished with focus glow, animated paste feedback, and mode-aware submit button; every interactive element site-wide has smooth CSS transitions; and the page load experience has an orchestrated stagger animation
**Depends on**: Phase 15
**Requirements**: INP-01, INP-02, INP-03, INP-04, MOT-01, MOT-02, MOT-04
**Success Criteria** (what must be TRUE):
  1. Focusing the textarea produces a visible emerald glow (box-shadow with accent color at low opacity) that is absent when the field is unfocused
  2. Pasting text into the textarea triggers a character count notification that slides in and fades out via CSS animation — the transition is visible and not an abrupt show/hide
  3. The submit button is emerald when Online mode is active and zinc/secondary when Offline mode is active, and it updates instantly (no page reload) when the toggle is switched
  4. The input card has a visible border and shadow treatment that creates depth separation from the zinc-950 page background
  5. On page load, the header, main content block, and footer animate in with a perceptible stagger sequence — each section begins its reveal after the previous one starts
  6. All interactive elements (buttons, pills, inputs, cards, links) across every page have smooth hover/focus/active transitions of at least 150ms — no element snaps abruptly between states
  7. Focused cards and inputs show a subtle border glow (box-shadow with accent color) in addition to the existing focus ring — observable as a soft colored halo around the focused element
**Plans**: TBD

Plans:

### Phase 17: Settings Page Polish
**Goal**: The settings page is elevated to match the v1.3 design quality — each section lives in a bordered card, the API key field uses monospace rendering with a show/hide toggle, and a status badge reflects actual key configuration
**Depends on**: Phase 16
**Requirements**: SET-01, SET-02, SET-03
**Success Criteria** (what must be TRUE):
  1. Each settings section (e.g. VirusTotal, MalwareBazaar) displays in a bordered card with the section name as a left-aligned header — not an unstyled group of fields
  2. The API key input renders in JetBrains Mono font — verifiable by inspecting font-family in DevTools — and has a show/hide toggle button that switches the field between password and text type
  3. A status badge next to or within the API key field shows "Configured" (with a success color) when the key is present in the environment, and "Not configured" (with a muted or warning color) when it is absent
**Plans**: TBD

Plans:

## Progress

**Execution Order:**
v1.3 phases execute in numeric order: 15 → 16 → 17

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
| 12. Shared Component Elevation | v1.2 | 3/3 | Complete | 2026-02-27 |
| 15. Results Page Visual Overhaul | v1.3 | 0/? | Not started | — |
| 16. Input Page and Global Motion | v1.3 | 0/? | Not started | — |
| 17. Settings Page Polish | v1.3 | 0/? | Not started | — |
