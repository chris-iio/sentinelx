# M002: Results Page Rework

**Vision:** Information-first redesign of the SentinelX results page — single-column layout, quiet precision design where verdict is the only loud color, progressive disclosure that shows tangible data at a glance and reveals details on demand. Make it feel like a production tool, not a junior project.

## Success Criteria

- Analyst sees verdict severity, real-world context, and key provider numbers for each IOC without any interaction
- Information hierarchy is immediately legible — eye lands on what matters without scanning competing badges
- Full provider details accessible via inline expand — no page navigation for the 80% triage case
- All existing functionality works: enrichment, filtering, export, detail page links, copy
- Visual design reads as professional production tooling, not portfolio project

## Key Risks / Unknowns

- **At-a-glance density** — showing verdict + context + provider numbers cleanly is the core design challenge
- **DOM structure migration** — new layout breaks all E2E selectors and may break filter/export wiring

## Proof Strategy

- At-a-glance density → retire in S02 by building the actual enrichment surface with real provider data and verifying readability
- DOM structure migration → retire in S04 by running full integration verification (filter, export, security), then S05 for E2E suite

## Verification Classes

- Contract verification: TypeScript compilation, CSS build, data-* attribute presence, lint clean
- Integration verification: enrichment polling → rendering → filtering → export pipeline
- Operational verification: none (local tool)
- UAT / human verification: visual design quality, information readability under real triage load

## Milestone Definition of Done

This milestone is complete only when all are true:

- All IOC types render correctly in single-column layout with verdict-only color
- At-a-glance surface shows verdict + context + provider numbers for enriched IOCs
- Inline expand works for full provider breakdown
- Dashboard and filter bar are compressed and functional
- Enrichment polling renders progressively into new layout
- Export produces correct JSON/CSV/clipboard output
- Security contracts verified (CSP, CSRF, SEC-08)
- E2E test suite passes with updated selectors

## Requirement Coverage

- Covers: R001, R002, R003, R004, R005, R006, R007, R008, R009, R010, R011
- Partially covers: none
- Leaves for later: R012 (detail page refresh), R013 (input page refresh)
- Orphan risks: none

## Slices

- [ ] **S01: Layout skeleton + quiet precision design system** `risk:high` `depends:[]`
  > After this: Offline results render in single-column full-width rows with verdict-only color, compressed dashboard placeholder, and simplified filter bar. Visually a complete departure from the current grid layout.

- [ ] **S02: At-a-glance enrichment surface** `risk:high` `depends:[S01]`
  > After this: Online enrichment streams into the new layout — each row shows verdict badge, real-world context (geo/ASN/DNS), key provider stat line, micro-bar, and staleness badge. No expand needed to see the important data.

- [ ] **S03: Inline expand + progressive disclosure** `risk:medium` `depends:[S02]`
  > After this: Clicking an IOC row expands full provider details inline — reputation section, infrastructure context, no-data collapse. Detail page link available from expanded view.

- [ ] **S04: Functionality integration + polish** `risk:medium` `depends:[S03]`
  > After this: Export (JSON/CSV/clipboard), dashboard-click-to-filter, verdict sorting, progress bar, warning banners all work. Security contracts verified. Visual polish pass complete.

- [ ] **S05: E2E test suite update** `risk:low` `depends:[S04]`
  > After this: Full E2E test suite passes against the new DOM structure. ResultsPage page object updated. No coverage reduction.

## Boundary Map

### S01 → S02

Produces:
- `results.html` — single-column layout with IOC row structure, data-* attribute contract preserved
- `_ioc_row.html` (replaces `_ioc_card.html`) — new row partial with verdict, type, value, actions, enrichment slot
- `_verdict_summary.html` (replaces `_verdict_dashboard.html`) — compressed inline dashboard
- `_filter_bar.html` — single-row filter bar with same data-filter-* attributes
- `input.css` — reworked design tokens (verdict-only color), new row/layout styles, compressed dashboard styles
- `cards.ts` — updated to work with new row structure (findCardForIoc → findRowForIoc, or same selector if class preserved)

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `row-factory.ts` — updated DOM builders for at-a-glance surface: verdict badge, context line, provider stat line, micro-bar, staleness badge
- `enrichment.ts` — updated to render into new row structure, summary row in new position
- Updated CSS for enrichment summary presentation within rows

Consumes from S01:
- New row DOM structure (IOC row container, enrichment slot position)
- Design tokens (verdict colors, muted text hierarchy)

### S03 → S04

Produces:
- Inline expand mechanism — click-to-expand on IOC rows, animated detail panel
- Provider detail rows rendered inside expanded section (reputation, context, no-data groups)
- Detail page link inside expanded view
- Updated `enrichment.ts` expand/collapse wiring

Consumes from S02:
- Enrichment summary row (at-a-glance surface)
- Row-factory DOM builders for provider detail rows

### S04 → S05

Produces:
- Fully working results page: export, filter, sort, progress, warnings, all integrated
- Security verification: CSP clean, CSRF present, textContent-only DOM confirmed
- Visual polish: consistent spacing, transitions, hover states

Consumes from S03:
- Complete DOM structure (rows + inline expand + provider details)
- All data-* attributes in final positions

### S04 → (downstream)

Produces:
- Stable, tested DOM contract for E2E test migration
- Known selector list for ResultsPage page object update

### S05 → (done)

Produces:
- Updated `tests/e2e/pages/results_page.py` — new selectors
- All E2E tests passing
- No coverage reduction

Consumes from S04:
- Final DOM structure and selector contract
