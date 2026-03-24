# S01: Adapter HTTP Consolidation + Session Pooling

**Goal:** Extract all HTTP boilerplate from 12 adapters into a shared `safe_request()` function, inject per-provider `requests.Session`, and update all tests.
**Demo:** All 12 HTTP adapters use `safe_request()`. Each adapter is ~40% shorter — only URL construction, headers, response parsing, and verdict logic remain. Per-provider sessions pool connections. 924+ tests pass.

## Must-Haves
- `safe_request()` exists in `http_safety.py` with signature: `safe_request(method, url, allowed_hosts, session=None, headers=None, no_data_on_404=False, json=None)`
- No HTTP adapter imports `validate_endpoint`, `read_limited`, or `TIMEOUT` directly
- No HTTP adapter contains `requests.get(` or `requests.post(` or `session.get(` or `session.post(`
- Each adapter has a `self._session: requests.Session` attribute
- `setup.py` creates a `requests.Session()` per adapter and passes it to the constructor
- All adapter-specific edge cases preserved: VT `_map_http_error()`, ThreatMiner body-level 404, AbuseIPDB 429 pre-check
- 924+ tests pass — zero regressions

## Tasks

- [x] **T01: Implement `safe_request()` in `http_safety.py`**
  Build the shared HTTP helper function. Write unit tests for it.

- [x] **T02: Convert GET adapters (batch 1: shodan, ip_api, hashlookup, crtsh, greynoise)**
  Convert 5 simpler GET adapters. These have no special error handling beyond the standard pattern. Update their tests.

- [ ] **T03: Convert GET adapters (batch 2: abuseipdb, otx, threatminer) + POST adapters (urlhaus, malwarebazaar)**
  Convert 5 adapters with mild complexity: AbuseIPDB's 429 pre-check, OTX's type map, ThreatMiner's multi-call + body-level 404, URLhaus/MalwareBazaar POST bodies. Update tests.

- [ ] **T04: Convert session-based adapters (virustotal, threatfox) + session injection in setup.py**
  Convert VT (with `_map_http_error` preservation) and ThreatFox (POST with json). Add session creation to `setup.py` and `__init__` for all 12 HTTP adapters. Final full-suite verification.

## Files Likely Touched
- `app/enrichment/http_safety.py` — add `safe_request()`
- `app/enrichment/adapters/*.py` — all 12 HTTP adapters
- `app/enrichment/setup.py` — session creation per adapter
- `tests/test_*.py` — all adapter test files (mock migration)
