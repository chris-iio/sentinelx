# S02 Research: Migrate remaining 11 HTTP adapters

## Summary

Straightforward application of the S01 migration recipe to 11 remaining HTTP adapters. The recipe is proven: remove `__init__`/`is_configured`/`lookup`, subclass `BaseHTTPAdapter`, implement `_build_url` + `_parse_response`, optionally override `_auth_headers`/`_make_pre_raise_hook`/`_http_method`/`_build_request_body`.

Two adapters require special handling beyond the standard recipe:

1. **CrtSh** — `safe_request()` returns a JSON array (Python `list`), not a `dict`. BaseHTTPAdapter.lookup() checks `isinstance(result, dict)` to distinguish success from error. A list would fail this check. CrtSh must override `lookup()` entirely, using `isinstance(result, EnrichmentError)` instead.

2. **ThreatMiner** — Multi-call `lookup()` with 3 sub-methods (`_lookup_ip`, `_lookup_domain`, `_lookup_hash`). Domain lookups make 2 sequential API calls and merge results. Cannot use the base class template-method `lookup()`. Must override `lookup()` entirely while inheriting `__init__`/`is_configured`.

All other 9 adapters fit the standard recipe cleanly.

## Recommendation

Batch the 11 adapters into 3 tasks by complexity:

- **T01: Simple GET adapters (5)** — abuseipdb, greynoise, hashlookup, ip_api, otx. Standard recipe: `_build_url` + `_parse_response` + `_auth_headers` + optional `_make_pre_raise_hook`. ~5 min each.
- **T02: POST adapters + crt.sh (4)** — malwarebazaar, threatfox, urlhaus, crtsh. POST adapters override `_http_method`/`_build_request_body`. CrtSh overrides `lookup()`. ~8 min each.
- **T03: Complex adapters (2)** — virustotal, threatminer. Both override `lookup()` entirely. VT has endpoint map + base64 URL encoding. ThreatMiner has multi-call routing. ~10 min each.

## Implementation Landscape

### Adapter Classification

| Adapter | Auth | Method | Hook | Body Override | lookup() Override | Tests |
|---------|------|--------|------|---------------|-------------------|-------|
| abuseipdb | `Key: {key}` | GET | 429 hook | — | No | 33 |
| crtsh | none | GET | — | — | **Yes** (list response) | 37 |
| greynoise | `key: {key}` | GET | 404 hook | — | No | 29 |
| hashlookup | none | GET | 404 hook | — | No | 34 |
| ip_api | none | GET | 404 hook | — | No | 50 |
| malwarebazaar | `Auth-Key: {key}` | POST | — | `data=` | No | 12 |
| otx | `X-OTX-API-KEY: {key}` | GET | 404 hook | — | No | 42 |
| threatfox | `Auth-Key: {key}` | POST | — | `json_payload=` | No | 15 |
| threatminer | none | GET | — | — | **Yes** (multi-call) | 69 |
| urlhaus | `Auth-Key: {key}` | POST | — | `data=` (varies by type) | No | 33 |
| virustotal | `x-apikey: {key}` | GET | 404/429/401/403 hook | — | **Yes** (ENDPOINT_MAP) | 17 |

### Constructor Signatures — No setup.py Changes

All `setup.py` constructor calls use keyword arguments (`api_key=key, allowed_hosts=hosts`). BaseHTTPAdapter's `__init__(self, allowed_hosts, *, api_key="")` accepts both forms. **Zero setup.py changes required.**

### CrtSh List Response Constraint

`safe_request()` return type is annotated `dict | EnrichmentError` but actually returns `list` for crt.sh (JSON array). BaseHTTPAdapter.lookup() uses `isinstance(result, dict)` — a list would be treated as an error. CrtSh must override lookup() with `isinstance(result, EnrichmentError)` check instead.

### ThreatMiner Multi-Call Pattern

ThreatMiner.lookup() dispatches to `_lookup_ip()`, `_lookup_domain()`, `_lookup_hash()` based on IOC type. Domain lookups make 2 sequential API calls (`_call()` twice) and merge results. The base class template-method `lookup()` (single URL → single call → single parse) cannot express this. ThreatMiner overrides `lookup()` entirely, inheriting only `__init__`/`is_configured` from the base.

### VirusTotal Endpoint Map Pattern

VT uses `ENDPOINT_MAP[ioc.type]` lambdas for URL construction (including base64 URL encoding for URL IOCs). The hook is complex (404→no_data, 429→rate limit, 401/403→auth error). VT also sets an extra `Accept: application/json` header. VT overrides `lookup()` but inherits `__init__`/`is_configured`.

### URLhaus Type-Specific Body

URLhaus uses `_ENDPOINT_MAP[ioc.type]` to get both URL path and POST body key name per IOC type. The `_build_url()` and `_build_request_body()` overrides both need access to the IOC type to look up the endpoint map. This fits naturally: `_build_url(ioc)` returns `f"{URLHAUS_BASE}{url_path}"`, `_build_request_body(ioc)` returns `(data_dict, None)`.

### ThreatFox IOC-Type-Dependent JSON Payload

ThreatFox sends different JSON payload keys based on whether the IOC is a hash vs other type. `_build_request_body(ioc)` returns `(None, json_payload_dict)`.

### Auth Header Patterns (all via `_auth_headers()` override)

- AbuseIPDB: `{"Key": key, "Accept": "application/json"}` — capital K
- GreyNoise: `{"key": key}` — lowercase k
- OTX: `{"X-OTX-API-KEY": key, "Accept": "application/json"}`
- VT: `{"x-apikey": key, "Accept": "application/json"}`
- MalwareBazaar: `{"Auth-Key": key, "Accept": "application/json"}`
- ThreatFox: `{"Content-Type": "application/json", "Auth-Key": key}`
- URLhaus: `{"Auth-Key": key, "Accept": "application/json"}`

### Test Impact

All 11 test files should pass **unchanged** — the same S01 proof holds. The base class implements the same contract every adapter previously implemented inline. Tests mock `adapter._session` directly (per KNOWLEDGE.md adapter test mock pattern), which is still an attribute set by `BaseHTTPAdapter.__init__`.

Total: 371 adapter tests across 11 files (+ 17 VT tests in test_vt_adapter.py = 388).

### Expected LOC Reduction Per Adapter

Each adapter removes `__init__` (~7 lines), `is_configured` (~3 lines), and most of `lookup()` (~15-25 lines of type guard + safe_request dispatch + isinstance check). Net reduction ~25-35 lines per standard adapter, ~10-15 lines for override-lookup adapters (only __init__/is_configured removed).

Estimated total LOC reduction: ~250-300 lines across 11 adapter files.

### Verification

Per-adapter: `python3 -m pytest tests/test_{adapter}.py -v` — all existing tests pass.
Slice-level:
- `python3 -m pytest tests/ -x -q` — full test suite passes
- `grep -c 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py` — 12 matches (all HTTP adapters)
- `grep -c 'class.*:$' app/enrichment/adapters/{dns_lookup,asn_cymru,whois_lookup}.py` — 3 standalone (R043)
- `python3 -c "from app.enrichment.setup import build_registry; ..."` — 15 providers instantiate

## Pitfalls

1. **CrtSh list response** — must override `lookup()`, not use base class template. The `isinstance(result, dict)` check in base class would reject the list.
2. **VT `supported_types` is a plain set, not frozenset** — `supported_types = {IOCType.IPV4, ...}` (line 130 of virustotal.py). BaseHTTPAdapter declares `supported_types: frozenset[IOCType]`. VT should convert to frozenset during migration.
3. **ThreatFox `_parse_response` takes 2 args** — module-level `_parse_response(ioc, body)` vs other adapters' `_parse_response(ioc, body, provider_name)`. The bridge method in the class handles this.
