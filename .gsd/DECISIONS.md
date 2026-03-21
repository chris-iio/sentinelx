# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M001/S01 | convention | E2E baseline expectation | 89/91 — 2 pre-existing title capitalization failures out of scope | Failures predate Phase 1 (stash-and-run verified); fixing them is unrelated to the redesign | No |
| D002 | M001/S01 | convention | CSS-CONTRACTS.md location | `.planning/phases/01-contracts-and-foundation/` (co-located with producing phase) | Keeps phase artifacts co-located; downstream phases reference via explicit path | No |
| D003 | M001/S01 | pattern | JS-created runtime classes catalogued separately | 18 JS-created classes documented alongside 24 template-sourced classes | Both are equally contractual because E2E tests can query runtime DOM | No |
| D004 | M001/S02 | pattern | formatDate visibility in row-factory.ts | Exported (not private) | renderEnrichmentResult in enrichment.ts needs it for scan_date formatting | No |
| D005 | M001/S02 | pattern | createProviderRow dispatcher | Thin dispatcher in row-factory.ts as stable API surface for Phase 3 | Gives visual redesign a single entry point instead of two separate create functions | No |
| D006 | M001/S02 | pattern | Unused imports cleanup | VERDICT_LABELS and EnrichmentResultItem removed from enrichment.ts imports | Only needed by row-factory.ts after extraction | No |
| D007 | M001/S03 | testing | TypeScript unit test framework choice | Vitest + jsdom (devDependencies only) | Project has zero TS unit tests. Vitest is the fastest setup for ESM TypeScript with jsdom DOM simulation. It natively understands TS without a separate transform step. jsdom provides sufficient DOM fidelity for testing createElement/querySelector patterns in row-factory.ts. The existing E2E suite remains Python/Playwright — vitest covers the unit layer only. | No |
| D008 | M001/S03 | convention | Whether to keep .consensus-badge dead CSS and consensusBadgeClass() function | Remove — micro-bar satisfies "consensus at a glance" information density requirement | VIS-02 replaced .consensus-badge with .verdict-micro-bar. No E2E test queries .consensus-badge (verified via grep). The information density requirement is satisfied by the micro-bar with title attribute encoding exact counts. Keeping dead code misleads future contributors. | No |
