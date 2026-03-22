# S03: Visual Redesign

**Goal:** Unit tests prove all 7 visual-redesign requirements (VIS-01, VIS-02, VIS-03, GRP-01, GRP-02, CTX-01, CTX-02) are correctly implemented in the extracted TypeScript modules.
**Demo:** `npx vitest run` passes 76 tests across 2 files covering every requirement, `make typecheck` is clean, and dead consensus-badge code is fully removed.

## Must-Haves

- Vitest + jsdom test framework bootstrapped (devDependencies only, no runtime Node.js dependency)
- verdict-compute.ts pure functions covered by unit tests (≥12 assertions)
- row-factory.ts DOM builders covered by jsdom unit tests (≥20 assertions) with requirement-ID-prefixed test names
- VIS-01: verdict badge class matches verdict value on detail rows
- VIS-02: micro-bar segments replace consensus badge — correct classes, percentage widths, title attribute
- VIS-03: CONTEXT_PROVIDERS membership distinguishes category; section headers injected post-enrichment
- GRP-01: context rows have `.provider-context-row` class with `data-verdict="context"`
- GRP-02: no-data rows get `.provider-row--no-data`; summary row with count text and click-to-expand toggle
- CTX-01: IP Context geo, ASN Intel priority suppression, DNS Records A-record max-3 tested
- CTX-02: staleness badge presence/absence based on `cachedAt` tested
- Dead `consensusBadgeClass()` function and `.consensus-badge` CSS removed (D008)

## Proof Level

- This slice proves: contract (DOM structure contracts validated by unit tests)
- Real runtime required: no (jsdom simulates DOM; CSS rendering not tested)
- Human/UAT required: no (all verification is automated via vitest)

## Verification

- `npx vitest run` — 76/76 tests pass across 2 files, exit code 0
- `make typecheck` — zero TypeScript errors
- `grep -c "consensus-badge" app/static/src/input.css` returns 0
- `grep -c "consensusBadgeClass" app/static/src/ts/modules/verdict-compute.ts` returns 0

## Observability / Diagnostics

- Runtime signals: `npx vitest run` exit code (0 = pass, non-zero = failures with assertion diffs)
- Inspection surfaces: `npx vitest run --reporter=verbose` shows per-test pass/fail with requirement ID prefixes (VIS-01, VIS-02, GRP-02, CTX-01, etc.)
- Failure visibility: vitest assertion diffs show expected vs actual DOM class names, attribute values, text content
- Redaction constraints: none (no secrets or PII in test fixtures)

## Integration Closure

- Upstream surfaces consumed: `row-factory.ts`, `verdict-compute.ts`, `enrichment.ts` (S02 extractions), `input.css`, `types/ioc.ts`, `types/api.ts`
- New wiring introduced in this slice: `package.json` + `vitest.config.ts` + `tsconfig.test.json` (test infrastructure); test files co-located with source modules
- What remains before the milestone is truly usable end-to-end: E2E tests (`make e2e`) remain the integration safety net — vitest covers the unit layer only

## Tasks

- [x] **T01: Bootstrap vitest and test verdict-compute.ts pure functions** `est:30m`
  - Why: No TS test framework exists; verdict-compute.ts is the simplest target (pure functions, no DOM)
  - Files: `package.json`, `vitest.config.ts`, `tsconfig.test.json`, `app/static/src/ts/modules/verdict-compute.test.ts`
  - Do: Create package.json with vitest/jsdom devDependencies, vitest.config.ts with jsdom environment, tsconfig.test.json extending base with vitest globals, and 22+ tests covering computeWorstVerdict, computeConsensus, computeAttribution, findWorstEntry
  - Verify: `npx vitest run` passes, `make typecheck` clean
  - Done when: ≥12 verdict-compute tests pass, vitest framework functional

- [x] **T02: Test row-factory.ts DOM builders covering all visual redesign requirements** `est:45m`
  - Why: Every visual requirement (VIS-01/02/03, GRP-01/02, CTX-01/02) is implemented through row-factory.ts exports — DOM tests prove correctness
  - Files: `app/static/src/ts/modules/row-factory.test.ts`
  - Do: Write 54 jsdom tests across 8 describe blocks covering getOrCreateSummaryRow, updateSummaryRow (VIS-02, CTX-02), createDetailRow (VIS-01, GRP-02), createContextRow (GRP-01), injectSectionHeadersAndNoDataSummary (VIS-03, GRP-02), updateContextLine (CTX-01), formatDate, CONTEXT_PROVIDERS
  - Verify: `npx vitest run` — all tests pass across both files, ≥30 total assertions
  - Done when: all 7 requirements have ≥1 test with requirement-ID prefix

- [x] **T03: Remove dead consensus-badge code and run full verification** `est:15m`
  - Why: VIS-02 replaced consensus badge with micro-bar (D008) — dead code misleads future contributors
  - Files: `app/static/src/ts/modules/verdict-compute.ts`, `app/static/src/input.css`, `app/static/src/ts/modules/verdict-compute.test.ts`
  - Do: Remove consensusBadgeClass() from verdict-compute.ts, all .consensus-badge CSS rules from input.css, consensusBadgeClass test from verdict-compute.test.ts
  - Verify: `make typecheck` clean, `npx vitest run` passes, zero grep hits for consensus-badge/consensusBadgeClass in source
  - Done when: dead code fully removed, 76 tests still pass

## Files Likely Touched

- `package.json` — new; vitest + jsdom devDependencies
- `vitest.config.ts` — new; jsdom environment, globals, test include pattern
- `tsconfig.test.json` — new; extends base tsconfig with vitest/globals types
- `tsconfig.json` — modified; added exclude for *.test.ts files
- `app/static/src/ts/modules/verdict-compute.test.ts` — new; 22 unit tests
- `app/static/src/ts/modules/row-factory.test.ts` — new; 54 unit tests
- `app/static/src/ts/modules/verdict-compute.ts` — modified; consensusBadgeClass() removed
- `app/static/src/input.css` — modified; .consensus-badge CSS rules removed
