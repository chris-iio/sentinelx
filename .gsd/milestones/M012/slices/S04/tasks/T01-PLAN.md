---
estimated_steps: 4
estimated_files: 5
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T01: Expose helper-layer history-save diagnostics through the settings inspection surface


Add additive diagnostics around the helper-owned history save path and surface them on the existing `/settings` inspection page so future agents can see whether background persistence is healthy without touching live polling, history replay, or the WAL-mode store implementation. Keep the change aggregate-only: no raw input text, IOC values, or full results should be exposed.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/routes/_helpers.py` background save wrapper | Keep enrichment completion intact and treat diagnostics as best-effort; never let diagnostic bookkeeping block or fail the save path | Do not add waits or retries in the request path; diagnostics must stay O(1) around the existing background job | Ignore malformed internal state and fall back to zero/default diagnostics rather than crashing `/settings` |
| `app/routes/settings.py` + `app/templates/settings.html` inspection surface | Render safe defaults if diagnostics are absent so the settings page still loads | N/A | Only show aggregate counts, timestamps, and error-summary strings; never render raw results or input text |
| Existing history/store contracts (`HistoryStore.save_analysis()`, `/history/<id>`, `_get_enrichment_status()`) | Leave them unchanged; if a diagnostic change requires contract churn, stop and keep diagnostics out of those paths | N/A | N/A |

## Load Profile

- **Shared resources**: helper module state, `/settings` page render, and the existing background history-save path.
- **Per-operation cost**: constant-time counter/timestamp updates on save attempt/success/failure plus one extra template render on `/settings`.
- **10x breakpoint**: unbounded diagnostic state or request-path coupling; the task fails if diagnostics grow per job without a bound or if `/settings` depends on raw analysis payloads.

## Negative Tests

- **Malformed inputs**: no diagnostics present yet, partially populated diagnostic state, or missing timestamps should still render the settings page safely.
- **Error paths**: `HistoryStore.save_analysis()` raises, returns after `get_status()` is `None`, or succeeds after background enrichment, and diagnostics must record the right aggregate outcome without changing enrichment behavior.
- **Boundary conditions**: first successful save, repeated failures, and skipped save paths all leave `/history/<analysis_id>` replay and `_get_enrichment_status()` cursor semantics untouched.

## Steps

1. Add a bounded helper-level diagnostics summary for history-save attempts/successes/failures/last outcome in `app/routes/_helpers.py`, keeping it additive and free of raw analysis content.
2. Surface the aggregate diagnostics on the existing settings inspection surface via `app/routes/settings.py` and `app/templates/settings.html` instead of touching live polling or history detail routes.
3. Extend `tests/test_history_routes.py` and `tests/test_settings.py` to prove success, failure, and skipped-save cases update the diagnostics correctly and render safe aggregate values.
4. Run focused pytest plus the fast verification lane so the helper/settings change is backed by fresh proof and broader regressions are caught immediately.

## Must-Haves

- [ ] The helper background save path exposes additive aggregate diagnostics without changing `HistoryStore.save_analysis()` payloads or the WAL-mode stores.
- [ ] `/settings` renders the diagnostics using counts, timestamps, and error summaries only; no raw IOC input, results JSON, or secrets leak into the page.
- [ ] `_get_enrichment_status()` and the `?since=` cursor contract remain untouched.
- [ ] `/history/<analysis_id>` replay and existing settings page provider/cache behavior still pass fresh tests.

## Verification

- `python3 -m pytest tests/test_history_routes.py tests/test_settings.py -q`
- `make verify-fast`

## Observability Impact

- Signals added/changed: helper-level history-save attempt/success/failure counts plus last outcome metadata.
- How a future agent inspects this: open `/settings` or run the focused pytest modules to confirm the additive diagnostics surface.
- Failure state exposed: history persistence failures stop being log-only and become visible as aggregate last-outcome diagnostics.

## Inputs

- `app/routes/_helpers.py` — existing background enrichment + history-save wrapper that currently logs failures without an inspection surface.
- `app/routes/settings.py` — existing settings inspection route that already surfaces cache stats.
- `app/templates/settings.html` — current settings template where additive diagnostics can be rendered without touching analyst results pages.
- `tests/test_history_routes.py` — existing wrapper tests for success/failure/skip history-save behavior.
- `tests/test_settings.py` — existing settings route coverage that should pin the new inspection surface.

## Expected Output

- `app/routes/_helpers.py` — additive helper diagnostics for history-save outcomes.
- `app/routes/settings.py` — settings route wiring for the new diagnostics surface.
- `app/templates/settings.html` — aggregate helper diagnostics rendered safely for inspection.
- `tests/test_history_routes.py` — proof that success/failure/skip paths update diagnostics without breaking persistence flow.
- `tests/test_settings.py` — proof that the settings page renders the diagnostics safely.
