# Phase 2: Shodan InternetDB (Zero-Auth Provider) - Research

**Researched:** 2026-03-02
**Domain:** Shodan InternetDB API, Python provider adapter pattern, pytest mocking
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOD-01 | Shodan InternetDB enriches IP addresses without requiring an API key — port/CVE/tag data appears in results | InternetDB GET endpoint requires no auth; always `is_configured() == True`; returns ports, vulns, tags, hostnames, cpes |
| SHOD-02 | The adapter was added by creating one file and one registration line — no orchestrator or route changes needed | Phase 1 established this pattern exactly; `setup.py` is the only non-adapter file to touch |
</phase_requirements>

---

## Summary

Phase 2 is the first provider added through the Phase 1 registry architecture. Its primary purpose is to prove the plugin model works end-to-end: one new adapter file plus one `registry.register()` call in `setup.py` is the complete changeset, with zero modifications to routes, orchestrator, templates, or TypeScript.

The Shodan InternetDB API is a free, zero-authentication REST API (`GET https://internetdb.shodan.io/{ip}`) that returns open ports, known vulnerabilities (CVE IDs), tags, hostnames, and CPE identifiers for any publicly routable IP address. It supports IPv4 and IPv6. Responses are JSON with six fields: `ip`, `ports`, `hostnames`, `cpes`, `vulns`, `tags`. A 404 response with `{"detail":"No information available"}` is returned for IPs with no data (including private/RFC1918 addresses). A 429 response is returned when rate-limited.

Verdict logic maps directly to the design doc: presence of CVE IDs in `vulns` array → `"suspicious"`; presence of known-bad tags (`malware`, `compromised`, `doublepulsar`) → `"malicious"`; any data but no vulns/bad tags → `"informational"` (rendered as `"no_data"` in the existing verdict set); 404 → `"no_data"`. The adapter follows the identical structure as `MBAdapter` and `TFAdapter` — same constructor signature, same HTTP safety controls, same `is_configured() -> True` pattern.

**Primary recommendation:** Model `ShodanAdapter` directly on `MBAdapter` (the simplest zero-auth reference implementation). Use `requests.get` (not POST), build the URL as `f"https://internetdb.shodan.io/{ioc.value}"`, and handle 404 as `no_data` rather than an error.

---

## Standard Stack

### Core (already in project — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | Already installed | HTTP GET to InternetDB | Already used by all three adapters |
| `app.enrichment.http_safety` | Project module | TIMEOUT, read_limited, validate_endpoint | All adapters use these three — mandatory for SEC-04/05/06/16 |
| `app.enrichment.models` | Project module | EnrichmentResult, EnrichmentError | Standard return types from Provider protocol |
| `app.pipeline.models` | Project module | IOC, IOCType | Standard input type from Provider protocol |
| `pytest` + `unittest.mock` | Already installed | TDD adapter tests | Identical pattern to test_malwarebazaar.py |

### No New Dependencies

Zero new pip packages. The InternetDB API requires no authentication and no client library.

**Installation:** nothing to install.

---

## Architecture Patterns

### File Structure for Phase 2

```
app/enrichment/
├── adapters/
│   ├── shodan.py        # NEW: ShodanAdapter (one file, ~80 lines)
│   ├── malwarebazaar.py # UNCHANGED
│   ├── threatfox.py     # UNCHANGED
│   └── virustotal.py    # UNCHANGED
├── setup.py             # MODIFIED: add one registry.register() call
├── provider.py          # UNCHANGED
├── registry.py          # UNCHANGED
├── http_safety.py       # UNCHANGED
└── models.py            # UNCHANGED

app/config.py            # MODIFIED: add "internetdb.shodan.io" to ALLOWED_API_HOSTS

tests/
├── test_shodan.py       # NEW: adapter unit tests (mirrors test_malwarebazaar.py)
├── test_registry_setup.py  # MODIFIED: assert 4 providers, assert "Shodan InternetDB" present
└── (all other tests)    # UNCHANGED
```

### Pattern 1: Zero-Auth Adapter Structure

**What:** An adapter that always returns `is_configured() == True` and uses GET (not POST).

**When to use:** Any provider with a public, unauthenticated REST API.

**Reference:** Mirror `MBAdapter` exactly, substituting GET for POST and the Shodan URL.

```python
# Source: MBAdapter pattern (app/enrichment/adapters/malwarebazaar.py)
# app/enrichment/adapters/shodan.py
from __future__ import annotations

import logging

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"

# Tags confirmed as indicating malicious/compromised activity
# Source: Shodan tag definitions (pkg.go.dev/github.com/denisgubin/shodan/models/tags)
_MALICIOUS_TAGS = {"malware", "compromised", "doublepulsar"}


class ShodanAdapter:
    """Adapter for the Shodan InternetDB API.

    Supports IPv4 and IPv6 lookups. No API key required.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "Shodan InternetDB"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        """Always returns True — Shodan InternetDB requires no API key."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url = f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url,
                timeout=TIMEOUT,           # SEC-04
                allow_redirects=False,     # SEC-06
                stream=True,               # SEC-05 setup
            )
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=0,
                    scan_date=None,
                    raw_stats={},
                )
            resp.raise_for_status()
            body = read_limited(resp)     # SEC-05: byte cap enforced
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(
                ioc=ioc, provider=self.name, error=f"HTTP {code}"
            )
        except Exception:
            logger.exception("Unexpected error during Shodan lookup for %s", ioc.value)
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )
```

### Pattern 2: Verdict Logic from Shodan Response

**What:** Map InternetDB fields to the project's four-verdict system.

**Priority order (highest to lowest):**
1. Bad tags (`malware`, `compromised`, `doublepulsar`) present → `"malicious"`
2. Vulns array non-empty → `"suspicious"`
3. Response has data but no vulns and no bad tags → `"informational"` mapped as `"no_data"` (Shodan is not a verdict authority on clean IPs — port data alone does not mean clean)
4. HTTP 404 → `"no_data"` (no Shodan data for this IP)

**Design rationale:** The design doc says "has vulns → suspicious; known-bad tags → malicious; else informational." The existing verdict set is `malicious | suspicious | clean | no_data`. "Informational" should map to `"no_data"` rather than `"clean"` because Shodan seeing open ports is not a clean verdict — it is simply neutral intelligence. Mapping to `"clean"` would be misleading.

```python
# app/enrichment/adapters/shodan.py
def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse an InternetDB 200 response into an EnrichmentResult.

    Args:
        ioc:           The IP IOC that was queried.
        body:          Parsed JSON from InternetDB response.
        provider_name: Provider name string for result attribution.

    Returns:
        EnrichmentResult with verdict based on vulns and tags.
    """
    vulns: list[str] = body.get("vulns", [])
    tags: list[str] = body.get("tags", [])
    ports: list[int] = body.get("ports", [])
    hostnames: list[str] = body.get("hostnames", [])
    cpes: list[str] = body.get("cpes", [])

    bad_tags = [t for t in tags if t in _MALICIOUS_TAGS]

    if bad_tags:
        verdict = "malicious"
        detection_count = 1
    elif vulns:
        verdict = "suspicious"
        detection_count = len(vulns)
    else:
        verdict = "no_data"
        detection_count = 0

    raw_stats: dict = {
        "ports": ports,
        "vulns": vulns,
        "tags": tags,
        "hostnames": hostnames,
        "cpes": cpes,
    }

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,   # InternetDB is single-source
        scan_date=None,    # InternetDB provides no timestamp in response
        raw_stats=raw_stats,
    )
```

### Pattern 3: setup.py Registration (one line change)

**What:** Add one import and one `registry.register()` call to `build_registry()`.

**When to use:** Every new provider follows this exact pattern.

```python
# app/enrichment/setup.py — MODIFIED
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.shodan import ShodanAdapter    # ADD THIS LINE
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.config_store import ConfigStore
from app.enrichment.registry import ProviderRegistry


def build_registry(
    allowed_hosts: list[str],
    config_store: ConfigStore,
) -> ProviderRegistry:
    registry = ProviderRegistry()
    vt_key = config_store.get_vt_api_key() or ""
    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_hosts))
    registry.register(MBAdapter(allowed_hosts=allowed_hosts))
    registry.register(TFAdapter(allowed_hosts=allowed_hosts))
    registry.register(ShodanAdapter(allowed_hosts=allowed_hosts))  # ADD THIS LINE
    return registry
```

### Pattern 4: SSRF Allowlist Update (config.py)

**What:** Add `"internetdb.shodan.io"` to `ALLOWED_API_HOSTS`.

**Critical:** `validate_endpoint()` blocks all calls to hosts not in this list. Without this change, every Shodan lookup returns an `EnrichmentError("... not in allowed_hosts")` — not a test failure but a silent runtime block.

```python
# app/config.py — MODIFIED
ALLOWED_API_HOSTS: list[str] = [
    "www.virustotal.com",
    "mb-api.abuse.ch",
    "threatfox-api.abuse.ch",
    "internetdb.shodan.io",   # ADD THIS LINE
]
```

### Pattern 5: Test Structure (mirrors test_malwarebazaar.py)

**What:** Six test classes covering: found with vulns, found with bad tags, found clean, not found (404), unsupported type, timeout, HTTP error, SSRF validation, supported_types set, response size limit.

```python
# tests/test_shodan.py — structure outline
import json
from unittest.mock import MagicMock, patch
import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.shodan import ShodanAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES

ALLOWED_HOSTS = ["internetdb.shodan.io"]

# Sample fixtures
SHODAN_FOUND_WITH_VULNS = {
    "ip": "1.2.3.4",
    "ports": [22, 80, 443],
    "cpes": [],
    "hostnames": ["example.com"],
    "tags": [],
    "vulns": ["CVE-2021-44228", "CVE-2022-0001"],
}

SHODAN_FOUND_WITH_BAD_TAG = {
    "ip": "1.2.3.4",
    "ports": [22],
    "cpes": [],
    "hostnames": [],
    "tags": ["malware"],
    "vulns": [],
}

SHODAN_FOUND_CLEAN = {
    "ip": "8.8.8.8",
    "ports": [53],
    "cpes": ["cpe:/a:isc:bind"],
    "hostnames": ["dns.google"],
    "tags": [],
    "vulns": [],
}

SHODAN_NOT_FOUND = {"detail": "No information available"}

# Tests:
# - TestLookupFound: vulns → suspicious, bad tags → malicious, clean → no_data
# - TestLookupNotFound: 404 → EnrichmentResult(verdict="no_data")
# - TestLookupErrors: unsupported type, timeout, HTTP 500, SSRF, response size cap
# - TestSupportedTypes: IPV4 and IPV6 in set, DOMAIN/MD5/etc not in set
# - TestProtocolConformance: isinstance(ShodanAdapter(...), Provider) == True
```

### Anti-Patterns to Avoid

- **Using `resp.raise_for_status()` before checking 404:** A 404 is a valid "not found" response from InternetDB, not an error. Check `resp.status_code == 404` BEFORE calling `raise_for_status()`, otherwise the 404 triggers an `HTTPError` and returns an `EnrichmentError` instead of `no_data`.
- **Mapping "has ports but no vulns" to `"clean"`:** Open ports are not a clean verdict. Shodan is not a reputation authority. Use `"no_data"` for IPs with ports but no vulns or bad tags.
- **Hardcoding `"internetdb.shodan.io"` in the URL without adding it to ALLOWED_API_HOSTS:** `validate_endpoint()` will silently block all requests with an EnrichmentError, not a test failure. Easy to miss.
- **Treating 429 as a hard error requiring special handling:** For a local triage tool used one-at-a-time, rate limiting is exceedingly unlikely. Treat 429 like any other HTTP error (EnrichmentError with the status code). Do not add delay or retry logic.
- **Building the URL with the base plus query string:** InternetDB uses a path parameter, not a query string. `https://internetdb.shodan.io/{ip}` — not `?ip=...`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP timeout enforcement | Custom signal-based timeout | `TIMEOUT = (5, 30)` from `http_safety` | Already project-standard SEC-04 |
| Response size cap | Custom byte counter | `read_limited(resp)` from `http_safety` | SEC-05 — 1 MB cap already implemented |
| SSRF allowlist check | Custom hostname check | `validate_endpoint(url, allowed_hosts)` from `http_safety` | SEC-16 — already used by all three adapters |
| Redirect prevention | Manual header inspection | `allow_redirects=False` kwarg | SEC-06 — one line |
| Unsupported type guard | Try/except around bad lookups | Early return EnrichmentError | Explicit, fast, tested pattern from MB and TF adapters |

**Key insight:** `http_safety.py` already contains every HTTP safety control needed. The adapter only needs to import three names from it: `TIMEOUT`, `read_limited`, `validate_endpoint`.

---

## Common Pitfalls

### Pitfall 1: 404 Must Be no_data, Not EnrichmentError

**What goes wrong:** Calling `resp.raise_for_status()` unconditionally — 404 raises `HTTPError`, which gets caught as an error and returns `EnrichmentError("HTTP 404")` instead of `EnrichmentResult(verdict="no_data")`.

**Why it happens:** `raise_for_status()` treats all 4xx/5xx as errors. But 404 from InternetDB means "no Shodan data for this IP" — a valid, expected, meaningful result.

**How to avoid:** Check `if resp.status_code == 404: return EnrichmentResult(verdict="no_data", ...)` BEFORE calling `resp.raise_for_status()`. Every other 4xx/5xx is a genuine error and should become `EnrichmentError`.

**Warning signs:** Tests for "not found" IP pass `"no_data"` expectation but get `EnrichmentError` instead.

### Pitfall 2: ALLOWED_API_HOSTS Must Include the Shodan Hostname

**What goes wrong:** `validate_endpoint()` checks that the request URL hostname is in `allowed_hosts`. If `"internetdb.shodan.io"` is not in `Config.ALLOWED_API_HOSTS`, every production lookup returns `EnrichmentError` with an SSRF allowlist message.

**Why it happens:** `validate_endpoint()` is designed to fail fast — it raises `ValueError` before any network call. The test suite passes `ALLOWED_HOSTS = ["internetdb.shodan.io"]` explicitly, so unit tests pass even without the config.py change. The production failure is only visible when actually running the app.

**How to avoid:** Add `"internetdb.shodan.io"` to `Config.ALLOWED_API_HOSTS` in `app/config.py` as part of the same commit as the adapter. Write an integration test that uses `Config.ALLOWED_API_HOSTS` directly (not a local override) to catch this.

**Warning signs:** Unit tests pass; app in online mode returns enrichment errors for all IPs but no error messages explain why.

### Pitfall 3: Provider Count Regression in test_registry_setup.py

**What goes wrong:** `test_registry_has_three_providers` asserts `len(registry.all()) == 3`. After adding ShodanAdapter, this test fails because there are now 4 providers.

**Why it happens:** The count assertion was written for the Phase 1 baseline.

**How to avoid:** Update `test_registry_has_three_providers` to `assert len(registry.all()) == 4` and add a `test_registry_contains_shodan` test. This is a straightforward update, not a design problem.

**Warning signs:** `test_registry_setup.py::TestBuildRegistry::test_registry_has_three_providers` fails immediately after adding the `registry.register(ShodanAdapter(...))` line.

### Pitfall 4: Provider Name String Must Be Consistent

**What goes wrong:** Using different string values for the provider name in different places — e.g., `"shodan"` in one place and `"Shodan InternetDB"` in another.

**Why it happens:** The `name` class attribute, the `EnrichmentResult.provider` field, and any string comparisons in tests must all use the exact same string.

**How to avoid:** Define `name = "Shodan InternetDB"` as the class attribute, use `self.name` (not a literal string) in all `EnrichmentResult` and `EnrichmentError` constructors. The test that checks `isinstance(adapter, Provider)` verifies the attribute exists; the tests that check `result.provider == "Shodan InternetDB"` verify the value.

**Warning signs:** Settings page (Phase 1-03 if implemented) shows wrong provider name; test assertions on `result.provider` fail.

### Pitfall 5: IPv6 Address in URL Path

**What goes wrong:** IPv6 addresses contain colons (`::1`, `2001:db8::1`). When used directly in a URL path `https://internetdb.shodan.io/2001:db8::1`, some HTTP clients or proxies may misinterpret the colons.

**Why it happens:** IPv6 literals in URLs should technically be bracketed: `https://internetdb.shodan.io/[2001:db8::1]`. However, Shodan's InternetDB is designed to accept unbracketed IPv6 values in the path.

**How to avoid:** Use `ioc.value` directly — the IOC extraction pipeline already produces canonical IPv6 strings. Test with a known IPv6 value to confirm the API returns a response (or 404). Do not add brackets around IPv6 values; InternetDB does not expect them.

**Warning signs:** HTTP 422 (Validation Error) from InternetDB for IPv6 lookups.

### Pitfall 6: `vulns` May Be Empty List, Not Absent

**What goes wrong:** Using `body["vulns"]` (KeyError if missing) instead of `body.get("vulns", [])` for IPs that have ports but no known CVEs.

**Why it happens:** The InternetDB OpenAPI spec lists `vulns` as a required field, but not all 200 responses include it in practice. Defensive coding requires `.get()` with a default.

**How to avoid:** Always use `body.get("vulns", [])`, `body.get("tags", [])`, `body.get("ports", [])`, etc. Never use direct key access on external API response dicts.

**Warning signs:** `KeyError: 'vulns'` in production logs for IPs that have ports but no CVEs.

---

## Code Examples

### InternetDB API Response (200 — found with vulns)

```json
{
  "ip": "1.2.3.4",
  "ports": [22, 80, 443],
  "cpes": ["cpe:/a:apache:http_server:2.4.49"],
  "hostnames": ["example.com"],
  "tags": [],
  "vulns": ["CVE-2021-41773", "CVE-2021-42013"]
}
```
Source: Official InternetDB OpenAPI spec at `https://internetdb.shodan.io/openapi.json`

### InternetDB API Response (404 — not found)

```json
{"detail": "No information available"}
```
Source: Confirmed in multiple implementations and issue trackers (bbot GitHub issue #2412)

### InternetDB API Response (429 — rate limited)

```json
{"error": "Rate limit exceeded. Contact sales@shodan.io if you need a higher rate limit."}
```
Source: bbot GitHub issue #2412

### Mock Helper for GET Requests (test pattern)

```python
# tests/test_shodan.py
def _make_mock_get_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response for GET requests."""
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

### Protocol Conformance Test

```python
# tests/test_shodan.py
from app.enrichment.provider import Provider
from app.enrichment.adapters.shodan import ShodanAdapter

def test_shodan_adapter_is_provider() -> None:
    """ShodanAdapter satisfies the Provider protocol."""
    adapter = ShodanAdapter(allowed_hosts=[])
    assert isinstance(adapter, Provider)
```

### Verdict Logic Tests (key cases)

```python
# tests/test_shodan.py
class TestLookupFound:

    def test_vulns_present_returns_suspicious(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, SHODAN_FOUND_WITH_VULNS)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"
        assert result.provider == "Shodan InternetDB"

    def test_malware_tag_returns_malicious(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="5.6.7.8", raw_match="5.6.7.8")
        mock_resp = _make_mock_get_response(200, SHODAN_FOUND_WITH_BAD_TAG)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_ports_only_returns_no_data(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, SHODAN_FOUND_CLEAN)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

class TestLookupNotFound:

    def test_404_returns_no_data(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        mock_resp = _make_mock_get_response(404, SHODAN_NOT_FOUND)
        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
```

---

## InternetDB API Reference

### Endpoint

```
GET https://internetdb.shodan.io/{ip}
```

- No authentication required
- No API key header
- No request body
- `ip` is a path parameter (IPv4 or IPv6 string)

### Response Schema (200)

| Field | Type | Description |
|-------|------|-------------|
| `ip` | string | The queried IP address |
| `ports` | list[int] | Open ports detected (weekly scan cadence) |
| `hostnames` | list[str] | Reverse DNS hostnames |
| `cpes` | list[str] | Common Platform Enumeration identifiers |
| `vulns` | list[str] | CVE identifiers for known vulnerabilities |
| `tags` | list[str] | Classification tags (see below) |

Source: OpenAPI spec at `https://internetdb.shodan.io/openapi.json` (verified 2026-03-02)

### Known Tags with Security Significance

| Tag | Meaning | Verdict Impact |
|-----|---------|----------------|
| `malware` | Confirmed C2 server (Malware Hunter) | `"malicious"` |
| `compromised` | Actively compromised (e.g., ransomware NoSQL) | `"malicious"` |
| `doublepulsar` | DoublePulsar backdoor detected | `"malicious"` |
| `scanner` | Device observed scanning the internet | None (informational) |
| `honeypot` | Appears to mimic a service | None (informational) |
| `tor` | Tor node | None (informational) |
| `onion` | Tor onion service leaking to clearnet | None (informational) |
| `self-signed` | Self-signed TLS certificate | None (informational) |
| `cdn` | Content delivery network | None (informational) |
| `vpn` | VPN service | None (informational) |

Source: Shodan tag definitions verified via `pkg.go.dev/github.com/denisgubin/shodan/models/tags` (MEDIUM confidence — third-party Go package but Shodan-specific); cross-referenced with Shodan blog.

### Status Codes

| Code | Meaning | Adapter Response |
|------|---------|-----------------|
| 200 | Data found | `EnrichmentResult` with verdict from vulns/tags |
| 404 | No data for this IP | `EnrichmentResult(verdict="no_data")` |
| 422 | Validation error (malformed IP) | `EnrichmentError(error="HTTP 422")` |
| 429 | Rate limited (temporary IP ban) | `EnrichmentError(error="HTTP 429")` |

Note: Private/RFC1918 addresses return 404 (not an error). Localhost (127.0.0.1) returns 404.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded adapters in routes.py | Plugin-style registry with setup.py | Phase 1 | Adding Shodan requires 1 file + 1 line |
| VT-only online mode guard | registry.configured() check | Phase 1 | Shodan's always-configured status automatically enables online mode |

**What Phase 2 adds:**
- `"internetdb.shodan.io"` to `ALLOWED_API_HOSTS`
- `ShodanAdapter` in `app/enrichment/adapters/shodan.py`
- One `registry.register(ShodanAdapter(...))` line in `setup.py`
- `test_shodan.py` with full unit test coverage
- Updated `test_registry_setup.py` provider count assertions

**What Phase 2 does NOT touch:**
- `routes.py` — zero changes
- `orchestrator.py` — zero changes
- Any template — zero changes
- Any TypeScript — zero changes
- `provider.py` — zero changes
- `registry.py` — zero changes

---

## Open Questions

1. **Should "informational" (ports only, no vulns, no bad tags) map to `"no_data"` or a new `"informational"` verdict?**
   - What we know: The four existing verdicts are `malicious`, `suspicious`, `clean`, `no_data`. The design doc says "else informational" without specifying which verdict string.
   - What's unclear: The Phase 4 Results UX may introduce a dedicated "informational" display treatment.
   - Recommendation: Map to `"no_data"` for now. "Clean" implies a reputation verdict (this IP is safe) which Shodan cannot assert. "No_data" means "this provider has no finding to report" which is accurate — having open ports is observation, not verdict. Phase 4 can re-examine if needed.

2. **Should `detection_count` reflect the number of CVEs or always be 0/1?**
   - What we know: `EnrichmentResult.detection_count` is used by the frontend progress bar and potentially by Phase 4 summary display. Other adapters use `1` for "found" and `0` for "not found".
   - Recommendation: For the `"suspicious"` verdict (vulns present), set `detection_count = len(vulns)` — this is more informative than `1` and aligns with how VirusTotal uses it (detection ratio). For `"malicious"` (bad tags), use `detection_count = len(bad_tags)`. For `"no_data"`, use `0`.

3. **Is there a meaningful `scan_date` to extract?**
   - What we know: The InternetDB 200 response does not include a timestamp field. The data is updated weekly but no per-record timestamp is exposed via the API.
   - Recommendation: Set `scan_date=None`. The `raw_stats` dict can include any auxiliary data for Phase 4 display if needed.

---

## Validation Architecture

The project has `workflow.nyquist_validation` set to `false` in `.planning/config.json`. This section is skipped.

---

## Sources

### Primary (HIGH confidence)

- `https://internetdb.shodan.io/openapi.json` — Official OpenAPI spec; endpoint, response schema, status codes verified 2026-03-02
- Project codebase direct inspection:
  - `app/enrichment/adapters/malwarebazaar.py` — Reference adapter pattern
  - `app/enrichment/adapters/threatfox.py` — Reference adapter pattern
  - `app/enrichment/http_safety.py` — HTTP safety utilities
  - `app/enrichment/setup.py` — Registration point
  - `app/enrichment/provider.py` — Provider protocol
  - `app/config.py` — ALLOWED_API_HOSTS
  - `tests/test_malwarebazaar.py` — Test structure reference
  - `tests/test_provider_protocol.py` — Protocol conformance test pattern
  - `tests/test_registry_setup.py` — Setup test that needs updating
- `.planning/phases/01-provider-registry-refactor/01-01-SUMMARY.md` and `01-02-SUMMARY.md` — Phase 1 decisions

### Secondary (MEDIUM confidence)

- `https://blog.shodan.io/introducing-the-internetdb-api/` — InternetDB introduction; fields confirmed
- `https://github.com/blacklanternsecurity/bbot/issues/2412` — 404 response body `{"detail":"No information available"}` confirmed; 429 response body confirmed
- `https://pkg.go.dev/github.com/denisgubin/shodan/models/tags` — Shodan tag definitions including malware, compromised, doublepulsar tags (third-party library but Shodan-specific)

### Tertiary (LOW confidence)

- General WebSearch results on InternetDB rate limiting — "~600 requests before temp ban" from empirical reports, not official docs. Not relevant to this single-IP-at-a-time tool.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code in project already; no new dependencies
- Architecture: HIGH — adapter structure directly specified by existing patterns; all code examples verified against real adapter code
- API behavior: HIGH — OpenAPI spec fetched directly; 404 behavior confirmed by multiple independent sources
- Tag classifications: MEDIUM — verified in third-party Shodan Go library; cross-referenced with Shodan blog; no official enumerated list published by Shodan
- Pitfalls: HIGH — derived from direct reading of MBAdapter, http_safety.py, and test patterns

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable REST API; Shodan rarely changes InternetDB schema)
