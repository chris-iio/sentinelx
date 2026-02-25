# Requirements: v1.1 UX Overhaul

**Defined:** 2026-02-24
**Core Value:** Make SentinelX's results page the one place a SOC analyst looks — better visual hierarchy, filtering, and export. No new providers; make existing data shine.
**Scope:** Frontend-only. Zero backend changes. Same routes, same data models.

## Stack

- **Tailwind CSS** standalone CLI — no Node.js, generates CSS from utility classes. Existing CSS custom properties become Tailwind theme extensions.
- **Alpine.js CSP build** (~15KB) — declarative reactivity for filtering, toggles, search. CSP-compatible (no eval). Served from `/static/`.
- **Vanilla JS** retained — enrichment polling and clipboard code unchanged.

## v1.1 Requirements

### Layout & Card Display

- [ ] **LAYOUT-01**: Results page displays IOCs as cards instead of table rows, with each card showing IOC value, type badge, verdict label, and provider details
- [ ] **LAYOUT-02**: Summary dashboard at the top of results shows verdict counts (malicious, suspicious, clean, no data) with colored count badges
- [ ] **LAYOUT-03**: IOC cards are sorted by verdict severity — malicious first, then suspicious, clean, and no data last
- [ ] **LAYOUT-04**: Each card has a colored left border indicating verdict severity (red=malicious, amber=suspicious, green=clean, gray=no data)
- [ ] **LAYOUT-05**: Card layout is responsive — single column on narrow viewports, multi-column on wide screens

### Filtering & Search

- [x] **FILTER-01**: Verdict filter bar with buttons: All | Malicious | Suspicious | Clean | No Data — clicking a button shows only IOCs with that verdict
- [x] **FILTER-02**: IOC type filter pills displayed only for types present in current results (e.g., if no CVEs extracted, no CVE pill shown)
- [x] **FILTER-03**: Text search input filters IOC cards in real-time by matching against the IOC value string
- [x] **FILTER-04**: Filter bar is sticky (stays visible when scrolling) and dashboard verdict badges are clickable as filter shortcuts

### Input Page

- [x] **INPUT-01**: Mode selector is a toggle switch (not a dropdown) clearly labeled "Offline" / "Online" with visual state indicator
- [x] **INPUT-02**: Paste event shows character count feedback ("N characters pasted") near the textarea
- [x] **INPUT-03**: Submit button label changes based on mode — "Extract IOCs" in offline mode, "Extract & Enrich" in online mode

### Export & Copy

- [ ] **EXPORT-01**: Export dropdown menu with three options: Copy to clipboard (text), Download JSON, Download CSV
- [ ] **EXPORT-02**: Clipboard copy produces structured text with headers and sections (IOC value, type, verdict, provider details) instead of raw dump
- [ ] **EXPORT-03**: Each IOC card has a selection checkbox for bulk operations
- [ ] **EXPORT-04**: "Select All" / "Copy Selected" buttons appear when any checkbox is checked, operating on the filtered view

### Settings & Polish

- [ ] **POLISH-01**: "Test Connection" button on settings/API key configuration that validates the VT API key with a lightweight API call
- [ ] **POLISH-02**: Accessibility audit — all interactive elements keyboard-navigable, ARIA labels on cards/filters/buttons, visible focus indicators
- [ ] **POLISH-03**: Performance verified — results page renders and filters smoothly with 100+ IOC cards (no jank, <100ms filter response)

## Out of Scope (v1.1)

| Feature | Reason |
|---------|--------|
| New threat intelligence providers | v1.1 is frontend-only; new providers require backend adapter work |
| Backend route changes | Same Flask routes, same data models — all changes in templates/static |
| Dark mode / theming | Defer to v1.2; v1.1 focuses on layout and interaction |
| Real-time WebSocket updates | Polling works; WebSocket adds backend complexity |
| Saved searches / history | Requires persistence; out of scope for v1.1 |
| PDF export | Low priority; JSON/CSV cover analyst needs |
| Provider status indicators | Moved to POLISH-01 (test connection); full provider dashboard deferred |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAYOUT-01 | Phase 6 | Pending |
| LAYOUT-02 | Phase 6 | Pending |
| LAYOUT-03 | Phase 6 | Pending |
| LAYOUT-04 | Phase 6 | Pending |
| LAYOUT-05 | Phase 6 | Pending |
| FILTER-01 | Phase 7 | Complete |
| FILTER-02 | Phase 7 | Complete |
| FILTER-03 | Phase 7 | Complete |
| FILTER-04 | Phase 7 | Complete |
| INPUT-01 | Phase 8 | Complete |
| INPUT-02 | Phase 8 | Complete |
| INPUT-03 | Phase 8 | Complete |
| EXPORT-01 | Phase 9 | Pending |
| EXPORT-02 | Phase 9 | Pending |
| EXPORT-03 | Phase 9 | Pending |
| EXPORT-04 | Phase 9 | Pending |
| POLISH-01 | Phase 10 | Pending |
| POLISH-02 | Phase 10 | Pending |
| POLISH-03 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after roadmap creation*
