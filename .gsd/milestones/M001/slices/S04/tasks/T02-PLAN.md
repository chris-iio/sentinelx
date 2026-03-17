---
estimated_steps: 4
estimated_files: 3
---

# T02: Run E2E suite and clean up dead code

**Slice:** S04 — Template Restructuring
**Milestone:** M001

## Description

Verify the atomic template+JS change from T01 doesn't break E2E tests, then clean up dead code left by the migration. The section-header injection logic was the main feature of `createSectionHeader()` — if nothing else uses it after T01's simplification, remove it. Confirm edge cases: empty sections are hidden, no-data collapse works within the scoped section, and no duplicate headers appear.

## Steps

1. **Run the full E2E suite:**
   ```bash
   pytest tests/ -m e2e --tb=short -q
   ```
   Expected: 89 passed, 2 failed (pre-existing title-case failures). If new failures appear, investigate — the most likely causes are:
   - JS routing targeting a container that doesn't exist (querySelector returns null → rows not appended → visible content changes)
   - `sortDetailRows` receiving wrong container → sort does nothing → verdict ordering breaks
   - No-data collapse toggle not finding `.no-data-expanded` class target

2. **Assess and remove `createSectionHeader()` in row-factory.ts:**
   - Check if `createSectionHeader` is called anywhere after T01's changes:
     ```bash
     grep -rn "createSectionHeader" app/static/src/ts/
     ```
   - If only the function definition remains (no call sites), remove the function AND its export.
   - If it's still exported but unused externally, remove the export. If tests or other modules reference it, keep it.

3. **Run SEC-08 gate:**
   ```bash
   grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/
   ```
   Must return zero results.

4. **Final rebuild and verify:**
   ```bash
   make typecheck && make js-dev && make css
   ```
   All must succeed. This confirms that any dead-code removal didn't introduce type errors.

## Must-Haves

- [ ] E2E suite passes at pre-existing baseline (89 pass, 2 pre-existing failures)
- [ ] `createSectionHeader` removed if no longer called anywhere
- [ ] Zero `innerHTML`/`insertAdjacentHTML` usage in TypeScript source (SEC-08)
- [ ] Final build passes (`make typecheck && make js-dev && make css`)

## Verification

- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing)
- `grep -rn "createSectionHeader" app/static/src/ts/` — zero results OR only function definition with no call sites
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero results
- `make typecheck && make js-dev && make css` — all pass

## Observability Impact

- **Signals removed:** `createSectionHeader()` export removed from row-factory.ts — any module that imported it will get a build error (intentional dead-code detection).
- **Inspection surface:** After this task, `grep -rn "createSectionHeader" app/static/src/ts/` should return zero results, confirming the migration from JS-injected headers to template-rendered headers is complete.
- **Failure state visibility:** If `createSectionHeader` is removed but still referenced somewhere, `make typecheck` will fail with an import error — this is the primary detection mechanism.
- **E2E baseline:** 89 pass / 2 fail (pre-existing title-case). Any deviation from this baseline after T01's changes indicates a regression in section routing, sort ordering, or no-data collapse.

## Inputs

- T01 completed: template has three `.enrichment-section` containers, JS routes rows to correct sections, `injectSectionHeadersAndNoDataSummary()` simplified
- Pre-existing E2E baseline: 89 pass, 2 fail (title-case)
- `createSectionHeader()` in row-factory.ts — may now be dead code

## Expected Output

- E2E test results confirming no regression
- `app/static/src/ts/modules/row-factory.ts` — `createSectionHeader` removed if dead
- `app/static/dist/main.js` — rebuilt bundle (if code removed)
- `app/static/dist/style.css` — rebuilt CSS (if needed)
