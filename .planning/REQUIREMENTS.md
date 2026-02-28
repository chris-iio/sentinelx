# Requirements: v2.0 Home Page Modernization

**Defined:** 2026-02-28
**Core Value:** Clean, minimal, contemporary home page that doesn't overwhelm — compact input, stripped header, simplified footer.
**Scope:** Frontend-only. Zero backend changes. Focused on index page + base template (header/footer).
**Foundation:** v1.2/v1.3 design tokens, self-hosted fonts, shared components — all in place.

## v2.0 Requirements

### Layout

- [ ] **LAY-01**: Header displays only logo icon, "SentinelX" brand text, and a settings gear icon — no tagline text visible
- [ ] **LAY-02**: Header padding is reduced to create a thinner, less dominant top bar
- [ ] **LAY-03**: Footer is simplified with minimal text and reduced padding, matching the header's minimal tone

### Input

- [ ] **INP-01**: Textarea defaults to approximately 5 visible rows instead of 14
- [ ] **INP-02**: Textarea auto-grows vertically as content is pasted or typed (up to a max height)
- [ ] **INP-03**: Form controls row (mode toggle + buttons) uses tighter spacing for a compact, modern feel

## Future Requirements

### Export & Clipboard

- **EXP-01**: User can copy all IOC results to clipboard in structured format
- **EXP-02**: User can export results as CSV file download
- **EXP-03**: User can export results as JSON file download

### Accessibility

- **A11Y-01**: All interactive elements fully keyboard navigable with visible focus indicators
- **A11Y-02**: Screen reader announcements for dynamic content updates

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend changes | v2.0 is frontend-only — same routes, same data models |
| Results page redesign | Already polished in v1.2/v1.3 |
| Settings page redesign | Already polished in v1.3 |
| New threat intelligence providers | Backend feature, not visual |
| Light mode / theme switching | Dark-first design, not a theming milestone |
| Mobile responsive redesign | Desktop-focused analyst workstation tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LAY-01 | — | Pending |
| LAY-02 | — | Pending |
| LAY-03 | — | Pending |
| INP-01 | — | Pending |
| INP-02 | — | Pending |
| INP-03 | — | Pending |

**Coverage:**
- v2.0 requirements: 6 total
- Mapped to phases: 0
- Unmapped: 6 ⚠️

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
