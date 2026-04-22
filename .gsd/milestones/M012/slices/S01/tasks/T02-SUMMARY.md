---
id: T02
parent: S01
milestone: M012
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/types/api.ts
  - app/static/src/ts/modules/enrichment.test.ts
key_decisions:
  - Handled terminal polling states by parsing JSON before checking `resp.ok`, because unknown/evicted jobs now return meaningful 404 payloads that the UI must interpret rather than discard.
  - Reused the existing warning/progress surfaces and slot-finalization behavior for terminal failures so analyst-visible feedback improved without changing the success-path rendering contract.
duration: 
verification_result: passed
completed_at: 2026-04-22T04:00:00.777Z
blocker_discovered: false
---

# T02: Surfaced terminal enrichment polling failures in the analyst UI and added focused Vitest coverage for failure and success paths.

**Surfaced terminal enrichment polling failures in the analyst UI and added focused Vitest coverage for failure and success paths.**

## What Happened

I updated the frontend enrichment poller to consume the additive terminal status contract from T01 instead of dropping non-2xx poll responses. `app/static/src/ts/types/api.ts` now models the optional terminal metadata, and `app/static/src/ts/modules/enrichment.ts` now parses JSON bodies before branching on `resp.ok`, stops polling when `terminal` is true, surfaces an analyst-visible failure banner/progress message for unknown/evicted/job_failed terminal states, and finalizes the loaded-slot UI without changing the existing success-path completion behavior. I also added `app/static/src/ts/modules/enrichment.test.ts` with focused Vitest coverage proving that terminal 404 payloads become visible stop states instead of endless polling and that the normal success path still renders results, marks completion, and enables export.

## Verification

Ran `npx vitest run`, which passed all frontend module tests including the new enrichment polling coverage (68 tests total). Also ran the corrected backend continuity command `python3 -m pytest tests/test_routes.py tests/test_orchestrator.py -q` to close the stale-plan verification gap that referenced a nonexistent `tests/test_routes_helpers.py` file in this checkout; both focused backend suites passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run` | 0 | ✅ pass | 788ms |
| 2 | `python3 -m pytest tests/test_routes.py tests/test_orchestrator.py -q` | 0 | ✅ pass | 680ms |

## Deviations

The task plan mentioned `app/static/src/ts/modules/results.ts` and `app/static/src/ts/modules/status.ts`, but those files do not exist in this repo. I adapted the work to the real module layout by changing `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/types/api.ts`, and adding `app/static/src/ts/modules/enrichment.test.ts`.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/types/api.ts`
- `app/static/src/ts/modules/enrichment.test.ts`
