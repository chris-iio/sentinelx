---
id: S03
parent: M011
milestone: M011
provides:
  - Orchestrator test suite runs in <0.1s (was 6.2s)
  - CSS audit evidence: all 207 classes in input.css are actively referenced
requires:
  []
affects:
  []
key_files:
  - tests/test_orchestrator.py
key_decisions:
  - No CSS classes removed — all 207 are referenced (3 via dynamic string concatenation in TS)
  - Set mock_adapter.requires_api_key = False in barrier test to avoid semaphore gating (MagicMock attrs are truthy by default)
  - Used simpler synchronous approach for test_zero_auth_completes_without_waiting_for_vt (Event.wait(timeout=0.01)) instead of threaded approach
patterns_established:
  - threading.Barrier for structural parallelism proof — barrier only releases when all N threads arrive, proving concurrency without wall-clock assertions
  - threading.Event coordination for concurrency measurement — Event.set() when threshold reached, Event.wait() to hold threads until measured
  - Defensive time.sleep patch on all concurrency tests — even when sleep isn't in the test's own mock, the orchestrator retry path calls sleep, so always patch app.enrichment.orchestrator.time.sleep
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M011/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T12:55:24.575Z
blocker_discovered: false
---

# S03: Dead CSS Removal & Orchestrator Test Speed

**Verified all 207 CSS classes in input.css are actively referenced (zero dead CSS), and rewrote 7 orchestrator tests to eliminate real time.sleep calls — full suite now runs in 0.09s (down from 6.2s).**

## What Happened

This slice addressed two independent cleanup targets: CSS dead-code audit and orchestrator test speed.

**CSS Audit (T01 Part B):** A cross-reference of all 207 custom CSS classes in input.css against templates (.html) and TypeScript (.ts) files found zero dead classes. Three classes that appear unreferenced in literal grep (`micro-bar-segment--suspicious`, `verdict-known_good`, `verdict-label--known_good`) are constructed via string concatenation at runtime: `row-factory.ts:336` builds `"micro-bar-segment micro-bar-segment--" + verdict`, `row-factory.ts:309/416` builds `"verdict-badge verdict-" + verdict`, and `cards.ts:60` builds `"verdict-label--" + worstVerdict`. No classes were removed — the CSS is fully utilized.

**Orchestrator Test Speed (T01 Part A + T02):** Seven tests in `test_orchestrator.py` were responsible for ~6.2s of wall-clock time due to real `time.sleep()` calls:

- **T01** patched 4 retry-path tests (`test_error_isolation`, `test_retry_on_failure`, `test_retry_still_fails`, `test_adapter_failure_isolated_across_providers`) with `with patch("app.enrichment.orchestrator.time.sleep"):` — the exact pattern already used by existing backoff tests. Each dropped from ~1.0s to <0.005s.

- **T02** rewrote 3 concurrency tests that used `time.sleep()` inside mock side-effect functions:
  - `test_enrich_all_parallel_execution`: replaced sleep(0.5) + wall-clock assertion with `threading.Barrier(5, timeout=2)` that structurally proves all 5 threads run concurrently (barrier only releases when all 5 arrive). Required explicitly setting `mock_adapter.requires_api_key = False` because MagicMock's truthy default triggered semaphore gating.
  - `test_vt_peak_concurrency_capped_at_4`: kept counter+lock peak measurement, replaced `time.sleep(0.3)` with `threading.Event` coordination (batch_full event set when 4 threads enter, threads hold until measured).
  - `test_zero_auth_completes_without_waiting_for_vt`: replaced VT `time.sleep(0.3)` with `Event.wait(timeout=0.01)` (near-instant expiry). Simpler synchronous approach chosen over threaded approach since the original test only asserted all 16 results + 8 DNS calls, not temporal ordering.

**Result:** 27 orchestrator tests pass in 0.09s (target: <1s). 1012 total tests pass with zero failures.

## Verification

Ran slice-level verification independently:

1. `python3 -m pytest tests/test_orchestrator.py -q --durations=10` → 27 passed in 0.09s. Only 1 test visible in slowest durations (test_zero_auth at 0.02s). All 7 previously-slow tests now <0.005s.

2. `python3 -m pytest --tb=short -q` → 1012 passed in 44.17s. Zero failures, zero warnings.

3. CSS audit verified: grep confirmed dynamic class references at row-factory.ts:336, row-factory.ts:309/416, cards.ts:60. All 207 classes accounted for.

## Requirements Advanced

- R058 — CSS audit verified all 207 classes referenced — zero dead CSS. 3 dynamic classes confirmed via string concatenation in row-factory.ts and cards.ts.
- R059 — All 7 slow orchestrator tests patched/rewritten. Suite runs in 0.09s (target <1s, baseline 6.2s). 1012 total tests pass.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 required setting `mock_adapter.requires_api_key = False` in the barrier test — the plan's Barrier(5) approach didn't account for MagicMock's truthy default on unset attributes, which triggered semaphore gating that capped concurrency at 4 and caused barrier deadlock. T02 also used the simpler synchronous approach for test_zero_auth instead of the threaded approach described in the plan.

## Known Limitations

None.

## Follow-ups

R058 and R059 exist in REQUIREMENTS.md but not in the GSD database (added outside tool chain). They should be validated: R058 (all 207 CSS classes referenced, zero removed) and R059 (orchestrator suite 0.09s, target <1s).

## Files Created/Modified

- `tests/test_orchestrator.py` — Patched time.sleep in 4 retry-path tests; rewrote 3 concurrency tests with threading.Barrier/Event primitives
- `.gsd/KNOWLEDGE.md` — Added MagicMock truthy-default gotcha for adapter boolean flags
- `.gsd/PROJECT.md` — Updated current state to reflect M011 S03 completion
