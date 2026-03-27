---
id: T02
parent: S01
milestone: M007
provides: []
requires: []
affects: []
key_files: ["app/enrichment/adapters/crtsh.py", "app/enrichment/adapters/threatminer.py", "app/enrichment/adapters/shodan.py", "app/enrichment/adapters/hashlookup.py", "app/enrichment/adapters/ip_api.py", "app/enrichment/adapters/otx.py", "tests/test_crtsh.py", "tests/test_threatminer.py"]
key_decisions: ["Pre-raise hooks use lambda closures for 404→no_data pattern in shodan, hashlookup, ip_api, otx", "crtsh/threatminer tests updated to session.get mock pattern per KNOWLEDGE consolidation-refactor guidance"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "257 adapter tests pass. Full suite: 1036 pass, 20 pre-existing failures (stale mock patches in test_history_routes/test_ioc_detail_routes/test_routes, confirmed on clean main). All 6 adapters use safe_request(), none import requests.exceptions, none call validate_endpoint/read_limited directly."
completed_at: 2026-03-27T13:05:00.623Z
blocker_discovered: false
---

# T02: Migrated 6 GET adapters (crtsh, threatminer, shodan, hashlookup, ip_api, otx) from inline HTTP boilerplate to safe_request(), removing 258 lines of duplicated exception handling

> Migrated 6 GET adapters (crtsh, threatminer, shodan, hashlookup, ip_api, otx) from inline HTTP boilerplate to safe_request(), removing 258 lines of duplicated exception handling

## What Happened
---
id: T02
parent: S01
milestone: M007
key_files:
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/otx.py
  - tests/test_crtsh.py
  - tests/test_threatminer.py
key_decisions:
  - Pre-raise hooks use lambda closures for 404→no_data pattern in shodan, hashlookup, ip_api, otx
  - crtsh/threatminer tests updated to session.get mock pattern per KNOWLEDGE consolidation-refactor guidance
duration: ""
verification_result: passed
completed_at: 2026-03-27T13:05:00.623Z
blocker_discovered: false
---

# T02: Migrated 6 GET adapters (crtsh, threatminer, shodan, hashlookup, ip_api, otx) from inline HTTP boilerplate to safe_request(), removing 258 lines of duplicated exception handling

**Migrated 6 GET adapters (crtsh, threatminer, shodan, hashlookup, ip_api, otx) from inline HTTP boilerplate to safe_request(), removing 258 lines of duplicated exception handling**

## What Happened

Migrated each adapter mechanically: replaced validate_endpoint/read_limited/TIMEOUT imports and requests.exceptions imports with a single safe_request import. Replaced the entire try/except block in each lookup() with a safe_request() call + isinstance(result, EnrichmentError) check. Four adapters use pre_raise_hook lambdas for 404→no_data. ThreatMiner uses two sequential safe_request() calls for domain lookups. Tests for crtsh and threatminer needed mock updates from validate_endpoint/read_limited patches to session.get mock pattern.

## Verification

257 adapter tests pass. Full suite: 1036 pass, 20 pre-existing failures (stale mock patches in test_history_routes/test_ioc_detail_routes/test_routes, confirmed on clean main). All 6 adapters use safe_request(), none import requests.exceptions, none call validate_endpoint/read_limited directly.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_crtsh.py tests/test_threatminer.py tests/test_shodan.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v` | 0 | ✅ pass | 5100ms |
| 2 | `grep -c 'safe_request' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx}.py` | 0 | ✅ pass | 100ms |
| 3 | `grep -c 'requests.exceptions' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx}.py` | 1 | ✅ pass (all 0) | 100ms |
| 4 | `python3 -m pytest -q --deselect test_history_routes::test_save_called (full suite)` | 1 | ✅ pass (1036 pass, 20 pre-existing fail) | 103100ms |


## Deviations

crtsh and threatminer test files needed mock updates (2 of 6, not 0 as plan anticipated). 20 pre-existing test failures in unrelated test files.

## Known Issues

20 pre-existing test failures in test_history_routes.py, test_ioc_detail_routes.py, test_routes.py — stale mock patches for app.routes.HistoryStore and app.routes.Thread.

## Files Created/Modified

- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/otx.py`
- `tests/test_crtsh.py`
- `tests/test_threatminer.py`


## Deviations
crtsh and threatminer test files needed mock updates (2 of 6, not 0 as plan anticipated). 20 pre-existing test failures in unrelated test files.

## Known Issues
20 pre-existing test failures in test_history_routes.py, test_ioc_detail_routes.py, test_routes.py — stale mock patches for app.routes.HistoryStore and app.routes.Thread.
