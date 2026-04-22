---
estimated_steps: 1
estimated_files: 4
skills_used: []
---

# T01: Define and implement explicit terminal status semantics

Inspect the current `_helpers.py` status serialization path, orchestrator lifecycle, and frontend polling/error handling to identify the smallest contract change that can represent terminal failure without breaking existing success/progress semantics. Document the contract shape in code comments or nearby tests as needed, then implement the backend status payload update and any required helper/runtime distinctions for unknown, evicted, or terminally failed jobs.

## Inputs

- `app/routes/_helpers.py`
- `app/enrichment/orchestrator.py`
- `existing enrichment route/helper tests`

## Expected Output

- `Explicit status payload semantics in Flask/helper code`
- `Backend tests covering terminal-status serialization and missing/evicted job behavior`

## Verification

python3 -m pytest tests/test_routes_helpers.py tests/test_orchestrator.py -q

## Observability Impact

Turns ambiguous polling failures into explicit backend states future slices and analysts can reason about.
