---
id: T01
parent: S01
milestone: M003
provides:
  - Per-provider threading.Semaphore dict in EnrichmentOrchestrator (default cap 4 for requires_api_key=True adapters)
  - max_workers default raised from 4 to 20 (thread pool no longer the concurrency gate)
  - _do_lookup refactored: semaphore wraps entire lookup+retry cycle via extracted _do_lookup_inner
  - TestPerProviderSemaphore test class (4 tests) proving VT capped at ≤4, zero-auth unblocked
key_files:
  - app/enrichment/orchestrator.py
  - tests/test_orchestrator.py
key_decisions:
  - Semaphore wraps entire _do_lookup_inner body (cache-check + lookup + retry), not per-attempt, to avoid re-entrant deadlock
  - Zero-auth adapters (requires_api_key=False) get no semaphore; unlimited concurrency preserved
  - provider_concurrency dict parameter allows per-name cap overrides at construction time
patterns_established:
  - _do_lookup → _do_lookup_inner split: outer method handles semaphore acquisition, inner method contains all business logic
  - MagicMock adapters without explicit requires_api_key are treated as keyed (truthy attribute) — harmless for small test batches
observability_surfaces:
  - No new runtime endpoints; semaphore state is internal
  - Future: logging.warning for 429 backoff (added in T02, not this task)
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Add per-provider semaphore dict and raise max_workers

**Added per-provider threading.Semaphore to EnrichmentOrchestrator so VT (and any requires_api_key=True provider) is capped at ≤4 concurrent lookups while zero-auth providers run freely, with max_workers raised from 4 to 20 to remove thread-pool starvation.**

## What Happened

Read `orchestrator.py`, `provider.py`, and the existing 15-test suite before writing any code.

Modified `app/enrichment/orchestrator.py`:
- Extended `from threading import Lock` to `from threading import Lock, Semaphore`
- Added optional `provider_concurrency: dict[str, int] | None = None` parameter to `__init__()`
- Raised `max_workers` default from `4` to `20` (thread pool is no longer the real gate)
- Added `self._semaphores` dict: iterates all adapters; for each with `requires_api_key=True` and a non-empty `name`, creates `Semaphore(concurrency.get(name, 4))`
- Refactored `_do_lookup()` into two methods: `_do_lookup()` (acquires semaphore if present, then delegates) and `_do_lookup_inner()` (all cache/lookup/retry/cache-store logic). The semaphore wraps the *entire* inner cycle, not individual attempts, to avoid re-entrant deadlock.

Modified `tests/test_orchestrator.py`:
- Added `threading` import
- Added helper functions `_make_keyed_adapter()` and `_make_public_adapter()` setting explicit `requires_api_key` bool
- Added `TestPerProviderSemaphore` class with 4 tests:
  1. `test_vt_peak_concurrency_capped_at_4` — 8 IOCs, slow VT (0.3s), shared counter proves peak ≤ 4
  2. `test_zero_auth_completes_without_waiting_for_vt` — instant DNS adapter completes all 8 lookups while VT is running; all 16 results present
  3. `test_semaphore_built_only_for_keyed_adapters` — asserts empty semaphore dict for public-only orchestrator, single entry for keyed
  4. `test_provider_concurrency_override` — verifies `_value` of semaphores matches default (4) vs custom (2) config

## Verification

Ran `python3 -m pytest tests/test_orchestrator.py -v`: all 19 tests passed (15 pre-existing + 4 new) in 2.27s.

Ran `python3 -m pytest tests/ -q --ignore=tests/e2e`: 803 tests passed, 1 pre-existing failure (`test_analyze_deduplicates` in `tests/test_routes.py`) confirmed to fail on the baseline before this task's changes — not a regression.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_orchestrator.py -v` | 0 | ✅ pass | 2.27s |
| 2 | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 1 | ✅ pass (pre-existing failure confirmed unrelated) | 5.07s |
| 3 | `git stash && pytest tests/test_routes.py::test_analyze_deduplicates` (baseline) | 1 | ✅ pre-existing, not a regression | <1s |

## Diagnostics

Per-provider semaphores are internal to `EnrichmentOrchestrator`. To inspect at runtime:
- `orchestrator._semaphores` — dict of `{provider_name: Semaphore}`; check `._value` on any entry to see remaining slots
- If peak concurrency is unexpectedly high, add a counter/lock to `_do_lookup_inner` (same pattern as test)
- Semaphore exhaustion shows as thread contention but never deadlocks: the entire inner cycle is wrapped, so a thread holding the semaphore will always release it (finally-safe `with` block)

## Deviations

None. Implementation followed the plan exactly, including the `_do_lookup` → `_do_lookup_inner` split.

## Known Issues

`tests/test_routes.py::test_analyze_deduplicates` was failing before this task and continues to fail — unrelated to orchestrator changes.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — raised max_workers to 20, added _semaphores dict, refactored _do_lookup/_do_lookup_inner
- `tests/test_orchestrator.py` — added threading import, two helper factories, TestPerProviderSemaphore class (4 tests)
