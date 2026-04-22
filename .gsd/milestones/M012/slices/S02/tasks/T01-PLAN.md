---
estimated_steps: 29
estimated_files: 5
skills_used: []
---

# T01: Extract a shared result-application coordinator for live and history rendering

Create a new stateful coordinator module, `app/static/src/ts/modules/result-application.ts`, that owns the shared "apply one `EnrichmentItem` into the cards/slots" path both live polling and history replay need. Keep transport/runtime concerns out of the shared core: `enrichment.ts` must continue to own `?since=` polling, terminal-state handling, warning banners, pending-indicator cadence, and debounced flush timing; `history.ts` must continue to own history JSON parsing and synchronous replay entry.

Move the duplicated DOM coordination into the shared module: finding the target card/slot, routing rows into context/reputation/no-data sections, tracking per-IOC verdict entries, updating summary rows, updating card verdicts, injecting copy-button `data-enrichment`, and exposing explicit flush/finalize hooks that let live stay debounced while history stays synchronous. Keep `shared-rendering.ts` focused on pure helpers; do not turn it into a module-private state bucket.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/templates/partials/_ioc_card.html` / `.enrichment-slot` DOM contract | Return early without throwing; do not break unrelated IOC cards | N/A | Ignore the single bad card/slot and let remaining cards render |
| Shared helpers in `row-factory.ts`, `cards.ts`, and `shared-rendering.ts` | Keep the coordinator thin so helper-local failures remain localized and testable | N/A | Do not widen helper inputs; normalize before calling them |
| `EnrichmentItem` payload shape from existing API/history data | Preserve discriminated-union handling for `result` vs `error` | N/A | Route malformed items to no-op behavior rather than unsafe DOM writes |

## Load Profile

- **Shared resources**: browser DOM mutation budget, per-IOC verdict maps, and live-mode debounce timers that remain owned by `enrichment.ts`.
- **Per-operation cost**: one card lookup, one slot mutation, one verdict-map update, and optional summary/sort flush scheduling per result.
- **10x breakpoint**: repeated summary rebuilds and detail-row resorting during bursts; the shared module must preserve a pluggable flush boundary so live mode does not regress into per-result thrash.

## Negative Tests

- **Malformed inputs**: missing card/slot elements, `error` results, and context-only providers with incomplete stats.
- **Error paths**: copy-button target absent, summary-row rebuild with no reputation entries, and no-data/error rows mixed with reputation rows.
- **Boundary conditions**: first result for an IOC, context-only IOC, repeated results for the same IOC, and final flush after the last provider.

## Steps

1. Read the duplicated application logic in `app/static/src/ts/modules/enrichment.ts` and `app/static/src/ts/modules/history.ts`, then define the smallest shared state/option shape that supports both live and history without hiding runtime ownership.
2. Implement `app/static/src/ts/modules/result-application.ts` with explicit apply/flush/finalize helpers that compose `row-factory.ts`, `cards.ts`, `verdict-compute.ts`, and `shared-rendering.ts`.
3. Refactor `enrichment.ts` and `history.ts` to consume the new coordinator while keeping live-only debounce/polling behavior and history-only replay timing outside the shared module.
4. Add focused unit coverage for the new coordinator so summary rows, detail routing, verdict updates, and copy-button enrichment parity are pinned before mode wiring changes land.

## Must-Haves

- [ ] `app/static/src/ts/modules/result-application.ts` becomes the only stateful result-application owner shared by live and history flows.
- [ ] Copy-button `data-enrichment` updates move into the shared path so history replay gains the same summary text live mode already has.
- [ ] `shared-rendering.ts` stays a pure helper layer; stateful coordination does not get pushed into it.
- [ ] The shared module exposes a flush/finalize seam that live and history can call with different timing semantics.

## Verification

- `npx vitest run app/static/src/ts/modules/result-application.test.ts`
- `npx tsc --noEmit`

## Inputs

- ``app/static/src/ts/modules/enrichment.ts` — current live polling owner with the duplicated result-application path and S01 terminal handling`
- ``app/static/src/ts/modules/history.ts` — current history replay coordinator with near-duplicate DOM application logic`
- ``app/static/src/ts/modules/shared-rendering.ts` — existing pure shared helpers that should stay pure`
- ``app/static/src/ts/modules/row-factory.ts` — DOM row builders and section/header helpers used by both modes`
- ``app/static/src/ts/modules/cards.ts` — card verdict/dashboard update helpers`
- ``app/templates/partials/_ioc_card.html` — stable slot/card DOM contract the shared module must target`

## Expected Output

- ``app/static/src/ts/modules/result-application.ts` — new shared stateful result-application coordinator for live and history`
- ``app/static/src/ts/modules/enrichment.ts` — live path refactored to call the coordinator without losing polling or debounce ownership`
- ``app/static/src/ts/modules/history.ts` — history replay refactored to call the same coordinator synchronously`
- ``app/static/src/ts/modules/result-application.test.ts` — focused unit proof for shared apply/flush/finalize behavior`

## Verification

npx vitest run app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

## Observability Impact

- Signals added/changed: shared apply/finalize behavior becomes directly observable through dedicated unit tests and DOM state assertions.
- How a future agent inspects this: run `npx vitest run app/static/src/ts/modules/result-application.test.ts` and inspect DOM assertions for summary rows, detail routing, and copy-button attributes.
- Failure state exposed: parity gaps between live/history rendering logic fail in one shared test target instead of hiding in two diverging modules.
