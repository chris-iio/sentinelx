# S01 Research: Route Duplication & Dead Code Cleanup

**Depth:** Light — well-understood refactoring on known code with established test patterns.

## Summary

Three distinct cleanup targets, all confirmed by code inspection:

1. **Orchestrator setup duplication** (~20 identical lines in `analysis.py` and `api.py`) — extract shared helper into `_helpers.py`
2. **Status endpoint duplication** (`enrichment.py:enrichment_status()` and `api.py:api_status()` are functionally identical) — extract body into `_helpers.py`, both endpoints call it
3. **Dead imports/exports** — `json` unused in `api.py`; `ResultDisplay` interface exported from `shared-rendering.ts` but never imported by name

All three are mechanical. The risk is test mocking paths — known from M007/M008 KNOWLEDGE entries.

## Recommendation

Three tasks, ordered by dependency:

1. **Extract orchestrator setup helper** — creates `_setup_orchestrator()` in `_helpers.py`, update `analysis.py` and `api.py` to call it. Update test patch targets. This is the highest-value change and the riskiest (test patches).
2. **Consolidate status endpoints** — extract `_get_enrichment_status()` helper in `_helpers.py`, both `enrichment_status()` and `api_status()` become thin wrappers. No URL changes — `/enrichment/status/<job_id>` and `/api/status/<job_id>` both stay alive. Update test mocking if needed.
3. **Remove dead imports/exports** — remove `import json` from `api.py`, remove `export interface ResultDisplay` from `shared-rendering.ts` (make it a non-exported interface since `computeResultDisplay` still uses it as a return type). Trivial, zero test impact.

## Implementation Landscape

### Orchestrator Setup Helper

**Shared core** (extractable into `_setup_orchestrator()`):
```
registry = current_app.registry
job_id = uuid.uuid4().hex
cache = current_app.cache_store
config_store = ConfigStore()
cache_ttl_hours = config_store.get_cache_ttl()
orchestrator = EnrichmentOrchestrator(adapters=..., cache=..., cache_ttl_seconds=...)
# register in _orchestrators with eviction
# submit to _enrichment_pool
```

**Divergent parts** (stay in each route):
- `analysis.py`: checks `registry.configured()` → flash + redirect on failure; builds `template_extras` with `type_providers`, `enrichable_count`, `provider_counts`, `provider_coverage`
- `api.py`: checks `registry.configured()` → jsonify 400 on failure; adds `job_id` and `status_url` to response

**Helper signature:** `_setup_orchestrator(iocs, text, mode, history_store) -> (job_id, orchestrator, registry)` — returns what the callers need for their divergent post-setup logic. The "not configured" check stays in each caller since the error response is route-specific.

**Alternative:** The helper could accept a callback for the "not configured" case, but that's over-engineering for two callers.

### Status Endpoint Consolidation

**File:** `app/routes/enrichment.py` — 42 lines total, only has the status endpoint.

**Approach:** Extract the body into `_helpers._get_enrichment_status(job_id)` that returns a Flask response tuple. Both `enrichment_status()` and `api_status()` become one-liners calling it. `enrichment.py` shrinks to ~10 lines.

**Alternative:** Delete `enrichment.py` entirely and add the `/enrichment/status/<job_id>` route to `api.py`. Simpler, but mixes Blueprint concerns (main vs api) and would require either adding the route to `bp` from inside `api.py` or moving it to `analysis.py`. The helper approach is cleaner.

**Frontend constraint:** `enrichment.ts` line 390 polls `/enrichment/status/<job_id>`. This URL MUST stay on the `main` Blueprint. The `/api/status/<job_id>` URL on the `api` Blueprint also stays — both are thin wrappers.

### Dead Code

1. `app/routes/api.py` line 11: `import json` — `json` is never used (all JSON serialization uses Flask's `jsonify`). `analysis.py` DOES use `json.dumps()` on line 96 — that import is live.

2. `app/static/src/ts/modules/shared-rendering.ts` line 21: `export interface ResultDisplay` — no module imports this interface by name. Both `enrichment.ts` and `history.ts` import `computeResultDisplay` (the function) and destructure the return value inline. The interface is used as the return type of `computeResultDisplay` but doesn't need to be exported. Change `export interface` → `interface` (keep as non-exported).

### Test Impact

**Patch targets at risk:**
- `test_routes.py` patches `app.routes.analysis._enrichment_pool` (5 occurrences) — this import chain (`analysis.py` → `from ._helpers import _enrichment_pool`) means the patch target already works through the re-export. After refactoring, if `analysis.py` still imports `_enrichment_pool` (for the helper to use), the patch continues to work. If the helper is in `_helpers.py` and `analysis.py` no longer imports `_enrichment_pool` directly, patch targets must change to `app.routes._helpers._enrichment_pool`.
- `test_routes.py` accesses `routes_module._orchestrators` via `import app.routes.analysis as routes_module` (8 occurrences for status tests). These tests test the `/enrichment/status/` endpoint. After the helper extraction, `_orchestrators` is still in `_helpers.py`, and `analysis.py` still re-imports it. But the cleaner path is to switch status tests to `import app.routes._helpers as helpers_module` and access `helpers_module._orchestrators`.
- `test_api.py` patches `app.routes.api._enrichment_pool` (1 occurrence) and accesses `helpers._orchestrators` via `from app.routes._helpers import _orchestrators` (already correct).

**Key insight:** `test_routes.py` uses `import app.routes.analysis as routes_module` then `routes_module._orchestrators[job_id] = ...` for ALL enrichment status tests (lines 354-578). But those tests hit `/enrichment/status/<job_id>` — a route defined in `enrichment.py`, not `analysis.py`. They work because `_orchestrators` is the same dict object everywhere (imported from `_helpers`). After refactoring, this still works as long as `analysis.py` continues to import `_orchestrators`. But it's fragile — the planner should consider whether to tighten these imports.

**Recommendation:** Keep `analysis.py`'s `from ._helpers import ...` imports as-is for patch target stability. The helper function lives in `_helpers.py` and is called by both routes. Test patches on `app.routes.analysis._enrichment_pool` continue to work because Python re-exports are the same object.

### Files Touched

| File | Change |
|------|--------|
| `app/routes/_helpers.py` | Add `_setup_orchestrator()` helper, add `_get_enrichment_status()` helper |
| `app/routes/analysis.py` | Replace inline setup with `_setup_orchestrator()` call |
| `app/routes/api.py` | Replace inline setup with `_setup_orchestrator()` call; remove `import json` |
| `app/routes/enrichment.py` | Replace body with `_get_enrichment_status()` call |
| `app/static/src/ts/modules/shared-rendering.ts` | `export interface ResultDisplay` → `interface ResultDisplay` |
| `tests/test_routes.py` | Possibly update patch targets (verify first — may not need changes) |
| `tests/test_api.py` | Possibly update patch targets (verify first — may not need changes) |

### Verification

```bash
# All tests pass
python3 -m pytest --tb=short -q

# No orchestrator setup duplication between routes
grep -c 'EnrichmentOrchestrator(' app/routes/analysis.py app/routes/api.py
# Expected: 0 in both (constructor moved to helper)

# No dead json import
grep -c '^import json' app/routes/api.py
# Expected: 0

# ResultDisplay not exported
grep -c 'export interface ResultDisplay' app/static/src/ts/modules/shared-rendering.ts
# Expected: 0

# TypeScript compiles
make typecheck

# Status endpoints still work (covered by existing tests)
python3 -m pytest tests/test_routes.py -k enrichment_status -q
python3 -m pytest tests/test_api.py -k api_status -q
```
