---
estimated_steps: 24
estimated_files: 8
skills_used:
  - test
  - verify-before-complete
---

# T01: Cache stable IOC DOM handles inside the shared result-application coordinator

Design and implement the narrow frontend hot-path fix that S01/S03 left queued: cache the stable per-IOC DOM handles once inside `createResultApplicationCoordinator()` and reuse them for both live polling and history replay instead of repeating `findCardForIoc()` / `.querySelector()` / provider-count parsing on every incoming result. Keep the work coordinator-local so S04 does not reopen polling cadence, owner resolution, or backend status semantics.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Server-rendered card/slot structure in `app/templates/results.html` + partials | Fail soft by skipping the IOC when a card/slot is genuinely absent; never throw and break the whole polling/history pass | N/A | Treat missing optional handles as absent and preserve the current graceful no-op behavior |
| Shared `cards.ts` helpers and verdict/dashboard/sort semantics | Keep verdict text/count/sort outcomes identical; if a new helper is needed, make it additive and keep selector contracts unchanged | Debounced sorting must still settle within the existing 100ms flush behavior | Do not let cache state drift from the actual DOM node identity after filtering/sorting re-append operations |
| Page-level provider-count metadata from `data-provider-counts` | Fall back to the existing default counts when the attribute is absent or invalid | N/A | Parse once and preserve the current fallback behavior for malformed JSON |

## Load Profile

- **Shared resources**: the `.ioc-card` grid, per-card `.enrichment-slot` subtree, copy buttons, pending-indicator text, and the shared debounce/sort path.
- **Per-operation cost**: target one IOC-map lookup plus local node reuse per result, instead of repeated whole-document selectors and repeated provider-count JSON parsing.
- **10x breakpoint**: repeated `querySelector` work across every result and every flush; the task fails if the coordinator still re-discovers stable card/slot handles or reparses page metadata on the hot path.

## Negative Tests

- **Malformed inputs**: missing card for an IOC, missing slot, missing provider-count attribute, and malformed provider-count JSON.
- **Error paths**: context-only results, provider error rows, and repeated results for the same IOC that must still converge on the correct worst verdict/copy text.
- **Boundary conditions**: one IOC with multiple providers, multiple IOC cards, history replay using the same coordinator path, and finalize after no-data/mixed-detail rows.

## Steps

1. Add a coordinator-local cache keyed by IOC value that captures the stable DOM nodes and provider-count snapshot once, while keeping dynamic nodes like summary rows and detail links created lazily through the existing row builders.
2. Route `apply()`, `flushIoc()`, and `finalize()` through those cached handles so live polling and history replay share the cheaper path without changing sorting/filtering/detail-link/copy/progress behavior.
3. Extend the focused Vitest coverage to prove live/history parity, provider-count fallback behavior, and finalize/link/copy continuity on the cached path.

## Must-Haves

- [ ] Stable IOC DOM handles are discovered once and reused across `apply()`, `flush()`, and `finalize()`.
- [ ] Provider-count parsing happens once per coordinator/page and preserves the current fallback semantics.
- [ ] Live polling and history replay still produce the same loaded-slot, summary-row, context/detail, copy-button, and detail-link outcomes.
- [ ] The task does not change owner resolution, polling cadence, route payload shape, or DOM-safety discipline.

## Inputs

- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/cards.ts``
- ``app/static/src/ts/types/ioc.ts``
- ``app/static/src/ts/modules/result-application.test.ts``
- ``app/static/src/ts/modules/enrichment.test.ts``
- ``app/static/src/ts/modules/history.test.ts``
- ``app/static/src/ts/modules/main.test.ts``
- ``app/templates/results.html``
- ``app/templates/partials/_ioc_card.html``
- ``app/templates/partials/_enrichment_slot.html``

## Expected Output

- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/result-application.test.ts``
- ``app/static/src/ts/modules/enrichment.test.ts``
- ``app/static/src/ts/modules/history.test.ts``

## Verification

npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts

## Observability Impact

- Signals added/changed: cheaper coordinator-local handle reuse while keeping `.enrichment-slot--loaded`, summary rows, pending text, and verdict/dashboard state unchanged.
- How a future agent inspects this: run the focused Vitest suite and inspect the coordinator cache path in `app/static/src/ts/modules/result-application.ts`.
- Failure state exposed: regressions localize to cached-handle misses, stale pending counts, or finalize/link/copy drift instead of ambiguous polling transport behavior.
