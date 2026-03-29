---
id: S02
parent: M009
milestone: M009
provides:
  - All 12 HTTP adapters unified under BaseHTTPAdapter hierarchy
  - Three migration patterns documented: simple GET, POST, complex override
requires:
  - slice: S01
    provides: BaseHTTPAdapter base class and proven Shodan migration recipe
affects:
  - S03
key_files:
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/virustotal.py
  - app/enrichment/adapters/threatminer.py
  - tests/e2e/conftest.py
key_decisions:
  - POST body encoding distinguished via _build_request_body: form-encoded returns (data, None), JSON returns (None, json_payload)
  - CrtSh, VT, and ThreatMiner override lookup() entirely rather than fitting into the base template — pragmatic over uniform
  - ThreatMiner abstract methods raise NotImplementedError rather than implementing no-op stubs, since lookup() never calls them
  - VT _build_url() uses ENDPOINT_MAP meaningfully rather than a stub
patterns_established:
  - Simple GET adapters: subclass BaseHTTPAdapter, implement _build_url + _parse_response + optional _auth_headers/_make_pre_raise_hook, inherit everything else
  - POST adapters: add _http_method = 'POST' + _build_request_body() returning (data, None) for form-encoded or (None, json) for JSON
  - Complex adapters (multi-call or non-dict response): override lookup() entirely, implement abstract methods as stubs or meaningful implementations
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M009/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T17:58:39.631Z
blocker_discovered: false
---

# S02: Migrate remaining 11 HTTP adapters

**All 12 HTTP adapters now subclass BaseHTTPAdapter; 3 non-HTTP adapters unchanged; 983 tests pass.**

## What Happened

Migrated the remaining 11 HTTP adapters (after Shodan in S01) to subclass BaseHTTPAdapter in three batches:

**T01 — 5 simple GET adapters** (abuseipdb, greynoise, hashlookup, ip_api, otx): Cleanest migrations. Removed `__init__`, `is_configured`, and `lookup` entirely. Each adapter now defines only `_build_url()`, `_parse_response()`, and optionally `_auth_headers()` and `_make_pre_raise_hook()`. All 188 tests passed unchanged.

**T02 — 3 POST adapters + 1 list-response GET** (malwarebazaar, threatfox, urlhaus, crtsh): POST adapters added `_http_method = "POST"` and `_build_request_body()` overrides. Form-encoded bodies (MalwareBazaar, URLhaus) return `(data, None)`; JSON bodies (ThreatFox) return `(None, json_payload)`. CrtSh required a full `lookup()` override because `safe_request()` returns a list not dict. All 97 tests passed unchanged.

**T03 — 2 complex adapters** (virustotal, threatminer): Both override `lookup()` entirely — VT uses ENDPOINT_MAP lambdas for URL construction, ThreatMiner dispatches to 3 sub-methods for IP/domain/hash lookups. VT's `supported_types` converted from `set` to `frozenset`. ThreatMiner's abstract methods raise NotImplementedError with explanatory messages. All 86 adapter tests passed.

**Environment fix during closure:** `iocextract`, `iocsearcher`, and `playwright` were missing from the test environment. Installed `iocextract` and `iocsearcher`; added `pytest.importorskip("playwright.sync_api")` guard to `tests/e2e/conftest.py` to prevent e2e collection failures when Playwright isn't installed. Final full suite: 983 passed, 1 skipped.

## Verification

All verification checks pass:
- 983 tests pass (`python3 -m pytest tests/ -x -q --ignore=tests/e2e` → 983 passed; full run with e2e guarded → 983 passed, 1 skipped)
- 12 non-base adapter files contain `class.*BaseHTTPAdapter` (grep verified)
- 3 non-HTTP adapters (dns_lookup, asn_cymru, whois_lookup) contain 0 references to BaseHTTPAdapter
- Registry instantiates all 15 providers (`build_registry()` → 15 providers OK)
- No stale `__init__`, `is_configured`, or `lookup` methods in the 6 simple adapters
- POST adapters have `_http_method = "POST"` (malwarebazaar, threatfox, urlhaus)
- CrtSh, VT, and ThreatMiner override `lookup()` as expected

## Requirements Advanced

None.

## Requirements Validated

- R042 — All 12 HTTP adapters subclass BaseHTTPAdapter — verified by grep (12 files) and 983 passing tests
- R043 — dns_lookup.py, asn_cymru.py, whois_lookup.py contain 0 BaseHTTPAdapter references — verified by grep

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Added pytest.importorskip guard to tests/e2e/conftest.py — pre-existing missing dependency issue, not planned in slice scope. Installed iocextract and iocsearcher to fix pre-existing environment gaps.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/enrichment/adapters/abuseipdb.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured/lookup, added _build_url/_parse_response/_auth_headers/_make_pre_raise_hook
- `app/enrichment/adapters/greynoise.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured/lookup, added _build_url/_parse_response/_auth_headers/_make_pre_raise_hook
- `app/enrichment/adapters/hashlookup.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured/lookup, added _build_url/_parse_response
- `app/enrichment/adapters/ip_api.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured/lookup, added _build_url/_parse_response/_make_pre_raise_hook
- `app/enrichment/adapters/otx.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured/lookup, added _build_url/_parse_response/_auth_headers
- `app/enrichment/adapters/malwarebazaar.py` — Subclassed BaseHTTPAdapter with POST, removed __init__/is_configured/lookup, added _build_url/_build_request_body/_parse_response/_auth_headers
- `app/enrichment/adapters/threatfox.py` — Subclassed BaseHTTPAdapter with POST, removed __init__/is_configured/lookup, added _build_url/_build_request_body/_parse_response/_auth_headers
- `app/enrichment/adapters/urlhaus.py` — Subclassed BaseHTTPAdapter with POST, removed __init__/is_configured/lookup, added _build_url/_build_request_body/_parse_response
- `app/enrichment/adapters/crtsh.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured, overrode lookup() for list response handling
- `app/enrichment/adapters/virustotal.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured, overrode lookup() with ENDPOINT_MAP dispatch, converted supported_types to frozenset
- `app/enrichment/adapters/threatminer.py` — Subclassed BaseHTTPAdapter, removed __init__/is_configured, kept full lookup() override with multi-call dispatch
- `tests/e2e/conftest.py` — Added pytest.importorskip('playwright.sync_api') guard to prevent collection failures
