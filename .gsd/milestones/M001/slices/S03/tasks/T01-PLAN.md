---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T01: Bootstrap vitest and test verdict-compute.ts pure functions

**Slice:** S03 — Visual Redesign
**Milestone:** M001

## Description

No TypeScript test framework exists in this project. The project uses esbuild for bundling and `tsc --noEmit` for type checking, but has zero TS-level unit tests (the existing 105 E2E tests are Python/Playwright). This task bootstraps vitest with jsdom and validates the setup by writing comprehensive tests for the pure computation functions in `verdict-compute.ts`.

`verdict-compute.ts` is the ideal first target because it contains only pure functions with no DOM access — the simplest possible test surface. The functions tested here (`computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry`) underpin the verdict rendering logic that all visual requirements depend on.

## Steps

1. Create `package.json` with vitest and jsdom as devDependencies. Use `npm install --save-dev vitest jsdom @vitest/coverage-v8` to install. Do NOT add any other dependencies — the project uses standalone esbuild/tailwind binaries, not npm-managed ones.

2. Create `vitest.config.ts` at project root:
   - Set `test.environment` to `"jsdom"` (needed for T02's DOM tests)
   - Set `test.include` to `["app/static/src/ts/**/*.test.ts"]`
   - Set `test.globals` to `true` for describe/it/expect without imports

3. Create `tsconfig.test.json` extending `tsconfig.json`:
   - Add `"types": ["vitest/globals"]` to compilerOptions
   - Set include to `["app/static/src/ts/**/*.ts"]` (same scope but with vitest globals)
   - Reference this from vitest.config.ts via `test.typecheck.tsconfig`

4. Create `app/static/src/ts/modules/verdict-compute.test.ts` with tests for:
   - `computeWorstVerdict()`: empty array returns "no_data"; single entry returns that verdict; mixed array returns highest severity; `known_good` overrides all other verdicts (design rule)
   - `computeConsensus()`: empty array → {flagged:0, responded:0}; only clean entries → {flagged:0, responded:N}; mixed verdicts count correctly; no_data and error entries are excluded from counts
   - `computeAttribution()`: empty array returns "No providers returned data" text; single entry returns its provider + statText; multiple entries picks highest totalEngines; ties broken by severity
   - `findWorstEntry()`: empty array returns undefined; single entry returns that entry; correctly identifies highest severity entry

5. Run `npx vitest run` and fix any issues until all tests pass.

## Must-Haves

- [ ] `package.json` exists with vitest and jsdom as devDependencies
- [ ] `vitest.config.ts` correctly configured for jsdom environment and TS test files
- [ ] `tsconfig.test.json` extends base tsconfig and includes vitest globals
- [ ] verdict-compute.test.ts has ≥12 test assertions across all 4 exported functions
- [ ] `npx vitest run` passes with zero failures
- [ ] `make typecheck` still passes (base tsconfig unchanged)

## Verification

- `npx vitest run` — all tests pass, exit code 0
- `make typecheck` — zero errors (existing tsconfig untouched, test tsconfig separate)
- Test count: `npx vitest run --reporter=verbose 2>&1 | grep -c "✓"` ≥ 12

## Inputs

- `app/static/src/ts/modules/verdict-compute.ts` — the module under test
- `app/static/src/ts/types/ioc.ts` — VerdictKey type and verdictSeverityIndex used by verdict-compute
- `tsconfig.json` — base TypeScript config to extend

## Expected Output

- `package.json` — new file with devDependencies
- `vitest.config.ts` — new vitest configuration
- `tsconfig.test.json` — new test-specific TypeScript config
- `app/static/src/ts/modules/verdict-compute.test.ts` — new test file with ≥12 assertions
- `node_modules/` — installed dependencies (gitignored)
