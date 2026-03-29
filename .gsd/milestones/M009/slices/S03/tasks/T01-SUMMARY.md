---
id: T01
parent: S03
milestone: M009
provides: []
requires: []
affects: []
key_files: ["tests/test_adapter_contract.py"]
key_decisions: ["Used dataclass AdapterEntry registry pattern for test parametrization rather than pytest fixtures or conftest factories"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran python3 -m pytest tests/test_adapter_contract.py -v (172 passed in 0.23s) and python3 -m pytest tests/ -x -q --ignore=tests/e2e (1155 passed in 9.69s, 0 failures)."
completed_at: 2026-03-29T19:29:14.769Z
blocker_discovered: false
---

# T01: Created tests/test_adapter_contract.py with 172 parametrized tests covering protocol/error/type-guard/safety contracts for all 15 adapters

> Created tests/test_adapter_contract.py with 172 parametrized tests covering protocol/error/type-guard/safety contracts for all 15 adapters

## What Happened
---
id: T01
parent: S03
milestone: M009
key_files:
  - tests/test_adapter_contract.py
key_decisions:
  - Used dataclass AdapterEntry registry pattern for test parametrization rather than pytest fixtures or conftest factories
duration: ""
verification_result: passed
completed_at: 2026-03-29T19:29:14.771Z
blocker_discovered: false
---

# T01: Created tests/test_adapter_contract.py with 172 parametrized tests covering protocol/error/type-guard/safety contracts for all 15 adapters

**Created tests/test_adapter_contract.py with 172 parametrized tests covering protocol/error/type-guard/safety contracts for all 15 adapters**

## What Happened

Built a shared parametrized adapter contract test module with an ADAPTER_REGISTRY of 15 AdapterEntry dataclass instances. 12 test classes cover: protocol conformance, adapter name, requires_api_key, is_configured, supported/excluded types, unsupported type rejection, timeout handling, HTTP 500 errors, SSRF validation, response size limits, and Config.ALLOWED_API_HOSTS membership. All 172 tests pass. Full suite (1155 tests) passes with 0 failures.

## Verification

Ran python3 -m pytest tests/test_adapter_contract.py -v (172 passed in 0.23s) and python3 -m pytest tests/ -x -q --ignore=tests/e2e (1155 passed in 9.69s, 0 failures).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_adapter_contract.py -v` | 0 | ✅ pass | 3900ms |
| 2 | `python3 -m pytest tests/ -x -q --ignore=tests/e2e` | 0 | ✅ pass | 10100ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_adapter_contract.py`


## Deviations
None.

## Known Issues
None.
