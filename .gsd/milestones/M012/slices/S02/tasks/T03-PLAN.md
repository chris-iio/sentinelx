---
estimated_steps: 31
estimated_files: 4
skills_used: []
---

# T03: Prove live/history parity and history non-polling with focused frontend and route tests

Add the parity proof this refactor currently lacks. The slice is not done when code is deduplicated; it is done when tests prove that the same result stream drives the same visible card/slot state in both live and history flows, and that history pages never leak into the live status poller.

Prefer focused automated coverage over broad manual proof. Use a new `history.test.ts` for history replay/runtime ownership assertions, extend `enrichment.test.ts` and/or `result-application.test.ts` where the shared path needs continuity assertions, and update `tests/test_history_routes.py` to pin the template/route contract the frontend relies on.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Vitest DOM/fetch mocks for live/history surfaces | Fail loudly; do not treat missing fetch assertions as pass | N/A | Normalize fixtures to real `EnrichmentItem` shapes so tests model production behavior |
| Flask history-detail route contract in `tests/test_history_routes.py` | Catch contract drift before frontend replay silently changes owners | N/A | Assert the exact rendered attributes the frontend dispatcher depends on |
| Shared coordinator tests from T01 | Extend rather than duplicate; keep parity expectations centralized | N/A | Add fixture variants for context rows, reputation rows, and copy-button enrichment text |

## Load Profile

- **Shared resources**: test-time DOM rendering, fetch spies, and the build/typecheck lane.
- **Per-operation cost**: one focused Vitest lane plus one focused pytest module; no real provider/network calls.
- **10x breakpoint**: parity tests that assert only presence can miss ordering/summary regressions, so the suite must assert rendered text, verdict state, export enablement, and non-polling behavior explicitly.

## Negative Tests

- **Malformed inputs**: invalid `data-history-results` JSON, empty result arrays, and result streams containing `error` items.
- **Error paths**: history page accidentally polling `/enrichment/status/history`, terminal warning banner appearing on history reload, and missing copy-button `data-enrichment` after replay.
- **Boundary conditions**: one-IOC replay, mixed reputation/context providers, and complete live polling with `next_since` continuity still intact.

## Steps

1. Add `app/static/src/ts/modules/history.test.ts` covering history replay through the shared module, export enablement, detail-link injection, progress completion, copy-button enrichment parity, and zero fetches to `/enrichment/status/history`.
2. Extend `app/static/src/ts/modules/enrichment.test.ts` and/or `app/static/src/ts/modules/result-application.test.ts` so live continuity and shared-path parity are both pinned from the same result fixtures.
3. Update `tests/test_history_routes.py` to assert the rendered history-detail ownership contract and any additive template markers the dispatcher needs.
4. Run the full slice verification commands and leave the plan with executable proof, not just compile confidence.

## Must-Haves

- [ ] Frontend tests prove history replay renders the same visible summary/detail/verdict/progress/export/copy-button state as the shared live path for equivalent results.
- [ ] Frontend tests prove history pages do not poll `/enrichment/status/history` and do not surface false terminal banners.
- [ ] Route tests pin the rendered HTML contract the exclusive-owner dispatcher depends on.
- [ ] The slice-level verification commands all pass after the refactor.

## Verification

- `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts`
- `python3 -m pytest tests/test_history_routes.py -q`
- `npx tsc --noEmit`
- `make build`

## Inputs

- ``app/static/src/ts/modules/result-application.ts` — shared coordinator extracted in T01`
- ``app/static/src/ts/modules/enrichment.ts` — live owner after T01/T02 refactor`
- ``app/static/src/ts/modules/history.ts` — history owner after T01/T02 refactor`
- ``app/static/src/ts/modules/enrichment.test.ts` — existing live polling continuity baseline from S01`
- ``tests/test_history_routes.py` — current history route/template contract coverage`

## Expected Output

- ``app/static/src/ts/modules/history.test.ts` — focused history replay and non-polling regression coverage`
- ``app/static/src/ts/modules/result-application.test.ts` — expanded shared-path parity coverage`
- ``app/static/src/ts/modules/enrichment.test.ts` — updated live continuity assertions after the shared-path extraction`
- ``tests/test_history_routes.py` — route assertions for the rendered history ownership contract`

## Verification

npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts && python3 -m pytest tests/test_history_routes.py -q && npx tsc --noEmit && make build

## Observability Impact

- Signals added/changed: explicit fetch-call assertions, DOM-state parity assertions, and rendered HTML-owner contract assertions.
- How a future agent inspects this: run the named Vitest lane plus `python3 -m pytest tests/test_history_routes.py -q` to localize whether a regression is in shared application, history dispatch, or Flask/template wiring.
- Failure state exposed: parity drift, accidental live polling on history pages, and missing export/detail/copy-button state become targeted test failures.
