---
id: T02
parent: S04
milestone: M003
provides:
  - All M003 gates verified passing — typecheck clean, bundle ≤ 30KB, 817 unit tests 0 failures, 105 E2E tests 0 failures
key_files:
  - tests/test_otx.py
  - tests/test_routes.py
key_decisions:
  - Updated OTX supported_types assertion from 8→9 to reflect IOCType.EMAIL added in S02; OTX adapter uses frozenset(IOCType) so it inherits all members automatically
  - Relaxed HTML occurrence count from <10 to <20 in test_analyze_deduplicates; the dedup guarantee is about separate IOC entries, not total HTML string occurrences — richer M002/M003 template markup produces ~12 occurrences of the IP string legitimately
patterns_established:
  - When using frozenset(IOCType) in adapters, all downstream count assertions must be updated whenever new IOCType members are added
observability_surfaces:
  - "python3 -m pytest tests/ -q --ignore=tests/e2e → 817 passed (0 failures)"
  - "python3 -m pytest tests/e2e/ -q → 105 passed (0 failures)"
  - "make typecheck → exit 0"
  - "wc -c app/static/dist/main.js → 26783 bytes ≤ 30000"
duration: ~3m
verification_result: passed
completed_at: 2026-03-20T06:20:00+09:00
blocker_discovered: false
---

# T02: Fix pre-existing test failures and verify all M003 gates

**Fixed two hardcoded test assertions broken by IOCType.EMAIL addition (8→9 for OTX, <10→<20 for HTML dedup count); all 4 M003 gates confirmed passing — 817 unit tests, 105 E2E tests, typecheck clean, bundle 26,783 bytes.**

## What Happened

Two surgical test fixes, no production code changes:

1. **`tests/test_otx.py` line ~196:** Updated `test_all_eight_ioc_types_supported` — docstring, assertion, and error message all changed from `8` to `9`. `OTXAdapter.supported_types` uses `frozenset(IOCType)` which now contains 9 members after S02 added `IOCType.EMAIL`.

2. **`tests/test_routes.py` line ~194:** Relaxed `assert count < 10` to `assert count < 20` in `test_analyze_deduplicates`. The richer M002/M003 template emits ~12 occurrences of the canonical IP string in rendered HTML (data attributes, detail sections, aria labels, etc.). The dedup invariant being tested is that a duplicate-submitted IP doesn't produce multiple separate IOC rows — not that the string appears fewer than 10 times in the full HTML document. Comment updated to make this explicit.

## Verification

- Targeted tests confirmed passing individually before running full suites
- Unit + integration suite: 817 passed, 0 failures
- E2E suite: 105 passed, 0 failures
- TypeScript typecheck: exit 0
- Bundle size: 26,783 bytes ≤ 30,000 gate

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_otx.py::TestOTXProtocol::test_all_eight_ioc_types_supported -v` | 0 | ✅ pass | <1s |
| 2 | `python3 -m pytest tests/test_routes.py::test_analyze_deduplicates -v` | 0 | ✅ pass | <1s |
| 3 | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 0 (817 passed) | ✅ pass | 4.1s |
| 4 | `python3 -m pytest tests/e2e/ -q` | 0 (105 passed) | ✅ pass | 36.7s |
| 5 | `make typecheck` | 0 | ✅ pass | 2.7s |
| 6 | `wc -c app/static/dist/main.js` → 26783 ≤ 30000 | 0 | ✅ pass | <1s |

## Diagnostics

- All M003 gate commands can be re-run verbatim to confirm status
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` → 4 (T01 signal, still valid)
- No new runtime signals introduced by this task (test-only changes)

## Deviations

None — implementation followed the plan exactly.

## Known Issues

None.

## Observability Impact

This task introduces no new runtime signals. The signals it validates:
- **Test suite health:** `python3 -m pytest tests/ -q` is the authoritative pass/fail surface for unit + integration correctness. A future regression in `OTXAdapter.supported_types` will immediately surface here.
- **E2E coverage:** `python3 -m pytest tests/e2e/ -q` covers full user-visible flows; 105 tests passing is the M003 baseline.
- **Failure state:** If a new `IOCType` member is added without updating `test_otx.py`, the assertion `len(OTXAdapter.supported_types) == 9` will fail with a message like `Expected 9 supported types, got 10: frozenset({...})` — self-describing.
- **Dedup assertion:** If template markup grows further, the `< 20` threshold may need a future bump. The comment in `test_routes.py` documents the intent so the next agent knows what to adjust.

## Files Created/Modified

- `tests/test_otx.py` — updated `test_all_eight_ioc_types_supported`: docstring + assertion + error message changed from 8 to 9
- `tests/test_routes.py` — relaxed HTML occurrence threshold from `< 10` to `< 20` with clarified comment
