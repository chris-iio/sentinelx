---
estimated_steps: 4
estimated_files: 4
skills_used:
  - tdd
  - verify-before-complete
---

# T02: Prove EmailRep renders through shared result application

Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.

Add shared-rendering proof that a configured email card receives an EmailRep result through `createResultApplicationCoordinator()` and ends in the same UI surfaces used by live polling and history replay. This task closes S03 at fixture-level integration and refreshes the JS bundle after the TypeScript source change.

## Steps
1. Extend `app/static/src/ts/modules/result-application.test.ts` with an email-card fixture (`data-ioc-type="email"`, `data-provider-counts='{"email":1}'`) and an `EmailRep` result containing representative compact `raw_stats`.
2. Apply the result through `createResultApplicationCoordinator().apply(...)`, then `flush()`/`finalize()`, and assert EmailRep appears under `.enrichment-section--reputation` rather than `.enrichment-section--context` or no-data.
3. Assert the visible surfaces a stakeholder would scan: `.verdict-label` updates to the EmailRep verdict, `.ioc-summary-row` attributes EmailRep, the provider row shows compact risk/reputation fields, and the waiting indicator is removed when the single email provider returns.
4. Assert the rendered DOM does not contain raw nested dumps or `[object Object]`, then run focused Vitest, full TypeScript typecheck, and `make js` so `app/static/dist/main.js` includes the row-factory wiring.

## Must-Haves
- [ ] Shared coordinator test proves EmailRep uses the same live/history result-application path as other reputation providers.
- [ ] EmailRep rows are sorted/rendered in the reputation section and still contribute to summary/verdict state.
- [ ] Email provider-count metadata (`{"email":1}`) is honored so the pending indicator clears after the EmailRep fixture.
- [ ] The test uses deterministic inline fixtures only; no live EmailRep key or network call.
- [ ] `app/static/dist/main.js` is refreshed by the JS build after TypeScript changes.

## Failure Modes
| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `createResultApplicationCoordinator()` shared DOM wiring | Test should fail with missing summary/verdict/provider row rather than silently passing row-factory-only proof | Not applicable; coordinator operations are synchronous in Vitest | Malformed raw_stats should still render the row and omit unsafe fields |
| `data-provider-counts` email metadata | Waiting indicator may remain stale; test should catch incorrect provider-count handling | Not applicable | Malformed metadata fallback is covered by existing tests and must not be changed here |

## Load Profile
- **Shared resources**: Per-IOC in-memory verdict arrays, handle cache, and DOM updates in the shared coordinator.
- **Per-operation cost**: One coordinator apply/flush per EmailRep result in the fixture; no polling interval or route changes.
- **10x breakpoint**: Large result batches rely on existing dirty-IOC batching and summary debounce outside this task; this task must not add extra polling or rebuild loops.

## Negative Tests
- **Malformed inputs**: Fixture includes at least one unknown nested raw_stats field and asserts it does not surface as raw object text.
- **Error paths**: EmailRep must not be treated as a context-only provider, because that would bypass summary/verdict updates.
- **Boundary conditions**: A single configured email provider should clear `enrichment-waiting-text`; script-like values remain text.

## Inputs
- `app/static/src/ts/modules/result-application.test.ts` — shared coordinator fixture tests.
- `app/static/src/ts/modules/row-factory.test.ts` — focused row-builder proof from T01.
- `app/static/src/ts/modules/row-factory.ts` — EmailRep field mapping produced by T01.
- `Makefile` — `js` and `typecheck` commands.

## Expected Output
- `app/static/src/ts/modules/result-application.test.ts` — EmailRep shared-rendering fixture test.
- `app/static/dist/main.js` — rebuilt browser bundle containing EmailRep row-factory mapping.

## Inputs

- `app/static/src/ts/modules/result-application.test.ts`
- `app/static/src/ts/modules/row-factory.test.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `Makefile`

## Expected Output

- `app/static/src/ts/modules/result-application.test.ts`
- `app/static/dist/main.js`

## Verification

npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit && make js

## Observability Impact

Signals changed: no new runtime diagnostics are added, but the shared coordinator test makes the user-facing diagnostics inspectable through existing DOM state (`.ioc-summary-row`, `.verdict-label`, `.enrichment-section--reputation`, `.enrichment-waiting-text`). Future agents can localize failures by running the focused Vitest command before escalating to S04 browser E2E.
