---
id: T01
parent: S02
milestone: M012
key_files:
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/modules/result-application.test.ts
key_decisions:
  - Kept live/history runtime ownership outside the coordinator by making `result-application.ts` expose `apply()`, `flush()`, and `finalize()` instead of owning polling or replay timing.
  - Moved copy-button `data-enrichment` updates into the shared flush path so history replay gains the same summary text parity as live rendering.
duration: 
verification_result: passed
completed_at: 2026-04-22T06:03:56.635Z
blocker_discovered: false
---

# T01: Extracted a shared result-application coordinator so live polling and history replay now render cards, summary rows, copy-button enrichment, and final slot cleanup through one path.

**Extracted a shared result-application coordinator so live polling and history replay now render cards, summary rows, copy-button enrichment, and final slot cleanup through one path.**

## What Happened

I extracted the duplicated per-result DOM/state coordination from `app/static/src/ts/modules/enrichment.ts` and `app/static/src/ts/modules/history.ts` into a new stateful module, `app/static/src/ts/modules/result-application.ts`. The new coordinator owns the shared apply path for one `EnrichmentItem`, tracks per-IOC verdict/result state, routes rows into context/reputation/no-data sections, updates pending indicators, and exposes explicit `flush()`/`finalize()` hooks. I kept runtime ownership in the callers: `enrichment.ts` still owns polling, warning banners, terminal handling, progress updates, export accumulation, and now also owns the live debounce boundary before calling `flush()`, while `history.ts` still owns history JSON parsing and synchronous replay timing and now calls the same coordinator directly. I also added focused unit coverage in `app/static/src/ts/modules/result-application.test.ts` to pin summary-row/card verdict/copy-button parity, context-only behavior, missing-card tolerance, and finalize-time detail-link behavior. This keeps `shared-rendering.ts` as a pure helper layer rather than turning it into a hidden state bucket.

## Verification

Verified the new shared coordinator directly with `npx vitest run app/static/src/ts/modules/result-application.test.ts`, then ran `npx tsc --noEmit` for type safety across the refactor, and finally ran `npx vitest run app/static/src/ts/modules/enrichment.test.ts` to confirm the existing live polling success/terminal flow still works after the extraction. All three commands passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run app/static/src/ts/modules/result-application.test.ts` | 0 | ✅ pass | 879ms |
| 2 | `npx tsc --noEmit` | 0 | ✅ pass | 413ms |
| 3 | `npx vitest run app/static/src/ts/modules/enrichment.test.ts` | 0 | ✅ pass | 872ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- `app/static/src/ts/modules/result-application.test.ts`
