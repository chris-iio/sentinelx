# S01: Route Duplication & Dead Code Cleanup

**Goal:** Eliminate route-layer duplication (orchestrator setup, status endpoints) and remove dead imports/exports. analysis.py and api.py share a single orchestrator setup helper; status endpoint bodies consolidated; dead code removed; all tests pass.
**Demo:** After this: After this: analysis.py and api.py share a single orchestrator setup helper; status endpoints consolidated; dead imports/exports removed; all tests pass.

## Tasks
- [x] **T01: Extract _setup_orchestrator() and _get_enrichment_status() into _helpers.py, eliminating ~40 duplicated lines across route modules** — Extract the ~20 identical lines of orchestrator setup (uuid, cache, config, constructor, registry, pool submit) from analysis.py and api.py into a `_setup_orchestrator()` helper in `_helpers.py`. Extract the identical status endpoint body from enrichment.py and api.py into a `_get_enrichment_status()` helper in `_helpers.py`. Update both route files to call the helpers. Fix any test patch targets that break.

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
  - Estimate: 45m
  - Files: app/routes/_helpers.py, app/routes/analysis.py, app/routes/api.py, app/routes/enrichment.py, tests/test_routes.py, tests/test_api.py
  - Verify: python3 -m pytest --tb=short -q && grep -c 'EnrichmentOrchestrator(' app/routes/analysis.py app/routes/api.py | grep -v ':0$' | wc -l | grep -q '^0$' && echo 'PASS: no inline orchestrator constructors in route files'
- [ ] **T02: Remove dead ResultDisplay export from shared-rendering.ts** — Change `export interface ResultDisplay` to `interface ResultDisplay` in shared-rendering.ts. The interface is used as the return type of `computeResultDisplay` but never imported by name anywhere — callers destructure the return value inline.

## Steps

1. Read `app/static/src/ts/modules/shared-rendering.ts` line 21.
2. Change `export interface ResultDisplay {` to `interface ResultDisplay {`.
3. Run `make typecheck` to confirm TypeScript still compiles (the function return type annotation uses `ResultDisplay` locally, which is fine as a non-exported interface).
4. Verify no module imports `ResultDisplay` by name: `rg 'ResultDisplay' app/static/src/ts/ --no-filename` should show only the definition and the function signature, not any import.

## Must-Haves

- [ ] `ResultDisplay` is no longer exported
- [ ] `make typecheck` passes
- [ ] No import of `ResultDisplay` by name exists in any TS file
  - Estimate: 5m
  - Files: app/static/src/ts/modules/shared-rendering.ts
  - Verify: make typecheck && grep -c 'export interface ResultDisplay' app/static/src/ts/modules/shared-rendering.ts | grep -q '^0$' && echo 'PASS: ResultDisplay no longer exported'
