# M002: Results Page Rework

**Gathered:** 2026-03-18
**Status:** Ready for planning

## Project Description

SentinelX is a local threat intelligence hub for SOC analysts. The results page is the core surface — where analysts triage extracted IOCs against 14 enrichment providers. The current results page works but reads as a junior-level project: flat information hierarchy, competing visual elements, cramped 2-column grid.

## Why This Milestone

The results page is where analysts spend 90% of their time. A poor presentation layer undermines the quality of the underlying enrichment data. The rework makes the same data dramatically more usable through information hierarchy, progressive disclosure, and quiet precision design.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Paste IOCs, hit Extract, and immediately scan a single-column results list where verdict severity jumps out and key context (geo, ASN, provider numbers) is visible without clicking anything
- Expand any IOC inline to see the full provider breakdown without leaving the results page
- Filter by verdict, type, or text search via a compact single-row filter bar
- See verdict counts at a glance via a compressed inline dashboard that doesn't push results below the fold

### Entry point / environment

- Entry point: http://127.0.0.1:5000 → paste IOCs → Extract → /analyze results page
- Environment: local dev / browser
- Live dependencies involved: enrichment providers (online mode), none (offline mode)

## Completion Class

- Contract complete means: templates render correctly, TypeScript compiles, CSS builds, all data-* attributes preserved for filtering/export
- Integration complete means: enrichment polling → DOM rendering → filtering → export pipeline works end-to-end
- Operational complete means: none (local tool)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Online enrichment results stream into the new layout correctly with progressive rendering
- Filtering by verdict, type, and text search works on the new DOM structure
- Export (JSON/CSV/clipboard) produces correct output from the new layout
- All security contracts verified (CSP no violations, textContent-only DOM, CSRF present)

## Risks and Unknowns

- **At-a-glance density** — showing verdict + context + provider numbers without expanding is the core design challenge. Too dense and it defeats the purpose; too sparse and we lose information. This risk is retired in S02 by building the actual enrichment surface and verifying it with real data.
- **E2E selector breakage** — new DOM structure will break every E2E test that touches results page selectors. Mitigated by updating the ResultsPage page object first, then fixing individual tests. Risk is low because the page object pattern isolates selector changes.
- **Filter/export wiring** — filtering and export rely on specific data-* attributes and DOM structure. Changing the structure could break this wiring silently. Mitigated by explicit integration verification in S04.

## Existing Codebase / Prior Art

- `app/templates/results.html` — results page template (Jinja2), orchestrates all partials
- `app/templates/partials/_ioc_card.html` — current IOC card structure with data-* attribute contract
- `app/templates/partials/_enrichment_slot.html` — enrichment container with three-section structure
- `app/templates/partials/_verdict_dashboard.html` — 5 KPI boxes for verdict counts
- `app/templates/partials/_filter_bar.html` — verdict buttons + type pills + search input
- `app/static/src/input.css` — 1835-line CSS with design tokens, all component styles
- `app/static/src/ts/modules/enrichment.ts` — polling orchestrator (491 lines)
- `app/static/src/ts/modules/row-factory.ts` — DOM row construction (564 lines)
- `app/static/src/ts/modules/cards.ts` — verdict updates, dashboard counts, severity sorting
- `app/static/src/ts/modules/filter.ts` — verdict/type/search filtering
- `tests/e2e/pages/results_page.py` — Playwright page object with all results page selectors

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R001 — Single-column layout is the structural foundation
- R002 — At-a-glance surface is the primary user value
- R003 — Verdict-only color is the design language
- R004 — Inline expand is the progressive disclosure mechanism
- R005 — Compressed dashboard reduces chrome weight
- R006 — Simplified filter bar reduces chrome weight
- R007 — Progressive disclosure is the information architecture principle
- R008 — All functionality preserved
- R009 — Security contracts preserved
- R010 — Performance maintained
- R011 — E2E tests updated and passing

## Scope

### In Scope

- Results page template restructure (results.html + all partials)
- CSS rework (design tokens, component styles, layout)
- TypeScript DOM construction updates (row-factory.ts, enrichment.ts, cards.ts, filter.ts)
- Verdict dashboard redesign (compressed inline)
- Filter bar redesign (single row)
- IOC row design (single-column, full-width)
- Inline expand for provider details
- E2E test updates (page object + test files)

### Out of Scope / Non-Goals

- Backend changes — routes, enrichment logic, provider adapters all untouched
- Detail page (ioc_detail.html) redesign — deferred (R012)
- Input page (index.html) redesign — deferred (R013)
- New features or providers — this is presentation only
- Mobile/responsive design — desktop browser on analyst workstation

## Technical Constraints

- All DOM construction must use createElement + textContent (SEC-08, no innerHTML)
- CSP headers must remain in effect — no inline styles via JS (use CSS classes)
- data-ioc-value, data-ioc-type, data-verdict attributes must remain on IOC row root elements (4 consumers: CSS, enrichment.ts, filter.ts, E2E tests)
- TypeScript strict mode — no `any` types
- Tailwind CSS standalone CLI — no Node.js/npm
- esbuild standalone binary — IIFE output format

## Integration Points

- `enrichment.ts` → `row-factory.ts` — enrichment results rendered via row-factory DOM builders
- `filter.ts` → DOM data-* attributes — filtering reads data-verdict, data-ioc-type, data-ioc-value
- `cards.ts` → DOM data-* attributes — verdict updates write data-verdict, update verdict labels
- `export.ts` → accumulated results array — export reads from allResults[], not from DOM
- `_ioc_card.html` contract — Copy button data-value, Detail link href, all consumed by clipboard.ts and E2E tests

## Open Questions

- Exact layout of compressed dashboard — inline pills vs. mini counters vs. bar segments. Will resolve during S01/S02 implementation.
- How to present provider numbers at a glance without it becoming a data table. Will iterate during S02.
