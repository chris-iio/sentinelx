# Phase 3: Free-Key Providers — Research

**Researched:** 2026-03-02
**Domain:** Python TI provider adapters (URLhaus, OTX AlienVault, GreyNoise Community, AbuseIPDB) + Flask settings page expansion
**Confidence:** HIGH — this codebase is fully read, all APIs are documented in the design doc, and a complete reference adapter (ShodanAdapter) is already committed

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| URL-01 | URLhaus adapter enriches URL, hash, IP, and domain IOCs using the abuse.ch v1 API | API endpoints, auth, verdict logic documented in design doc and impl plan |
| OTX-01 | OTX AlienVault adapter enriches all IOC types including CVE using the OTX v1 API | Pulse count verdict thresholds documented; CVE type already in IOCType enum |
| GREY-01 | GreyNoise Community adapter enriches IP IOCs using the GreyNoise v3 community API | riot/noise/classification verdict logic documented in design doc |
| ABUSE-01 | AbuseIPDB adapter enriches IP IOCs using the AbuseIPDB v2 API | Score-threshold verdict logic documented; abuseConfidenceScore thresholds known |
| MULTI-01 | All four providers register through the same registry pattern with no hardcoded lists | ProviderRegistry + setup.py pattern already proven in Phase 2 |
| MULTI-02 | Unconfigured providers (no API key) are gracefully skipped without errors | is_configured() + registry.providers_for_type() already implements this |
</phase_requirements>

---

## Summary

Phase 3 adds four free-API-key threat intelligence providers to SentinelX: URLhaus, OTX AlienVault, GreyNoise Community, and AbuseIPDB. The registry architecture from Phase 1 and the TDD adapter pattern from Phase 2 are already proven — this phase is a structured repeat of that pattern four times plus a settings page extension.

The codebase has everything needed: a `Provider` protocol (`app/enrichment/provider.py`), a `ProviderRegistry` (`app/enrichment/registry.py`), a `ConfigStore` with `get_provider_key(name)` / `set_provider_key(name, key)` for multi-provider key storage, and HTTP safety utilities (`http_safety.py`) with SSRF validation, timeouts, and response size capping. The `ShodanAdapter` is the canonical reference for how to build an adapter — it should be copied as a structural template for each new adapter.

The settings page currently renders a single VT key form. Phase 3 extends it to a dynamic multi-provider form driven by a `PROVIDER_INFO` metadata list in `setup.py`. The implementation plan contains complete code for all six tasks; research is confirmatory and fills in API-level specifics and pitfalls the plan omits.

**Primary recommendation:** Build each adapter in isolation using TDD (tests-first, then implementation), register all four at the end in a single setup.py pass, and extend the settings page last. Do not combine adapter creation with settings changes — keep concerns isolated.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | installed | HTTP client for all provider API calls | Already used by all 4 existing adapters; no new dep |
| `configparser` | stdlib | Multi-provider API key storage | Already used by ConfigStore |
| `typing.Protocol` | stdlib | Provider protocol structural typing | Already defined in `app/enrichment/provider.py` |
| `dataclasses` (frozen) | stdlib | EnrichmentResult / EnrichmentError return types | Already defined in `app/enrichment/models.py` |
| `unittest.mock` | stdlib | Mock HTTP calls in tests | Used throughout existing adapter test suite |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | installed | Test runner | All adapter test files |
| `frozenset` | stdlib | Immutable `supported_types` class attribute | Use for class-level sets (Phase 2 decision: [02-01]) |
| `json` | stdlib | Mock response encoding in tests | Same `json.dumps(body).encode()` pattern as Shodan tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests.get` / `requests.post` | `httpx`, `aiohttp` | Project standard is `requests`; changing would require new dep and async architecture rewrite |
| ConfigStore `[providers]` section | Env vars per provider | Env vars require app restart; ConfigStore matches existing VT key pattern and settings page UX |

**Installation:** No new packages needed. All dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
app/enrichment/adapters/
├── virustotal.py       # API-key adapter (reference for auth pattern)
├── malwarebazaar.py    # No-auth adapter (reference for POST pattern)
├── shodan.py           # No-auth GET adapter (reference for 404 handling)
├── threatfox.py        # No-auth POST adapter
├── urlhaus.py          # NEW: free-key POST adapter (URL, hash, IP, domain)
├── otx.py              # NEW: free-key GET adapter (all types incl. CVE)
├── greynoise.py        # NEW: free-key GET adapter (IP only)
└── abuseipdb.py        # NEW: free-key GET adapter (IP only)

tests/
├── test_urlhaus.py     # NEW
├── test_otx.py         # NEW
├── test_greynoise.py   # NEW
├── test_abuseipdb.py   # NEW
└── test_registry_setup.py  # UPDATE: extend to 8 providers
```

### Pattern 1: Free-Key Adapter Structure (canonical)

**What:** Each adapter is a class with class-level `name`, `supported_types` (frozenset), `requires_api_key`, and instance `__init__(self, api_key: str, allowed_hosts: list[str])`.

**When to use:** All four new adapters follow this pattern exactly.

```python
# Source: app/enrichment/adapters/shodan.py (zero-auth variant) +
#         app/enrichment/adapters/virustotal.py (key variant)

class URLhausAdapter:
    name = "URLhaus"
    supported_types: frozenset[IOCType] = frozenset({
        IOCType.URL, IOCType.IPV4, IOCType.IPV6,
        IOCType.DOMAIN, IOCType.MD5, IOCType.SHA256,
    })
    requires_api_key = True

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")
        # ... validate_endpoint, HTTP call, parse response
```

### Pattern 2: HTTP Safety (mandatory for every adapter)

**What:** Four controls applied to every outbound request. Non-negotiable.

**When to use:** Every `requests.get()` or `requests.post()` call in every adapter.

```python
# Source: app/enrichment/http_safety.py

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint

# Before every network call:
try:
    validate_endpoint(url, self._allowed_hosts)
except ValueError as exc:
    return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

# Every request:
resp = requests.get(
    url,
    headers={"X-OTX-API-KEY": self._api_key},
    timeout=TIMEOUT,           # (5, 30) connect/read
    allow_redirects=False,     # SEC-06
    stream=True,               # SEC-05 setup
)
# 404 check BEFORE raise_for_status (critical pattern)
if resp.status_code == 404:
    return EnrichmentResult(..., verdict="no_data", ...)
resp.raise_for_status()
body = read_limited(resp)      # SEC-05: 1 MB cap
```

### Pattern 3: 404 Before raise_for_status (critical ordering)

**What:** For providers that return 404 to mean "not found" (not an error), check status code before calling `raise_for_status()`. This is a proven pitfall from Phase 2.

**When to use:** URLhaus (not found = `no_results` in body, not 404), OTX (404 possible for unknown IOCs), GreyNoise (404 for unrecognized IP), AbuseIPDB (always returns 200 even for unknown).

```python
# Source: app/enrichment/adapters/shodan.py line 120
# CRITICAL: check 404 BEFORE raise_for_status
if resp.status_code == 404:
    return EnrichmentResult(
        ioc=ioc, provider=self.name, verdict="no_data",
        detection_count=0, total_engines=0, scan_date=None, raw_stats={},
    )
resp.raise_for_status()
body = read_limited(resp)
```

### Pattern 4: ConfigStore Key Retrieval (for free-key adapters)

**What:** New adapters read their API keys from the `[providers]` INI section via `config_store.get_provider_key(name)`.

**When to use:** setup.py `build_registry()` function for all four new adapters.

```python
# Source: app/enrichment/config_store.py — get_provider_key() / set_provider_key()
# Source: docs/plans/2026-03-02-universal-threat-intel-hub.md Task 3.5

urlhaus_key = config_store.get_provider_key("urlhaus") or ""
registry.register(URLhausAdapter(api_key=urlhaus_key, allowed_hosts=allowed_hosts))

otx_key = config_store.get_provider_key("otx") or ""
registry.register(OTXAdapter(api_key=otx_key, allowed_hosts=allowed_hosts))

gn_key = config_store.get_provider_key("greynoise") or ""
registry.register(GreyNoiseAdapter(api_key=gn_key, allowed_hosts=allowed_hosts))

abuseipdb_key = config_store.get_provider_key("abuseipdb") or ""
registry.register(AbuseIPDBAdapter(api_key=abuseipdb_key, allowed_hosts=allowed_hosts))
```

### Pattern 5: Test Structure (from Shodan tests — canonical)

**What:** All adapter tests use `unittest.mock.patch("requests.get", ...)` or `patch("requests.post", ...)` with `_make_mock_get_response()` helper. No real API calls.

```python
# Source: tests/test_shodan.py

def _make_mock_get_response(status_code: int, body: dict | None = None) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp
```

### Anti-Patterns to Avoid

- **Mutable class attribute for `supported_types`:** Use `frozenset`, not `set`. Phase 2 decision [02-01] documents this.
- **Instance method `_parse_response`:** The Phase 2 ShodanAdapter uses a module-level function. Either is fine — be consistent within an adapter.
- **Calling `read_limited()` before checking 404:** The 404 check must come first or `raise_for_status()` will fire before body is read.
- **Logging the API key:** Never pass `self._api_key` to `logger.*`. Log only IOC value and provider name.
- **Global state in adapters:** Each `lookup()` call must create its own `requests.Session` (or use standalone `requests.get`) to be thread-safe under `ThreadPoolExecutor`.

---

## Provider-Specific API Details

### URLhaus (abuse.ch)

**Endpoints:** POST (not GET) — different endpoint per IOC type:
- URL: `POST https://urlhaus-api.abuse.ch/v1/url/` with body `{"url": value}`
- IP / Domain: `POST https://urlhaus-api.abuse.ch/v1/host/` with body `{"host": value}`
- MD5: `POST https://urlhaus-api.abuse.ch/v1/payload/` with body `{"md5_hash": value}`
- SHA256: `POST https://urlhaus-api.abuse.ch/v1/payload/` with body `{"sha256_hash": value}`

**Auth:** HTTP header `Auth-Key: {api_key}`

**Supported types:** `{URL, IPV4, IPV6, DOMAIN, MD5, SHA256}` — no SHA1, no CVE

**Verdict logic:**
- `query_status == "is_listed"` (URL) or `query_status == "ok"` (host/payload) → `"malicious"`
- `query_status == "no_results"` → `"no_data"`
- Other status → return `EnrichmentError`

**HTTP notes:** abuse.ch returns 200 for all queries; verdict is in `query_status` field. No 404 pattern. Same `urlhaus-api.abuse.ch` hostname as MalwareBazaar is on different domains — add `"urlhaus-api.abuse.ch"` to `ALLOWED_API_HOSTS` (distinct from `"mb-api.abuse.ch"`).

**ALLOWED_API_HOSTS entry:** `"urlhaus-api.abuse.ch"`

**raw_stats to capture:** `tags`, `urls_count`, `blacklists`, malware `signature`, `payloads` (truncated)

### OTX AlienVault

**Endpoint:** GET `https://otx.alienvault.com/api/v1/indicators/{ioc_type_str}/{value}/general`

**IOC type string mapping:**
- `IOCType.IPV4` → `"IPv4"`
- `IOCType.IPV6` → `"IPv6"`
- `IOCType.DOMAIN` → `"domain"`
- `IOCType.URL` → `"url"`
- `IOCType.MD5` / `IOCType.SHA1` / `IOCType.SHA256` → `"file"`
- `IOCType.CVE` → `"cve"`

**Auth:** HTTP header `X-OTX-API-KEY: {api_key}`

**Supported types:** ALL IOCType values — `{IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256, CVE}`. OTX is the only CVE provider in v4.0.

**Verdict logic (pulse_info.count):**
- `>= 5` → `"malicious"`
- `1–4` → `"suspicious"`
- `0` → `"no_data"`

**HTTP notes:** OTX returns 404 for unknown IOCs. Use the 404-before-raise_for_status pattern.

**ALLOWED_API_HOSTS entry:** `"otx.alienvault.com"`

**raw_stats to capture:** `pulse_info.count`, `reputation`, `indicator` (the IOC value echo), `type_title`, related pulse `names` (first 3-5)

### GreyNoise Community

**Endpoint:** GET `https://api.greynoise.io/v3/community/{ip}`

**Auth:** HTTP header `key: {api_key}` (note: lowercase `key`, not `Authorization`)

**Supported types:** `{IPV4, IPV6}` only

**Verdict logic:**
- `riot == true` → `"clean"` (known benign: Google, Cloudflare, etc.)
- `classification == "malicious"` → `"malicious"` (known bad scanner)
- `noise == true` AND `classification != "malicious"` → `"suspicious"` (mass scanner, not classified bad)
- everything else → `"no_data"`

**HTTP notes:** 404 returned for IPs not in GreyNoise database — use 404-before-raise_for_status pattern.

**ALLOWED_API_HOSTS entry:** `"api.greynoise.io"`

**raw_stats to capture:** `noise`, `riot`, `classification`, `name`, `link`, `last_seen`

### AbuseIPDB

**Endpoint:** GET `https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90`

**Auth:** HTTP header `Key: {api_key}` (note: capital `Key`)

**Accept header required:** `Accept: application/json` — without this, API may return HTML

**Supported types:** `{IPV4, IPV6}` only

**Verdict logic (data.abuseConfidenceScore, data.totalReports):**
- `abuseConfidenceScore >= 75` → `"malicious"`
- `25 <= score < 75` → `"suspicious"`
- `score < 25 AND totalReports > 0` → `"clean"`
- `totalReports == 0` → `"no_data"`

**detection_count / total_engines:** Use `totalReports` / `numDistinctUsers`

**HTTP notes:** AbuseIPDB returns 200 for all known IPs (score=0 for clean IPs). Does not return 404 for unknown IPs — just returns score=0 and totalReports=0.

**Rate limiting:** Free tier is 1000 checks/day. 429 response → `EnrichmentError("Rate limit exceeded (429)")`.

**ALLOWED_API_HOSTS entry:** `"api.abuseipdb.com"`

**raw_stats to capture:** `abuseConfidenceScore`, `totalReports`, `numDistinctUsers`, `countryCode`, `isp`, `usageType`, `lastReportedAt`, `isWhitelisted`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key storage | Custom file format / env var loader | `ConfigStore.get_provider_key()` / `set_provider_key()` | Already built, tested, secure (0o600 permissions) |
| SSRF prevention | Custom hostname check | `validate_endpoint()` from `http_safety.py` | Already handles URL parsing, allowlist check, error message |
| Response size cap | `resp.content` with size check | `read_limited()` from `http_safety.py` | Streaming, 8KB chunk, 1MB cap, JSON parse — already tested |
| Provider filtering by type | Manual list filtering | `registry.providers_for_type(ioc_type)` | Already filters by `is_configured()` + `supported_types` |
| Multi-provider settings HTML | Custom form logic | `PROVIDER_INFO` list in `setup.py` + Jinja2 loop | Keeps template declarative, avoids N per-provider code paths |

**Key insight:** Every security control (SSRF, timeout, size cap) and every data-access pattern (key storage, provider filtering) is already implemented. New adapters are thin wrappers around these shared utilities.

---

## Common Pitfalls

### Pitfall 1: URLhaus Uses POST, Not GET
**What goes wrong:** Writing a GET request to URLhaus endpoints returns 405 Method Not Allowed.
**Why it happens:** URLhaus API is form-POST based (abuse.ch convention), unlike most REST APIs.
**How to avoid:** Use `requests.post(..., data={...})` not `requests.get(...)`. Use `data=` not `json=` — URLhaus expects form-encoded body.
**Warning signs:** 405 in test mocks not triggering correctly; verify mock patches `requests.post` not `requests.get`.

### Pitfall 2: URLhaus Has Multiple Endpoints (Not One)
**What goes wrong:** Sending a URL IOC to `/host/` endpoint or a hash IOC to `/url/` endpoint returns unexpected `query_status`.
**Why it happens:** URLhaus has three separate endpoints for different IOC types. The routing must be implemented.
**How to avoid:** Use an `ENDPOINT_MAP` dict (similar to VTAdapter's `ENDPOINT_MAP`) mapping `IOCType` → `(url, body_key)` tuple.
**Warning signs:** `query_status == "no_results"` for known-malicious IOCs in tests.

### Pitfall 3: OTX `supported_types` Must Include CVE
**What goes wrong:** CVE IOCs silently fall through with `EnrichmentError("Unsupported type")` because CVE was excluded from the set.
**Why it happens:** OTX is the first CVE provider; easy to forget CVE when defining the set.
**How to avoid:** Explicitly include `IOCType.CVE` in `OTXAdapter.supported_types`. Add a test: `assert IOCType.CVE in OTXAdapter.supported_types`.
**Warning signs:** CVE-2021-44228 test returns `EnrichmentError` instead of a verdict.

### Pitfall 4: OTX File Hash Type Mapping
**What goes wrong:** MD5/SHA1/SHA256 lookups return 404 because the wrong type string is used in the URL path.
**Why it happens:** OTX uses `"file"` for all hash types — not `"md5"`, `"sha1"`, or `"sha256"`.
**How to avoid:** Map all three hash `IOCType` values to `"file"` in the endpoint type string map.
**Warning signs:** Hash lookups return 404 in real API calls.

### Pitfall 5: GreyNoise Header Name Is Lowercase `key`
**What goes wrong:** Authentication fails (401) because the header is sent as `Key` or `Authorization`.
**Why it happens:** GreyNoise Community API uses a non-standard header name `key`.
**How to avoid:** `headers={"key": self._api_key, "Accept": "application/json"}`.
**Warning signs:** 401 responses in real API calls; tests pass because mocks don't check headers.

### Pitfall 6: AbuseIPDB `Accept` Header Required
**What goes wrong:** API returns HTML instead of JSON, causing `json.JSONDecodeError` in `read_limited()`.
**Why it happens:** AbuseIPDB serves HTML by default without `Accept: application/json`.
**How to avoid:** Always include `Accept: application/json` in request headers.
**Warning signs:** `json.JSONDecodeError` wrapped in `EnrichmentError("Unexpected error")`.

### Pitfall 7: AbuseIPDB Does Not Return 404 for Unknown IPs
**What goes wrong:** Code that checks for 404 (no_data) misses the case where AbuseIPDB returns 200 with score=0 and totalReports=0.
**Why it happens:** AbuseIPDB always returns 200 with data for any valid IP. The no-data signal is `totalReports == 0`.
**How to avoid:** Parse the body first and use `totalReports == 0` as the `no_data` condition — do NOT rely on HTTP status for no_data.
**Warning signs:** All IPs return verdicts, never `no_data`, even for private/reserved IPs.

### Pitfall 8: test_registry_setup.py Provider Count
**What goes wrong:** `test_registry_has_four_providers` fails after adding new providers.
**Why it happens:** The test asserts exactly 4 providers; after adding 4 more, there are 8.
**How to avoid:** Update `test_registry_has_four_providers` → `test_registry_has_eight_providers` in the same task that adds the registration calls.
**Warning signs:** CI green but the count test is wrong; count assertion is a magic number.

### Pitfall 9: SSRF Allowlist Must Be Updated Alongside Each Adapter
**What goes wrong:** Adapter passes tests (mocked) but fails in production because the hostname is blocked by SSRF validation.
**Why it happens:** `validate_endpoint()` checks against `Config.ALLOWED_API_HOSTS`; new hostnames must be added.
**How to avoid:** Each adapter task includes updating `app/config.py` ALLOWED_API_HOSTS as a required step. The Shodan test pattern includes `test_config_allows_shodan` that verifies the hostname — add equivalent tests.
**Warning signs:** `EnrichmentError("...not in allowed_hosts (SSRF allowlist SEC-16)...")` in production.

---

## Code Examples

### Example 1: Registry Setup for All 8 Providers (setup.py after Phase 3)

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub.md Task 3.5

def build_registry(allowed_hosts: list[str], config_store: ConfigStore) -> ProviderRegistry:
    registry = ProviderRegistry()

    # Existing providers
    vt_key = config_store.get_vt_api_key() or ""
    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_hosts))
    registry.register(MBAdapter(allowed_hosts=allowed_hosts))
    registry.register(TFAdapter(allowed_hosts=allowed_hosts))
    registry.register(ShodanAdapter(allowed_hosts=allowed_hosts))

    # New Phase 3 providers
    urlhaus_key = config_store.get_provider_key("urlhaus") or ""
    registry.register(URLhausAdapter(api_key=urlhaus_key, allowed_hosts=allowed_hosts))

    otx_key = config_store.get_provider_key("otx") or ""
    registry.register(OTXAdapter(api_key=otx_key, allowed_hosts=allowed_hosts))

    gn_key = config_store.get_provider_key("greynoise") or ""
    registry.register(GreyNoiseAdapter(api_key=gn_key, allowed_hosts=allowed_hosts))

    abuseipdb_key = config_store.get_provider_key("abuseipdb") or ""
    registry.register(AbuseIPDBAdapter(api_key=abuseipdb_key, allowed_hosts=allowed_hosts))

    return registry
```

### Example 2: URLhaus Endpoint Selection (IOC-type routing)

```python
# Source: design doc + impl plan Task 3.1

_ENDPOINT_MAP: dict[IOCType, tuple[str, str, str]] = {
    # (base_path, body_key, body_value_is_ioc)
    IOCType.URL:    ("/v1/url/",     "url",        "value"),
    IOCType.IPV4:   ("/v1/host/",    "host",       "value"),
    IOCType.IPV6:   ("/v1/host/",    "host",       "value"),
    IOCType.DOMAIN: ("/v1/host/",    "host",       "value"),
    IOCType.MD5:    ("/v1/payload/", "md5_hash",   "value"),
    IOCType.SHA256: ("/v1/payload/", "sha256_hash","value"),
}

# In lookup():
path, body_key, _ = _ENDPOINT_MAP[ioc.type]
url = f"https://urlhaus-api.abuse.ch{path}"
resp = requests.post(
    url,
    data={body_key: ioc.value},
    headers={"Auth-Key": self._api_key, "Accept": "application/json"},
    timeout=TIMEOUT,
    allow_redirects=False,
    stream=True,
)
```

### Example 3: OTX Type String Mapping

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub.md Task 3.2

_OTX_TYPE_MAP: dict[IOCType, str] = {
    IOCType.IPV4:   "IPv4",
    IOCType.IPV6:   "IPv6",
    IOCType.DOMAIN: "domain",
    IOCType.URL:    "url",
    IOCType.MD5:    "file",
    IOCType.SHA1:   "file",
    IOCType.SHA256: "file",
    IOCType.CVE:    "cve",
}

# In lookup():
otx_type = _OTX_TYPE_MAP[ioc.type]
url = f"https://otx.alienvault.com/api/v1/indicators/{otx_type}/{ioc.value}/general"
```

### Example 4: GreyNoise Verdict Logic

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub-design.md

def _parse_greynoise(ioc: IOC, body: dict, name: str) -> EnrichmentResult:
    riot = body.get("riot", False)
    noise = body.get("noise", False)
    classification = body.get("classification", "")

    if riot:
        verdict = "clean"
    elif classification == "malicious":
        verdict = "malicious"
    elif noise:
        verdict = "suspicious"
    else:
        verdict = "no_data"

    return EnrichmentResult(
        ioc=ioc, provider=name, verdict=verdict,
        detection_count=1 if verdict in ("malicious", "suspicious") else 0,
        total_engines=1, scan_date=body.get("last_seen"),
        raw_stats={
            "noise": noise, "riot": riot,
            "classification": classification,
            "name": body.get("name"), "link": body.get("link"),
        },
    )
```

### Example 5: AbuseIPDB Verdict Logic

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub-design.md

def _parse_abuseipdb(ioc: IOC, body: dict, name: str) -> EnrichmentResult:
    data = body.get("data", {})
    score = data.get("abuseConfidenceScore", 0)
    total_reports = data.get("totalReports", 0)
    distinct_users = data.get("numDistinctUsers", 0)

    if score >= 75:
        verdict = "malicious"
    elif score >= 25:
        verdict = "suspicious"
    elif total_reports > 0:
        verdict = "clean"
    else:
        verdict = "no_data"

    return EnrichmentResult(
        ioc=ioc, provider=name, verdict=verdict,
        detection_count=total_reports,
        total_engines=distinct_users,
        scan_date=data.get("lastReportedAt"),
        raw_stats={
            "abuseConfidenceScore": score,
            "totalReports": total_reports,
            "numDistinctUsers": distinct_users,
            "countryCode": data.get("countryCode"),
            "isp": data.get("isp"),
            "usageType": data.get("usageType"),
        },
    )
```

### Example 6: Settings Page Multi-Provider Route (routes.py)

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub.md Task 3.6

from app.enrichment.setup import PROVIDER_INFO

def settings_get():
    config_store = ConfigStore()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        key = config_store.get_vt_api_key() if pid == "virustotal" else config_store.get_provider_key(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    return render_template("settings.html", providers=providers_with_status)
```

---

## ALLOWED_API_HOSTS: Final State After Phase 3

```python
# Source: docs/plans/2026-03-02-universal-threat-intel-hub.md Task 3.5
# app/config.py

ALLOWED_API_HOSTS: list[str] = [
    "www.virustotal.com",
    "mb-api.abuse.ch",
    "threatfox-api.abuse.ch",
    "internetdb.shodan.io",
    "urlhaus-api.abuse.ch",    # URLhaus — note: different from mb-api.abuse.ch
    "otx.alienvault.com",
    "api.greynoise.io",
    "api.abuseipdb.com",
]
```

---

## Task Plan (6 tasks, matching implementation plan)

| Task | Scope | Files Created | Files Modified |
|------|-------|---------------|----------------|
| 03-01 | URLhausAdapter (TDD) | `adapters/urlhaus.py`, `tests/test_urlhaus.py` | `app/config.py` |
| 03-02 | OTXAdapter (TDD) | `adapters/otx.py`, `tests/test_otx.py` | `app/config.py` |
| 03-03 | GreyNoiseAdapter (TDD) | `adapters/greynoise.py`, `tests/test_greynoise.py` | `app/config.py` |
| 03-04 | AbuseIPDBAdapter (TDD) | `adapters/abuseipdb.py`, `tests/test_abuseipdb.py` | `app/config.py` |
| 03-05 | Register all 4 in registry | — | `app/enrichment/setup.py`, `tests/test_registry_setup.py` |
| 03-06 | Settings page multi-provider | — | `app/routes.py`, `app/templates/settings.html`, `app/enrichment/setup.py`, `app/static/src/ts/modules/settings.ts` |

Each of tasks 03-01 through 03-04 is independently testable and committable. Each adds one new hostname to `ALLOWED_API_HOSTS` to keep the allowlist in sync with the adapter.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded adapter lists in orchestrator | Registry pattern: `registry.providers_for_type(ioc_type)` | Phase 1 (v4.0) | New adapters need zero orchestrator changes |
| Single VT key in `[virustotal]` INI section | Multi-provider keys in `[providers]` INI section | Phase 1 (v4.0) | `ConfigStore.get_provider_key(name)` ready to use |
| Settings page: single VT form | Multi-provider: PROVIDER_INFO loop in template | Phase 3 (this phase) | Settings page scales to any number of providers |

---

## Open Questions

1. **URLhaus SHA1 support**
   - What we know: The implementation plan says `supported_types = {URL, IPV4, IPV6, DOMAIN, MD5, SHA256}` — no SHA1.
   - What's unclear: URLhaus `/payload/` accepts `sha256_hash` and `md5_hash` params. SHA1 is not documented as supported.
   - Recommendation: Exclude SHA1 as the plan specifies. If SHA1 is needed later, it can be added by adding `IOCType.SHA1` to supported_types and a `sha1_hash` body key.

2. **GreyNoise 404 vs. empty body**
   - What we know: GreyNoise returns 404 for IPs not in its database; the verdict is `no_data`.
   - What's unclear: Some versions of GreyNoise Community may return a body with `{"message": "ip not observed scanning the internet or contained in RIOT"}` with a 404.
   - Recommendation: Handle 404 as `no_data` using the standard 404-before-raise_for_status pattern, regardless of body content.

3. **Settings page: MalwareBazaar, ThreatFox, Shodan display**
   - What we know: `PROVIDER_INFO` in the impl plan lists only the 5 key-requiring providers (VT + 4 new). The 3 zero-auth providers (MB, TF, Shodan) are not in the list.
   - What's unclear: Should zero-auth providers appear in the settings page as "No Key Required"?
   - Recommendation: Follow the implementation plan as written — only key-requiring providers in `PROVIDER_INFO`. Zero-auth providers can be added to a read-only status display in Phase 4.

---

## Sources

### Primary (HIGH confidence)
- `docs/plans/2026-03-02-universal-threat-intel-hub.md` — complete implementation plan with per-task code for all Phase 3 tasks
- `docs/plans/2026-03-02-universal-threat-intel-hub-design.md` — API endpoints, auth headers, verdict logic for all 4 providers
- `app/enrichment/adapters/shodan.py` — canonical adapter pattern to replicate
- `app/enrichment/adapters/virustotal.py` — canonical API-key adapter pattern
- `app/enrichment/http_safety.py` — validate_endpoint, read_limited, TIMEOUT constants
- `app/enrichment/config_store.py` — get_provider_key / set_provider_key already implemented
- `app/enrichment/setup.py` — build_registry factory to extend
- `app/config.py` — ALLOWED_API_HOSTS to extend
- `tests/test_shodan.py` — canonical test structure to replicate
- `tests/test_registry_setup.py` — registry setup test to extend to 8 providers

### Secondary (MEDIUM confidence)
- URLhaus API documentation: https://urlhaus.abuse.ch/api/ — POST endpoints, Auth-Key header, query_status values
- OTX AlienVault API documentation: https://otx.alienvault.com/api — endpoint format, X-OTX-API-KEY header, pulse_info structure
- GreyNoise API documentation: https://docs.greynoise.io/reference/get_v3-community-ip — riot/noise/classification response fields
- AbuseIPDB API documentation: https://docs.abuseipdb.com/#check-endpoint — abuseConfidenceScore, totalReports, maxAgeInDays

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all patterns proven in existing codebase
- Architecture: HIGH — adapter pattern fully proven in Phases 1 and 2; this is structured repetition
- API specifics (endpoints, auth, verdict logic): HIGH — documented in design doc and impl plan, cross-referenced with official docs
- Pitfalls: HIGH — sourced from existing adapter implementations and design decisions already captured in STATE.md

**Research date:** 2026-03-02
**Valid until:** 2026-04-01 (API endpoint formats are stable; verdict thresholds come from design doc decisions, not upstream changes)
