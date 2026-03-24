# M001 Context

**Milestone:** v1.1 Results Page Redesign
**Migrated from:** `.planning/` (v1.1 milestone, phases 1-5)

## Upstream Dependencies

None — this is the active milestone. All prior work (v1.0 through v7.0) is shipped as v1.0 Foundation.

## Completion State at Migration

- **S01 (Contracts And Foundation):** Complete — CSS-CONTRACTS.md committed, inline annotations added, E2E baseline confirmed at 89/91
- **S02 (TypeScript Module Extractions):** Complete — enrichment.ts split into 3 modules, all tests passing
- **S03 (Visual Redesign):** Not started — research and UI spec complete, ready for planning
- **S04 (Template Restructuring):** Not started — depends on S03
- **S05 (Context And Staleness):** Not started — depends on S04

## Key Context

- Phase ordering is non-negotiable: contracts before code, extractions before visual, CSS before HTML
- 91 E2E tests with 20+ hard-coded CSS selectors are the primary risk; test gate after every phase
- E2E baseline is 89/91 — 2 pre-existing failures (page title capitalization) are out of scope
- Resume point: S03 planning — research complete at `.gsd/milestones/M001/slices/S03/S03-RESEARCH.md`

## Accumulated Decisions

- Version reset: all previous milestones collapsed into v1.0 Foundation
- formatDate exported from row-factory.ts (not private) — renderEnrichmentResult needs it for scan_date
- createProviderRow thin dispatcher in row-factory.ts — stable API surface for Phase 3 visual work
- One-directional dependency graph: enrichment.ts → verdict-compute.ts, enrichment.ts → row-factory.ts, row-factory.ts → verdict-compute.ts (no reverse)
