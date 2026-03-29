---
estimated_steps: 43
estimated_files: 5
skills_used: []
---

# T02: Migrate 4 POST adapters + CrtSh to BaseHTTPAdapter

Migrate malwarebazaar, threatfox, urlhaus (POST adapters) and crtsh (GET but list response) to subclass BaseHTTPAdapter.

POST adapters follow the standard recipe plus: override `_http_method = "POST"` and `_build_request_body(ioc)` returning `(data_dict, None)` for form-encoded or `(None, json_dict)` for JSON bodies.

CrtSh requires a `lookup()` override because `safe_request()` returns a JSON array (Python `list`), not a `dict`. The base class `lookup()` uses `isinstance(result, dict)` which would reject the list. CrtSh overrides `lookup()` with `isinstance(result, EnrichmentError)` instead.

## Steps

1. Read `app/enrichment/adapters/shodan.py` and `app/enrichment/adapters/base.py` for reference.
2. Migrate `app/enrichment/adapters/malwarebazaar.py`:
   - Subclass BaseHTTPAdapter, set `_http_method = "POST"`
   - `_build_url(ioc)` returns the MalwareBazaar API URL
   - `_build_request_body(ioc)` returns `({"query": "get_info", "hash": ioc.value}, None)` — form-encoded data
   - `_auth_headers()` returns `{"Auth-Key": self._api_key, "Accept": "application/json"}`
   - `_parse_response(ioc, body)` bridges to module-level function
   - Remove `__init__`, `is_configured`, `lookup`
   - Run: `python3 -m pytest tests/test_malwarebazaar.py -v`
3. Migrate `app/enrichment/adapters/threatfox.py`:
   - Subclass BaseHTTPAdapter, set `_http_method = "POST"`
   - `_build_request_body(ioc)` returns `(None, json_dict)` — JSON payload (not form-encoded)
   - ThreatFox uses different JSON keys based on IOC type (hash vs other)
   - `_auth_headers()` returns `{"Content-Type": "application/json", "Auth-Key": self._api_key}`
   - Run: `python3 -m pytest tests/test_threatfox.py -v`
4. Migrate `app/enrichment/adapters/urlhaus.py`:
   - Subclass BaseHTTPAdapter, set `_http_method = "POST"`
   - Uses `_ENDPOINT_MAP[ioc.type]` for both URL path and POST body key per type
   - `_build_url(ioc)` and `_build_request_body(ioc)` both read from `_ENDPOINT_MAP`
   - Run: `python3 -m pytest tests/test_urlhaus.py -v`
5. Migrate `app/enrichment/adapters/crtsh.py`:
   - Subclass BaseHTTPAdapter but **override `lookup()`** entirely
   - CrtSh is a GET adapter but `safe_request()` returns a list, not dict
   - Override `lookup()` to use `isinstance(result, EnrichmentError)` check instead of `isinstance(result, dict)`
   - Inherit `__init__` and `is_configured` from base
   - `_build_url` and `_parse_response` still implemented as abstract method overrides
   - Run: `python3 -m pytest tests/test_crtsh.py -v`
6. Run all 4 test files: `python3 -m pytest tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py -v`

## Must-Haves

- [ ] All 4 adapters subclass BaseHTTPAdapter
- [ ] POST adapters have `_http_method = "POST"` and `_build_request_body()` overrides
- [ ] CrtSh overrides `lookup()` with list-aware isinstance check
- [ ] All 97 tests across 4 files pass unchanged

## Pitfalls

- CrtSh `safe_request()` returns a `list` not `dict` — must override `lookup()`, not use base class template
- MalwareBazaar uses form-encoded POST (`data=`), not JSON (`json_payload=`)
- ThreatFox uses JSON POST (`json_payload=`), not form-encoded
- URLhaus endpoint map has both URL path AND body key per IOC type
- CrtSh still needs `_build_url` and `_parse_response` abstract methods implemented even though it overrides `lookup()` — they are abstract and must be defined

## Inputs

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter abstract base class`
- ``app/enrichment/adapters/shodan.py` — reference migration pattern`
- ``app/enrichment/adapters/malwarebazaar.py` — adapter to migrate`
- ``app/enrichment/adapters/threatfox.py` — adapter to migrate`
- ``app/enrichment/adapters/urlhaus.py` — adapter to migrate`
- ``app/enrichment/adapters/crtsh.py` — adapter to migrate`

## Expected Output

- ``app/enrichment/adapters/malwarebazaar.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/threatfox.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/urlhaus.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/crtsh.py` — migrated to BaseHTTPAdapter subclass`

## Verification

python3 -m pytest tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py -v && grep -c 'class.*BaseHTTPAdapter' app/enrichment/adapters/malwarebazaar.py app/enrichment/adapters/threatfox.py app/enrichment/adapters/urlhaus.py app/enrichment/adapters/crtsh.py | grep -v ':1' | wc -l | xargs test 0 -eq
