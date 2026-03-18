# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R001 — IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Class: core-capability
- Status: active
- Description: IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Why it matters: Eliminates cramped hashes, gives context and provider numbers room to breathe, establishes natural top-to-bottom scan flow for triage.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: unmapped
- Notes: Long hashes (SHA256) and URLs must render without wrapping awkwardly

### R002 — Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Class: primary-user-loop
- Status: active
- Description: Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Why it matters: The analyst's primary workflow is scanning results for actionable IOCs. Every click required to see key data slows triage.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: unmapped
- Notes: This is the hardest design challenge — dense data that reads cleanly

### R003 — Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Class: quality-attribute
- Status: active
- Description: Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Why it matters: Eliminates the "wall of badges" junior-project aesthetic. Analyst's eye lands on what matters without parsing competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: S03 confirmed: expanded panel polish uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover, --radius-sm). Detail link uses --text-secondary/--text-primary on hover. No new bright non-verdict colors introduced. T02 explicitly verified R003 compliance.
- Notes: IOC type still needs to be identifiable — just via muted text, not bright colored badges

### R004 — Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Class: core-capability
- Status: active
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context — no page load, no back-button navigation, results list stays visible.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: S03 delivered: .ioc-summary-row is the click target; event delegation wires expand/collapse for all dynamically-created rows; .enrichment-details toggles .is-open; aria-expanded tracks state; keyboard Enter/Space supported; "View full detail →" link with encodeURIComponent href injected via injectDetailLink(). 36 E2E tests pass with no regression.
- Notes: Detail page still exists for deep dives (relationship graph, annotations) — linked from expanded view

### R005 — Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Class: core-capability
- Status: active
- Description: Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Why it matters: Current KPI boxes push IOC results below the fold. Compact dashboard gives the same information while keeping IOCs visible.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: unmapped
- Notes: Must still be clickable to filter by verdict

### R006 — Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Class: core-capability
- Status: active
- Description: Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Why it matters: Current filter bar is visually heavy and pushes IOC content down. Lightweight tool should have lightweight chrome.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: unmapped
- Notes: All filter functionality preserved — verdict toggle, type toggle, text search

### R007 — Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Class: quality-attribute
- Status: active
- Description: Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Why it matters: Core design philosophy of the rework. Information hierarchy through showing vs. hiding rather than through competing visual weight.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S02
- Validation: S03 delivered: expand/collapse gate means provider details (the less-important data) are hidden by default and revealed on deliberate click or keyboard action. Summary row always shows verdict + context + key stats (established in S02). Full provider breakdown only on demand. No-data providers hidden in collapsed section (established in M001). "View full detail" link visible only after expand.
- Notes: Applies to: provider detail rows, no-data providers, context fields, cache staleness

### R008 — Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Class: continuity
- Status: active
- Description: Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Why it matters: This is a presentation rework, not a feature change. Nothing should regress.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: S04 validated: 18-point wiring verification matrix confirms every sub-feature intact (file:line evidence in T01-SUMMARY.md). 91/91 E2E tests pass exercising the full pipeline. allResults[] accumulation → export.ts confirmed via closure; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard.
- Notes: Export and copy depend on data-* attributes on DOM elements — must preserve or migrate

### R009 — CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: active
- Description: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress during a UI redesign.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 validated: six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only (graph.ts:10, row-factory.ts:230). document.write/eval() return zero matches (grep exit 1). All .style.xxx assignments are DOM property access (width, display) not <style> injection. row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout.
- Notes: Every DOM construction in new TypeScript code must use createElement + textContent

### R010 — Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Class: quality-attribute
- Status: active
- Description: Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight. Performance regressions during redesign are common and unacceptable.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 validated: production bundle 27,226 bytes (≤ 30KB gate; baseline was ~13KB IIFE pre-rework; new figure reflects ESM+inline sourcemap dev vs minified prod — minified prod is 26.6KB). Polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts. CSS polish pass confirmed no performance-affecting style injections. Build gate reproducible: `wc -c app/static/dist/main.js`.
- Notes: Monitor build size — current main.js is ~13KB IIFE

### R011 — All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Class: quality-attribute
- Status: active
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Why it matters: Test suite is the safety net that proves the redesign doesn't break functionality.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: unmapped
- Notes: ResultsPage page object needs selector updates; test logic should mostly survive

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
| R001 | core-capability | active | M002/S01 | none | unmapped |
| R002 | primary-user-loop | active | M002/S02 | M002/S01 | unmapped |
| R003 | quality-attribute | active | M002/S01 | M002/S02, M002/S03 | S03 confirmed: expanded panel polish uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover, --radius-sm). Detail link uses --text-secondary/--text-primary on hover. No new bright non-verdict colors introduced. T02 explicitly verified R003 compliance. |
| R004 | core-capability | active | M002/S03 | none | S03 delivered: .ioc-summary-row is the click target; event delegation wires expand/collapse for all dynamically-created rows; .enrichment-details toggles .is-open; aria-expanded tracks state; keyboard Enter/Space supported; "View full detail →" link with encodeURIComponent href injected via injectDetailLink(). 36 E2E tests pass with no regression. |
| R005 | core-capability | active | M002/S02 | M002/S01 | unmapped |
| R006 | core-capability | active | M002/S02 | M002/S01 | unmapped |
| R007 | quality-attribute | active | M002/S03 | M002/S02 | S03 delivered: expand/collapse gate means provider details (the less-important data) are hidden by default and revealed on deliberate click or keyboard action. Summary row always shows verdict + context + key stats (established in S02). Full provider breakdown only on demand. No-data providers hidden in collapsed section (established in M001). "View full detail" link visible only after expand. |
| R008 | continuity | active | M002/S04 | M002/S01, M002/S02, M002/S03 | S04 validated: 18-point wiring matrix + 91/91 E2E pass |
| R009 | compliance/security | active | M002/S04 | all | S04 validated: six grep-based audit checks; zero violations |
| R010 | quality-attribute | active | M002/S04 | all | S04 validated: production bundle 27,226 bytes ≤ 30KB; patterns unchanged |
| R011 | quality-attribute | active | M002/S05 | none | unmapped |
| R012 | quality-attribute | deferred | none | none | unmapped |
| R013 | quality-attribute | deferred | none | none | unmapped |

## Coverage Summary

- Active requirements: 11
- Mapped to slices: 11
- Validated: 3 (R008, R009, R010 — S04 evidence)
- Unmapped active requirements: 0
