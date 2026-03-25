# S01: Analysis History & Persistence

**Goal:** Persist every online analysis run to SQLite (HistoryStore), display recent analyses on the home page, and reload full results from stored data via /history/<id>.
**Demo:** Analyst submits IOCs in online mode, sees results, closes the tab, returns to the home page, sees past analysis in the recent list, clicks it, and the full results page reloads from stored data.

## Must-Haves

- **Must-Haves:**
- `HistoryStore` class with `save_analysis()`, `list_recent()`, `load_analysis()` following the CacheStore SQLite WAL-mode pattern
- Every online analysis saved to history after enrichment completes (thread target wraps `enrich_all` + `save_analysis`)
- `/history/<analysis_id>` route loads stored data and renders `results.html` with full enrichment results
- Home page (`/`) shows recent analyses list with timestamp, IOC count, and top verdict
- Clicking a recent analysis navigates to `/history/<id>` and displays complete results
- A JS `history.ts` module reads `data-history-results` from the page and replays results through the existing rendering pipeline
- All 944+ existing tests continue to pass
- New HistoryStore unit tests pass (roundtrip, list ordering, missing ID)
- New route tests pass (save integration, history detail 200/404, recent list)
- **Verification:**
- `python3 -m pytest tests/test_history_store.py -v` — HistoryStore unit tests pass
- `python3 -m pytest tests/test_history_routes.py -v` — route integration tests pass
- `python3 -m pytest` — all 944+ existing tests plus new tests pass, zero failures
- `make js` — TypeScript builds with no errors (history.ts compiles)
- `make css` — CSS builds with no errors (new classes included)

## Proof Level

- This slice proves: - This slice proves: integration (backend persistence ↔ Flask routes ↔ template rendering ↔ JS replay)
- Real runtime required: yes (Flask test client + browser rendering via JS build)
- Human/UAT required: no

## Integration Closure

- Upstream surfaces consumed: `app/cache/store.py` (CacheStore pattern), `app/routes.py` (`_serialize_result`, `analyze` route), `app/templates/results.html`, `app/static/src/ts/modules/enrichment.ts` (rendering functions via row-factory/cards/verdict-compute)
- New wiring introduced: `HistoryStore` → `routes.py` (save + load + list), `results.html` `data-history-results` attribute → `history.ts` JS replay, `index.html` recent analyses list → `/history/<id>` links
- What remains before the milestone is truly usable end-to-end: S04 restyling of the home page and recent list for visual consistency

## Verification

- Runtime signals: SQLite WAL-mode DB at `~/.sentinelx/history.db` — row count and created_at timestamps provide analysis history audit trail
- Inspection surfaces: `HistoryStore.list_recent()` returns recent entries; `/history/<id>` route returns 404 for missing IDs
- Failure visibility: history save failures in background thread are silent (enrichment still works); missing history DB is auto-created on first access
- Redaction constraints: none (no secrets stored; input text and results are analyst data)

## Tasks

- [x] **T01: Implement HistoryStore class with SQLite persistence and unit tests** `est:45m`
  Create the `HistoryStore` class following the CacheStore SQLite WAL-mode pattern. New file `app/enrichment/history_store.py` with schema for `analysis_history` table (id, input_text, mode, iocs_json, results_json, total_count, top_verdict, created_at). Methods: `save_analysis()` serializes IOCs/results to JSON and inserts row, `list_recent(limit=20)` returns recent analyses ordered by created_at DESC, `load_analysis(id)` returns full row dict or None. Uses `threading.Lock` on writes, `Path.home() / '.sentinelx' / 'history.db'` default path with constructor `db_path` override for test isolation.

Write comprehensive unit tests in `tests/test_history_store.py` following the `test_cache_store.py` structure: roundtrip save/load, list_recent ordering and limit, missing ID returns None, top_verdict computation at save time, IOC serialization/deserialization fidelity, concurrent write safety.
  - Files: `app/enrichment/history_store.py`, `tests/test_history_store.py`
  - Verify: python3 -m pytest tests/test_history_store.py -v && python3 -m pytest --tb=short -q 2>&1 | tail -3

- [x] **T02: Wire history save, reload route, and recent analyses into Flask routes and templates** `est:1h30m`
  Integrate HistoryStore into Flask routes and templates:

1. **Save after enrichment** — In `app/routes.py`, change the `analyze()` route's Thread target from `orchestrator.enrich_all` to a wrapper function `_run_enrichment_and_save()` that calls `enrich_all()`, then serializes results via `_serialize_result()` and saves to `HistoryStore`. Pass `input_text`, `mode`, `iocs`, and `total_count` to the wrapper. The `job_id` (already `uuid.uuid4().hex`) becomes the analysis `id`.

2. **History reload route** — Add `@bp.route('/history/<analysis_id>')` that loads from `HistoryStore().load_analysis(analysis_id)`, returns 404 if not found, reconstructs `IOC` objects from stored JSON, calls `group_by_type()`, and renders `results.html` with the same template variables as live analysis. Set `mode='online'` and pass a `job_id` value of `'history'` (truthy so enrichment slots render). Add `history_results` template variable containing the JSON-serialized results for JS replay.

3. **Recent analyses on home page** — Modify `index()` route to query `HistoryStore().list_recent(limit=10)` and pass `recent_analyses` to template. Format `created_at` for display.

4. **Template changes** — In `results.html`, add `data-history-results` attribute on `.page-results` when `history_results` is provided. In `index.html`, add a conditional `{% if recent_analyses %}` block below the form showing clickable rows with timestamp, IOC count, and top verdict badge. Add minimal CSS for `.recent-analyses` in `app/static/src/input.css`.

5. **Route tests** — Write `tests/test_history_routes.py` covering: save is called after enrichment (mock HistoryStore), `/history/<id>` returns 200 with seeded data and 404 for unknown ID, index page includes recent analyses when present.

Key constraints:
- `_serialize_result()` is already in routes.py — reuse it, don't duplicate
- The history route must pass `enrichable_count` computed from stored results length so the progress bar text makes sense
- IOC reconstruction: `IOC(type=IOCType(d['type']), value=d['value'], raw_match=d['raw_match'])`
- Keep CSS minimal — S04 will restyle the home page
  - Files: `app/routes.py`, `app/templates/results.html`, `app/templates/index.html`, `app/static/src/input.css`, `tests/test_history_routes.py`
  - Verify: python3 -m pytest tests/test_history_routes.py -v && python3 -m pytest --tb=short -q 2>&1 | tail -3

- [x] **T03: Build JS history replay module and verify end-to-end build** `est:1h`
  Create `app/static/src/ts/modules/history.ts` — a JS module that detects stored history results on the page and replays them through the existing rendering pipeline, making a history-loaded results page look identical to a completed live analysis.

The module:
1. Checks for `data-history-results` attribute on `.page-results`
2. If present, parses the JSON array of enrichment results
3. Iterates each result and calls the existing rendering building blocks:
   - `findCardForIoc()` to locate the card
   - For context providers (check `CONTEXT_PROVIDERS` set): `createContextRow()` + `updateContextLine()`
   - For reputation providers: `createDetailRow()` to build the row, append to the correct `.enrichment-section--reputation` or `.enrichment-section--no-data` container
   - Track `iocVerdicts` and `iocResultCounts` locally (same shape as enrichment.ts)
   - Call `updateSummaryRow()` per IOC after all its results are processed
   - Call `updateCardVerdict()` per IOC with computed worst verdict
4. After all results replayed: call `updateDashboardCounts()`, `sortCardsBySeverity()`, `injectSectionHeadersAndNoDataSummary()` per slot, `injectDetailLink()` per loaded slot
5. Wire expand/collapse toggles (call same pattern as enrichment.ts `wireExpandToggles`)
6. Mark enrichment complete (enable export button, add .complete class to progress)

Import and init from `main.ts` — add `import { init as initHistory } from './modules/history'` and call `initHistory()` after `initEnrichment()`.

Also need to export `wireExpandToggles` and `markEnrichmentComplete` from enrichment.ts (or duplicate the small wireExpandToggles in history.ts since it's event delegation setup). Actually, history.ts should have its own `wireExpandToggles` call since it sets up the same event delegation pattern — and `wireExpandToggles` in enrichment.ts only runs when `mode=online && jobId` which won't be true for history mode. So history.ts needs to call `wireExpandToggles`-equivalent setup.

Simplest approach: extract `wireExpandToggles` into its own export from enrichment.ts, or just duplicate the event delegation in history.ts (it's 20 lines of DOM event wiring). Research recommends reuse — so export `wireExpandToggles` from enrichment.ts.

Key constraints:
- The `renderEnrichmentResult` function in enrichment.ts is private and uses closures — do NOT try to import it. Use the exported building blocks directly.
- For history replay, there's no debouncing needed (all results available synchronously)
- The `allResults` array in enrichment.ts is module-private — history.ts should build its own for export functionality
- `data-history-results` JSON is HTML-entity-encoded by Jinja2's `{{ }}` — parse with standard JSON.parse after reading the attribute

Verify the full build pipeline: `make js` succeeds, `make css` succeeds, all Python tests still pass.
  - Files: `app/static/src/ts/modules/history.ts`, `app/static/src/ts/main.ts`, `app/static/src/ts/modules/enrichment.ts`
  - Verify: make js && make css && python3 -m pytest --tb=short -q 2>&1 | tail -3

## Files Likely Touched

- app/enrichment/history_store.py
- tests/test_history_store.py
- app/routes.py
- app/templates/results.html
- app/templates/index.html
- app/static/src/input.css
- tests/test_history_routes.py
- app/static/src/ts/modules/history.ts
- app/static/src/ts/main.ts
- app/static/src/ts/modules/enrichment.ts
