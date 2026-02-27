# Requirements: v1.2 Modern UI Redesign

**Defined:** 2026-02-25
**Core Value:** Elevate SentinelX from functional dark prototype to premium Linear/GreyNoise-quality security tool — dark-first zinc/emerald/teal design system, Inter + JetBrains Mono typography, WCAG AA verified.
**Scope:** Frontend-only. Zero backend changes. Same routes, same data models.

## Stack

- **Tailwind CSS** standalone CLI v3.4.x — existing build pipeline, `darkMode: 'selector'` added
- **Inter Variable** (~70KB woff2, self-hosted) — UI typeface for all chrome
- **JetBrains Mono Variable** (~60KB woff2, self-hosted) — monospace for IOC values
- **Heroicons v2** (inline SVG, zero install) — UI icons via Jinja2 macros
- **`@tailwindcss/forms`** (bundled in standalone CLI) — form element reset
- **Vanilla JS** retained — enrichment polling and clipboard unchanged

## v1.2 Requirements

### Foundation — Design Tokens & Base CSS

- [x] **FOUND-01**: Design token system defined as CSS custom properties at `:root` — zinc-based surface hierarchy (950/900/800/700), emerald/teal accent system, four-state verdict color triples (text/bg/border per verdict)
- [x] **FOUND-02**: Inter Variable font self-hosted in `app/static/fonts/` with `@font-face` declaration and `crossorigin` preload link in `base.html`
- [x] **FOUND-03**: JetBrains Mono Variable font self-hosted in `app/static/fonts/` with `@font-face` declaration, applied to all IOC value displays
- [x] **FOUND-04**: `<meta name="color-scheme" content="dark">` added to `base.html` and `:root { color-scheme: dark; }` in CSS, fixing native form controls and scrollbar rendering
- [ ] **FOUND-05**: All text/background token pairs pass WCAG AA contrast — 4.5:1 for normal text, 3:1 for UI components — verified before any component work begins
- [x] **FOUND-06**: Browser autofill override CSS prevents yellow flash on dark input fields (settings page API key field)
- [x] **FOUND-07**: `tailwind.config.js` updated with `darkMode: 'selector'`, extended theme colors mapping to CSS tokens, and `@tailwindcss/forms` plugin activated
- [x] **FOUND-08**: Typography scale defined — 3-tier weight system (headings, body, captions) with -0.02em tracking on headings, consistent line-height ratios

### Shared Components

- [x] **COMP-01**: Verdict badges unified — all five states (malicious, suspicious, clean, no record, pending) use tinted-background + colored-border + colored-text pattern (eliminate solid amber outlier)
- [x] **COMP-02**: Focus rings standardized on all interactive elements — `outline: 2px solid var(--accent); outline-offset: 2px` on `:focus-visible`, replacing all low-opacity box-shadow focus indicators
- [x] **COMP-03**: Button component styles — primary (emerald), secondary (zinc), and ghost variants with hover/active/disabled states and 150ms transitions
- [ ] **COMP-04**: Form element styling via `@tailwindcss/forms` — textarea, text inputs, and select elements reset with dark-theme-appropriate borders and focus states
- [ ] **COMP-05**: Sticky filter bar uses `backdrop-filter: blur(12px)` with semi-transparent zinc-950 background
- [ ] **COMP-06**: Heroicons icon macro created (`templates/macros/icons.html`) for reusable inline SVG icons across all pages
- [ ] **COMP-07**: Header/footer redesigned with updated typography, spacing, and emerald accent treatment

### Results Page

- [ ] **RESULTS-01**: Jinja2 template partials extracted — `_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `_enrichment_slot.html` — with E2E tests passing after extraction before any visual changes
- [ ] **RESULTS-02**: IOC card hover elevation — `translateY(-1px)` + subtle shadow + border-color shift on hover with 150ms ease transition
- [ ] **RESULTS-03**: IOC type badge dot indicator — `::before` 6px colored circle on each type badge for quick visual scanning
- [ ] **RESULTS-04**: Search input has inline SVG magnifying glass icon prefix
- [ ] **RESULTS-05**: Empty state displays shield/search icon with "No IOCs detected" headline and body text listing supported IOC types
- [ ] **RESULTS-06**: Verdict stat dashboard upgraded to KPI-style cards — large monospace number, colored top border, small-caps label
- [ ] **RESULTS-07**: Shimmer skeleton loader replaces spinner during enrichment-pending state — 2-3 animated skeleton rectangles per card placeholder
- [ ] **RESULTS-08**: 3px left-border accent on IOC cards in verdict color for instant visual scanning of severity

### Input & Settings Pages

- [ ] **PAGE-01**: Input page textarea refined — dark zinc-800 background, teal focus ring, Inter Variable typography, improved sizing
- [ ] **PAGE-02**: Submit button uses emerald variant for Online mode, secondary variant for Offline mode — updates reactively on toggle
- [ ] **PAGE-03**: Mode toggle visual upgrade — improved styling consistent with new design system
- [ ] **PAGE-04**: Paste feedback animation — `@keyframes` appear/fade effect on character count notification
- [ ] **PAGE-05**: Settings page uses Vercel-style section cards — bordered card per section with header row (section name left, action button right)
- [ ] **PAGE-06**: Settings API key input styled as monospace field with show/hide toggle and configured/unconfigured status badge

## Deferred to v1.3+

| Feature | Reason |
|---------|--------|
| Custom scrollbar styling | Low cross-browser ROI, `color-scheme: dark` handles the worst case |
| Search result text highlighting | High complexity (DOM text manipulation), low priority |
| Copy-button contextual tooltip | Complexity vs value unclear |
| Dark/light mode toggle | Doubles CSS maintenance, not a real SOC use case |
| Export dropdown (clipboard/JSON/CSV) | Deferred from v1.1, revisit after redesign settles |
| Bulk selection with checkboxes | Deferred from v1.1, revisit after redesign settles |
| Test Connection button | Deferred from v1.1, may fold into settings redesign |
| Accessibility audit (full) | Partial coverage in FOUND-05 + COMP-02; full audit deferred |
| Performance verification (100+ IOCs) | Address if issues arise during implementation |

## Out of Scope (v1.2)

| Feature | Reason |
|---------|--------|
| Sidebar navigation | Consumes 220px needed for IOC hash display |
| Glassmorphism on content cards | GPU jank at 50+ cards during scroll |
| Inline charts/sparklines | Single-shot tool, no history to chart |
| New threat intelligence providers | Frontend-only milestone |
| Backend route changes | Same Flask routes, same data models |
| Real-time WebSocket updates | Polling works, WebSocket adds backend complexity |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 11 | Complete |
| FOUND-02 | Phase 11 | Complete |
| FOUND-03 | Phase 11 | Complete |
| FOUND-04 | Phase 11 | Complete |
| FOUND-05 | Phase 11 | Pending |
| FOUND-06 | Phase 11 | Complete |
| FOUND-07 | Phase 11 | Complete |
| FOUND-08 | Phase 11 | Complete |
| COMP-01 | Phase 12 | Complete |
| COMP-02 | Phase 12 | Complete |
| COMP-03 | Phase 12 | Complete |
| COMP-04 | Phase 12 | Pending |
| COMP-05 | Phase 12 | Pending |
| COMP-06 | Phase 12 | Pending |
| COMP-07 | Phase 12 | Pending |
| RESULTS-01 | Phase 13 | Pending |
| RESULTS-02 | Phase 13 | Pending |
| RESULTS-03 | Phase 13 | Pending |
| RESULTS-04 | Phase 13 | Pending |
| RESULTS-05 | Phase 13 | Pending |
| RESULTS-06 | Phase 13 | Pending |
| RESULTS-07 | Phase 13 | Pending |
| RESULTS-08 | Phase 13 | Pending |
| PAGE-01 | Phase 14 | Pending |
| PAGE-02 | Phase 14 | Pending |
| PAGE-03 | Phase 14 | Pending |
| PAGE-04 | Phase 14 | Pending |
| PAGE-05 | Phase 14 | Pending |
| PAGE-06 | Phase 14 | Pending |

**Coverage:**
- v1.2 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0

---
*Requirements defined: 2026-02-25*
*Last updated: 2026-02-25 after initial definition*
