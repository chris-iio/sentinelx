# S03: Best Optimization Implementation

**Goal:** Ship the M017 do-now optimization for SentinelX’s analyst IOC triage loop by ensuring enrichment status polling uses tail-only snapshots instead of repeated full result-list snapshots, with focused proof, refreshed audit evidence, and behavior-preserving regressions.
**Demo:** The highest-value optimization from the M017 audit is shipped with measurement or code-path proof and behavior-preserving tests.

## Must-Haves

- The status polling route in `app/routes/_helpers.py` obtains cursor responses through the tail-only `EnrichmentOrchestrator.get_incremental_status()` contract in `app/enrichment/orchestrator.py`, without paying a full `get_status()` result-list copy on normal polling.
- Focused tests cover route cursor behavior, tail-only cached marker alignment, terminal/unknown/evicted behavior, negative/out-of-range `since` compatibility, and proof that the route does not call the full status snapshot for live polling.
- The M017 audit artifact is regenerated after the optimization and contains current measurement or explicit code-path proof for the shipped S03 optimization.
- Analyst-facing IOC intake, enrichment polling, results continuity, history persistence, diagnostics snapshots, cache markers, provider retry/backoff, and security/redaction behavior remain intact.
- Verification evidence includes focused pytest, `make verify-fast`, and `make verify-deep` because this slice touches live enrichment/status polling.

## Proof Level

- This slice proves: Integration proof. Real runtime required: yes for repo verification commands; human/UAT required: no. Threat surface: user-controlled `job_id` path parameter and `since` query parameter continue to reach in-memory job lookup only; no secrets or analyst IOC values may be added to logs/audit evidence. Requirement impact: owns R086 and supports R087/R088; re-verify enrichment polling, diagnostics, cache-marker serialization, history save continuity, and mocked-online browser flow. Failure modes: missing/evicted/failed jobs must remain explicit terminal payloads instead of hidden performance shortcuts. Load profile: shared resources are the in-memory orchestrator registry, per-job result lists, cache-marker map, and bounded thread pools; per-poll cost should be O(delta results) serialization plus scalar snapshot, not O(all retained results) list copying; at 10x polling/result volume the first breakpoint should not be Python list snapshot churn on every status request. Negative tests: malformed/out-of-range/negative `since`, unknown job, evicted job, failed job, and cached-marker tails.

## Integration Closure

Upstream surfaces consumed: S02’s M017 audit target, `docs/project-map.md`, `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`, `app/routes/enrichment.py`, `app/pipeline/models.py`, and existing route/orchestrator tests. New wiring introduced: the normal Flask status route must rely on the orchestrator’s incremental status contract and audit regeneration must record the shipped proof. Remaining before milestone end-to-end usability: S04 may address browser rendering churn or explicitly reject it; S05 still must run final integrated proof.

## Verification

- Runtime signals are unchanged response fields (`status`, `terminal`, `terminal_reason`, `error`, `next_since`) plus existing safe diagnostics from `get_orchestration_diagnostics_snapshot()`. Inspection surfaces are `/enrichment/status/<job_id>`, focused pytest assertions, `make audit-m017`, and `.gsd/milestones/M017/M017-AUDIT.md`. Failure visibility must preserve job_failed/unknown/evicted terminal states and bounded, redacted diagnostics; no API keys, tokens, or raw analyst-sensitive IOC payloads may be emitted.

## Tasks

- [x] **T01: Lock the incremental status contract with focused regressions** `est:45m`
  ---
  estimated_steps: 6
  estimated_files: 2
  skills_used:
    - tdd
    - test
  ---
  - Files: `tests/test_orchestrator.py`, `tests/test_routes.py`
  - Verify: python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py -k "IncrementalStatusSnapshot or enrichment_status"

- [x] **T02: Ship tail-only enrichment status snapshots** `est:1h`
  ---
  estimated_steps: 7
  estimated_files: 2
  skills_used:
    - tdd
    - best-practices
  ---
  - Files: `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`
  - Verify: python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py

- [ ] **T03: Refresh M017 audit evidence for the shipped optimization** `est:30m`
  ---
  estimated_steps: 5
  estimated_files: 3
  skills_used:
    - test
    - write-docs
  ---
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M017/M017-AUDIT.md`
  - Verify: python3 -m pytest -q tests/test_optimization_audit.py && python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md

- [ ] **T04: Run integrated regression proof for analyst continuity** `est:45m`
  ---
  estimated_steps: 4
  estimated_files: 0
  skills_used:
    - verify-before-complete
    - test
  ---
  - Files: `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`, `tests/test_orchestrator.py`, `tests/test_routes.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M017/M017-AUDIT.md`
  - Verify: python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py tests/test_optimization_audit.py && make verify-fast && make verify-deep && python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md

## Files Likely Touched

- tests/test_orchestrator.py
- tests/test_routes.py
- app/enrichment/orchestrator.py
- app/routes/_helpers.py
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M017/M017-AUDIT.md
