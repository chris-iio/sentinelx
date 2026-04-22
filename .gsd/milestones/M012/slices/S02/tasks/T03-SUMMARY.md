---
id: T03
parent: S02
milestone: M012
key_files:
  - app/static/src/ts/modules/history.test.ts
  - app/static/src/ts/modules/enrichment.test.ts
  - app/static/src/ts/modules/result-application.test.ts
  - tests/test_history_routes.py
key_decisions:
  - Proved live/history parity with one mixed IOC fixture rendered through both paths and compared via visible DOM state instead of only asserting isolated presence checks.
  - Pinned the history-detail route contract at the HTML layer so frontend owner-dispatch regressions fail in server-side tests before replay behavior drifts.
duration: 
verification_result: passed
completed_at: 2026-04-22T06:21:24.270Z
blocker_discovered: false
---

# T03: Added parity-focused frontend and route tests proving history replay matches live rendering and never polls the live status endpoint.

**Added parity-focused frontend and route tests proving history replay matches live rendering and never polls the live status endpoint.**

## What Happened

I extended the slice proof instead of changing runtime behavior. In `app/static/src/ts/modules/history.test.ts`, I replaced the minimal replay checks with a focused parity harness that replays one mixed IOC fixture through history and live paths, compares the visible DOM state they produce, and explicitly proves history never fetches `/enrichment/status/history` or shows a false terminal warning. I also added malformed-history coverage so invalid `data-history-results` JSON fails loudly without silently marking the page complete.

In `app/static/src/ts/modules/enrichment.test.ts`, I expanded live coverage from a single terminal success case to a two-poll continuity case that asserts `next_since` progression across poll ticks while still ending in the same shared-path UI state: summary row, detail link, copy-button enrichment, reputation/no-data rows, export enablement, and completion state. In `app/static/src/ts/modules/result-application.test.ts`, I tightened the shared coordinator proof around one mixed fixture containing context, reputation, and error items so ordering, no-data grouping, copy-button enrichment, dashboard counts, and detail-link injection are pinned at the shared seam itself. Finally, I strengthened `tests/test_history_routes.py` to assert the exact history-detail HTML contract the dispatcher depends on: `data-results-owner="history"`, `data-job-id="history"`, `data-mode="online"`, `data-provider-counts="{}"`, and the expected progress/export markup for replay pages.

## Verification

Ran the focused Vitest lane for `result-application.test.ts`, `history.test.ts`, and `enrichment.test.ts`, which passed and proved live/history DOM parity, history non-polling, malformed-history handling, and live `next_since` continuity. Ran `python3 -m pytest tests/test_history_routes.py -q`, which passed and pinned the rendered history-detail ownership contract. Ran `npx tsc --noEmit` and `make build`, which both passed, confirming the updated tests and existing frontend bundle compile cleanly under the slice verification contract.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts` | 0 | ✅ pass | 1163ms |
| 2 | `python3 -m pytest tests/test_history_routes.py -q` | 0 | ✅ pass | 1083ms |
| 3 | `npx tsc --noEmit` | 0 | ✅ pass | 685ms |
| 4 | `make build` | 0 | ✅ pass | 1600ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/history.test.ts`
- `app/static/src/ts/modules/enrichment.test.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- `tests/test_history_routes.py`
