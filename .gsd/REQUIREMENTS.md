# Requirements

This file is the explicit capability and coverage contract for the project.

## Validated

### R001 — IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Class: core-capability
- Status: validated
- Description: IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Why it matters: Eliminates cramped hashes, gives context and provider numbers room to breathe, establishes natural top-to-bottom scan flow for triage.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: S01 added display:flex;flex-direction:column to .ioc-card; #ioc-cards-grid uses grid-template-columns:1fr with no 2-column breakpoint. Confirmed by 99/99 E2E passing and grep confirming zero grid-cols-2 or repeat(2 in input.css.
- Notes: Long hashes (SHA256) and URLs must render without wrapping awkwardly

### R002 — Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Class: primary-user-loop
- Status: validated
- Description: Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Why it matters: The analyst's primary workflow is scanning results for actionable IOCs. Every click required to see key data slows triage.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S02 delivered enrichment slot CSS — .enrichment-slot--loaded opacity:1 override, context-line padding fix, micro-bar width tuned. row-factory.ts and enrichment.ts wired verdict badge, context line, provider stat line, micro-bar, staleness badge into .enrichment-slot. S05 added 8 enrichment surface E2E tests confirming .ioc-summary-row, .verdict-micro-bar, .enrichment-slot--loaded all present after route-mocked polling. 99/99 passing.
- Notes: This is the hardest design challenge — dense data that reads cleanly

### R003 — Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Class: quality-attribute
- Status: validated
- Description: Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Why it matters: Eliminates the "wall of badges" junior-project aesthetic. Analyst's eye lands on what matters without parsing competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: S01 collapsed all 8 IOC type badge variants to single zinc neutral rule. S03 confirmed expanded panel uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover). S04 T02 grep audit confirmed zero bright non-verdict colors in dist CSS. 99/99 E2E passing.
- Notes: IOC type still needs to be identifiable — just via muted text, not bright colored badges

### R004 — Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Class: core-capability
- Status: validated
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context — no page load, no back-button navigation, results list stays visible.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: S03 delivered .ioc-summary-row as whole-row click target; wireExpandToggles() event delegation on .page-results; .enrichment-details toggles .is-open; aria-expanded state maintained; keyboard Enter/Space supported; injectDetailLink() injects "View full detail →" with encodeURIComponent href at /detail/<type>/<value>. S05 test_expand_collapse_ioc_row and test_detail_link_injected pass. 99/99 E2E passing.
- Notes: Detail page still exists for deep dives (relationship graph, annotations) — linked from expanded view

### R005 — Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Class: core-capability
- Status: validated
- Description: Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Why it matters: Current KPI boxes push IOC results below the fold. Compact dashboard gives the same information while keeping IOCs visible.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S01 restructured _verdict_dashboard.html to flex-direction:row with border-right dividers and verdict-colored count text. S04 T01 wiring matrix confirmed filter.ts binds .verdict-kpi-card[data-verdict] for click-to-filter. 99/99 E2E passing including verdict filter tests.
- Notes: Must still be clickable to filter by verdict

### R006 — Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Class: core-capability
- Status: validated
- Description: Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Why it matters: Current filter bar is visually heavy and pushes IOC content down. Lightweight tool should have lightweight chrome.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S01 restructured _filter_bar.html to single flex row with flex-wrap. S04 T01 wiring matrix confirmed all filter functionality (verdict toggle, type toggle, text search) intact. 99/99 E2E passing.
- Notes: All filter functionality preserved — verdict toggle, type toggle, text search

### R007 — Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Class: quality-attribute
- Status: validated
- Description: Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Why it matters: Core design philosophy of the rework. Information hierarchy through showing vs. hiding rather than through competing visual weight.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S02
- Validation: S03 delivered expand/collapse gate — provider details hidden by default in .enrichment-details, revealed on deliberate click/keypress. Summary row always shows at-a-glance surface. "View full detail →" link only visible in expanded state. S05 test_enrichment_section_in_expanded_row confirms progressive disclosure behavior. 99/99 E2E passing.
- Notes: Applies to: provider detail rows, no-data providers, context fields, cache staleness

### R008 — Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Class: continuity
- Status: validated
- Description: Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Why it matters: This is a presentation rework, not a feature change. Nothing should regress.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: S04 T01 produced 18-point wiring verification matrix (file:line evidence). allResults[] accumulation → export.ts via closure confirmed; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard. 91/91 E2E at S04 close; 99/99 at S05 close.
- Notes: Export and copy depend on data-* attributes on DOM elements — must preserve or migrate

### R009 — CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress during a UI redesign.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 T02 six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only (graph.ts:10, row-factory.ts:230). document.write/eval() return zero matches (grep exit 1). All .style.xxx assignments are DOM property access (width, display) not <style> injection. row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout.
- Notes: Every DOM construction in new TypeScript code must use createElement + textContent

### R010 — Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight. Performance regressions during redesign are common and unacceptable.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 T03 production bundle 27,226 bytes (≤ 30KB gate). 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts. CSS polish pass confirmed no performance-affecting style injections. Build gate reproducible: `wc -c app/static/dist/main.js`.
- Notes: Monitor build size — current main.js is 27,226 bytes (minified prod)

### R011 — All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Class: quality-attribute
- Status: validated
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Why it matters: Test suite is the safety net that proves the redesign doesn't break functionality.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed (up from 91 baseline). ResultsPage page object expanded from 118 to 266 lines with 18+ new locators and 5 helpers covering all S01–S04 enrichment surface elements. 8 new tests added covering inline expand/collapse, enrichment summary rows, micro-bar, detail links, enrichment-slot loaded state, and offline-mode guard. No tests removed.
- Notes: Delivered in M002/S05. Route-mocking infrastructure in conftest.py enables future enrichment surface tests without external API dependency.

## Deferred

### R012 — Update the per-IOC detail page (ioc_detail.html) to match the new results page design language.
- Class: quality-attribute
- Status: deferred
- Description: Update the per-IOC detail page (ioc_detail.html) to match the new results page design language.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred — detail page works fine, results page is the priority

### R013 — Update the input/home page to match the new design language.
- Class: quality-attribute
- Status: deferred
- Description: Update the input/home page to match the new design language.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred — input page is minimal and functional

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | validated | M002/S01 | none | S01 single-column layout; zero grid-cols-2 in input.css; 99/99 E2E |
| R002 | primary-user-loop | validated | M002/S02 | M002/S01 | S02 enrichment slot CSS + S05 E2E confirming .ioc-summary-row and .verdict-micro-bar; 99/99 |
| R003 | quality-attribute | validated | M002/S01 | M002/S02, M002/S03 | S01 type badge muting + S03 design-token-only expanded panel + S04 grep audit; 99/99 |
| R004 | core-capability | validated | M002/S03 | none | S03 inline expand implementation + S05 expand/collapse and detail link E2E tests; 99/99 |
| R005 | core-capability | validated | M002/S02 | M002/S01 | S01 compact dashboard + S04 click-to-filter wiring confirmed; 99/99 |
| R006 | core-capability | validated | M002/S02 | M002/S01 | S01 single-row filter bar + S04 full filter wiring confirmed; 99/99 |
| R007 | quality-attribute | validated | M002/S03 | M002/S02 | S03 expand/collapse gate + S05 progressive disclosure E2E tests; 99/99 |
| R008 | continuity | validated | M002/S04 | M002/S01, M002/S02, M002/S03 | S04 18-point wiring matrix + 99/99 E2E |
| R009 | compliance/security | validated | M002/S04 | all | S04 six grep-based security checks; zero violations across all contracts |
| R010 | quality-attribute | validated | M002/S04 | all | S04 production bundle 27,226 bytes ≤ 30KB; polling/sort patterns unchanged |
| R011 | quality-attribute | validated | M002/S05 | none | 99 passed (from 91 baseline); page object 118 → 266 lines; 8 new enrichment surface tests |
| R012 | quality-attribute | deferred | none | none | unmapped |
| R013 | quality-attribute | deferred | none | none | unmapped |

## Coverage Summary

- Active requirements: 0
- Validated: 11 (R001–R011)
- Deferred: 2 (R012, R013)
- Unmapped active requirements: 0
