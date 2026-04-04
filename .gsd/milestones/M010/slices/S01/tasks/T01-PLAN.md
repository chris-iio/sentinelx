---
estimated_steps: 39
estimated_files: 6
skills_used: []
---

# T01: Extract orchestrator setup helper and consolidate status endpoint logic

Extract the ~20 identical lines of orchestrator setup (uuid, cache, config, constructor, registry, pool submit) from analysis.py and api.py into a `_setup_orchestrator()` helper in `_helpers.py`. Extract the identical status endpoint body from enrichment.py and api.py into a `_get_enrichment_status()` helper in `_helpers.py`. Update both route files to call the helpers. Fix any test patch targets that break.

## Steps

1. Read `app/routes/_helpers.py`, `app/routes/analysis.py`, `app/routes/api.py`, `app/routes/enrichment.py` to understand current code.

2. Add `_setup_orchestrator()` to `_helpers.py`:
   - Signature: `_setup_orchestrator(iocs: list[IOC], text: str, mode: str, history_store) -> tuple[str, EnrichmentOrchestrator, ProviderRegistry]`
   - Move these imports to `_helpers.py` if not already there: `uuid`, `ConfigStore`
   - Body: get registry from `current_app.registry`, generate `job_id = uuid.uuid4().hex`, get cache/config/ttl, construct `EnrichmentOrchestrator`, register in `_orchestrators` with eviction under `_orch_lock`, submit to `_enrichment_pool` via `_run_enrichment_and_save`, return `(job_id, orchestrator, registry)`
   - The 'not configured' check stays in each caller (response format differs)

3. Update `analysis.py`:
   - Remove direct imports of `uuid`, `ConfigStore`, `EnrichmentOrchestrator`
   - Import `_setup_orchestrator` from `._helpers`
   - Replace the inline setup block (from `job_id = uuid.uuid4().hex` through `_enrichment_pool.submit(...)`) with a call to `_setup_orchestrator(iocs, text, mode, current_app.history_store)` — returns `(job_id, orchestrator, registry)`
   - Keep the `template_extras` dict construction that uses `registry` and `job_id`

4. Update `api.py`:
   - Remove `import json`, `import uuid`, and direct imports of `ConfigStore`, `EnrichmentOrchestrator`
   - Import `_setup_orchestrator` and `_get_enrichment_status` from `._helpers`
   - Replace inline orchestrator setup with `_setup_orchestrator()` call
   - Replace `api_status()` body with `return _get_enrichment_status(job_id)`

5. Add `_get_enrichment_status()` to `_helpers.py`:
   - Signature: `_get_enrichment_status(job_id: str) -> tuple[Response, int] | Response`
   - Body: the shared status logic (lock, orchestrator lookup, get_status, since param, serialize, jsonify)
   - Needs `request` import from flask

6. Update `enrichment.py`:
   - Import `_get_enrichment_status` from `._helpers`
   - Replace `enrichment_status()` body with `return _get_enrichment_status(job_id)`

7. Run `python3 -m pytest --tb=short -q` to identify any broken test patches.

8. Fix broken test patch targets:
   - `tests/test_routes.py`: patches `app.routes.analysis.EnrichmentOrchestrator` (5 occurrences) and `app.routes.analysis._enrichment_pool` (5 occurrences). After refactoring, `analysis.py` no longer imports `EnrichmentOrchestrator` or `_enrichment_pool` directly. Update patches to `app.routes._helpers.EnrichmentOrchestrator` and `app.routes._helpers._enrichment_pool`.
   - `tests/test_api.py`: patches `app.routes.api._enrichment_pool` (1 occurrence). Update to `app.routes._helpers._enrichment_pool`.
   - `tests/test_routes.py` status tests: `import app.routes.analysis as routes_module` then `routes_module._orchestrators[job_id] = ...`. These work because `_orchestrators` is the same dict object (imported from `_helpers`). Verify they still pass — if not, switch to `import app.routes._helpers as helpers_module`.

9. Run `python3 -m pytest --tb=short -q` again — all 1060 tests must pass.

## Must-Haves

- [ ] `_setup_orchestrator()` exists in `_helpers.py` and handles uuid, cache, config, constructor, registry, pool submit
- [ ] `_get_enrichment_status()` exists in `_helpers.py` and handles lock, lookup, serialize, jsonify
- [ ] `analysis.py` calls `_setup_orchestrator()` — no inline `EnrichmentOrchestrator(` constructor
- [ ] `api.py` calls `_setup_orchestrator()` — no inline `EnrichmentOrchestrator(` constructor
- [ ] `enrichment.py` calls `_get_enrichment_status()` — body is a one-liner
- [ ] `api_status()` calls `_get_enrichment_status()` — body is a one-liner
- [ ] All test patch targets updated and all 1060 tests pass

## Inputs

- ``app/routes/_helpers.py` — existing shared state module with _orchestrators, _enrichment_pool, _serialize_result, etc.`
- ``app/routes/analysis.py` — contains inline orchestrator setup to extract`
- ``app/routes/api.py` — contains inline orchestrator setup and status endpoint to extract`
- ``app/routes/enrichment.py` — contains status endpoint body to extract`
- ``tests/test_routes.py` — patches app.routes.analysis.EnrichmentOrchestrator and app.routes.analysis._enrichment_pool`
- ``tests/test_api.py` — patches app.routes.api._enrichment_pool`

## Expected Output

- ``app/routes/_helpers.py` — gains _setup_orchestrator() and _get_enrichment_status() helpers`
- ``app/routes/analysis.py` — orchestrator setup replaced with helper call`
- ``app/routes/api.py` — orchestrator setup and status body replaced with helper calls; import json removed`
- ``app/routes/enrichment.py` — status body replaced with helper call`
- ``tests/test_routes.py` — patch targets updated from app.routes.analysis.X to app.routes._helpers.X`
- ``tests/test_api.py` — patch target updated from app.routes.api._enrichment_pool to app.routes._helpers._enrichment_pool`

## Verification

python3 -m pytest --tb=short -q && grep -c 'EnrichmentOrchestrator(' app/routes/analysis.py app/routes/api.py | grep -v ':0$' | wc -l | grep -q '^0$' && echo 'PASS: no inline orchestrator constructors in route files'
