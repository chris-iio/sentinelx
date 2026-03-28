---
id: S01
parent: M007
milestone: M007
provides:
  - safe_request() in http_safety.py — single canonical HTTP+exception path for all adapters
  - 12 adapter lookup() methods reduced to: build URL/params → safe_request() → parse body
  - 14 unit tests for safe_request() covering all exception types, SSRF, hooks, GET/POST
requires:
  []
affects:
  - S03
key_files:
  - app/enrichment/http_safety.py
  - tests/test_http_safety.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/virustotal.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/urlhaus.py
  - tests/test_routes.py
  - tests/test_history_routes.py
  - tests/test_ioc_detail_routes.py
key_decisions:
  - getattr(session, method.lower()) dispatch preserves existing test mocks (KNOWLEDGE constraint)
  - Exception chain ordering SSLError → ConnectionError enforced as correctness constraint
  - VT _map_http_error() removed — all status code handling consolidated into pre_raise_hook closure
  - Stale route test mocks fixed to use client.application.attr = mock pattern instead of patching removed imports
patterns_established:
  - safe_request() canonical pattern: build URL/params → safe_request(session, url, allowed_hosts, ioc, provider, ...) → isinstance check → parse body
  - Pre-raise hook pattern for status code handling: lambda resp → EnrichmentResult/EnrichmentError or None
  - Route test mock pattern: set client.application.{registry,cache_store,history_store} instead of patching class constructors on app.routes
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M007/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M007/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-27T13:38:34.124Z
blocker_discovered: false
---

# S01: safe_request() consolidation

**Consolidated all 12 HTTP adapters from inline boilerplate to a single safe_request() call in http_safety.py, removing ~500 lines of duplicated exception handling, and fixed 18 stale test mocks — 1057 tests pass.**

## What Happened

Built `safe_request()` in `app/enrichment/http_safety.py` — a single function composing SSRF validation, HTTP dispatch, optional pre-raise hooks, raise_for_status, and byte-limited JSON read. Uses `getattr(session, method.lower())` dispatch (not `session.request()`) to preserve existing test mocks. Exception chain ordering (SSLError before ConnectionError) is enforced as a correctness constraint.

Migrated all 12 HTTP adapters in two batches:
- **T02 (batch 1):** crtsh, threatminer, shodan, hashlookup, ip_api, otx — GET-only adapters. Four use lambda pre-raise hooks for 404→no_data. ThreatMiner uses two sequential safe_request() calls. Tests for crtsh and threatminer needed mock updates from validate_endpoint/read_limited patches to session.get pattern.
- **T03 (batch 2):** abuseipdb, greynoise, virustotal, malwarebazaar, threatfox, urlhaus — includes POST adapters, per-request header removal, VT's compound pre-raise hook (404/429/401/403), and AbuseIPDB's 429 hook. VT's `_map_http_error()` was removed. Six test files needed assertion updates for safe_request error message format.

During closer verification, discovered that task executors had introduced changes to `routes.py` (removing `HistoryStore` import, replacing `Thread` with `ThreadPoolExecutor`, using `current_app.registry` instead of `build_registry()`) that broke 18 tests across `test_routes.py`, `test_history_routes.py`, and `test_ioc_detail_routes.py`. These used stale `patch("app.routes.ClassName")` calls for names no longer imported. Fixed all 18 by switching to `client.application.attr = mock` pattern and patching `_enrichment_pool` instead of `Thread`.

## Verification

All slice-level checks pass:
- `python3 -m pytest -x -q` → 1057 passed, 0 failed
- All 12 adapters use safe_request() (grep count ≥ 1 for each)
- Zero adapters import requests.exceptions
- Zero adapters call validate_endpoint or read_limited directly
- AbuseIPDB and GreyNoise have zero per-request `headers={}` dicts
- `grep -c 'def safe_request' app/enrichment/http_safety.py` → 1

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Closer fixed 18 stale test mocks in test_routes.py, test_history_routes.py, and test_ioc_detail_routes.py that task executors didn't catch (they reported these as "pre-existing" failures). T02 and T03 each needed 2-6 test file updates for mock pattern changes — plan anticipated zero test changes.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/enrichment/http_safety.py` — Added safe_request() with full exception chain, SSRF validation, pre_raise_hook, getattr dispatch
- `tests/test_http_safety.py` — 14 new tests covering safe_request() GET/POST success, SSRF, all exception types, hooks
- `app/enrichment/adapters/crtsh.py` — Replaced inline HTTP boilerplate with safe_request() call
- `app/enrichment/adapters/threatminer.py` — Replaced inline HTTP boilerplate with two safe_request() calls
- `app/enrichment/adapters/shodan.py` — Replaced inline HTTP boilerplate with safe_request() + 404 pre-raise hook
- `app/enrichment/adapters/hashlookup.py` — Replaced inline HTTP boilerplate with safe_request() + 404 pre-raise hook
- `app/enrichment/adapters/ip_api.py` — Replaced inline HTTP boilerplate with safe_request() + 404 pre-raise hook
- `app/enrichment/adapters/otx.py` — Replaced inline HTTP boilerplate with safe_request() + 404 pre-raise hook
- `app/enrichment/adapters/abuseipdb.py` — Replaced inline HTTP boilerplate with safe_request() + 429 pre-raise hook, removed redundant headers
- `app/enrichment/adapters/greynoise.py` — Replaced inline HTTP boilerplate with safe_request() + 404 pre-raise hook, removed redundant headers
- `app/enrichment/adapters/virustotal.py` — Replaced inline HTTP boilerplate with safe_request() + compound pre-raise hook, removed _map_http_error()
- `app/enrichment/adapters/malwarebazaar.py` — Replaced inline HTTP boilerplate with safe_request() POST with data=
- `app/enrichment/adapters/threatfox.py` — Replaced inline HTTP boilerplate with safe_request() POST with json_payload=
- `app/enrichment/adapters/urlhaus.py` — Replaced inline HTTP boilerplate with safe_request() POST with data=
- `tests/test_crtsh.py` — Updated mocks from validate_endpoint/read_limited patches to session.get pattern
- `tests/test_threatminer.py` — Updated mocks from validate_endpoint/read_limited patches to session.get pattern
- `tests/test_abuseipdb.py` — Updated error message assertions for safe_request format
- `tests/test_greynoise.py` — Updated error message assertions for safe_request format
- `tests/test_vt_adapter.py` — Updated error message assertions for safe_request format
- `tests/test_malwarebazaar.py` — Updated error message assertions for safe_request format
- `tests/test_threatfox.py` — Updated error message assertions for safe_request format
- `tests/test_urlhaus.py` — Updated json assertion for safe_request compatibility
- `tests/test_routes.py` — Fixed 6 tests: replaced Thread/build_registry patches with _enrichment_pool/client.application.registry
- `tests/test_history_routes.py` — Fixed 12 tests: replaced HistoryStore patch with direct history_store parameter/client.application.history_store
- `tests/test_ioc_detail_routes.py` — Fixed 3 tests: replaced monkeypatch DEFAULT_DB_PATH with client.application.cache_store
