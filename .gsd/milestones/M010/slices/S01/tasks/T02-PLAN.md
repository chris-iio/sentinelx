---
estimated_steps: 10
estimated_files: 1
skills_used: []
---

# T02: Remove dead ResultDisplay export from shared-rendering.ts

Change `export interface ResultDisplay` to `interface ResultDisplay` in shared-rendering.ts. The interface is used as the return type of `computeResultDisplay` but never imported by name anywhere — callers destructure the return value inline.

## Steps

1. Read `app/static/src/ts/modules/shared-rendering.ts` line 21.
2. Change `export interface ResultDisplay {` to `interface ResultDisplay {`.
3. Run `make typecheck` to confirm TypeScript still compiles (the function return type annotation uses `ResultDisplay` locally, which is fine as a non-exported interface).
4. Verify no module imports `ResultDisplay` by name: `rg 'ResultDisplay' app/static/src/ts/ --no-filename` should show only the definition and the function signature, not any import.

## Must-Haves

- [ ] `ResultDisplay` is no longer exported
- [ ] `make typecheck` passes
- [ ] No import of `ResultDisplay` by name exists in any TS file

## Inputs

- ``app/static/src/ts/modules/shared-rendering.ts` — contains `export interface ResultDisplay` on line 21`

## Expected Output

- ``app/static/src/ts/modules/shared-rendering.ts` — ResultDisplay changed from exported to non-exported interface`

## Verification

make typecheck && grep -c 'export interface ResultDisplay' app/static/src/ts/modules/shared-rendering.ts | grep -q '^0$' && echo 'PASS: ResultDisplay no longer exported'
