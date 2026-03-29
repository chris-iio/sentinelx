---
id: T02
parent: S02
milestone: M009
provides: []
requires: []
affects: []
key_files: ["app/enrichment/adapters/malwarebazaar.py", "app/enrichment/adapters/threatfox.py", "app/enrichment/adapters/urlhaus.py", "app/enrichment/adapters/crtsh.py"]
key_decisions: ["CrtSh overrides lookup() entirely rather than using base class template, because safe_request() returns a list not dict", "POST body encoding distinguished via _build_request_body: form-encoded returns (data, None), JSON returns (None, json_payload)"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "Ran all 97 tests across 4 test files — all pass (0.16s). Grep verified each of the 4 files has exactly 1 BaseHTTPAdapter subclass."
completed_at: 2026-03-29T17:46:09.629Z
blocker_discovered: false
---

# T02: Migrated malwarebazaar, threatfox, urlhaus (POST), and crtsh (list-response GET) to BaseHTTPAdapter subclasses with all 97 tests passing unchanged

> Migrated malwarebazaar, threatfox, urlhaus (POST), and crtsh (list-response GET) to BaseHTTPAdapter subclasses with all 97 tests passing unchanged

## What Happened
---
id: T02
parent: S02
milestone: M009
key_files:
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/crtsh.py
key_decisions:
  - CrtSh overrides lookup() entirely rather than using base class template, because safe_request() returns a list not dict
  - POST body encoding distinguished via _build_request_body: form-encoded returns (data, None), JSON returns (None, json_payload)
duration: ""
verification_result: passed
completed_at: 2026-03-29T17:46:09.629Z
blocker_discovered: false
---

# T02: Migrated malwarebazaar, threatfox, urlhaus (POST), and crtsh (list-response GET) to BaseHTTPAdapter subclasses with all 97 tests passing unchanged

**Migrated malwarebazaar, threatfox, urlhaus (POST), and crtsh (list-response GET) to BaseHTTPAdapter subclasses with all 97 tests passing unchanged**

## What Happened

Migrated four adapters to subclass BaseHTTPAdapter, removing manual __init__, is_configured, and lookup methods (except CrtSh which retains a custom lookup() because safe_request() returns a list not dict). POST adapters distinguished via _http_method = "POST" and _build_request_body() returning (data, None) for form-encoded (MalwareBazaar, URLhaus) or (None, json) for JSON (ThreatFox). CrtSh overrides lookup() entirely with isinstance(result, EnrichmentError) check. All module-level parse functions preserved unchanged.

## Verification

Ran all 97 tests across 4 test files — all pass (0.16s). Grep verified each of the 4 files has exactly 1 BaseHTTPAdapter subclass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py -v` | 0 | ✅ pass | 160ms |
| 2 | `grep -c 'class.*BaseHTTPAdapter' ...4 files | grep -v ':1' | wc -l | xargs test 0 -eq` | 0 | ✅ pass | 50ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/crtsh.py`


## Deviations
None.

## Known Issues
None.
