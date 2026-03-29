# S02: Migrate remaining 11 HTTP adapters

**Goal:** All 12 HTTP adapters subclass BaseHTTPAdapter. 3 non-HTTP adapters unchanged. Full test suite passes.
**Demo:** After this: After this: All 12 HTTP adapters use BaseHTTPAdapter. 3 non-HTTP adapters unchanged. Full test suite passes.

## Tasks
- [x] **T01: Migrated 5 simple GET adapters (abuseipdb, greynoise, hashlookup, ip_api, otx) to BaseHTTPAdapter subclasses** — Migrate abuseipdb, greynoise, hashlookup, ip_api, and otx to subclass BaseHTTPAdapter. Each adapter follows the proven Shodan recipe: remove `__init__`, `is_configured`, and `lookup` methods; add `class XAdapter(BaseHTTPAdapter)` inheritance; implement `_build_url(ioc)` and `_parse_response(ioc, body)` as bridges to existing module-level functions; override `_auth_headers()` for adapters with API keys; override `_make_pre_raise_hook(ioc)` for adapters with status code hooks.

## Steps

1. Read `app/enrichment/adapters/shodan.py` as the reference migration pattern.
2. Read `app/enrichment/adapters/base.py` to understand BaseHTTPAdapter's interface.
3. Migrate `app/enrichment/adapters/abuseipdb.py`:
   - Change class to `class AbuseIPDBAdapter(BaseHTTPAdapter)`
   - Add import: `from app.enrichment.adapters.base import BaseHTTPAdapter`
   - Remove `__init__`, `is_configured`, `lookup` methods
   - Add `_build_url(self, ioc)` returning `f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"`
   - Add `_parse_response(self, ioc, body)` bridging to module-level `_parse_response(ioc, body, self.name)`
   - Add `_auth_headers(self)` returning `{"Key": self._api_key, "Accept": "application/json"}`
   - Add `_make_pre_raise_hook(self, ioc)` returning a closure that checks for 429
   - Remove stale `import requests` if no longer used directly
   - Run: `python3 -m pytest tests/test_abuseipdb.py -v`
4. Migrate `app/enrichment/adapters/greynoise.py` — same pattern. Auth: `{"key": self._api_key}`. Hook: 404→no_data. Run tests.
5. Migrate `app/enrichment/adapters/hashlookup.py` — no auth (public API). Hook: 404→no_data. Run tests.
6. Migrate `app/enrichment/adapters/ip_api.py` — no auth (public API). Hook: 404→no_data. Run tests.
7. Migrate `app/enrichment/adapters/otx.py` — Auth: `{"X-OTX-API-KEY": self._api_key, "Accept": "application/json"}`. No hook. Run tests.
8. Run all 5 test files together: `python3 -m pytest tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v`

## Must-Haves

- [ ] All 5 adapters subclass BaseHTTPAdapter
- [ ] No `__init__`, `is_configured`, or inline `lookup` boilerplate remains in any of the 5
- [ ] All 188 tests across 5 files pass unchanged
- [ ] Module-level `_parse_response` functions preserved — adapter bridge methods delegate to them

## Pitfalls

- AbuseIPDB auth header uses capital `Key` (not `key`) — must match exactly in `_auth_headers()`
- GreyNoise auth header uses lowercase `key` (not `Key`)
- OTX `supported_types` is an explicit frozenset excluding EMAIL — preserve the exact set
- ip_api has no API key (`requires_api_key = False`) — no `_auth_headers()` override needed
- hashlookup has no API key — same as ip_api
- Each module-level `_parse_response` has slightly different signatures (some take `provider_name` arg, some don't) — the bridge method must match
  - Estimate: 45m
  - Files: app/enrichment/adapters/abuseipdb.py, app/enrichment/adapters/greynoise.py, app/enrichment/adapters/hashlookup.py, app/enrichment/adapters/ip_api.py, app/enrichment/adapters/otx.py, app/enrichment/adapters/base.py
  - Verify: python3 -m pytest tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v && grep -c 'class.*BaseHTTPAdapter' app/enrichment/adapters/abuseipdb.py app/enrichment/adapters/greynoise.py app/enrichment/adapters/hashlookup.py app/enrichment/adapters/ip_api.py app/enrichment/adapters/otx.py | grep -v ':1' | wc -l | xargs test 0 -eq
- [x] **T02: Migrated malwarebazaar, threatfox, urlhaus (POST), and crtsh (list-response GET) to BaseHTTPAdapter subclasses with all 97 tests passing unchanged** — Migrate malwarebazaar, threatfox, urlhaus (POST adapters) and crtsh (GET but list response) to subclass BaseHTTPAdapter.

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
  - Estimate: 45m
  - Files: app/enrichment/adapters/malwarebazaar.py, app/enrichment/adapters/threatfox.py, app/enrichment/adapters/urlhaus.py, app/enrichment/adapters/crtsh.py, app/enrichment/adapters/base.py
  - Verify: python3 -m pytest tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py -v && grep -c 'class.*BaseHTTPAdapter' app/enrichment/adapters/malwarebazaar.py app/enrichment/adapters/threatfox.py app/enrichment/adapters/urlhaus.py app/enrichment/adapters/crtsh.py | grep -v ':1' | wc -l | xargs test 0 -eq
- [x] **T03: Migrated VTAdapter and ThreatMinerAdapter to BaseHTTPAdapter subclasses with all 86 adapter tests and 853 suite tests passing** — Migrate the 2 complex adapters that require full `lookup()` overrides, then run the complete test suite and structural verification checks.

VirusTotal uses `ENDPOINT_MAP[ioc.type]` lambdas for URL construction (including base64 URL encoding for URL IOCs) and a complex pre-raise hook (404→no_data, 429→rate limit, 401/403→auth error). VT overrides `lookup()` entirely.

ThreatMiner has a multi-call `lookup()` with 3 sub-methods (`_lookup_ip`, `_lookup_domain`, `_lookup_hash`). Domain lookups make 2 sequential API calls and merge results. Cannot use the base class template-method `lookup()`. Overrides `lookup()` entirely, inheriting only `__init__`/`is_configured`.

## Steps

1. Migrate `app/enrichment/adapters/virustotal.py`:
   - Subclass BaseHTTPAdapter
   - Remove `__init__` and `is_configured`
   - Keep `lookup()` as an override — VT's endpoint-map + hook logic doesn't fit the base template
   - Convert `supported_types` from plain `set` to `frozenset` (pitfall from roadmap)
   - `_auth_headers()` returns `{"x-apikey": self._api_key, "Accept": "application/json"}`
   - `_build_url` and `_parse_response` implemented but `lookup()` doesn't call them via super — it has its own dispatch. They satisfy the abstract requirement.
   - Actually — `_build_url` can raise NotImplementedError since VT uses ENDPOINT_MAP lambdas directly. Better: implement `_build_url` to use the ENDPOINT_MAP so the abstract is satisfied meaningfully, even if `lookup()` calls it directly.
   - Run: `python3 -m pytest tests/test_vt_adapter.py -v`
2. Migrate `app/enrichment/adapters/threatminer.py`:
   - Subclass BaseHTTPAdapter
   - Remove `__init__` and `is_configured`
   - Keep entire `lookup()` override and all sub-methods (`_lookup_ip`, `_lookup_domain`, `_lookup_hash`, `_call`)
   - `_build_url` and `_parse_response` must be implemented (abstract) — can be simple stubs that raise NotImplementedError with comment explaining lookup() is overridden, OR implement `_build_url` to return a base URL and `_parse_response` as a no-op. Since ThreatMiner uses multiple calls, stubs are more honest.
   - Run: `python3 -m pytest tests/test_threatminer.py -v`
3. Run full test suite: `python3 -m pytest tests/ -x -q`
4. Run structural verification:
   - `grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | wc -l` → 12
   - `grep -c 'BaseHTTPAdapter' app/enrichment/adapters/dns_lookup.py app/enrichment/adapters/asn_cymru.py app/enrichment/adapters/whois_lookup.py` → all 0
   - `python3 -c "from app.enrichment.setup import build_registry; ..."` → 15 providers

## Must-Haves

- [ ] VT and ThreatMiner subclass BaseHTTPAdapter
- [ ] VT `supported_types` is frozenset, not plain set
- [ ] VT and ThreatMiner override `lookup()` entirely — multi-call / endpoint-map logic preserved
- [ ] All 86 tests (17 VT + 69 ThreatMiner) pass unchanged
- [ ] Full test suite passes (`python3 -m pytest tests/ -x -q`)
- [ ] 12 adapter files contain `BaseHTTPAdapter` subclass
- [ ] 3 non-HTTP adapters do NOT contain `BaseHTTPAdapter`
- [ ] Registry instantiates all 15 providers

## Pitfalls

- VT `supported_types` is currently a plain `set` — must convert to `frozenset` for BaseHTTPAdapter type annotation
- VT and ThreatMiner still need `_build_url` and `_parse_response` defined (they're abstract in base) even though `lookup()` is overridden. For VT, `_build_url` can use ENDPOINT_MAP meaningfully. For ThreatMiner, stubs are appropriate.
- ThreatMiner `_parse_response` signature in the module-level function takes `(ioc, body)` — same as the abstract method, no bridge needed IF it's used. But ThreatMiner's lookup doesn't call it via the template — the sub-methods have their own parsing.
- VT test file is `tests/test_vt_adapter.py` (not `test_virustotal.py`)
- ThreatMiner test file is `tests/test_threatminer.py`
  - Estimate: 45m
  - Files: app/enrichment/adapters/virustotal.py, app/enrichment/adapters/threatminer.py, app/enrichment/adapters/base.py
  - Verify: python3 -m pytest tests/test_vt_adapter.py tests/test_threatminer.py -v && python3 -m pytest tests/ -x -q && test $(grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | wc -l) -eq 12 && python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(ConfigStore(':memory:')); assert len(r.all()) == 15, f'Expected 15, got {len(r.all())}'; print('15 providers OK')"
