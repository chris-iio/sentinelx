# S01: Route Duplication & Dead Code Cleanup — UAT

**Milestone:** M010
**Written:** 2026-04-04T05:09:08.487Z

## UAT: S01 — Route Duplication & Dead Code Cleanup

### Preconditions
- Python 3.10+ with project dependencies installed
- Node.js with TypeScript compiler available via `make typecheck`
- All 1060 tests passing before verification

---

### TC-01: _setup_orchestrator() exists and is used exclusively

**Steps:**
1. Open `app/routes/_helpers.py`
2. Search for `def _setup_orchestrator(`
3. Confirm it accepts `iocs`, `text`, `mode`, `history_store` parameters
4. Confirm it returns a tuple of `(job_id, orchestrator, registry)`
5. `grep -c 'EnrichmentOrchestrator(' app/routes/analysis.py` → expect `0`
6. `grep -c 'EnrichmentOrchestrator(' app/routes/api.py` → expect `0`
7. `grep -c '_setup_orchestrator' app/routes/analysis.py` → expect `≥1`
8. `grep -c '_setup_orchestrator' app/routes/api.py` → expect `≥1`

**Expected:** No inline EnrichmentOrchestrator construction remains in analysis.py or api.py. Both call the shared helper.

---

### TC-02: _get_enrichment_status() exists and is used exclusively

**Steps:**
1. Open `app/routes/_helpers.py`
2. Search for `def _get_enrichment_status(`
3. Confirm it accepts `job_id` parameter
4. `grep -c '_get_enrichment_status' app/routes/enrichment.py` → expect `≥1`
5. `grep -c '_get_enrichment_status' app/routes/api.py` → expect `≥1`
6. Confirm enrichment_status() in enrichment.py is a one-liner delegation
7. Confirm api_status() in api.py is a one-liner delegation

**Expected:** Both status endpoints delegate to the shared helper with no duplicated body.

---

### TC-03: Test patch targets correctly updated

**Steps:**
1. `grep -c 'app.routes.analysis.EnrichmentOrchestrator' tests/test_routes.py` → expect `0`
2. `grep -c 'app.routes.analysis._enrichment_pool' tests/test_routes.py` → expect `0`
3. `grep -c 'app.routes.api._enrichment_pool' tests/test_api.py` → expect `0`
4. `grep -c 'app.routes._helpers.EnrichmentOrchestrator' tests/test_routes.py` → expect `≥1`
5. `grep -c 'app.routes._helpers._enrichment_pool' tests/test_routes.py` → expect `≥1`
6. `python3 -m pytest --tb=short -q` → expect `1060 passed`

**Expected:** All old patch paths removed, new paths target _helpers module, full suite green.

---

### TC-04: ResultDisplay export removed

**Steps:**
1. `grep -c 'export interface ResultDisplay' app/static/src/ts/modules/shared-rendering.ts` → expect `0`
2. `grep -c 'interface ResultDisplay' app/static/src/ts/modules/shared-rendering.ts` → expect `1`
3. `rg 'import.*ResultDisplay' app/static/src/ts/` → expect no matches
4. `make typecheck` → expect exit 0

**Expected:** ResultDisplay is a module-private interface. No consumer imports it. TypeScript compiles cleanly.

---

### TC-05: No dead imports in cleaned route modules

**Steps:**
1. `grep 'import uuid' app/routes/analysis.py` → expect no match
2. `grep 'import json' app/routes/api.py` → expect no match
3. `grep 'ConfigStore' app/routes/analysis.py` → expect no match (unless re-exported from _helpers)
4. `grep 'ConfigStore' app/routes/api.py` → expect no match

**Expected:** Imports that moved to _helpers.py are no longer present in the route modules that no longer need them.
