---
id: T01
parent: S03
milestone: M011
provides: []
requires: []
affects: []
key_files: ["tests/test_orchestrator.py"]
key_decisions: ["No CSS classes removed — all 207 are referenced (3 via dynamic string concatenation in TS)"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "python3 -m pytest tests/test_orchestrator.py -q --durations=10 → 27 passed in 2.30s, patched tests hidden at <0.005s. python3 -m pytest --tb=short -q → 1012 passed in 48.14s. Grep confirmed dynamic class references in row-factory.ts:336, row-factory.ts:309,416, cards.ts:60."
completed_at: 2026-04-04T12:42:50.163Z
blocker_discovered: false
---

# T01: Patched time.sleep in 4 orchestrator retry-path tests (each now <0.005s, down from ~1.0s) and verified all 207 CSS classes in input.css are actively referenced

> Patched time.sleep in 4 orchestrator retry-path tests (each now <0.005s, down from ~1.0s) and verified all 207 CSS classes in input.css are actively referenced

## What Happened
---
id: T01
parent: S03
milestone: M011
key_files:
  - tests/test_orchestrator.py
key_decisions:
  - No CSS classes removed — all 207 are referenced (3 via dynamic string concatenation in TS)
duration: ""
verification_result: passed
completed_at: 2026-04-04T12:42:50.164Z
blocker_discovered: false
---

# T01: Patched time.sleep in 4 orchestrator retry-path tests (each now <0.005s, down from ~1.0s) and verified all 207 CSS classes in input.css are actively referenced

**Patched time.sleep in 4 orchestrator retry-path tests (each now <0.005s, down from ~1.0s) and verified all 207 CSS classes in input.css are actively referenced**

## What Happened

Added `with patch("app.enrichment.orchestrator.time.sleep"):` around enrich_all() and assertions in test_error_isolation, test_retry_on_failure, test_retry_still_fails, and test_adapter_failure_isolated_across_providers. All four now complete in <0.005s (previously ~1.0s each). Verified CSS audit: all 207 custom classes are referenced, including 3 constructed via string concatenation in TypeScript (row-factory.ts and cards.ts).

## Verification

python3 -m pytest tests/test_orchestrator.py -q --durations=10 → 27 passed in 2.30s, patched tests hidden at <0.005s. python3 -m pytest --tb=short -q → 1012 passed in 48.14s. Grep confirmed dynamic class references in row-factory.ts:336, row-factory.ts:309,416, cards.ts:60.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_orchestrator.py -q --durations=10` | 0 | ✅ pass | 2300ms |
| 2 | `python3 -m pytest --tb=short -q` | 0 | ✅ pass | 48140ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_orchestrator.py`


## Deviations
None.

## Known Issues
None.
