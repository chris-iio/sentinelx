---
id: T02
parent: S02
milestone: M012
key_files:
  - app/static/src/ts/main.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/modules/shared-rendering.ts
  - app/templates/results.html
  - app/routes/history.py
  - app/static/src/ts/modules/main.test.ts
  - app/static/src/ts/modules/history.test.ts
  - app/static/src/ts/modules/enrichment.test.ts
  - tests/test_history_routes.py
key_decisions:
  - Made `.page-results[data-results-owner]` the authoritative ownership contract and treated malformed explicit live markers as non-live/static instead of falling back to polling.
  - Kept history detail pages on the existing online-mode DOM shape for UI parity, but required the owner marker rather than `data-job-id` to decide runtime ownership.
  - Made expand/export listener wiring idempotent with page-root markers so duplicate initializer calls cannot double-bind handlers by accident.
duration: 
verification_result: passed
completed_at: 2026-04-22T06:13:00.163Z
blocker_discovered: false
---

# T02: Made results-surface ownership explicit so only one runtime initializes each results page and history pages no longer leak live polling or duplicate listener wiring.

**Made results-surface ownership explicit so only one runtime initializes each results page and history pages no longer leak live polling or duplicate listener wiring.**

## What Happened

I added an additive `data-results-owner` contract to `app/templates/results.html` and set history detail pages to `results_owner="history"` in `app/routes/history.py` while preserving the existing online-mode DOM shape and `job_id="history"` parity. In the frontend, `app/static/src/ts/main.ts` now resolves exactly one results-surface owner, records the resolved owner on `.page-results`, and dispatches to either live enrichment or history replay instead of unconditionally starting both modules. I then hardened `app/static/src/ts/modules/enrichment.ts` and `app/static/src/ts/modules/history.ts` so each module defensively verifies ownership before doing work, sets runtime markers, resets its export buffer on init, and uses one-time expand/export wiring markers so duplicate listeners cannot accumulate even if an initializer is invoked twice. I also updated `app/static/src/ts/modules/shared-rendering.ts` so export dropdown wiring is idempotent at the page root, added focused Vitest coverage for dispatcher ownership, history replay no-poll behavior, empty-history handling, and duplicate toggle/export prevention, and extended `tests/test_history_routes.py` to assert the rendered history owner marker in server HTML.

## Verification

Ran focused frontend tests with `npx vitest run app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts` to prove exclusive dispatch, no `/enrichment/status/history` polling on history pages, empty-history completion behavior, and one-time expand/export wiring. Ran `pytest tests/test_history_routes.py` to confirm the history route still renders correctly and now advertises `data-results-owner="history"`. Ran `npx tsc --noEmit` and `make build` to verify the TypeScript composition path compiles cleanly and the production bundle rebuilds successfully.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts` | 0 | ✅ pass | 3900ms |
| 2 | `pytest tests/test_history_routes.py` | 0 | ✅ pass | 5100ms |
| 3 | `npx tsc --noEmit` | 0 | ✅ pass | 3900ms |
| 4 | `make build` | 0 | ✅ pass | 5100ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/main.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- `app/static/src/ts/modules/shared-rendering.ts`
- `app/templates/results.html`
- `app/routes/history.py`
- `app/static/src/ts/modules/main.test.ts`
- `app/static/src/ts/modules/history.test.ts`
- `app/static/src/ts/modules/enrichment.test.ts`
- `tests/test_history_routes.py`
