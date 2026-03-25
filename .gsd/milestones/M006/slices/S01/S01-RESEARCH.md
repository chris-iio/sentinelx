# S01 Research: Analysis History & Persistence

**Depth:** Targeted  
**Rationale:** Known technology (SQLite, Flask routes, Jinja2 templates), established codebase patterns to follow (CacheStore), moderate complexity in data serialization and reload flow. No unfamiliar libraries or APIs.

---

## Summary

This slice adds three capabilities: (1) persist every online analysis run to SQLite, (2) list recent analyses on the home page, (3) reload a past analysis as a full results page. The codebase has a clean SQLite WAL-mode pattern in `CacheStore` to replicate, a well-defined results template data contract, and a simple routing convention. The main design question is *what* to store (full serialized enrichment results + IOC list + input text) and *when* to store it (after enrichment completes).

**Requirements targeted:**
- **R030** (active, owner: M006/S01) — Persist every analysis run; revisit past analyses with full results
- **R031** (active, owner: M006/S01) — Recent analyses list on home page with timestamp, IOC count, top verdict; click reloads full results

---

## Recommendation

Follow the CacheStore pattern exactly: new file `app/enrichment/history_store.py` with a `HistoryStore` class using `~/.sentinelx/history.db` (SQLite WAL-mode). Store input text, IOC list (as JSON), and the full enrichment results (as JSON) per analysis run. The `analyze` route saves after enrichment completes (background thread callback). The index route queries recent analyses. A new `/history/<analysis_id>` route reloads stored data into `results.html`.

---

## Implementation Landscape

### 1. HistoryStore — new file `app/enrichment/history_store.py`

**Pattern to follow:** `app/cache/store.py` (CacheStore)

Key design elements to replicate:
- `DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "history.db"` — separate DB from cache
- Constructor: `db_path` param (default + test override), `mkdir(parents=True, exist_ok=True, mode=0o700)`, `connect(check_same_thread=False)`, `PRAGMA journal_mode=WAL`, `CREATE TABLE IF NOT EXISTS`
- `threading.Lock` for write operations
- `db_path` param in constructor for test isolation via `tmp_path`

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS analysis_history (
    id          TEXT PRIMARY KEY,           -- uuid hex (same format as job_id)
    input_text  TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'online',
    iocs_json   TEXT NOT NULL,             -- JSON array of {type, value, raw_match}
    results_json TEXT NOT NULL,            -- JSON array of serialized EnrichmentResult/Error dicts
    total_count INTEGER NOT NULL,
    created_at  TEXT NOT NULL              -- ISO8601 UTC
)
```

**Methods needed:**
- `save_analysis(id, input_text, mode, iocs, results, total_count)` — serializes IOCs and results to JSON, inserts row
- `list_recent(limit=20)` — returns list of `{id, total_count, created_at, top_verdict, ioc_count}` ordered by `created_at DESC`
- `load_analysis(id)` — returns full row dict or None; deserializes JSON back to dicts

**IOC serialization:** Each `IOC` dataclass → `{"type": "ipv4", "value": "1.2.3.4", "raw_match": "1[.]2[.]3[.]4"}`. On reload, reconstruct `IOC(type=IOCType(d["type"]), value=d["value"], raw_match=d["raw_match"]))`.

**Results serialization:** Reuse the existing `_serialize_result()` function from `routes.py` which already converts `EnrichmentResult`/`EnrichmentError` to JSON-safe dicts.

### 2. Saving Analysis — modify `app/routes.py`

**When to save:** After `orchestrator.enrich_all()` completes (in the background thread). The cleanest approach is to wrap the thread target:

```python
def _run_enrichment_and_save(orchestrator, job_id, iocs, input_text, mode, total_count):
    orchestrator.enrich_all(job_id, iocs)
    # After enrichment completes, save to history
    status = orchestrator.get_status(job_id)
    if status is not None:
        history = HistoryStore()
        serialized = [_serialize_result(r) for r in status["results"]]
        history.save_analysis(job_id, input_text, mode, iocs, serialized, total_count)
```

The `job_id` (already `uuid.uuid4().hex`) becomes the analysis `id` — single ID space, no mapping needed.

**Key constraint:** The thread target function needs access to `input_text` and `mode` from the request context. These are simple strings, already available in `analyze()` — just pass them to the thread target. No Flask app context needed since `HistoryStore` uses its own SQLite connection.

### 3. Reload Route — new route in `app/routes.py`

```python
@bp.route("/history/<analysis_id>")
def history_detail(analysis_id: str):
```

**What it does:**
1. `HistoryStore().load_analysis(analysis_id)` — returns the stored row or 404
2. Deserialize `iocs_json` back to `IOC` objects → `group_by_type()` for template
3. Deserialize `results_json` — these are already in `_serialize_result()` format
4. Render `results.html` with the same template variables as the live analysis, but **without** `job_id` (no polling needed — results are complete)

**Template compatibility:** The results template already handles the no-`job_id` case gracefully:
- `{% if mode == "online" and job_id %}` guards the progress bar, enrichment slots, verdict dashboard, export group
- Without `job_id`, the template renders like offline mode — just IOC cards with no enrichment UI

**Problem:** For history reload, we want to show enrichment results (verdicts, provider data) but the current template only shows enrichment data via JS polling. Without `job_id`, the JS enrichment module never starts.

**Solution options:**
1. **Server-render enrichment data into the template** — add a `history_results` variable that the template can use to pre-render verdict labels and provider rows. This requires adding Jinja2 blocks to `_ioc_card.html` for pre-populated enrichment data.
2. **Fake a completed job** — register a pre-completed orchestrator in `_orchestrators` with all results, set `job_id` in template. The JS polling picks it up on first tick and renders normally. This is clever but fragile (depends on JS polling interval, adds complexity).
3. **Inject results as JSON into page data, let JS render** — add `data-history-results` attribute to `.page-results`, create a small JS module that reads it and calls the same rendering functions as enrichment.ts. Cleanest separation but requires a new JS module.

**Recommended: Option 3 (JSON data attribute + JS replay)**. Reasons:
- Reuses all existing JS rendering (verdict computation, row factory, card updates, sorting)
- No template changes to `_ioc_card.html` (preserves the contract documented in the file)
- The JS replay module is small — iterate results, call the same dispatch functions enrichment.ts uses
- The results page looks identical to a completed live analysis

The `results.html` template would get:
```html
<div class="page-results" 
     {% if history_results %}data-history-results="{{ history_results }}"{% endif %}
     ...>
```

A new `app/static/src/ts/modules/history.ts` module:
- Check for `data-history-results` on `.page-results`
- If present, parse JSON, iterate results, call the same rendering pipeline as enrichment.ts
- Needs the enrichment slot HTML to be rendered in cards — so the route must pass `job_id` as a sentinel (or add a `history_mode` flag)

**Refinement:** Actually, the simpler path is: the history route renders `results.html` with `mode="online"` and a synthetic `job_id` like `"history"`, plus `enrichable_count`, `provider_counts`, etc. computed from stored data. The enrichment slots render in the template. Then inject `data-history-results` with the serialized results JSON. A small `history.ts` init function detects this attribute and replays results through the existing card/row-factory pipeline instead of polling.

### 4. Recent Analyses on Home Page — modify `app/routes.py` and `app/templates/index.html`

**Route change:** The `index()` route queries `HistoryStore().list_recent(limit=10)` and passes it to the template.

**Template change:** Below the form in `index.html`, add a conditional block:
```html
{% if recent_analyses %}
<div class="recent-analyses">
    <h3 class="recent-analyses-title">Recent Analyses</h3>
    {% for analysis in recent_analyses %}
    <a href="{{ url_for('main.history_detail', analysis_id=analysis.id) }}" class="recent-analysis-item">
        <span class="recent-analysis-time">{{ analysis.created_at_display }}</span>
        <span class="recent-analysis-count">{{ analysis.ioc_count }} IOCs</span>
        <span class="recent-analysis-verdict verdict-label--{{ analysis.top_verdict }}">{{ analysis.top_verdict | upper }}</span>
    </a>
    {% endfor %}
</div>
{% endif %}
```

**Top verdict computation:** In `list_recent()`, compute the worst verdict from the stored `results_json` per row. Options:
- Store `top_verdict` as a computed column at save time (avoids re-parsing JSON on every list query)
- Compute on read from `results_json` (simpler schema, but N×JSON-parse per list)

**Recommendation:** Store `top_verdict` as a column. It's known at save time and avoids JSON parsing on the hot path (home page load).

### 5. CSS for Recent Analyses List

Minimal CSS additions in `app/static/src/input.css`:
- `.recent-analyses` — container with top margin
- `.recent-analysis-item` — flex row, hover state, link styling
- `.recent-analysis-time`, `.recent-analysis-count` — typography

These follow existing zinc-token patterns. S04 will restyle further, so keep it functional here.

### 6. Existing Data Flow Reference

The `analyze()` route in `routes.py` (lines 105-191) constructs these template variables for `results.html`:
- `grouped` — `dict[IOCType, list[IOC]]` from `group_by_type(iocs)`
- `mode` — `"offline"` or `"online"`
- `total_count` — `len(iocs)`
- `no_results` — `total_count == 0`
- (online only) `job_id`, `enrichable_count`, `provider_counts` (JSON string), `provider_coverage` (dict)

For history reload, we need to reconstruct `grouped` and provide the same template variables. The `provider_counts` and `provider_coverage` can be omitted (they drive the progress bar and coverage row, which don't apply to completed historical data).

---

## Key Findings & Constraints

1. **CacheStore pattern is the blueprint.** `app/cache/store.py` is 130 lines. HistoryStore will be ~100 lines following the same structure. `tmp_path` injection for tests is proven.

2. **`_serialize_result()` already exists.** The serialization format from `routes.py` lines 73-97 is exactly what we need to store in `results_json`. No new serialization code needed.

3. **IOC reconstruction is simple.** `IOC` is a frozen dataclass with three fields (type, value, raw_match). `IOCType` is a string enum. JSON round-trip: `{"type": "ipv4", "value": "1.2.3.4", "raw_match": "1[.]2[.]3[.]4"}` → `IOC(type=IOCType("ipv4"), value="1.2.3.4", raw_match="1[.]2[.]3[.]4")`.

4. **The template's `{% if mode == "online" and job_id %}` guards are the key branching point.** For history reload, we need enrichment slots rendered (so we need `job_id` truthy), but we don't want polling. The `data-history-results` attribute + JS replay module solves this cleanly.

5. **The `enrichable_count` variable drives the progress bar text.** For history, we can compute this from the stored results count, or simply set it to the results count (all complete).

6. **`provider_counts` is a JSON string mapping IOC type → provider count.** For history, this isn't needed since the progress bar completes immediately. But the enrichment.ts module reads it — if we replay via JS, we may need to provide it or guard against its absence.

7. **Thread safety:** `HistoryStore` needs `threading.Lock` on writes (same as CacheStore). The save happens in a background thread; reads happen in Flask request threads. WAL mode + lock handles this.

8. **No auto-purge per D042/open questions.** Local tool — analysts delete the DB if it gets large. Schema doesn't need a TTL column.

9. **Existing test count: 944.** All must continue passing after changes.

---

## Natural Task Decomposition

The work divides into four independent units:

### T01: HistoryStore class (backend, pure Python, fully testable in isolation)
- New file: `app/enrichment/history_store.py`
- New test file: `tests/test_history_store.py`
- Methods: `save_analysis()`, `list_recent()`, `load_analysis()`
- Pattern: follow CacheStore exactly
- No dependencies on routes or templates
- **Verify:** `python3 -m pytest tests/test_history_store.py -v`

### T02: Save analysis after enrichment (route integration)
- Modify: `app/routes.py` — wrap thread target to save after enrichment completes
- Import HistoryStore, wire save_analysis() call
- Depends on T01
- **Verify:** Unit test that mocks HistoryStore and confirms save_analysis() called after enrich_all()

### T03: History reload route + JS replay module
- New route: `/history/<analysis_id>` in `app/routes.py`
- Modify: `app/templates/results.html` — add `data-history-results` attribute
- New file: `app/static/src/ts/modules/history.ts` — reads data attribute, replays through existing rendering pipeline
- Modify: `app/static/src/ts/main.ts` — import and init history module
- Depends on T01
- **Verify:** E2E test that saves analysis data, navigates to `/history/<id>`, confirms results rendered

### T04: Recent analyses list on home page
- Modify: `app/routes.py` — index route queries list_recent()
- Modify: `app/templates/index.html` — add recent analyses list HTML
- Add minimal CSS in `app/static/src/input.css`
- Depends on T01
- **Verify:** E2E test that submits analysis, returns to home page, sees recent analysis entry, clicks it

---

## Verification Strategy

- **Unit tests for HistoryStore:** Roundtrip (save/load), list_recent ordering, missing ID returns None, thread safety on concurrent writes. Follow `test_cache_store.py` structure (~12 tests).
- **Unit tests for save integration:** Mock HistoryStore in route tests, confirm save called with correct data after enrichment.
- **Unit tests for history route:** Flask test client GET `/history/<id>` with pre-seeded data returns 200 with results template; unknown ID returns 404.
- **E2E test for full round-trip:** Submit IOCs in online mode (mocked enrichment) → navigate home → see recent entry → click → see full results page. This is the R030+R031 acceptance test.
- **Regression:** `python3 -m pytest` — all 944+ tests pass.
- **Build:** `make js` succeeds (new history.ts module compiles), `make css` succeeds (new CSS classes included).

---

## Don't Hand-Roll

- **SQLite connection management:** Follow CacheStore's `connect(check_same_thread=False)` + WAL pattern exactly. Don't use a connection pool or ORM.
- **JSON serialization of results:** Reuse `_serialize_result()` from routes.py (or extract it to a shared module). Don't create a second serialization format.
- **UUID generation:** Reuse `uuid.uuid4().hex` already used for `job_id`. Don't add a separate ID scheme.
- **DOM rendering for history replay:** Reuse the existing `createDetailRow()`, `updateSummaryRow()`, `updateCardVerdict()` from enrichment.ts/row-factory.ts. Don't create parallel rendering code.
