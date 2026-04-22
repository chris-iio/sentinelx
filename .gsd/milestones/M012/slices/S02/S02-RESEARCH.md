# S02 Research — Shared result-application path for live and history views

## Summary

This is **targeted research**, not deep unknown-territory work. The codebase already has the right primitives: `row-factory.ts` owns DOM row construction, `cards.ts` owns card/dashboard state, and `shared-rendering.ts` already holds pure shared helpers. The missing piece is a **shared stateful result-application layer** between live polling and history replay.

The important finding is that S02 is not just about deduping some DOM code. History detail pages currently render `results.html` in `mode="online"` with `job_id="history"`, and `main.ts` initializes **both** `initEnrichment()` and `initHistory()` on that surface. That means the history page matches the live-poller guard, can start polling `/enrichment/status/history`, and also gets duplicate expand/export event wiring. The slice should fix that exclusivity bug while extracting one shared result-application path.

Per the loaded `write-docs` skill, this research is organized for a fresh planner: seams first, then constraints, then the smallest viable task split.

## Continuity Requirements This Slice Owns / Supports

Primary continuity to preserve while refactoring:

- **R008** — enrichment cards, detail rows, export, detail links, copy buttons, progress, and filtering must still work.
- **R009** — DOM updates must stay on the existing safe path (`createElement`, `textContent`, no `innerHTML` regression).
- **R010** — live-path debounced sorting / rendering behavior must remain unchanged or better.
- **R019** — cursor-based live polling semantics must remain intact; S02 should not rework polling.
- **R040** — refactor coverage must be explicit; parity needs tests, not just code dedupe.

Secondary support:

- S02 depends on S01’s additive terminal contract and must not regress it.

## Recommendation

### Recommended extraction boundary

Extract a **shared result-application module** for the work both paths already do:

- apply one `EnrichmentItem` into the right card/slot/section
- accumulate per-IOC verdict state
- update per-card verdict/copy summary when reputation data arrives
- finalize loaded slots / detail links / no-data summaries
- provide a per-IOC or end-of-pass flush step so live can debounce while history can run synchronously

Keep these concerns **outside** the shared core:

- live polling interval, `since` cursor, terminal-state handling, warning banners → stay in `enrichment.ts`
- history JSON parsing and “replay all results now” entry logic → stay in `history.ts`
- backend route/storage contract → stay unchanged unless needed for frontend guard clarity

### Module shape recommendation

Do **not** keep expanding `shared-rendering.ts` into a stateful coordinator. Its current role is pure/idempotent rendering helpers (`computeResultDisplay`, detail link injection, sort, export wiring). S02 needs a new module with a clearer name, something like:

- `result-application.ts`
- or `enrichment-apply.ts`

That new module should own the shared stateful path; `shared-rendering.ts` can remain the pure helper layer it already is.

### Mode exclusivity recommendation

Make live and history initialization **mutually exclusive**.

Current behavior is unsafe:

- `app/routes/history.py` renders history detail with `mode="online"` and `job_id="history"`
- `app/templates/results.html` therefore emits the same `.page-results` live attributes plus `data-history-results`
- `app/static/src/ts/main.ts` calls `initEnrichment()` and then `initHistory()` unconditionally
- `app/static/src/ts/modules/enrichment.ts` only guards on `data-mode="online"` + `data-job-id`

That means history detail pages satisfy the live guard and can start the polling loop. Since `/enrichment/status/history` is not a real job, S01’s terminal-404 path can surface a failure banner on a history page. On top of that, both `wireExpandToggles()` and `initExportButton()` are wired twice.

The slice should fix this directly. Smallest safe version: history presence (`data-history-results`) should prevent live poller init. Cleaner version: one top-level results-surface dispatcher decides whether the page is live or history and initializes only one mode.

## Implementation Landscape

### Shared surface contract

These files define the shared UI surface both modes already use:

- `app/templates/results.html`
  - single results-page DOM contract
  - history detail injects `data-history-results` on the same `.page-results` root
- `app/templates/partials/_ioc_card.html`
  - stable `.ioc-card` contract with `data-ioc-value`, `data-ioc-type`, `data-verdict`
- `app/templates/partials/_enrichment_slot.html`
  - stable slot/details/section container DOM both modes render into

This is a good seam. S02 should reuse this surface, not invent a second one.

### Live path today

`app/static/src/ts/modules/enrichment.ts` currently owns four different things at once:

1. **transport/runtime concerns**
   - polling interval
   - `since` cursor
   - terminal-state handling from S01
   - warning banners for 429/auth failures
2. **shared result application**
   - find card/slot
   - remove spinner, mark slot loaded
   - route rows to context/reputation/no-data sections
   - update summary row / card verdict / copy-button enrichment summary
3. **live-only coordination**
   - pending-provider indicator
   - debounced detail sorting
   - debounced summary-row rebuilds
4. **global completion UI**
   - finalize slots
   - mark progress complete
   - enable export

The slice should extract (2) and the reusable part of (4), but leave (1) and the live-only pieces of (3) in place.

### History path today

`app/static/src/ts/modules/history.ts` is structurally a second coordinator over the same DOM:

- parse `data-history-results`
- loop results synchronously
- run a near-duplicate of `renderEnrichmentResult()` via `replayResult()`
- do a second per-IOC pass for summary rows / card verdict / detail sort
- finalize slots / links / progress / export
- import `wireExpandToggles()` from `enrichment.ts`

This is the duplication seam the roadmap called out.

### Already-shared pieces worth preserving

These are already correct and should remain shared primitives rather than be re-inlined:

- `app/static/src/ts/modules/shared-rendering.ts`
  - `computeResultDisplay()`
  - `injectDetailLink()`
  - synchronous `sortDetailRows()`
  - `initExportButton()`
- `app/static/src/ts/modules/row-factory.ts`
  - `createContextRow()`
  - `createDetailRow()`
  - `updateSummaryRow()`
  - `updateContextLine()`
  - `injectSectionHeadersAndNoDataSummary()`
- `app/static/src/ts/modules/cards.ts`
  - `updateCardVerdict()`
  - `updateDashboardCounts()`
  - `sortCardsBySeverity()`

S02 should compose these; not replace them.

## Important Findings / Risks

### 1. History pages currently satisfy the live poller guard

Evidence:

- `app/routes/history.py` renders history detail with `mode="online"` and `job_id="history"`
- `app/templates/results.html` emits `data-job-id`, `data-mode`, and `data-history-results` on the same root
- `app/static/src/ts/main.ts` calls `initEnrichment()` and `initHistory()` back-to-back
- `app/static/src/ts/modules/enrichment.ts` only checks `.page-results`, `data-job-id`, and `data-mode === "online"`

Implication:

- history detail can start polling `/enrichment/status/history`
- S01’s explicit terminal failure path can then surface an incorrect “job not found”/evicted style banner on history pages
- even if that race is not commonly noticed, the code path is wrong and doubles work

This is the riskiest integration point in the slice and should be fixed first.

### 2. Event wiring is currently non-idempotent

Evidence:

- `wireExpandToggles()` adds click + keydown listeners on `.page-results`
- `initExportButton()` adds click listeners on the export button, export items, and document
- history pages currently call both init paths

Implication:

- expand/collapse handlers can be bound twice
- export handlers can be bound twice
- this is both a behavior bug and a future refactor trap

Do not paper over this with “it usually works.” Fix exclusivity or make shared wiring explicitly one-shot.

### 3. History replay does not currently set per-card copy-button enrichment text

Evidence:

- live path calls private `updateCopyButtonWorstVerdict()` after each reputation result
- history path never performs the equivalent update
- `clipboard.ts` uses optional `data-enrichment` on `.copy-btn` to include worst-verdict summary in copied text

Implication:

- history detail is not actually parity-complete today for copy-button behavior
- the shared result-application core should own this update so both modes inherit it

This is easy to miss if tests only assert summary rows and detail links.

### 4. Live and history do not want the same flush semantics

Live mode needs:

- debounced summary-row rebuilds
- debounced reputation-row sorting
- pending-provider indicator updates per result

History mode wants:

- no pending state
- synchronous batch apply
- one per-IOC finalize pass after replay

So the shared boundary should not be “one generic init function that hides everything.” It should be “one shared application core with pluggable flush/finalize semantics.”

### 5. Existing frontend tests do not pin history parity yet

Current coverage shape:

- `app/static/src/ts/modules/enrichment.test.ts` covers live terminal failure and live success-path continuity
- `app/static/src/ts/modules/row-factory.test.ts` covers DOM builders thoroughly
- `tests/test_history_routes.py` only covers backend/template contract (`data-history-results`, 200/404, counts)
- there is **no** dedicated `history.ts` Vitest coverage and no history-detail Playwright coverage

This means the shared-path refactor can regress history without tripping current frontend tests.

## Natural Task Split

### Task 1 — Extract shared result-application core

Primary files:

- new module under `app/static/src/ts/modules/` for shared result application
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`

Goal:

- move duplicated result-to-DOM coordination out of both modules
- keep live-only polling/runtime concerns local
- keep history parsing/replay loop local

Expected sub-seam inside the shared module:

- `applyResult(result, state, options)`
- `finalizeIoc(...)` or `flushIoc(...)`
- `finalizeView(...)`

The planner should keep this task frontend-only and avoid route/template churn unless the mode guard needs a small contract tweak.

### Task 2 — Fix mode exclusivity and shared wiring ownership

Primary files:

- `app/static/src/ts/main.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- possibly `app/templates/results.html` only if a clearer explicit mode marker helps

Goal:

- ensure history pages do not start the live poller
- ensure expand/export wiring happens once
- preserve S01 live terminal behavior on true live pages

Recommended bias:

- prefer a simple, explicit guard over a clever listener-dedup workaround

### Task 3 — Add parity tests around history replay

Primary files:

- new frontend Vitest coverage (either `history.test.ts` or tests for the new shared module)
- existing `app/static/src/ts/modules/enrichment.test.ts`
- `tests/test_history_routes.py`

Goal:

- prove the same result stream produces the same visible slot/card state in both live and history modes
- explicitly cover the history-only regression risks: no live poller, export enabled once, copy button enrichment text present, detail links injected, summary rows and verdict labels correct

## Verification Strategy

Fast proof for the slice should stay mostly frontend-local.

### Recommended verification commands

- `npx vitest run app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/row-factory.test.ts <new-history-or-shared-module-test>`
- `python3 -m pytest tests/test_history_routes.py -q`
- `npx tsc --noEmit`
- `make build`

If the executor adds focused route/template logic for exclusivity, this backend test layer is enough. Only add Playwright if the Vitest path cannot credibly prove history/live parity.

### What the tests should prove

At minimum, new frontend coverage should prove:

1. **Live mode still works**
   - terminal failure still stops polling and surfaces S01 text
   - success path still updates summary row, detail rows, card verdict, detail link, export enablement
2. **History mode reuses the same visible rendering path**
   - summary row appears
   - verdict label/card verdict match the replayed results
   - detail row lands in the correct section
   - detail link exists
   - progress shows complete
   - export button is enabled
   - copy button has `data-enrichment` parity
3. **History mode does not start live polling**
   - no fetch to `/enrichment/status/history`
   - no terminal warning banner from the live status route
   - no duplicate event wiring side effects

## Skill Discovery (suggested)

Directly relevant installed skills:

- `write-docs` — already used here for planner-first structure

No installed skill is a strong match for this specific vanilla TypeScript DOM seam.

External skills worth noting, but **not needed for this slice unless the user wants them**:

- Flask:
  - `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`
  - `npx skills add jezweb/claude-skills@flask`
- SQLite:
  - `npx skills add martinholovsky/claude-skills-generator@sqlite database expert`

These are more relevant to S04-style helper/persistence work than to S02’s frontend/shared-rendering seam.

## Planner Notes

- Treat S02 as a **frontend coordination slice with one real integration bug** (history pages accidentally look live to the poller).
- Do not spend the slice redesigning polling, storage, or route semantics.
- The low-regret win is: **one shared apply path, one mode owner per page, parity tests that prove history and live produce the same UI state from the same result stream.**
