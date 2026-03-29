# S01 Research: BaseHTTPAdapter + Proof Migration

## Summary

The 12 HTTP adapters share a highly uniform structural skeleton. A `BaseHTTPAdapter` abstract base class can absorb ~60% of each adapter's code — `__init__`, session setup, `supported_types` guard, `is_configured`, and the `safe_request()` dispatch + result-check boilerplate. The Shodan adapter is the simplest (zero-auth, single GET, no custom headers) and the ideal proof migration target. All 25 existing Shodan tests should pass unchanged against a subclass.

## Relevant Requirements

| ID | Status | How this slice addresses it |
|----|--------|-----------------------------|
| R041 | active | Primary deliverable — create `BaseHTTPAdapter` in `base.py` |
| R048 | active | All 25 Shodan tests must pass unchanged after migration |

## Implementation Landscape

### The Shared Skeleton (repeated 12 times)

Every HTTP adapter follows this exact structure:

```python
class XAdapter:
    supported_types: frozenset[IOCType] = frozenset({...})
    name = "..."
    requires_api_key = True/False

    def __init__(self, [api_key: str,] allowed_hosts: list[str]) -> None:
        self._api_key = api_key          # only if requires_api_key
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()
        self._session.headers.update({...})  # only if api_key

    def is_configured(self) -> bool:
        return bool(self._api_key)  # or True for zero-auth

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")
        url = ...  # provider-specific URL construction
        # optional: define a pre_raise_hook closure
        result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name, ...)
        if not isinstance(result, dict):
            return result
        return _parse_response(ioc, result, ...)
```

### Constructor Signature Variants

Two patterns exist, governed by `requires_api_key`:

| Pattern | Adapters | Signature |
|---------|----------|-----------|
| api_key + allowed_hosts | abuseipdb, greynoise, malwarebazaar, otx, threatfox, urlhaus, virustotal (7) | `__init__(self, api_key: str, allowed_hosts: list[str])` |
| allowed_hosts only | crtsh, hashlookup, ip_api, shodan, threatminer (5) | `__init__(self, allowed_hosts: list[str])` |

**Base class approach:** Accept `api_key: str = ""` as an optional kwarg. Subclasses that need it pass it through; zero-auth subclasses ignore it. This preserves the existing `setup.py` constructor calls unchanged.

### Header Configuration Variation

Each api_key adapter sets different auth headers:

| Adapter | Header Name | Notes |
|---------|------------|-------|
| AbuseIPDB | `Key` (capital K) | Also sets `Accept: application/json` |
| GreyNoise | `key` (lowercase) | No Accept header |
| MalwareBazaar | `Auth-Key` | Also sets `Accept: application/json` |
| OTX | `X-OTX-API-KEY` | Also sets `Accept: application/json` |
| ThreatFox | `Auth-Key` + `Content-Type: application/json` | |
| URLhaus | `Auth-Key` | Also sets `Accept: application/json` |
| VirusTotal | `x-apikey` | Also sets `Accept: application/json` |

**Base class approach:** Provide a `_auth_headers() -> dict[str, str]` method that returns `{}` by default. Subclasses override to return their specific header dict. The base `__init__` calls `self._session.headers.update(self._auth_headers())`.

### lookup() Template

The `lookup()` body follows a template with three subclass extension points:

1. **URL construction** — `_build_url(ioc) -> str` — every adapter constructs URLs differently
2. **Pre-raise hook** — `_pre_raise_hook(ioc, resp) -> T | None` — 8 of 12 adapters define one (404→no_data, 429→error, etc.)
3. **Response parsing** — `_parse_response(ioc, body: dict) -> EnrichmentResult` — every adapter has unique parsing

The base `lookup()` would be:
```python
def lookup(self, ioc):
    if ioc.type not in self.supported_types:
        return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")
    url = self._build_url(ioc)
    hook = self._make_pre_raise_hook(ioc)
    result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name,
                          method=self._http_method, data=..., json_payload=...,
                          pre_raise_hook=hook)
    if not isinstance(result, dict):
        return result
    return self._parse_response(ioc, result)
```

### POST Adapter Variant

Three adapters use POST: malwarebazaar (form data), threatfox (JSON payload), urlhaus (form data). The base class needs:
- `_http_method: str = "GET"` class variable (POST adapters override to `"POST"`)
- `_build_request_body(ioc) -> tuple[dict | None, dict | None]` returning `(data, json_payload)`, defaulting to `(None, None)` for GET adapters

### The ThreatMiner Exception

ThreatMiner is the only adapter that makes multiple API calls per `lookup()` (domain IOCs make 2 calls, merged). Its `lookup()` dispatches to `_lookup_ip()`, `_lookup_domain()`, `_lookup_hash()` — each with distinct URL/parsing logic. It also has a private `_call()` helper that wraps `safe_request()`.

**Recommendation:** ThreatMiner should subclass `BaseHTTPAdapter` for the `__init__` / `is_configured` / `supported_types` / session skeleton, but **override `lookup()` entirely**. The base class template method doesn't fit multi-call adapters. This still eliminates ~30 lines of ThreatMiner boilerplate. This is a decision for S02, not S01.

### VirusTotal's ENDPOINT_MAP

VT uses a lambda-map `ENDPOINT_MAP: dict[IOCType, callable]` for URL construction and checks `ioc.type not in ENDPOINT_MAP` instead of `self.supported_types`. The base class unsupported-type guard uses `self.supported_types`, so VT's subclass just needs `_build_url()` to use its existing ENDPOINT_MAP. The guard behavior is identical since VT's `supported_types` and `ENDPOINT_MAP.keys()` match.

### crt.sh Difference

crt.sh's safe_request call does NOT use a pre_raise_hook and checks `isinstance(result, EnrichmentError)` instead of `not isinstance(result, dict)`. Both are functionally equivalent since `safe_request()` returns either `dict` or `EnrichmentError`. The base class template using `not isinstance(result, dict)` covers this correctly.

## Shodan Proof Migration

### What changes in shodan.py:

```python
# Before:
class ShodanAdapter:
    supported_types = ...
    name = ...
    requires_api_key = False
    def __init__(self, allowed_hosts): ...
    def is_configured(self): ...
    def lookup(self, ioc): ...   # ~45 lines

# After:
class ShodanAdapter(BaseHTTPAdapter):
    supported_types = ...
    name = ...
    requires_api_key = False
    def _build_url(self, ioc): return f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"
    def _make_pre_raise_hook(self, ioc): return _404_hook_factory(ioc, self.name)
    def _parse_response(self, ioc, body): return _parse_response(ioc, body, self.name)
```

### What stays in shodan.py:
- `_MALICIOUS_TAGS` constant
- `_parse_response()` module-level function (verdict logic)
- `SHODAN_INTERNETDB_BASE` constant

### Test impact:
All 25 Shodan tests should pass without modification because:
- Constructor signature unchanged: `ShodanAdapter(allowed_hosts=[...])`
- `adapter._session` still exists (set by base `__init__`)
- `mock_adapter_session()` helper works on `_session` attribute
- `lookup()` behavior identical — same safe_request call, same hook, same parse
- `is_configured()` returns `True` (base class default for `requires_api_key=False`)
- `supported_types`, `name`, `requires_api_key` still class-level attributes
- `isinstance(adapter, Provider)` still passes (base class satisfies Provider protocol)

## Recommendation

### Task Decomposition (for the planner)

**T01: Create BaseHTTPAdapter in `app/enrichment/adapters/base.py`** (~45 min)

Build the abstract base class with:
- `__init__(self, allowed_hosts, api_key="")` — session setup + `_auth_headers()` call
- `is_configured()` — `bool(self._api_key)` if `requires_api_key`, else `True`
- `lookup()` template method — type guard → `_build_url` → `_make_pre_raise_hook` → `safe_request` → `_parse_response`
- Abstract methods: `_build_url(ioc)`, `_parse_response(ioc, body)`
- Optional override methods: `_auth_headers() -> dict`, `_make_pre_raise_hook(ioc) -> callable|None`, `_http_method` class var, `_build_request_body(ioc) -> tuple`
- Must satisfy the `Provider` protocol (has `name`, `supported_types`, `requires_api_key`, `lookup`, `is_configured`)

Key files: `app/enrichment/adapters/base.py` (new)

**T02: Migrate ShodanAdapter to subclass BaseHTTPAdapter** (~20 min)

- Replace `__init__`, `is_configured`, `lookup` with base class implementations
- Define `_build_url()`, `_make_pre_raise_hook()`, `_parse_response()` overrides
- Keep module constants and `_parse_response()` module function
- Run all 25 Shodan tests — zero changes to `tests/test_shodan.py`

Key files: `app/enrichment/adapters/shodan.py` (modify)

**Verification:**
```bash
# All Shodan tests pass:
pytest tests/test_shodan.py -v

# Provider protocol conformance:
python3 -c "from app.enrichment.adapters.shodan import ShodanAdapter; from app.enrichment.provider import Provider; assert isinstance(ShodanAdapter(allowed_hosts=[]), Provider)"

# setup.py still works:
python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(['internetdb.shodan.io'], ConfigStore(':memory:')); print(f'{r.provider_count_for_type} providers')"

# No import errors:
python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; print('OK')"
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `abc.ABC` + `@abstractmethod` might break `isinstance(adapter, Provider)` runtime check | Tests fail | Verify with `runtime_checkable` protocol — ABC subclasses satisfy structural protocols if they implement the required attributes/methods |
| Base class `__init__` signature change breaks `setup.py` constructor calls | Shodan construction fails | Base class uses `allowed_hosts` as first positional arg (matching zero-auth pattern); api_key is keyword-only with default `""` |
| `mock_adapter_session()` helper assumes `_session` attribute | Test mock pattern breaks | Base class uses `self._session` — same attribute name as current code |

## Key Constraints

- `base.py` must NOT import any adapter-specific modules — it's a pure skeleton
- The `Provider` protocol is structural (duck-typed via `@runtime_checkable`) — the base class doesn't need to explicitly inherit from it, but it must satisfy all protocol members
- `setup.py` constructor calls must work unchanged — no signature changes visible to callers
- The three non-HTTP adapters (dns_lookup, asn_cymru, whois_lookup) are completely unaffected — they don't use `safe_request()` and won't subclass `BaseHTTPAdapter`
