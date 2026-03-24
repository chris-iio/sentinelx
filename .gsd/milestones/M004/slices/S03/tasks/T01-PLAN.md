---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Remove dead TS exports/functions and dead CSS rules

**Slice:** S03 — Frontend tightening — TypeScript + CSS audit
**Milestone:** M004

## Description

Remove dead TypeScript code (unused exports and functions) and dead CSS rules that are no longer referenced anywhere. This is mechanical cleanup — no behavioral changes. Three TS items and six CSS rules to remove.

## Steps

1. **Un-export `getOrCreateSummaryRow` in `app/static/src/ts/modules/row-factory.ts`** (line 233). Change `export function getOrCreateSummaryRow` to `function getOrCreateSummaryRow`. The function is still called internally at line 292 by `updateSummaryRow` — only the `export` keyword is removed.

2. **Delete `computeConsensus()` and `consensusBadgeClass()` from `app/static/src/ts/modules/verdict-compute.ts`**. These are two entire functions (lines 50-67 for `computeConsensus`, lines 72-77 for `consensusBadgeClass`) plus their JSDoc comments. Neither is imported anywhere — confirmed by grep. Delete the functions entirely including their doc comments. Do NOT delete any other functions in this file (`computeWorstVerdict`, `computeAttribution`, `findWorstEntry` — all are actively used).

3. **Delete dead CSS rules from `app/static/src/input.css`**:
   - `.alert-success` block (starts at line 327, 5 lines including closing brace) — never used in any template or TS file
   - `.alert-warning` block (starts at line 333, 5 lines) — never used
   - `.consensus-badge` section (starts around line 1237 with the section comment `/* ---- Phase 4 Results UX — Consensus badge ---- */` through the end of `.consensus-badge--red` closing brace, approximately lines 1237-1265) — only referenced by dead `consensusBadgeClass()` which is deleted in step 2

4. **Verify builds and dead code absence**. Run `npx tsc --noEmit`, `make js`, `make css`. Grep to confirm all dead patterns are gone.

## Must-Haves

- [ ] `export` keyword removed from `getOrCreateSummaryRow` (function body preserved)
- [ ] `computeConsensus()` function deleted entirely from verdict-compute.ts
- [ ] `consensusBadgeClass()` function deleted entirely from verdict-compute.ts
- [ ] `.alert-success` CSS rule deleted from input.css
- [ ] `.alert-warning` CSS rule deleted from input.css
- [ ] `.consensus-badge` and its 3 modifier rules deleted from input.css
- [ ] `npx tsc --noEmit` passes with zero errors
- [ ] `make js` succeeds (may need `tools/esbuild` — copy from main project if missing)
- [ ] `make css` succeeds (may need `tools/tailwindcss` — copy from main project if missing)

## Verification

- `npx tsc --noEmit` exits 0
- `! grep -q 'export function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts`
- `grep -q 'function getOrCreateSummaryRow' app/static/src/ts/modules/row-factory.ts` (function still exists, just not exported)
- `! grep -q 'computeConsensus' app/static/src/ts/modules/verdict-compute.ts`
- `! grep -q 'consensusBadgeClass' app/static/src/ts/modules/verdict-compute.ts`
- `! grep -q 'alert-success' app/static/src/input.css`
- `! grep -q 'alert-warning' app/static/src/input.css`
- `! grep -q 'consensus-badge' app/static/src/input.css`

## Inputs

- `app/static/src/ts/modules/row-factory.ts` — contains `export function getOrCreateSummaryRow` at line 233
- `app/static/src/ts/modules/verdict-compute.ts` — contains dead `computeConsensus()` at line 50 and `consensusBadgeClass()` at line 72
- `app/static/src/input.css` — contains dead `.alert-success` (line 327), `.alert-warning` (line 333), `.consensus-badge` family (lines 1238-1265)

## Expected Output

- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow` no longer exported
- `app/static/src/ts/modules/verdict-compute.ts` — `computeConsensus` and `consensusBadgeClass` deleted
- `app/static/src/input.css` — 6 dead CSS rules removed (~30 lines)

## Observability Impact

- **Signals changed:** None — this task removes dead code only; no runtime behavior changes.
- **Inspection:** Future agents can verify dead code absence via grep assertions in the Verification section. Bundle size decrease confirms dead code elimination (`make js` reports byte count).
- **Failure visibility:** If any code still references the removed exports/functions, `npx tsc --noEmit` will fail with import errors. If CSS classes are still referenced, E2E visual regression tests will catch missing styles.
