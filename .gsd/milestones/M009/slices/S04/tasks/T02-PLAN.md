---
estimated_steps: 15
estimated_files: 4
skills_used: []
---

# T02: CSS audit confirmation + full slice verification

Confirm the CSS audit finding (no dead CSS rules in input.css) by cross-referencing selectors. Verify the full frontend build chain and measure LOC reduction from the TypeScript dedup.

## Steps

1. Verify CSS audit: run a sampling check — pick 5-10 CSS class selectors from input.css and confirm each appears in at least one template (.html) or TypeScript (.ts) file via `rg`. Document that all selectors are actively referenced. This confirms R046 finding: no dead CSS exists.

2. Run `make css` — must succeed. Confirm `app/static/dist/style.css` is generated.

3. Run `make typecheck` — must pass with zero errors.

4. Run `make js` — must succeed.

5. Measure LOC: run `wc -l` on shared-rendering.ts, enrichment.ts, and history.ts. Compare against baseline (enrichment.ts: 582, history.ts: 355). Confirm net reduction ≥ 80 lines.

6. Verify no private copies remain: `grep -c 'function injectDetailLink' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/history.ts` should return 0 for both. Same for `function initExportButton` and the standalone `function sortDetailRows` in history.ts.

## Must-Haves

- [ ] CSS audit confirmed: no dead selectors found in input.css
- [ ] `make css` passes
- [ ] `make typecheck` passes
- [ ] `make js` passes
- [ ] Net TypeScript LOC reduction ≥ 80 lines
- [ ] Zero private copies of extracted functions remain in enrichment.ts or history.ts

## Inputs

- `app/static/src/ts/modules/shared-rendering.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- `app/static/src/input.css`

## Expected Output

- `app/static/src/ts/modules/shared-rendering.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`

## Verification

make typecheck && make js && make css && echo 'S04 fully verified'
