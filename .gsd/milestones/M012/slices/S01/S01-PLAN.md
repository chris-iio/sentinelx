# S01: Enrichment failure visibility and runtime baseline

**Goal:** Harden the live enrichment status contract so failure states are visible and measurable without changing the core orchestration semantics.
**Demo:** An analyst can run enrichment through the existing UI and see explicit terminal states for missing/evicted/failed jobs instead of silent endless polling, with verification evidence that the live status path still preserves cursor polling, concurrency/backoff behavior, and current security boundaries.

## Must-Haves

- The status API exposes an explicit terminal outcome for missing/evicted/failed polling states.
- The frontend stops silent retry-forever behavior and surfaces a clear analyst-visible state when the job cannot continue.
- Existing enrichment workflow behavior remains intact for successful jobs, including incremental updates and result rendering.
- Verification covers both the live contract and targeted continuity for concurrency/backoff/cursor-polling behavior.

## Proof Level

- This slice proves: Real UI/status-route proof plus focused automated tests for touched backend/frontend modules and continuity checks for orchestrator semantics.

## Integration Closure

Backend status serialization, Flask helper behavior, and frontend polling/render handling agree on explicit terminal states and preserve existing enrichment workflow continuity.

## Verification

- The enrichment path exposes analyst-visible terminal failure states and gives future slices a stable runtime-verification surface instead of silent retry loops.

## Tasks

- [x] **T01: Define and implement explicit terminal status semantics** `est:0.75d`
  Inspect the current `_helpers.py` status serialization path, orchestrator lifecycle, and frontend polling/error handling to identify the smallest contract change that can represent terminal failure without breaking existing success/progress semantics. Document the contract shape in code comments or nearby tests as needed, then implement the backend status payload update and any required helper/runtime distinctions for unknown, evicted, or terminally failed jobs.
  - Files: `app/routes/_helpers.py`, `app/enrichment/orchestrator.py`, `tests/test_routes_helpers.py`, `tests/test_orchestrator.py`
  - Verify: python3 -m pytest tests/test_routes_helpers.py tests/test_orchestrator.py -q

- [x] **T02: Surface terminal polling failures in the analyst UI** `est:0.75d`
  Update the enrichment UI polling flow to interpret the hardened status contract, stop silent endless polling on terminal failure, and present clear analyst-visible feedback while preserving current success-path rendering. Add or update frontend unit tests for status/error handling and any touched DOM state transitions.
  - Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/results.ts`, `app/static/src/ts/modules/status.ts`, `app/static/src/ts/modules/__tests__/*.test.ts`
  - Verify: npx vitest run

- [x] **T03: Prove live-path continuity and baseline the slice** `est:0.5d`
  Run focused end-to-end verification through the existing local build and targeted tests to prove that successful enrichment still works, terminal states are visible, and the continuity constraints remain intact. Capture the evidence needed to make this slice the stable baseline for downstream UI and proof-loop slices.
  - Files: `tests/test_analysis_page.py`, `tests/test_api_enrichment.py`, `app/static/src/ts/modules/enrichment.ts`, `.gsd/milestones/M012/slices/S01/`
  - Verify: make build && python3 -m pytest tests/test_api_enrichment.py tests/test_analysis_page.py -q && npx vitest run

## Files Likely Touched

- app/routes/_helpers.py
- app/enrichment/orchestrator.py
- tests/test_routes_helpers.py
- tests/test_orchestrator.py
- app/static/src/ts/modules/enrichment.ts
- app/static/src/ts/modules/results.ts
- app/static/src/ts/modules/status.ts
- app/static/src/ts/modules/__tests__/*.test.ts
- tests/test_analysis_page.py
- tests/test_api_enrichment.py
- .gsd/milestones/M012/slices/S01/
