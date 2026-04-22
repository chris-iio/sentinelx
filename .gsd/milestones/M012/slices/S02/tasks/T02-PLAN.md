---
estimated_steps: 29
estimated_files: 5
skills_used: []
---

# T02: Make results-surface ownership exclusive and wire shared runtime hooks once

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

## Inputs

- ``app/static/src/ts/main.ts` — current unconditional initializer order that runs both live and history modules`
- ``app/static/src/ts/modules/enrichment.ts` — live guard and shared event-wiring owner today`
- ``app/static/src/ts/modules/history.ts` — history replay init that currently re-wires expand/export behavior`
- ``app/templates/results.html` — `.page-results` contract used by both live and history detail pages`
- ``app/routes/history.py` — history detail route that currently renders `mode="online"` with `job_id="history"``

## Expected Output

- ``app/static/src/ts/main.ts` — exclusive results-surface dispatcher`
- ``app/static/src/ts/modules/enrichment.ts` — live initializer updated to assume exclusive ownership`
- ``app/static/src/ts/modules/history.ts` — history initializer updated to assume exclusive ownership`
- ``app/templates/results.html` — explicit/additive surface-owner marker if required`
- ``app/routes/history.py` — history detail context aligned with the exclusive ownership contract`

## Verification

npx tsc --noEmit && make build

## Observability Impact

- Signals added/changed: page-ownership markers and one-owner initialization behavior.
- How a future agent inspects this: inspect `.page-results` attributes in rendered HTML and use frontend tests/fetch spies to verify that only one initializer runs.
- Failure state exposed: accidental history polling and duplicate listener binding become visible through a single owner decision instead of silent UI flakiness.
