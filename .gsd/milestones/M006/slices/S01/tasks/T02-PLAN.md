---
estimated_steps: 11
estimated_files: 5
skills_used: []
---

# T02: Wire history save, reload route, and recent analyses into Flask routes and templates

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

## Inputs

- ``app/enrichment/history_store.py` — HistoryStore class from T01`
- ``app/routes.py` — existing analyze(), index(), _serialize_result() functions`
- ``app/templates/results.html` — existing results template with job_id/mode guards`
- ``app/templates/index.html` — existing home page template`
- ``app/static/src/input.css` — existing CSS file`
- ``app/pipeline/models.py` — IOC, IOCType, group_by_type for reconstruction`

## Expected Output

- ``app/routes.py` — updated with _run_enrichment_and_save(), history_detail() route, index() with recent_analyses`
- ``app/templates/results.html` — updated with data-history-results attribute`
- ``app/templates/index.html` — updated with recent analyses list block`
- ``app/static/src/input.css` — updated with .recent-analyses CSS`
- ``tests/test_history_routes.py` — route integration tests for save, reload, recent list`

## Verification

python3 -m pytest tests/test_history_routes.py -v && python3 -m pytest --tb=short -q 2>&1 | tail -3

## Observability Impact

- Signals: history save happens in background thread after enrichment — failures are silent (enrichment results still returned to user)
- Inspection: `/history/<unknown_id>` returns 404; `HistoryStore.list_recent()` returns empty list when no history exists
- Failure state: if history DB is corrupted/missing, HistoryStore auto-creates on init; save failures don't break the enrichment flow
