# M001: v1.1 Results Page Redesign

**Vision:** Make 14 providers feel like one cohesive intelligence report instead of 14 separate search results stapled together.

## Success Criteria

- Uniform information architecture across all provider types (verdict, context, no-data)
- Cohesive visual presentation that matches the value of the data
- Results page that embodies the "meta-search engine" identity
- All 91 E2E tests pass after every phase

## Slices

- [x] **S01: Contracts And Foundation** `risk:low` `depends:[]`
  > CSS contract catalog, inline source-file annotations, CSS layer ownership rule, and E2E baseline confirmation protecting all subsequent phases from accidentally breaking tests.
- [x] **S02: TypeScript Module Extractions** `risk:low` `depends:[S01]`
  > Split 928-LOC enrichment.ts into verdict-compute.ts (pure functions), row-factory.ts (DOM builders), and trimmed enrichment.ts (polling orchestrator) with zero behavioral change.
- [x] **S03: Visual Redesign** `risk:medium` `depends:[S02]`
  > Verdict badge prominence (VIS-01), micro-bar replacing consensus badge (VIS-02), category labels (VIS-03), and no-data collapse (GRP-02) — all changes confined to row-factory.ts and input.css.
- [x] **S04: Template Restructuring** `risk:medium` `depends:[S03]`
  > HTML template delivers three explicit sections — Reputation, Infrastructure Context, No Data — as the structural backbone of each IOC card (GRP-01).
- [x] **S05: Context And Staleness** `risk:medium` `depends:[S04]`
  > Key context fields (GeoIP, ASN org, registrar) visible in IOC card header without expanding (CTX-01), plus cache staleness indicator (CTX-02).
