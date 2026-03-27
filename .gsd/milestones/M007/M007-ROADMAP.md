# M007: 

## Vision
Eliminate dead code, consolidate duplicated HTTP boilerplate across 12 adapters via safe_request(), trim bloated adapter docstrings, remove dead CSS, and standardize test helper usage. Pure cleanup — zero behavior changes, 1043 tests as safety net.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | safe_request() consolidation | medium | — | ⬜ | Every HTTP adapter's lookup() is: build URL/params → call safe_request() → parse body. http_safety.py has the single canonical HTTP+exception path. All tests pass. |
| S02 | Docstring trimming & dead CSS | low | — | ⬜ | Adapter files are ~40% shorter. SEC control docs live once in http_safety.py. consensus-badge CSS gone. |
| S03 | Test DRY-up | low | S01 | ⬜ | Adapter test files use shared make_mock_response/make_*_ioc factories. Inline MagicMock setup eliminated. |
