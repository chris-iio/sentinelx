---
estimated_steps: 7
estimated_files: 3
skills_used: []
---

# T01: Lock route helper behavior with focused regressions

Expected executor skills: tdd, verify-before-complete.

Why: S02 changes request/status route seams that shape analyst-visible intake, enrichment results, history replay, diagnostics links, and API payloads. Before moving grouping/serialization code, pin the current contracts with tests that do not read `.gsd/` or other ignored planning paths.

Threat Surface (Q3): User-submitted IOCs and persisted enrichment rows reach HTML templates and JSON responses; preserve existing DOM-safety/CSRF/redirect behavior and do not expose secrets. Requirement Impact (Q4): touches R096, supports R097/R098/R099/R100, and must preserve D082/D083.

Failure Modes (Q5): Empty or missing provider state must keep the existing redirect/empty payload behavior; malformed or incomplete persisted rows must not crash history replay; API serialization must keep diagnostics/error fields visible but redacted according to existing helpers.

Load Profile (Q6): Shared resource is in-memory route payload construction over IOC/result rows; per-operation cost should remain linear in result count; 10x load should not add duplicate grouping passes across route modules.

Negative Tests (Q7): Cover empty history replay/no IOCs, duplicate normalized IOC values, provider/error diagnostics fields, and grouped template/API boundary shapes where existing fixtures make those paths practical.

Do: Inspect the existing route tests, then add or tighten tests in `tests/test_routes.py`, `tests/test_api.py`, and `tests/test_history_routes.py` that characterize the highest-risk contracts: analysis template IOC context/grouping, API serialized IOC response shape, history replay grouping/empty-state behavior, and failure/diagnostic visibility. Prefer assertions against public route responses/test-client behavior over private implementation details. Done when these tests fail against an intentionally broken grouping/serialization seam and pass against the current intended behavior.

## Inputs

- `app/routes/analysis.py`
- `app/routes/api.py`
- `app/routes/history.py`
- `app/routes/_helpers.py`
- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Expected Output

- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`

## Verification

python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py

## Observability Impact

Adds executable inspection of route-visible failure states: redirects/empty states, diagnostics/error fields, grouped payloads, and safe response rendering remain visible to future agents through focused pytest failures.
