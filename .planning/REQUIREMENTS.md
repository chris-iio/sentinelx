# Requirements: v1.3 Visual Experience Overhaul

**Defined:** 2026-02-28
**Core Value:** Transform every page from functional-but-bare into a polished, animated, premium dark UI that feels alive and intentional.
**Scope:** Frontend-only. Zero backend changes. Builds on v1.2 design token & component foundation.
**Foundation:** v1.2 design tokens, self-hosted fonts, shared components, Jinja2 partials — all in place.

## v1.3 Requirements

### Results Page

- [ ] **RES-01**: Hovering an IOC card produces a visible lift effect (translateY + enhanced shadow) within 150ms transition
- [ ] **RES-02**: IOC cards animate in on page load with staggered cascade delay (each card offset by ~50ms)
- [ ] **RES-03**: During enrichment loading, each pending card shows animated shimmer rectangles instead of a spinner — smooth animation without scroll jank
- [ ] **RES-04**: Verdict stat dashboard displays KPI cards with large monospace numbers and colored top borders, replacing inline pill badges
- [ ] **RES-05**: When no IOCs are found, a centered icon with "No IOCs detected" headline and supported-types body text replaces the empty list
- [ ] **RES-06**: Each IOC type badge shows a small colored dot before the type label, distinguishable without reading text
- [ ] **RES-07**: Text search input has a magnifying glass icon prefix inside the field

### Input Page

- [ ] **INP-01**: Textarea shows a subtle emerald border glow on focus (box-shadow with accent color at low opacity)
- [ ] **INP-02**: Pasting text triggers a character count notification that slides in and fades out via CSS animation (not abrupt show/hide)
- [ ] **INP-03**: Submit button is emerald (primary) when Online mode active and zinc (secondary) when Offline, updating instantly on toggle
- [ ] **INP-04**: Input card has visible depth separation from page background (subtle border + shadow treatment)

### Settings Page

- [ ] **SET-01**: Each settings section displays in a bordered card with section name as a left-aligned header
- [ ] **SET-02**: API key input renders in JetBrains Mono with a show/hide toggle button
- [ ] **SET-03**: API key field shows a "Configured" or "Not configured" status badge reflecting actual key presence

### Global Motion & Polish

- [ ] **MOT-01**: Main page content fades and slides in on load with orchestrated stagger timing (header → content → footer)
- [ ] **MOT-02**: All interactive elements (buttons, pills, inputs, cards, links) have smooth CSS transitions (≥150ms) on hover/focus/active states
- [ ] **MOT-03**: Filter bar gains enhanced shadow/border treatment when page is scrolled past threshold (scroll-aware)
- [ ] **MOT-04**: Focused cards and inputs show subtle border glow effects (box-shadow with accent color)

## Future Requirements

### Export & Clipboard

- **EXP-01**: User can copy all IOC results to clipboard in structured format
- **EXP-02**: User can export results as CSV file download
- **EXP-03**: User can export results as JSON file download

### Accessibility

- **A11Y-01**: All interactive elements fully keyboard navigable with visible focus indicators
- **A11Y-02**: Screen reader announcements for dynamic content updates (enrichment status, filter changes)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend changes | v1.3 is frontend-only — same routes, same data models |
| New threat intelligence providers | Backend feature, not visual |
| Light mode / theme switching | Dark-first design, not a theming milestone |
| Mobile responsive redesign | Desktop-focused analyst workstation tool |
| Complex JS animation libraries | CSS-only animations, no new dependencies |
| WebSocket for enrichment | Current polling approach works, not a visual concern |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RES-01 | Phase 15 | Pending |
| RES-02 | Phase 15 | Pending |
| RES-03 | Phase 15 | Pending |
| RES-04 | Phase 15 | Pending |
| RES-05 | Phase 15 | Pending |
| RES-06 | Phase 15 | Pending |
| RES-07 | Phase 15 | Pending |
| MOT-03 | Phase 15 | Pending |
| INP-01 | Phase 16 | Pending |
| INP-02 | Phase 16 | Pending |
| INP-03 | Phase 16 | Pending |
| INP-04 | Phase 16 | Pending |
| MOT-01 | Phase 16 | Pending |
| MOT-02 | Phase 16 | Pending |
| MOT-04 | Phase 16 | Pending |
| SET-01 | Phase 17 | Pending |
| SET-02 | Phase 17 | Pending |
| SET-03 | Phase 17 | Pending |

**Coverage:**
- v1.3 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 — traceability table populated after roadmap creation*
