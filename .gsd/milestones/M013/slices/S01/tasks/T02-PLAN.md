---
estimated_steps: 2
estimated_files: 3
skills_used: []
---

# T02: Run the baseline full-stack audit and publish the first ranked findings

Use the checked-in workflow to run the first full SentinelX optimization pass across the main seams already identified by research: orchestrator/provider dispatch, Flask helper/request flow, WAL-backed cache/history stores, and frontend polling/render coordination. Capture timings where practical; where direct timing is awkward, write the explicit code-path reasoning that justifies the ranking.

Publish the first durable ranked findings artifact in the milestone directory. The artifact must make keep decisions explicit, not implicit, and it must show how the table-stakes continuity requirements stay guarded while the pass identifies true do-now work.

## Inputs

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `app/cache/store.py`
- `app/enrichment/history_store.py`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `tests/test_orchestrator.py`
- `tests/test_routes_helpers.py`
- `tests/test_history_store.py`
- `tests/test_analysis_page.py`
- `tests/test_api_enrichment.py`
- `tests/e2e/conftest.py`

## Expected Output

- `First baseline ranked findings artifact for M013`
- `Per-seam notes covering runtime/provider, request/persistence, and frontend/render boundaries`
- `Explicit continuity guardrail mapping for R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040`

## Verification

python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md

## Observability Impact

Turns the codebase’s major optimization seams into a durable, comparable evidence set instead of ad hoc notes.
