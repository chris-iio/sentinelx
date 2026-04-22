---
estimated_steps: 1
estimated_files: 4
skills_used: []
---

# T02: Surface terminal polling failures in the analyst UI

Update the enrichment UI polling flow to interpret the hardened status contract, stop silent endless polling on terminal failure, and present clear analyst-visible feedback while preserving current success-path rendering. Add or update frontend unit tests for status/error handling and any touched DOM state transitions.

## Inputs

- `app/static/src/ts/modules/enrichment.ts`
- `existing Vitest coverage for enrichment modules`
- `status contract from T01`

## Expected Output

- `Frontend polling flow that handles terminal states explicitly`
- `Frontend tests covering terminal failure display and preserved success-path behavior`

## Verification

npx vitest run

## Observability Impact

Makes failure states visible in the analyst UI instead of disappearing into retry loops.
