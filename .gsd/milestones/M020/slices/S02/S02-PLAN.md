# S02: Highest-Risk Rewrite Target

**Goal:** Ship or explicitly reject the highest-ranked M020 rewrite target: centralize duplicate route-owned IOC grouping/template/API payload construction across analysis, API, and history replay while preserving analyst workflow, security, diagnostics, and response-shape contracts.
**Demo:** The top audit-ranked rewrite or optimization is shipped or explicitly rejected with evidence, focused regression tests, and make verify-fast proof.

## Must-Haves

- The S01 audit-ranked request/status helper rewrite is either shipped in code or explicitly rejected with code-path reasoning.
- Focused regression coverage proves analysis route template context, API JSON payload shape, and history replay grouping behavior remain stable, including negative/empty-path coverage.
- The generated M020 audit records the S02 shipped/rejected outcome and retains proof requirements, verification lanes, failure-state visibility, and redaction guardrails.
- `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py tests/test_optimization_audit.py` and `make verify-fast` pass before closeout.

## Proof Level

- This slice proves: integration proof. Real runtime required: no for live providers; yes for Flask/test client route execution. Human/UAT required: no.

## Integration Closure

Upstream surfaces consumed: `.gsd/milestones/M020/M020-AUDIT.md`, `app/routes/analysis.py`, `app/routes/api.py`, `app/routes/history.py`, `app/routes/_helpers.py`, `tests/test_routes.py`, `tests/test_api.py`, `tests/test_history_routes.py`, `tools/optimization_audit.py`, and `tests/test_optimization_audit.py`. New wiring introduced: route modules should delegate shared IOC grouping/template/API payload work to `app/routes/_helpers.py` while keeping route-specific redirects, CSRF/DOM-safety behavior, diagnostics handling, and response ownership in the route files. What remains before M020 is end-to-end complete: later slices must handle the second cross-seam target, analyst-visible optimization/rejection, final audit refresh, and full `make verify`.

## Verification

- The slice preserves failure visibility by keeping online-admission errors, missing-provider redirects, history empty states, diagnostics proof language, and redaction constraints observable through existing route responses/tests and the generated M020 audit outcome row. No new runtime logging surface is required unless implementation discovers a hidden failure state.

## Tasks

- [x] **T01: Lock route helper behavior with focused regressions** `est:1h`
  Expected executor skills: tdd, verify-before-complete.
  - Files: `tests/test_routes.py`, `tests/test_api.py`, `tests/test_history_routes.py`
  - Verify: python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py

- [x] **T02: Centralize duplicate IOC grouping and payload builders** `est:1h30m`
  Expected executor skills: tdd, verify-before-complete.
  - Files: `app/routes/_helpers.py`, `app/routes/analysis.py`, `app/routes/api.py`, `app/routes/history.py`
  - Verify: python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py

- [x] **T03: Record S02 outcome in the generated audit and prove the lane** `est:45m`
  Expected executor skills: verify-before-complete.
  - Files: `tools/optimization_audit.py`, `.gsd/milestones/M020/M020-AUDIT.md`, `tests/test_optimization_audit.py`
  - Verify: make verify-fast

## Files Likely Touched

- tests/test_routes.py
- tests/test_api.py
- tests/test_history_routes.py
- app/routes/_helpers.py
- app/routes/analysis.py
- app/routes/api.py
- app/routes/history.py
- tools/optimization_audit.py
- .gsd/milestones/M020/M020-AUDIT.md
- tests/test_optimization_audit.py
