# Phase 03: Passive DNS Pivoting - Research

**Researched:** 2026-03-13
**Domain:** ThreatMiner API integration — passive DNS, related samples, multi-IOC-type zero-auth adapter
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DINT-03 | User can see passive DNS history and related IOCs via ThreatMiner for all IOC types without an API key | ThreatMiner API is free, zero-auth, and supports IP (rt=2 passive DNS), domain (rt=2 passive DNS), and hash (rt=4 related samples) with a 10 req/min rate limit that maps naturally to EnrichmentError("HTTP 429") — same pattern as ip-api.com |

</phase_requirements>

---

## Summary

ThreatMiner (api.threatminer.org) is a free, zero-authentication REST API that provides passive DNS history for IPs and domains, and related malware sample hashes for any IOC type. The API is structurally a perfect fit for SentinelX's existing adapter pattern: one `ThreatMinerAdapter` class with `supported_types = {IPV4, IPV6, DOMAIN, MD5, SHA1, SHA256}` and a routing table that dispatches to the correct endpoint and `rt` parameter per IOC type.

The single hard constraint is a 10 requests/minute rate limit enforced with HTTP 429. Per the success criteria, this must be transparent to the analyst (slow, not an error banner). The correct behavior is to propagate `EnrichmentError("HTTP 429")` and let the frontend's normal "1 provider still loading…" indicator handle it without showing a warning banner — the existing `showEnrichWarning` logic only activates if the error string contains "rate limit" or "429", so the UI already handles this correctly.

The adapter requires two or three API calls per IOC (one per data type, e.g., passive DNS + related samples for domains). This is correct and expected: ThreatMiner separates data types by `rt` parameter. A single adapter can serialize these as two distinct `EnrichmentResult` objects, or make both calls and merge them into one result. The simpler, more predictable approach is a single merged result per IOC — one call per supported query type, merged into one `raw_stats` dict.

**Primary recommendation:** Implement `ThreatMinerAdapter` as a single-result-per-IOC adapter that makes one or two sequential API calls (passive DNS + related samples where applicable), merges results into a single `raw_stats`, and propagates HTTP 429 as `EnrichmentError` without triggering the warning banner.

---

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | >=2.31 | HTTP calls to ThreatMiner | Already used by all adapters |
| app.enrichment.http_safety | project | SSRF validation, timeout, size cap | Mandatory for all adapters (SEC-04/05/06/16) |
| app.enrichment.models | project | EnrichmentResult, EnrichmentError | All adapters use this |
| app.pipeline.models | project | IOC, IOCType | All adapters use this |

No new dependencies needed. ThreatMiner is a plain REST API returning JSON over HTTPS.

**Installation:** None required — all dependencies present.

---

## Architecture Patterns

### Recommended Project Structure

```
app/enrichment/adapters/
└── threatminer.py       # New: ThreatMinerAdapter
tests/
└── test_threatminer.py  # New: unit tests, all mocked
app/enrichment/setup.py  # Edit: register ThreatMinerAdapter
app/config.py            # Edit: add "api.threatminer.org" to ALLOWED_API_HOSTS
app/static/src/ts/modules/enrichment.ts  # Edit: PROVIDER_CONTEXT_FIELDS + CONTEXT_PROVIDERS
```

### Pattern 1: Multi-Type Routing in a Single Adapter

**What:** One adapter class, multiple API endpoints, dispatch by IOC type.
**When to use:** When a single provider has different API paths per IOC type but the same HTTP safety, verdict semantics, and result structure.

The ThreatMiner adapter routes each IOC type to a different base URL and `rt` parameter:

```python
# Source: adapted from CrtShAdapter and IPApiAdapter patterns in this codebase
_ENDPOINT_MAP = {
    IOCType.IPV4:   ("https://api.threatminer.org/v2/host.php", "2"),    # passive DNS
    IOCType.IPV6:   ("https://api.threatminer.org/v2/host.php", "2"),    # passive DNS
    IOCType.DOMAIN: ("https://api.threatminer.org/v2/domain.php", "2"),  # passive DNS
    IOCType.MD5:    ("https://api.threatminer.org/v2/sample.php", "4"),  # related samples
    IOCType.SHA1:   ("https://api.threatminer.org/v2/sample.php", "4"),  # related samples
    IOCType.SHA256: ("https://api.threatminer.org/v2/sample.php", "4"),  # related samples
}
```

For domain IOCs, two calls are made: passive DNS (rt=2) returns IP addresses the domain resolved to; related samples (rt=4) returns associated malware hashes. Both are merged into one `raw_stats` dict.

### Pattern 2: ThreatMiner API Response Structure

**What:** ThreatMiner always returns `{status_code, status_message, results}`.
**Key behaviors:**

| Response | Meaning | Handling |
|----------|---------|---------|
| `status_code: "200"` | Results found | Parse `results` array |
| `status_code: "404"` | No results | verdict=no_data, raw_stats={} — NOT an error |
| HTTP 429 | Rate limited (>10/min) | EnrichmentError("HTTP 429") |
| HTTP 403 | Blocked/IP ban | EnrichmentError("HTTP 403") |
| Timeout | Network slow | EnrichmentError("Timeout") |

**CRITICAL:** ThreatMiner returns HTTP 200 for both "found" and "not found" responses — the `status_code` field inside the JSON body is the authoritative indicator. This mirrors ip-api.com's pattern where HTTP 200 + body status "fail" = no_data.

```python
# Correct handling (NOT using resp.raise_for_status() as the primary gate)
body = read_limited(resp)
if body.get("status_code") == "404" or not body.get("results"):
    return EnrichmentResult(ioc=ioc, provider=self.name, verdict="no_data", ...)
```

### Pattern 3: Response Shapes Per IOC Type

**IP/Domain passive DNS (rt=2):**
```json
{
  "status_code": "200",
  "status_message": "Results found.",
  "results": [
    {
      "ip": "209.29.221.235",
      "first_seen": "2013-09-19 00:00:00",
      "last_seen": "2016-02-01 09:41:15"
    }
  ]
}
```
For domain (rt=2), each result has `ip` + `first_seen` + `last_seen`.
For IP (rt=2), each result has `domain` + `first_seen` + `last_seen` (reverse: what domains resolved to this IP).

**Hash related samples (rt=4) for domain or hash IOCs:**
```json
{
  "status_code": "200",
  "status_message": "Results found.",
  "results": [
    "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1",
    "abf736e1a8e0508b6dd840b012d4231cf13f8b48c2dcb3ed18ce92a59dba7109"
  ]
}
```
Results are a plain list of SHA-256 hash strings.

**Hash sample metadata (rt=1) — NOT used in this phase:**
Returns detailed metadata. Out of scope — the success criteria only needs related sample hashes, which is rt=4.

### Pattern 4: Rate-Limiting Behavior (10 req/min)

**What:** ThreatMiner enforces exactly 10 requests per minute. Exceeding returns HTTP 429.
**How to handle it:** Return `EnrichmentError(ioc=ioc, provider=self.name, error="HTTP 429")`.
**Frontend behavior:** The existing `showEnrichWarning` logic activates for "rate limit" or "429" substrings in error messages. This will show the warning banner. That is the correct behavior — it is transparent (the analyst sees a warning rather than a silent failure).

**Important design note:** For domain IOCs that make TWO API calls (passive DNS + related samples), if the first call hits rate limit, skip the second call and return the error immediately. No retry logic — propagate the error.

### Anti-Patterns to Avoid

- **Making 3+ calls per IOC**: ThreatMiner has many `rt` values; only rt=2 (passive DNS) and rt=4 (related samples for domains) are in scope for DINT-03.
- **Using 404 HTTP status as an error**: ThreatMiner body `status_code: "404"` means "not found" — it is a no_data result, not a failure.
- **Retry on 429**: Do not retry. Propagate as EnrichmentError and let the analyst be aware.
- **Storing state for rate limiting**: No rate limiter state needed — just handle 429 when it arrives.
- **Multiple result objects per IOC**: One IOC should produce one `EnrichmentResult` with merged data (passive DNS hosts + related samples), not separate result objects for each call.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP safety | Custom timeout/redirect logic | `http_safety.TIMEOUT`, `read_limited()`, `validate_endpoint()` | Already tested, SEC-04/05/06/16 compliant |
| SSRF prevention | Host checking logic | `validate_endpoint(url, self._allowed_hosts)` | Centralized, audited |
| Result models | Custom dataclass | `EnrichmentResult` / `EnrichmentError` | Type-safe, immutable, serializable |
| Frontend field rendering | Custom HTML builder | `PROVIDER_CONTEXT_FIELDS` + `createContextFields()` | Already handles text/tags field types |
| Rate limit retry | Exponential backoff library | Nothing — propagate as EnrichmentError | This is zero-auth; no quota management |

---

## Common Pitfalls

### Pitfall 1: ThreatMiner 200 vs 404 in JSON Body
**What goes wrong:** Developer calls `resp.raise_for_status()` as the primary gate, then parses — but ThreatMiner always returns HTTP 200, even for "not found". The body's `status_code` field is `"404"` (string, not int) when no data exists.
**Why it happens:** Standard HTTP error handling pattern doesn't apply here.
**How to avoid:** Check `body.get("status_code") == "404"` OR `not body.get("results")` before treating as valid data.
**Warning signs:** Tests pass for found IOCs but "not found" returns an empty result or fails to parse.

### Pitfall 2: IP vs Domain Passive DNS Field Names
**What goes wrong:** The `results` array fields differ based on the query direction.
- Domain query (rt=2): Each result has `ip`, `first_seen`, `last_seen` (IPs this domain resolved to).
- IP query (rt=2): Each result has `domain`, `first_seen`, `last_seen` (domains that pointed to this IP).
**Why it happens:** Passive DNS is inherently bidirectional; ThreatMiner uses different field names for each direction.
**How to avoid:** Use the key `ip` for domain-type lookups and `domain` for IP-type lookups. The `_parse_response` function must accept the IOC type to know which field to extract.
**Warning signs:** All passive DNS results show empty lists even for IOCs with known history.

### Pitfall 3: SSRF Allowlist Not Updated
**What goes wrong:** Adapter is implemented but `api.threatminer.org` is not in `Config.ALLOWED_API_HOSTS`, causing every lookup to return `EnrichmentError("... not in allowed_hosts (SSRF allowlist SEC-16)")`.
**Why it happens:** Config update is in a different file than adapter creation, easy to miss.
**How to avoid:** Always update `app/config.py` ALLOWED_API_HOSTS when adding a new adapter with a new hostname.

### Pitfall 4: Rate Limit Warning Banner Noise
**What goes wrong:** With multiple IOCs and ThreatMiner being the slowest provider, rate limit errors show warning banners that alarm analysts.
**Why it happens:** The `showEnrichWarning` in enrichment.ts triggers on "429" in error messages.
**How to avoid:** This is actually correct behavior per the success criteria: "rate limiting is transparent (slow result, not error)". The warning banner IS the transparency mechanism. Accept this behavior.

### Pitfall 5: Results Cap Missing
**What goes wrong:** ThreatMiner may return hundreds of passive DNS records for well-known IPs/domains. Rendering all of them as frontend tags would be noisy and slow.
**Why it happens:** No cap applied in the parse function.
**How to avoid:** Apply a cap (20-25 records) to the `hosts` and `samples` lists in `raw_stats`, similar to how CrtShAdapter caps subdomains at 50. Document the cap in the adapter docstring.

### Pitfall 6: IPv6 URL Encoding
**What goes wrong:** IPv6 addresses in URLs may need encoding (square brackets in some contexts). ThreatMiner uses `host.php` for both IPv4 and IPv6.
**Why it happens:** IPv6 format (e.g., `2001:db8::1`) requires URL-safe encoding.
**How to avoid:** Use `requests.get(url, params={"q": ioc.value, "rt": rt})` — `requests` handles URL encoding automatically. Do NOT manually f-string the IOC value into a query string for IPv6.

---

## Code Examples

Verified patterns from existing codebase:

### Adapter Skeleton (from CrtShAdapter + IPApiAdapter patterns)
```python
# Source: adapted from app/enrichment/adapters/crtsh.py and ip_api.py

THREATMINER_BASE_IP     = "https://api.threatminer.org/v2/host.php"
THREATMINER_BASE_DOMAIN = "https://api.threatminer.org/v2/domain.php"
THREATMINER_BASE_SAMPLE = "https://api.threatminer.org/v2/sample.php"

# Results cap — keep frontend manageable
_MAX_HOSTS   = 25
_MAX_SAMPLES = 20


class ThreatMinerAdapter:
    supported_types: frozenset[IOCType] = frozenset({
        IOCType.IPV4, IOCType.IPV6,
        IOCType.DOMAIN,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
    })
    name = "ThreatMiner"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")

        if ioc.type in (IOCType.IPV4, IOCType.IPV6):
            return self._lookup_ip(ioc)
        elif ioc.type == IOCType.DOMAIN:
            return self._lookup_domain(ioc)
        else:  # hash types
            return self._lookup_hash(ioc)
```

### Single API Call Helper
```python
# Source: adapted from crtsh.py lookup() pattern

def _call(
    self, ioc: IOC, base_url: str, rt: str
) -> dict | EnrichmentError:
    """Make one ThreatMiner API call. Returns parsed JSON dict or EnrichmentError."""
    url = base_url  # validate_endpoint checks hostname only
    try:
        validate_endpoint(url, self._allowed_hosts)
    except ValueError as exc:
        return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

    try:
        resp = requests.get(
            url,
            params={"q": ioc.value, "rt": rt},
            timeout=TIMEOUT,           # SEC-04
            allow_redirects=False,     # SEC-06
            stream=True,               # SEC-05 setup
        )
        resp.raise_for_status()
        return read_limited(resp)      # SEC-05: byte cap enforced
    except requests.exceptions.Timeout:
        return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
    except Exception:
        logger.exception("Unexpected error during ThreatMiner lookup for %s", ioc.value)
        return EnrichmentError(ioc=ioc, provider=self.name, error="Unexpected error")
```

### Parsing IP Passive DNS Response
```python
# Source: ThreatMiner API docs — host.php rt=2 response shape
# Results are: [{"domain": "evil.com", "first_seen": "...", "last_seen": "..."}, ...]

def _lookup_ip(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
    body_or_err = self._call(ioc, THREATMINER_BASE_IP, "2")
    if isinstance(body_or_err, EnrichmentError):
        return body_or_err
    body = body_or_err

    # status_code "404" in body = no data (NOT an HTTP error)
    if body.get("status_code") == "404" or not body.get("results"):
        return EnrichmentResult(
            ioc=ioc, provider=self.name, verdict="no_data",
            detection_count=0, total_engines=0, scan_date=None, raw_stats={}
        )

    # Extract domains (what resolved to this IP)
    domains = [
        r["domain"] for r in body["results"]
        if isinstance(r, dict) and r.get("domain")
    ][:_MAX_HOSTS]

    return EnrichmentResult(
        ioc=ioc, provider=self.name, verdict="no_data",
        detection_count=0, total_engines=0, scan_date=None,
        raw_stats={"passive_dns": domains}
    )
```

### Frontend PROVIDER_CONTEXT_FIELDS Entry
```typescript
// Source: enrichment.ts PROVIDER_CONTEXT_FIELDS pattern
"ThreatMiner": [
  { key: "passive_dns", label: "Passive DNS", type: "tags" },
  { key: "samples",     label: "Samples",     type: "tags" },
],
```

### CONTEXT_PROVIDERS Update
```typescript
// Source: enrichment.ts line 305
const CONTEXT_PROVIDERS = new Set(["IP Context", "DNS Records", "Cert History", "ThreatMiner"]);
```

### Config Update
```python
# Source: app/config.py ALLOWED_API_HOSTS pattern
ALLOWED_API_HOSTS: list[str] = [
    # ... existing entries ...
    "api.threatminer.org",  # v6.0 Phase 03-01: ThreatMiner passive DNS (zero-auth)
]
```

### Registry Update
```python
# Source: app/enrichment/setup.py build_registry() pattern
from app.enrichment.adapters.threatminer import ThreatMinerAdapter

# In build_registry():
registry.register(ThreatMinerAdapter(allowed_hosts=allowed_hosts))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ThreatMiner API v1 | ThreatMiner API v2 (`api.threatminer.org/v2/`) | Pre-2018 | v2 is current, v1 no longer documented |
| Separate adapters per IOC type | Single multi-type adapter with routing | Phase 02 CrtShAdapter pattern | Simpler — one adapter, one test file |
| Status code-based "not found" (HTTP 404) | Body-field-based "not found" (status_code="404" in JSON) | Always ThreatMiner-specific | Must check body, not HTTP status |

**Deprecated/outdated:**
- ThreatMiner `www.threatminer.org/api/v1/`: Not current; use `api.threatminer.org/v2/`.

---

## Open Questions

1. **IPv6 passive DNS coverage in ThreatMiner**
   - What we know: ThreatMiner uses `host.php` for both IPv4 and IPv6. The API docs don't distinguish.
   - What's unclear: Whether ThreatMiner actually has IPv6 passive DNS data. Coverage may be IPv4-only.
   - Recommendation: Include IPv6 in `supported_types` but expect frequent `status_code: "404"` responses for IPv6. This is correct behavior — treat as `no_data`.

2. **Domain rt=4 (related samples) field shape**
   - What we know: For hash rt=4, results are a list of SHA-256 strings. For domains, rt=4 should also return a list of SHA-256 strings (same endpoint semantics).
   - What's unclear: Whether domain rt=4 results are plain strings or dicts with hash fields.
   - Recommendation: Implement with the string-list assumption (consistent with hash rt=4). Add a defensive check `if isinstance(r, str)` when iterating results. If they are dicts, fall back to extracting a `sha256` key.

3. **ThreatMiner API availability in 2026**
   - What we know: ThreatMiner has been operational since ~2016. The API endpoints are still documented and referenced widely.
   - What's unclear: Whether the free tier has any additional restrictions introduced since 2024.
   - Recommendation: The adapter must handle HTTP 403 gracefully (some IPs get blocked temporarily). Treat HTTP 403 as `EnrichmentError("HTTP 403")` — same as any other non-429 HTTP error.

---

## Validation Architecture

nyquist_validation is enabled in .planning/config.json.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no new install needed) |
| Config file | None at project root — run via `python -m pytest` |
| Quick run command | `python -m pytest tests/test_threatminer.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DINT-03 | ThreatMiner adapter exists and satisfies Provider protocol | unit | `python -m pytest tests/test_threatminer.py::TestProviderProtocol -x` | ❌ Wave 0 |
| DINT-03 | IP IOC passive DNS (rt=2) returns passive_dns list in raw_stats | unit | `python -m pytest tests/test_threatminer.py::TestIPLookup -x` | ❌ Wave 0 |
| DINT-03 | Domain IOC passive DNS (rt=2) returns passive_dns list | unit | `python -m pytest tests/test_threatminer.py::TestDomainLookup -x` | ❌ Wave 0 |
| DINT-03 | Domain IOC related samples (rt=4) returns samples list | unit | `python -m pytest tests/test_threatminer.py::TestDomainLookup -x` | ❌ Wave 0 |
| DINT-03 | Hash IOC related samples (rt=4) returns samples list | unit | `python -m pytest tests/test_threatminer.py::TestHashLookup -x` | ❌ Wave 0 |
| DINT-03 | status_code="404" in body returns no_data (not error) | unit | `python -m pytest tests/test_threatminer.py::TestNoDataHandling -x` | ❌ Wave 0 |
| DINT-03 | HTTP 429 returns EnrichmentError("HTTP 429") | unit | `python -m pytest tests/test_threatminer.py::TestHTTPErrors -x` | ❌ Wave 0 |
| DINT-03 | All HTTP safety controls enforced (timeout, stream, no redirects, SSRF) | unit | `python -m pytest tests/test_threatminer.py::TestHTTPSafetyControls -x` | ❌ Wave 0 |
| DINT-03 | ThreatMiner registered in build_registry() | unit | `python -m pytest tests/test_registry_setup.py -x` | ✅ (needs update) |
| DINT-03 | api.threatminer.org in ALLOWED_API_HOSTS | unit | `python -m pytest tests/test_security_audit.py -x` | ✅ (needs update) |
| DINT-03 | Frontend renders passive_dns and samples context fields | manual | Visual verify in browser | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_threatminer.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_threatminer.py` — covers all DINT-03 unit tests (adapter protocol, IP/domain/hash lookups, no_data handling, HTTP errors, safety controls)
- [ ] Update `tests/test_registry_setup.py` — bump provider count from 12 to 13, add ThreatMiner assertion
- [ ] Update `tests/test_security_audit.py` — add `"api.threatminer.org"` to expected ALLOWED_API_HOSTS

*(No new framework install needed — pytest already present)*

---

## Sources

### Primary (HIGH confidence)
- `https://www.threatminer.org/api.php` — Official ThreatMiner API documentation (rate limit, endpoints, rt parameters, response shape)
- `https://github.com/asrabon/ThreatMiner` — Reference Python library showing exact response JSON shapes for passive DNS (ip/first_seen/last_seen) and related samples (plain string array)
- Existing codebase: `app/enrichment/adapters/crtsh.py`, `app/enrichment/adapters/ip_api.py` — canonical adapter patterns for this project

### Secondary (MEDIUM confidence)
- Cortex XSOAR ThreatMiner integration docs — confirms IP/domain/hash command structure
- recon-ng ThreatMiner module — confirms endpoint URLs and rt parameter usage

### Tertiary (LOW confidence)
- Domain response passive DNS field being `ip` vs `domain` (IP query) — verified from asrabon library README but ThreatMiner IP query response confirming `domain` field is not officially documented in the API page; inferred from the bidirectional nature of passive DNS and community implementations

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, proven patterns in codebase
- Architecture: HIGH — ThreatMiner API documented, response shapes verified via reference library
- Pitfalls: HIGH for 200-body-404 and field name direction; MEDIUM for IPv6 coverage and domain rt=4 field shape
- Frontend pattern: HIGH — CONTEXT_PROVIDERS/PROVIDER_CONTEXT_FIELDS pattern fully understood from enrichment.ts

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (ThreatMiner API is stable; rate limit and endpoint structure unchanged for years)
