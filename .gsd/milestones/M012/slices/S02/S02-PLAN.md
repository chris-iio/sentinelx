# S02: Shared result-application path for live and history views

**Goal:** Unify live polling and history replay behind one shared result-application path while making the results surface choose exactly one mode owner, so the same enrichment cards, detail rows, progress state, detail links, export gating, and copy-button summaries render from both live and stored data without duplicate polling or duplicate event wiring.
**Demo:** A user sees the same enrichment cards, detail rows, progress, and verdict rendering whether results arrive live or are replayed from history, with one shared application path carrying the behavior.

## Must-Haves

- ## Demo
- A user sees the same enrichment cards, detail rows, progress, verdict badges, detail links, export readiness, and copy-button enrichment text whether results stream in live or are replayed from history, and history pages never start the live `/enrichment/status/<job_id>` poller.
- ## Must-Haves
- Extract a shared stateful result-application module instead of growing `shared-rendering.ts` into a mixed pure/stateful helper.
- Keep live-only concerns local to `app/static/src/ts/modules/enrichment.ts`: polling cadence, `?since=` cursor handling, terminal-state handling from S01, and debounced live flush behavior.
- Keep history-only concerns local to `app/static/src/ts/modules/history.ts`: parsing `data-history-results`, replay entry, and synchronous completion.
- Make results-surface ownership exclusive so only one initializer owns expand/export wiring and runtime behavior on any given page.
- Preserve continuity requirements R008, R009, R010, and R019 while adding explicit parity proof for the refactor boundary (R040 support).
- ## Threat Surface
- **Abuse**: The main regression risk is an incorrect surface guard that makes history pages poll `/enrichment/status/history`, produces false terminal banners, or doubles click handlers; the plan must make mode ownership explicit and test it.
- **Data exposure**: No new sensitive data is introduced; this slice continues rendering only stored enrichment results already exposed on the history detail page.
- **Input trust**: Untrusted values still flow only through existing `createElement`/`textContent` row builders and safe attribute setters; the shared path must not introduce `innerHTML` or string-built DOM injection.
- ## Requirement Impact
- **Requirements touched**: R008, R009, R010, R019.
- **Re-verify**: live success-path rendering, cursor-based polling continuity, history replay parity, export enablement, detail-link injection, copy-button enrichment summaries, and no accidental live polling on history pages.
- **Decisions revisited**: D050 and D052 inform the slice; no roadmap-order change is needed, but the extraction boundary must follow the low-regret/shared-proof intent they set.
- ## Verification
- `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts`
- `python3 -m pytest tests/test_history_routes.py -q`
- `npx tsc --noEmit`
- `make build`

## Proof Level

- This slice proves: - This slice proves: integration
- Real runtime required: no
- Human/UAT required: no

## Integration Closure

- Upstream surfaces consumed: S01 additive terminal polling contract in `app/static/src/ts/modules/enrichment.ts`, the shared results-page DOM contract in `app/templates/results.html` and `app/templates/partials/_ioc_card.html`, and the existing pure helpers in `app/static/src/ts/modules/shared-rendering.ts`, `app/static/src/ts/modules/row-factory.ts`, and `app/static/src/ts/modules/cards.ts`.
- New wiring introduced in this slice: a dedicated shared result-application module composed by both `enrichment.ts` and `history.ts`, plus one explicit results-surface ownership path from `app/static/src/ts/main.ts` / `.page-results` so live and history initialization cannot run together.
- What remains before the milestone is truly usable end-to-end: nothing for this seam once parity tests and build/typecheck proof pass.

## Verification

- Runtime signals: `.page-results` surface ownership markers, progress/warning/export DOM state, and fetch-call behavior in focused frontend tests.
- Inspection surfaces: `app/templates/results.html` rendered attributes, Vitest fetch spies in `history.test.ts` / `enrichment.test.ts`, and visible detail-link / summary-row / copy-button state in the DOM.
- Failure visibility: accidental `/enrichment/status/history` fetches, duplicate event wiring, and missing parity updates become explicit test failures instead of latent UI drift.
- Redaction constraints: keep existing stored-result exposure unchanged; no new secrets or provider credentials enter the client.

## Tasks

- [x] **T01: Extract a shared result-application coordinator for live and history rendering** `est:0.75d`
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
  - Files: `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/history.ts`, `app/static/src/ts/modules/shared-rendering.ts`, `app/static/src/ts/modules/result-application.test.ts`
  - Verify: npx vitest run app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit

- [ ] **T02: Make results-surface ownership exclusive and wire shared runtime hooks once** `est:0.5d`
  Fix the integration bug where history detail pages satisfy the live poller guard and can start polling `/enrichment/status/history`, then receive duplicate expand/export listener wiring. The smallest acceptable outcome is exclusive ownership; the preferred outcome is an explicit results-surface dispatcher that chooses exactly one owner for the page.

Use `app/static/src/ts/main.ts` and the `.page-results` contract as the composition boundary. If the template/route layer needs an explicit owner marker to make the dispatch unambiguous, add it in `app/templates/results.html` and `app/routes/history.py` without changing the analyst-visible successful online/history behavior. Preserve S01’s terminal contract on true live pages and keep history replay additive over stored results rather than inventing a second UI surface.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `.page-results` ownership attributes in `app/templates/results.html` | Fall back to a single safe owner; never run both initializers | N/A | Treat ambiguous pages as non-live unless the live contract is complete |
| `app/routes/history.py` history-detail template context | Keep stored results rendering working even if a new owner flag is absent | N/A | Prefer explicit template markers over string-matching `job_id` hacks |
| Shared event wiring (`wireExpandToggles`, export dropdown setup) | Wire once per page load; avoid dedup-by-accident listener behavior | N/A | If ownership is ambiguous, skip the second initializer instead of double-binding handlers |

## Load Profile

- **Shared resources**: browser event listeners on `.page-results`, export dropdown/document click listeners, and the live poll interval.
- **Per-operation cost**: one owner decision per page load; zero additional runtime work after initialization.
- **10x breakpoint**: duplicate listeners and accidental polling loops on history pages; the dispatcher must cap this at one owner and one listener set.

## Negative Tests

- **Malformed inputs**: `.page-results` with `data-history-results` but no job id, `.page-results` with a live job id but no history payload, and ambiguous owner attributes.
- **Error paths**: history pages receiving a terminal 404 payload if live polling leaks through, duplicate export dropdown toggles, and duplicate summary-row expand events.
- **Boundary conditions**: true live page, true history page, empty history payload, and results page with no `.page-results` root.

## Steps

1. Decide the ownership contract for `.page-results` (explicit owner marker preferred; `data-history-results` guard acceptable only if it stays obvious in tests) and update `app/templates/results.html` / `app/routes/history.py` only as much as needed to express it clearly.
2. Refactor `app/static/src/ts/main.ts` so results pages dispatch to exactly one initializer instead of always calling both `initEnrichment()` and `initHistory()`.
3. Update `app/static/src/ts/modules/enrichment.ts` and `app/static/src/ts/modules/history.ts` so expand/export wiring is owned by the active surface once, while true live pages still preserve the S01 polling/terminal-state behavior.
4. Rebuild the frontend bundle to confirm the new composition path compiles cleanly.

## Must-Haves

- [ ] History detail pages never fetch `/enrichment/status/history`.
- [ ] Expand/collapse and export listeners are owned by one initializer per page load.
- [ ] True live pages still poll on the 750ms cursor path and keep S01 terminal-failure handling intact.
- [ ] Any template/route contract tweak stays additive and does not create a second results-page DOM shape.

## Verification

- `npx tsc --noEmit`
- `make build`
  - Files: `app/static/src/ts/main.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/history.ts`, `app/templates/results.html`, `app/routes/history.py`
  - Verify: npx tsc --noEmit && make build

- [ ] **T03: Prove live/history parity and history non-polling with focused frontend and route tests** `est:0.75d`
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
  - Files: `app/static/src/ts/modules/result-application.test.ts`, `app/static/src/ts/modules/history.test.ts`, `app/static/src/ts/modules/enrichment.test.ts`, `tests/test_history_routes.py`
  - Verify: npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts && python3 -m pytest tests/test_history_routes.py -q && npx tsc --noEmit && make build

## Files Likely Touched

- app/static/src/ts/modules/result-application.ts
- app/static/src/ts/modules/enrichment.ts
- app/static/src/ts/modules/history.ts
- app/static/src/ts/modules/shared-rendering.ts
- app/static/src/ts/modules/result-application.test.ts
- app/static/src/ts/main.ts
- app/templates/results.html
- app/routes/history.py
- app/static/src/ts/modules/history.test.ts
- app/static/src/ts/modules/enrichment.test.ts
- tests/test_history_routes.py
