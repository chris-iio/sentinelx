---
id: T02
parent: S05
milestone: M001
provides:
  - CTX-02 staleness badge in summary row for cached verdict results
  - Full S05 slice E2E verification (89 pass, 2 pre-existing fail)
key_files:
  - app/static/src/ts/modules/verdict-compute.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/input.css
  - app/static/dist/main.js
  - app/static/dist/style.css
key_decisions:
  - Staleness badge shows oldest cached_at across all providers (not newest) to indicate worst-case data age
  - Error results never carry cachedAt (only "result" type responses can be cached)
patterns_established:
  - VerdictEntry propagates optional metadata (cachedAt) from API through to summary row rendering
observability_surfaces:
  - "document.querySelectorAll('.staleness-badge').length — count of IOCs showing staleness"
  - ".staleness-badge textContent shows relative cache age (e.g., 'cached 4h ago')"
  - "Zero .staleness-badge elements when all results are fresh"
duration: 8m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Add staleness badge to summary row and run full E2E verification

**Added staleness badge showing oldest cached_at relative time in IOC summary rows; full S05 slice E2E passes (89/2)**

## What Happened

Extended `VerdictEntry` interface with optional `cachedAt?: string` field. Populated it in `enrichment.ts` from `result.cached_at` when result type is "result" (error results excluded). Modified `updateSummaryRow()` in `row-factory.ts` to filter entries with `cachedAt`, find the oldest timestamp via sort, and append a `.staleness-badge` span with `formatRelativeTime()` output. Added CSS rule pushing the badge right via `margin-left: auto` in the flex summary row.

Initial typecheck failed because `sort()[0]` returns `string | undefined` — added a guard `if (oldestCachedAt)` before calling `formatRelativeTime()`. Second typecheck passed cleanly.

## Verification

- `make typecheck` — zero errors ✅
- `make js-dev` — bundle compiled (194.9kb) ✅
- `make css` — Tailwind rebuilt ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case) ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts ✅ (SEC-08)
- `grep -n "cachedAt" verdict-compute.ts` — field on line 24 ✅
- `grep -n "cachedAt" enrichment.ts` — populated on line 300 ✅
- `grep -n "staleness-badge" row-factory.ts` — created on line 314 ✅
- `grep -n "staleness-badge" input.css` — CSS rule on line 1473 ✅

### Slice-level verification (S05 final task):
- All task-level verification checks passed (see above)
- Template: `.ioc-context-line` exists in `_ioc_card.html` (T01)
- CSS: `.ioc-context-line:empty { display: none }` present in input.css (T01)
- JS: `updateContextLine` exported from row-factory.ts, called in enrichment.ts context branch (T01)
- JS: `VerdictEntry.cachedAt` optional field exists in verdict-compute.ts (this task)
- JS: `updateSummaryRow()` renders `.staleness-badge` when cached entries exist (this task)

## Diagnostics

- `document.querySelectorAll('.staleness-badge').length` — count of IOCs showing staleness badge
- Each `.staleness-badge` element's `textContent` contains "cached Xh ago" relative time
- If badge absent when expected: inspect `iocVerdicts` entries for `cachedAt` field — if missing, `result.cached_at` was not in API response
- If badge shows raw ISO instead of relative: `formatRelativeTime()` threw during parsing (falls back to raw string)

## Deviations

- Added `if (oldestCachedAt)` guard around badge creation to satisfy TypeScript strict null check on `sort()[0]` return type. Plan code assumed non-undefined since `cachedEntries.length > 0`, but `sort()[0]` is typed `string | undefined`.
- Error-type results explicitly get `cachedAt: undefined` rather than attempting `result.cached_at` on the error discriminated union branch.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/verdict-compute.ts` — Added `cachedAt?: string` to VerdictEntry interface
- `app/static/src/ts/modules/enrichment.ts` — Populated `cachedAt` from `result.cached_at` in verdict entry construction
- `app/static/src/ts/modules/row-factory.ts` — Added staleness badge rendering in `updateSummaryRow()` after micro-bar
- `app/static/src/input.css` — Added `.staleness-badge` CSS rule (muted, right-aligned)
- `app/static/dist/main.js` — Rebuilt JS bundle
- `app/static/dist/style.css` — Rebuilt CSS
- `.gsd/milestones/M001/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section
