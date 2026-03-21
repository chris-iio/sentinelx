# S03: Visual Redesign

**Goal:** Unit tests prove all seven visual-redesign requirements (VIS-01, VIS-02, VIS-03, GRP-01, GRP-02, CTX-01, CTX-02) work correctly.
**Demo:** `npx vitest run` passes with ≥30 assertions covering every exported function in `row-factory.ts` and `verdict-compute.ts`, plus `make typecheck` is clean.

## Must-Haves

- Vitest + jsdom test framework bootstrapped (package.json, vitest.config.ts, test tsconfig)
- Unit tests for all pure computation functions in `verdict-compute.ts` (worst verdict, consensus, attribution, finding worst entry)
- Unit tests for `updateSummaryRow()` proving VIS-02 (micro-bar segments) and CTX-02 (staleness badge)
- Unit tests for `createDetailRow()` proving correct class assignment for verdict and no-data rows (VIS-01 hierarchy, GRP-02 no-data class)
- Unit tests for `createContextRow()` proving context row rendering path (GRP-01 section separation)
- Unit tests for `injectSectionHeadersAndNoDataSummary()` proving GRP-02 no-data collapse + toggle
- Unit tests for `updateContextLine()` proving CTX-01 inline context fields
- Dead `.consensus-badge` CSS and unused `consensusBadgeClass()` function removed
- `make typecheck` passes with zero errors after all changes

## Verification

- `npx vitest run` — all tests pass, ≥30 assertions across 2 test files
- `make typecheck` — zero TypeScript errors
- `grep -c "consensus-badge" app/static/src/input.css` returns 0
- `grep -c "consensusBadgeClass" app/static/src/ts/modules/verdict-compute.ts` returns 0

## Tasks

- [x] **T01: Bootstrap vitest and test verdict-compute.ts pure functions** `est:45m`
  - Why: No TypeScript test framework exists. This task creates the foundation and proves it works by testing the simplest module (pure functions, no DOM).
  - Files: `package.json`, `vitest.config.ts`, `tsconfig.test.json`, `app/static/src/ts/modules/verdict-compute.test.ts`
  - Do: Create package.json with vitest + jsdom devDependencies. Create vitest.config.ts targeting the TS source. Create test-specific tsconfig extending base. Write tests for `computeWorstVerdict`, `computeConsensus`, `consensusBadgeClass`, `computeAttribution`, `findWorstEntry` covering happy paths, edge cases (empty arrays, all no-data, known_good override), and boundary conditions.
  - Verify: `npx vitest run` passes with all verdict-compute tests green
  - Done when: `npx vitest run` reports 0 failures and ≥12 test assertions for verdict-compute.ts

- [x] **T02: Test row-factory.ts DOM builders covering all visual redesign requirements** `est:1h`
  - Why: Every visual requirement (VIS-01, VIS-02, VIS-03, GRP-01, GRP-02, CTX-01, CTX-02) is implemented in row-factory.ts exports. Unit tests with jsdom prove the DOM output matches requirements.
  - Files: `app/static/src/ts/modules/row-factory.test.ts`
  - Do: Write jsdom-based tests for all exported functions: `getOrCreateSummaryRow` (creates row with chevron, a11y attributes), `updateSummaryRow` (micro-bar segments verify VIS-02, staleness badge verifies CTX-02), `createDetailRow` (verdict class + `provider-row--no-data` class verifies GRP-02), `createContextRow` (context rendering path verifies GRP-01), `injectSectionHeadersAndNoDataSummary` (no-data count row + click toggle verifies GRP-02), `updateContextLine` (IP Context, ASN Intel, DNS Records verifies CTX-01). Test edge cases: zero-count micro-bar, no cached entries, empty raw_stats.
  - Verify: `npx vitest run` passes with all row-factory tests green
  - Done when: `npx vitest run` reports 0 failures and ≥20 test assertions for row-factory.ts; every requirement has at least one covering test

- [ ] **T03: Remove dead consensus-badge code and run full verification** `est:30m`
  - Why: `consensusBadgeClass()` and `.consensus-badge` CSS are dead code since VIS-02 replaced the consensus badge with the micro-bar. Removing them keeps the codebase honest and confirms nothing depends on them.
  - Files: `app/static/src/ts/modules/verdict-compute.ts`, `app/static/src/input.css`, `app/static/src/ts/modules/verdict-compute.test.ts`
  - Do: Remove `consensusBadgeClass()` export from verdict-compute.ts. Remove all `.consensus-badge` CSS rules from input.css. Remove the test for `consensusBadgeClass` from verdict-compute.test.ts. Grep entire codebase to confirm no remaining references. Run typecheck + test suite.
  - Verify: `make typecheck && npx vitest run` both pass; `grep -r "consensus-badge" app/static/src/` returns only the comment in CSS-CONTRACTS.md (if any)
  - Done when: Zero references to consensus-badge in source files (CSS + TS), typecheck clean, all tests pass

## Observability / Diagnostics

- **Test runner output:** `npx vitest run --reporter=verbose` shows per-test pass/fail status with test names mapping to requirement IDs.
- **Type-check surface:** `make typecheck` exits non-zero with file:line errors if test files or source files have type issues.
- **Failure visibility:** Vitest provides stack traces and inline diffs on assertion failures. Exit code 1 on any failure.
- **Inspection commands:** `npx vitest run --reporter=json` produces machine-readable test results for downstream tooling.
- **Dead code detection:** `grep -c` commands in Verification section detect whether consensus-badge removal is complete.
- **Redaction:** No sensitive data in this slice — all tests use synthetic VerdictEntry fixtures.

## Files Likely Touched

- `package.json` (new)
- `vitest.config.ts` (new)
- `tsconfig.test.json` (new)
- `app/static/src/ts/modules/verdict-compute.test.ts` (new)
- `app/static/src/ts/modules/row-factory.test.ts` (new)
- `app/static/src/ts/modules/verdict-compute.ts` (dead code removal)
- `app/static/src/input.css` (dead code removal)
