---
id: T02
parent: S04
milestone: M017
key_files:
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/result-application.test.ts
key_decisions:
  - Use the existing verdict-snapshot gate as the smallest shared-path optimization instead of introducing new cached signatures or dirty-flag plumbing.
  - Keep the T01 regression tests as the proof surface for provider-only/no-op deltas skipping global dashboard recount/reorder and severity-changing deltas still updating counts/order.
duration: 
verification_result: passed
completed_at: 2026-05-13T17:45:01.760Z
blocker_discovered: false
---

# T02: Activated the existing shared result-application severity-change gate by removing the duplicate broad flush implementation that always recounted and reordered cards.

**Activated the existing shared result-application severity-change gate by removing the duplicate broad flush implementation that always recounted and reordered cards.**

## What Happened

Inspected the T01 result-application tests and the shared coordinator implementation. The narrow optimization already existed in an earlier `flush()` implementation: it snapshots card verdicts before and after dirty IOC flushes, then only calls `updateDashboardCounts()` and `sortCardsBySeverity()` when severity/order-affecting card state changes. However, a later duplicate `flush()` declaration in the same coordinator scope shadowed that optimized implementation and always ran the global dashboard recount and card reorder after every dirty flush. Removed the duplicate broad flush so live polling and history/detail replay both use the optimized shared path. The existing T01 tests now prove provider-only/no-op deltas preserve summaries/provider rows/copy/detail affordances while skipping unnecessary global work, and severity-changing deltas still update counts and order.

## Verification

Ran the focused result-application test file to verify the provider-only negative path and severity-changing positive path. Then ran the required full frontend test suite plus the two browser e2e suites for results and mocked-online EmailRep coverage. All checks passed: 12 focused TypeScript tests, 97 total TypeScript tests across 7 files, and 32 Python e2e tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npm test -- --run app/static/src/ts/modules/result-application.test.ts` | 0 | ✅ pass — 12 tests passed | 1008ms |
| 2 | `npm test -- --run && python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py` | 0 | ✅ pass — 7 frontend test files / 97 tests and 32 e2e tests passed | 17310ms |

## Deviations

Expected output listed several adjacent frontend modules, but only `app/static/src/ts/modules/result-application.ts` required a change because the optimization was already implemented there and merely shadowed by a duplicate function declaration.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/result-application.test.ts`
