---
id: T02
parent: S01
milestone: M006
key_files:
  - app/routes.py
  - app/enrichment/history_store.py
  - app/templates/results.html
  - app/templates/index.html
  - app/static/src/input.css
  - tests/test_history_routes.py
key_decisions:
  - Extended HistoryStore.save_analysis() with optional analysis_id parameter to reuse the enrichment job_id as the history row id — keeps the same id across the polling endpoint and history reload
  - History save failures are silently caught in the wrapper — enrichment results must always be available to the user regardless of persistence issues
  - HistoryStore errors on the home page are caught gracefully — the page renders normally with no recent analyses section rather than returning a 500
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:12:24.362Z
blocker_discovered: false
---

# T02: Wire history save, reload route, and recent analyses into Flask routes and templates

**Wire history save, reload route, and recent analyses into Flask routes and templates**

## What Happened

Integrated HistoryStore into the Flask application across routes and templates:

1. **Save after enrichment** — Added `_run_enrichment_and_save()` wrapper that calls `orchestrator.enrich_all()`, then serializes results via `_serialize_result()` and IOCs via new `_serialize_ioc()` helper, saving to HistoryStore with the job_id as the analysis_id. The Thread target in `analyze()` now uses this wrapper. Failures during history save are silently caught so enrichment results remain available to the polling endpoint.

2. **History reload route** — Added `GET /history/<analysis_id>` that loads from HistoryStore, returns 404 if not found, reconstructs IOC objects from stored JSON using `IOC(type=IOCType(d['type']), value=d['value'], raw_match=d['raw_match'])`, groups them via `group_by_type()`, and renders `results.html` with `job_id='history'` (truthy so enrichment slots render) and `history_results` containing JSON-serialized results for JS replay.

3. **Recent analyses on home page** — Updated `index()` to query `HistoryStore().list_recent(limit=10)` and pass `recent_analyses` to template. Wrapped in try/except so HistoryStore failures don't break the home page.

4. **Template changes** — Added `data-history-results` attribute on `.page-results` in `results.html` when `history_results` is provided. Added conditional `{% if recent_analyses %}` block in `index.html` showing clickable rows with truncated input text, IOC count, verdict badge, and timestamp. Added minimal CSS for `.recent-analyses` in `input.css`.

5. **HistoryStore update** — Extended `save_analysis()` to accept an optional `analysis_id` parameter so the enrichment job_id can be reused as the history row id (backward-compatible — defaults to UUID4 when not provided).

6. **Route tests** — Wrote 13 tests in `tests/test_history_routes.py` covering: save called after enrichment (mock HistoryStore), save failure doesn't break enrichment, save skipped when status is None, `/history/<id>` returns 200 with seeded data and 404 for unknown ID, history response contains data-history-results attribute, renders online mode with job_id='history', correct IOC count, index shows recent analyses, index works with empty history, index handles HistoryStore exceptions gracefully, verdict badge shown, and _serialize_ioc helper.

## Verification

Ran `python3 -m pytest tests/test_history_routes.py -v` — all 13 tests passed in 0.35s. Ran `python3 -m pytest --tb=short -q --ignore=tests/test_playwright` — all 977 tests passed in 47.94s (964 existing + 13 new). No regressions. Verified slice-level behaviors directly: list_recent returns empty list with no history, load_analysis returns None for missing IDs, save_analysis accepts explicit analysis_id.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_history_routes.py -v` | 0 | ✅ pass | 646ms |
| 2 | `python3 -m pytest --tb=short -q --ignore=tests/test_playwright` | 0 | ✅ pass | 69268ms |


## Deviations

Extended HistoryStore.save_analysis() to accept an optional `analysis_id` parameter — the plan assumed the job_id would be reused as the row id but the original method always generated a new UUID. This backward-compatible change lets the wrapper pass the job_id directly. Added _serialize_ioc() helper function not in the original plan — needed to convert IOC dataclass objects to dicts for HistoryStore persistence.

## Known Issues

None.

## Files Created/Modified

- `app/routes.py`
- `app/enrichment/history_store.py`
- `app/templates/results.html`
- `app/templates/index.html`
- `app/static/src/input.css`
- `tests/test_history_routes.py`
