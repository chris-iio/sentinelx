---
estimated_steps: 5
estimated_files: 3
---

# T02: Build verification and integration test suite

**Slice:** S02 — At-a-glance enrichment surface
**Milestone:** M002

## Description

After T01's CSS fixes, this task runs the full build and test pipeline to prove the at-a-glance enrichment surface integrates correctly with the existing TypeScript rendering pipeline and no DOM contracts or E2E tests are broken. This is pure verification — no code changes expected unless a test failure requires a targeted fix.

The build pipeline (`make css`, `make typecheck`, `make js-dev`) confirms CSS compiles, TypeScript has no errors, and the JS bundle builds. The E2E suite (`pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py`) confirms all 36 tests pass — same baseline as S01.

## Steps

1. **Install build tools if missing.** The worktree may not have `tools/tailwindcss` or `tools/esbuild` — they're not committed. Run:
   ```bash
   make tailwind-install
   make esbuild-install
   ```
   These are idempotent — they skip if already present.

2. **Run `make css`** and confirm exit 0. This compiles `input.css` → `app/static/css/main.css` using the local Tailwind binary.

3. **Run `make typecheck`** and confirm exit 0 with zero errors. This runs `npx tsc --noEmit` against the TypeScript source. Any DOM contract breakage (renamed selectors, changed types) would surface here.

4. **Run `make js-dev`** and confirm exit 0. This bundles the TypeScript into `app/static/js/main.js` using the local esbuild binary.

5. **Run the E2E test suite:**
   ```bash
   pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q
   ```
   Confirm 36 tests pass. If any test fails:
   - Read the failure output to understand what broke
   - Check if T01's CSS changes affected DOM structure (they shouldn't — CSS-only changes)
   - If a test failure is a genuine regression, fix it in the relevant file
   - If a test failure is pre-existing (not caused by T01), document it

6. **Verify the opacity fix landed correctly:**
   ```bash
   grep -n 'enrichment-slot--loaded' app/static/src/input.css
   ```
   Should show the new `opacity: 1` rule.

7. **Verify no bright colors in enrichment surface:**
   ```bash
   grep -n '#[0-9a-fA-F]\{3,6\}' app/static/src/input.css | grep -i 'context-line\|summary-row\|micro-bar\|staleness'
   ```
   Should return empty or only muted/verdict token references.

## Must-Haves

- [ ] `make css` exits 0
- [ ] `make typecheck` exits 0
- [ ] `make js-dev` exits 0
- [ ] 36 E2E tests pass (same as S01 baseline)
- [ ] Opacity fix confirmed via grep

## Verification

- All three `make` targets exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` → 36 passed
- `grep -n 'enrichment-slot--loaded' app/static/src/input.css` shows opacity: 1 rule
- No bright non-verdict hex colors in enrichment at-a-glance CSS

## Inputs

- `app/static/src/input.css` — Modified by T01 with opacity fix, spacing adjustments
- `app/static/src/ts/modules/row-factory.ts` — Read-only; contains `updateSummaryRow()` and `updateContextLine()` DOM builders
- `app/static/src/ts/modules/enrichment.ts` — Read-only; contains rendering orchestrator that adds `.enrichment-slot--loaded` class
- T01 summary — confirms what CSS changes were made
- Build tools: always use `make` targets (`make css`, `make typecheck`, `make js-dev`, `make tailwind-install`, `make esbuild-install`) — never bare binaries

## Expected Output

- All build targets exit 0 (CSS compiled, TS clean, JS bundled)
- 36 E2E tests pass with no regressions
- Confirmation that the at-a-glance enrichment surface CSS is correctly integrated
