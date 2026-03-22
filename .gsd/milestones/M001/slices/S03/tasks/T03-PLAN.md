---
estimated_steps: 4
estimated_files: 4
skills_used:
  - lint
  - review
---

# T03: Remove dead consensus-badge code and run full verification

**Slice:** S03 — Visual Redesign
**Milestone:** M001

## Description

VIS-02 replaced the `.consensus-badge` text element with the `.verdict-micro-bar` visual bar in `updateSummaryRow()`. The old consensus-badge CSS rules and the `consensusBadgeClass()` helper function are now dead code. No E2E test queries `.consensus-badge` (verified: `grep -r "consensus-badge" tests/e2e/` returns zero results). The CSS-CONTRACTS.md lists it in the "JS-Created Runtime Classes" table and "Information Density Acceptance Criteria" — but the micro-bar now satisfies the information density requirement ("consensus at a glance"). This task removes the dead code, updates the test file, and runs the full verification suite.

## Steps

1. Remove `consensusBadgeClass()` function from `app/static/src/ts/modules/verdict-compute.ts`. It is currently exported but no production code calls it — `updateSummaryRow()` in row-factory.ts no longer creates a `.consensus-badge` element. Verify with: `grep -rn "consensusBadgeClass" app/static/src/ts/` — should only show the definition and the test.

2. Remove all `.consensus-badge` CSS rules from `app/static/src/input.css`. There are 4 rules to remove: `.consensus-badge` (base), `.consensus-badge--green`, `.consensus-badge--yellow`, `.consensus-badge--red`. These are approximately at lines 1238-1265.

3. Update `app/static/src/ts/modules/verdict-compute.test.ts` to remove the test(s) for `consensusBadgeClass()` since the function no longer exists. Ensure the import is also removed.

4. Run full verification:
   - `make typecheck` — confirms no TS compilation errors from removed export
   - `npx vitest run` — confirms all remaining tests pass
   - `grep -r "consensus-badge" app/static/src/` — confirms zero remaining references in source
   - `grep -r "consensusBadgeClass" app/static/src/` — confirms zero remaining references

## Must-Haves

- [ ] `consensusBadgeClass()` function removed from verdict-compute.ts
- [ ] All `.consensus-badge` CSS rules removed from input.css
- [ ] Test for `consensusBadgeClass` removed from verdict-compute.test.ts
- [ ] `make typecheck` passes
- [ ] `npx vitest run` passes with zero failures
- [ ] Zero grep hits for "consensus-badge" in `app/static/src/` (CSS and TS)

## Verification

- `make typecheck` — zero errors
- `npx vitest run` — all tests pass
- `grep -rc "consensus-badge" app/static/src/` — all counts are 0
- `grep -rc "consensusBadgeClass" app/static/src/ts/` — all counts are 0

## Observability Impact

- **Dead code verification:** `grep -rc "consensus-badge" app/static/src/` and `grep -rc "consensusBadgeClass" app/static/src/ts/` both return all zeros, confirming complete removal.
- **Test count change:** Removing 4 `consensusBadgeClass` tests reduces verdict-compute.test.ts from 26 to 22 tests. The total suite should remain above the ≥30 threshold due to row-factory.test.ts's 54 tests.
- **No runtime signal change:** The removed function was already dead code (not called by production code). No runtime logs, error shapes, or user-visible behavior changes.
- **Failure state:** If something still referenced `consensusBadgeClass` or `.consensus-badge`, the grep checks above would return non-zero counts and `make typecheck` would fail with "not exported" errors.

## Inputs

- `app/static/src/ts/modules/verdict-compute.ts` — contains dead `consensusBadgeClass()` function
- `app/static/src/input.css` — contains dead `.consensus-badge` CSS rules (lines ~1238-1265)
- `app/static/src/ts/modules/verdict-compute.test.ts` — T01 output, contains test for `consensusBadgeClass` that must be removed
- `vitest.config.ts` — test framework config (read-only)
- `package.json` — dependencies (read-only)

## Expected Output

- `app/static/src/ts/modules/verdict-compute.ts` — `consensusBadgeClass()` removed
- `app/static/src/input.css` — `.consensus-badge` rules removed
- `app/static/src/ts/modules/verdict-compute.test.ts` — `consensusBadgeClass` test removed
