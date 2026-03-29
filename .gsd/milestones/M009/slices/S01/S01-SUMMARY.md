---
id: S01
parent: M009
milestone: M009
provides:
  - BaseHTTPAdapter abstract base class in app/enrichment/adapters/base.py
  - Proven migration recipe for S02 (11 remaining HTTP adapters)
  - 21 contract tests in tests/test_base_adapter.py
requires:
  []
affects:
  - S02
key_files:
  - app/enrichment/adapters/base.py
  - tests/test_base_adapter.py
  - app/enrichment/adapters/shodan.py
key_decisions:
  - D049: BaseHTTPAdapter uses abc.ABC with template-method pattern — absorbs __init__, is_configured, lookup; subclasses define only _build_url, _parse_response, and optional overrides
  - ShodanAdapter._parse_response bridges to module-level _parse_response() function via self.name, keeping verdict logic untouched and co-located
patterns_established:
  - BaseHTTPAdapter migration recipe: remove __init__/is_configured/lookup, subclass BaseHTTPAdapter, implement _build_url + _parse_response, optionally override _auth_headers/_make_pre_raise_hook/_http_method/_build_request_body
  - Bridge pattern for _parse_response: adapter method delegates to existing module-level function, preserving co-located verdict logic while satisfying the abstract interface
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M009/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T16:32:19.658Z
blocker_discovered: false
---

# S01: BaseHTTPAdapter + proof migration

**Created BaseHTTPAdapter abstract base class with template-method lookup pipeline and migrated ShodanAdapter as proof — 21 base tests + 25 Shodan tests pass, proving the migration recipe for S02.**

## What Happened

Built `app/enrichment/adapters/base.py` with a full template-method skeleton: `__init__` creates a `requests.Session` with auth headers, `is_configured()` gates on `requires_api_key`, and `lookup()` runs the pipeline: type guard → `_build_url()` → `_make_pre_raise_hook()` → `_build_request_body()` → `safe_request()` → isinstance check → `_parse_response()`. Two abstract methods (`_build_url`, `_parse_response`) and four override points (`_auth_headers`, `_make_pre_raise_hook`, `_http_method`, `_build_request_body`).

Created `tests/test_base_adapter.py` with 4 stub subclasses (zero-auth GET, API-key GET, API-key POST, hook-enabled) and 21 tests across 9 test classes covering: Provider protocol conformance, `is_configured()` logic, type guard rejection, GET/POST dispatch through `safe_request()`, auth header injection, pre-raise hook wiring and short-circuiting, and abstract enforcement.

Migrated `ShodanAdapter` (simplest HTTP adapter) to subclass `BaseHTTPAdapter`. Removed `__init__`, `is_configured`, and `lookup` methods — inherited from base. The adapter now defines only 3 overrides: `_build_url`, `_make_pre_raise_hook` (404→no_data), and `_parse_response` (bridges to the existing module-level function). All 25 Shodan tests pass with zero modifications to the test file, confirming backward compatibility. Shodan went from 167 → 127 lines (24% reduction).

The migration recipe proven here: (1) remove `__init__`, `is_configured`, `lookup`; (2) add `class Adapter(BaseHTTPAdapter)`; (3) implement `_build_url` and `_parse_response`; (4) optionally override `_make_pre_raise_hook`, `_auth_headers`, `_http_method`, `_build_request_body`. Tests should pass unchanged because the base class implements the exact same contract that every adapter previously implemented inline.

## Verification

All slice-level verification checks pass:

1. `python3 -m pytest tests/test_base_adapter.py -v` — 21/21 passed
2. `python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; print('import OK')"` — OK
3. Protocol conformance isinstance check — OK
4. `python3 -m pytest tests/test_shodan.py -v` — 25/25 passed
5. `isinstance(ShodanAdapter(allowed_hosts=[...]), Provider)` — True
6. `build_registry(...)` — 15 providers created successfully
7. `grep -c 'class ShodanAdapter(BaseHTTPAdapter)' app/enrichment/adapters/shodan.py` — 1 match
8. Full unit test suite (855 tests) — all pass (5 failures and 87 errors are pre-existing `iocextract` module absence, unrelated to S01)

## Requirements Advanced

- R041 — BaseHTTPAdapter exists with full template-method skeleton. Shodan successfully migrated as proof. Recipe validated — ready for S02 to complete remaining 11 adapters.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

S02 migrates the remaining 11 HTTP adapters using the recipe proven here.

## Files Created/Modified

- `app/enrichment/adapters/base.py` — New file — BaseHTTPAdapter abstract base class with template-method lookup pipeline, session management, is_configured gating, and 4 override points
- `tests/test_base_adapter.py` — New file — 21 tests across 9 classes covering protocol conformance, auth, POST dispatch, hooks, type guard, and abstract enforcement
- `app/enrichment/adapters/shodan.py` — Rewritten to subclass BaseHTTPAdapter — removed __init__/is_configured/lookup, kept only _build_url/_make_pre_raise_hook/_parse_response overrides (167→127 lines)
