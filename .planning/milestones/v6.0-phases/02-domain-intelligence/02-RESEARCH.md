# Phase 02: Domain Intelligence — Research

**Researched:** 2026-03-13
**Domain:** DNS resolution via dnspython, certificate transparency via crt.sh HTTP API, zero-auth adapter pattern extension, context row rendering
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DINT-01 | User can see live DNS records (A, MX, NS, TXT) for any domain IOC without an API key | dnspython 2.8.0 stdlib-level DNS resolution; no API key, no SSRF allowlist; four record types queryable via `dns.resolver.resolve(domain, rdtype)` |
| DINT-02 | User can see certificate transparency history for any domain IOC without an API key | crt.sh `https://crt.sh/?q=<domain>&output=json` — free, no-auth HTTP API; returns cert count, date range, SANs for subdomain enumeration |
</phase_requirements>

---

## Summary

Phase 02 adds two zero-auth domain intelligence features: live DNS record lookups (A, MX, NS, TXT) and certificate transparency history from crt.sh. Both are purely contextual enrichments — like IP Context in Phase 01, they carry no threat verdict. They follow the same adapter + context-row rendering pattern established in Phase 01.

**DNS lookups** use the `dnspython` library (`dns.resolver.resolve()`). This is NOT an HTTP call — it goes directly to DNS servers using UDP/TCP on port 53. Consequently, `http_safety.py` controls (SSRF allowlist, timeout tuple, size cap) do NOT apply. dnspython has its own exception hierarchy and `lifetime` parameter for timeout control. The `dns.resolver.Resolver` is safe to call from multiple threads concurrently.

**Certificate transparency** uses the `crt.sh` public API at `https://crt.sh/?q=<domain>&output=json`. This IS an HTTP call and MUST use `http_safety.py` controls, and `crt.sh` must be added to `ALLOWED_API_HOSTS`. The API is unofficial, slow, and occasionally returns HTTP 502s. It returns a JSON array of certificate objects from which the planner extracts cert count, date range, and unique subdomains from `name_value` SANs.

Both adapters use `verdict="no_data"` — they are contextual intelligence providers, not threat scorers. Both should follow the `createContextRow()` rendering path established for IP Context, with a new "Domain Context" row for DNS data and a new "Cert History" row for crt.sh data.

**Primary recommendation:** Two separate adapters (`DnsAdapter`, `CrtShAdapter`), each its own file, registered in `setup.py`, rendered via the existing `createContextRow()` pattern extended with new provider names in `PROVIDER_CONTEXT_FIELDS`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dnspython | 2.8.0 | DNS resolution (A, MX, NS, TXT) | Industry standard Python DNS library; supports Python 3.10+; thread-safe for concurrent `resolve()` calls; raises typed exceptions |
| requests | 2.32.5 (already installed) | HTTP call to crt.sh API | Already in requirements.txt; consistent with all other HTTP adapters |

### Installation

```bash
pip install dnspython==2.8.0
```

Add to `requirements.txt`:
```
dnspython==2.8.0
```

crt.sh requires no new library — uses `requests` already in the project.

---

## Architecture Patterns

### Two Separate Adapters

Phase 02 produces two adapter files:

```
app/enrichment/adapters/
├── dns_lookup.py      # DnsAdapter — dnspython, IOCType.DOMAIN, no HTTP safety controls
└── crtsh.py           # CrtShAdapter — requests + http_safety, IOCType.DOMAIN, crt.sh API
```

Each is registered separately in `setup.py`. Both output `verdict="no_data"` with contextual data in `raw_stats`.

### Pattern 1: DnsAdapter — Direct DNS Resolution (No HTTP)

**What:** Uses `dns.resolver.resolve(domain, rdtype)` for four record types. Returns all record values as lists in `raw_stats`.

**Key difference from all other adapters:** DNS goes directly to port 53, not through an HTTP API. Therefore:
- Do NOT call `validate_endpoint()` — no URL to validate
- Do NOT use `http_safety.TIMEOUT` tuple — not applicable to DNS
- Do NOT require an entry in `ALLOWED_API_HOSTS` — no HTTP host to allowlist
- DO use `dns.resolver.Resolver(configure=True)` with `lifetime=5.0` per record type query

**Thread safety:** `dns.resolver.Resolver.resolve()` is safe for concurrent calls per official documentation. A single Resolver instance can be shared or a new one created per `lookup()` call.

**Recommended approach:** Create a new `Resolver` instance per `lookup()` call (stateless, matches existing adapter pattern).

**Record types and extraction:**

```python
# Source: dnspython 2.8.0 docs + verified community examples
import dns.resolver
import dns.exception

resolver = dns.resolver.Resolver(configure=True)
resolver.lifetime = 5.0  # total seconds for all nameserver attempts per query

# A records
for rdata in resolver.resolve(domain, 'A'):
    a_records.append(rdata.to_text())

# MX records — access .exchange (Name) and .preference (int)
for rdata in resolver.resolve(domain, 'MX'):
    mx_records.append(f"{rdata.preference} {rdata.exchange.to_text()}")

# NS records
for rdata in resolver.resolve(domain, 'NS'):
    ns_records.append(rdata.to_text())

# TXT records — each rdata has multiple strings; join them
for rdata in resolver.resolve(domain, 'TXT'):
    txt_records.append(b''.join(rdata.strings).decode('utf-8', errors='replace'))
```

**Exception handling per record type:**

```python
# Source: dnspython 2.8.0 exception docs
try:
    answers = resolver.resolve(domain, rdtype)
except dns.resolver.NXDOMAIN:
    pass  # domain does not exist — not an error
except dns.resolver.NoAnswer:
    pass  # domain exists but has no records of this type — normal, not an error
except dns.resolver.NoNameservers:
    pass  # all nameservers failed — treat as no_data or error
except dns.exception.Timeout:
    pass  # lifetime exceeded
except Exception:
    pass  # catch-all
```

**NXDOMAIN and NoAnswer are expected for many domains and MUST be treated as `no_data`, not as errors.**

**raw_stats structure for DnsAdapter:**

```python
raw_stats = {
    "a": ["1.2.3.4", "5.6.7.8"],          # list[str], empty if none
    "mx": ["10 mail.example.com."],         # list[str], "pref host" format
    "ns": ["ns1.example.com."],             # list[str]
    "txt": ["v=spf1 include:...", "..."],   # list[str], full TXT value
    "lookup_errors": ["NS: timeout"],       # list[str] for per-type failures
}
```

**Provider name:** `"DNS Records"` — matches IP Context naming pattern (short, descriptive, no URL).

### Pattern 2: CrtShAdapter — HTTP API with Safety Controls

**What:** GET `https://crt.sh/?q=<domain>&output=json`, parse JSON array, extract cert count, earliest/latest issue dates, and unique subdomains from `name_value` SANs.

**MUST use full http_safety controls:**

```python
# Source: IPApiAdapter / HashlookupAdapter pattern (same project)
from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint

url = f"https://crt.sh/?q={domain}&output=json"
validate_endpoint(url, self._allowed_hosts)  # SEC-16 SSRF check
resp = requests.get(
    url,
    timeout=TIMEOUT,           # SEC-04: (5, 30)
    allow_redirects=False,     # SEC-06
    stream=True,               # SEC-05 setup
)
resp.raise_for_status()
body = read_limited(resp)      # SEC-05: 1 MB byte cap
```

**`crt.sh` MUST be added to `ALLOWED_API_HOSTS` in `app/config.py`.**

**crt.sh API response structure (verified via live query):**

```json
[
  {
    "id": 12345678,
    "issuer_ca_id": 123,
    "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
    "common_name": "example.com",
    "name_value": "example.com\n*.example.com\nwww.example.com",
    "not_before": "2024-01-01T00:00:00",
    "not_after": "2024-04-01T00:00:00",
    "entry_timestamp": "2024-01-01T01:23:45"
  }
]
```

**Key fields:**
- `name_value`: newline-separated list of SANs — split on `\n`, strip `*.` prefix, deduplicate to get subdomain set
- `not_before`: ISO 8601 issue date (can be null for some entries)
- `not_after`: ISO 8601 expiry date (can be null for some entries)
- Array length = certificate count

**raw_stats structure for CrtShAdapter:**

```python
raw_stats = {
    "cert_count": 47,                       # int: len(parsed array)
    "earliest": "2019-03-15",              # str: earliest not_before date (YYYY-MM-DD)
    "latest": "2024-12-01",                # str: most recent not_before date
    "subdomains": ["www", "mail", "api"],  # list[str]: deduplicated SANs, stripped of *. prefix
}
```

**Edge cases for crt.sh:**
- HTTP 502: crt.sh frequently returns gateway errors under load — catch as `EnrichmentError`
- Empty array `[]`: Domain has no CT log entries — return `no_data` with empty raw_stats
- `name_value` null/missing: Skip that certificate record
- Very large domains: May return thousands of certificates — limit subdomain list to first 50 unique values to prevent data explosion
- Rate limit: 5 req/min per IP — with per-enrichment-run scope, this is not a problem for typical usage (one lookup per domain per enrichment job)
- `not_before` can be null in some records — skip those when computing date range

**Provider name:** `"Cert History"` — short, clear.

### Pattern 3: Context Row Rendering (Frontend)

Phase 01 established the `createContextRow()` pattern for "IP Context". The same pattern extends naturally to domain context providers. Two new entries in `PROVIDER_CONTEXT_FIELDS` in `enrichment.ts`, plus new `if (result.provider === "DNS Records" || result.provider === "Cert History")` branches in `renderEnrichmentResult()` to route through `createContextRow()`.

**New `PROVIDER_CONTEXT_FIELDS` entries:**

```typescript
// Source: enrichment.ts PROVIDER_CONTEXT_FIELDS pattern (same project)
"DNS Records": [
  { key: "a",   label: "A",   type: "tags" },
  { key: "mx",  label: "MX",  type: "tags" },
  { key: "ns",  label: "NS",  type: "tags" },
  { key: "txt", label: "TXT", type: "tags" },
],
"Cert History": [
  { key: "cert_count", label: "Certs",      type: "text" },
  { key: "earliest",   label: "First seen", type: "text" },
  { key: "latest",     label: "Latest",     type: "text" },
  { key: "subdomains", label: "Subdomains", type: "tags" },
],
```

**Sort pinning:** Both new providers use `data-verdict="context"` on their rows, which causes `sortDetailRows()` to pin them to the top of the details container (same as IP Context).

**`createContextRow()` generalization:** Currently hardcodes `"IP Context"` as the provider name text. For Phase 02, this function should be generalized to use `result.provider` instead. This is a one-line change that enables reuse for all context providers.

### Anti-Patterns to Avoid

- **Do NOT call `validate_endpoint()` for DNS lookups** — there is no URL to validate; DNS goes to port 53 via OS resolver, not to a named HTTP host.
- **Do NOT use `http_safety.TIMEOUT` for DNS** — the tuple `(5, 30)` is a requests.get parameter; use `resolver.lifetime = 5.0` instead.
- **Do NOT add DNS servers to `ALLOWED_API_HOSTS`** — this allowlist is for HTTP API hostnames only. DNS is a different protocol entirely.
- **Do NOT treat `NXDOMAIN` or `NoAnswer` as errors** — these are expected responses for many legitimate domains. Return `no_data`, not `EnrichmentError`.
- **Do NOT use `dns.resolver.query()`** — deprecated alias for `resolve()`, kept only for backwards compatibility.
- **Do NOT skip `validate_endpoint()` for crt.sh** — it is an HTTP API and MUST have SSRF protection.
- **Do NOT merge DNS and CT into one adapter** — they are architecturally different (one is non-HTTP, one is HTTP). Keep them separate.
- **Do NOT render TXT record values as verdicts** — the `txt` list contains raw SPF/DMARC/other strings, rendered as tags like ports/vulns.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DNS resolution | Custom UDP socket queries | `dns.resolver.resolve()` (dnspython) | NXDOMAIN, NoAnswer, SERVFAIL, retries, nameserver fallback, CNAME chasing, TTL, thread safety — all handled |
| MX record preference sorting | Manual string parsing | dnspython `rdata.preference` attribute | MX records have typed structure; dnspython exposes `.preference` (int) and `.exchange` (Name) directly |
| TXT record multi-string handling | Manual byte concatenation | `b''.join(rdata.strings)` | TXT records can have multiple string segments per rdata object (RFC 4408); dnspython handles this |
| Certificate parsing from CT logs | Manual X.509 parsing | crt.sh API | crt.sh already aggregates all CT logs, parses certs, exposes SANs — no local cert parsing needed |

**Key insight:** DNS has significant complexity in record type semantics (MX preferences, TXT multi-strings, CNAME chasing, SOA TTLs). dnspython abstracts all of it. The `to_text()` method on any rdata produces a canonical string representation safe to store and display.

---

## Common Pitfalls

### Pitfall 1: DNS Timeout Confusion

**What goes wrong:** Using `TIMEOUT = (5, 30)` from `http_safety.py` for DNS queries, causing a TypeError since `Resolver.lifetime` expects a float, not a tuple.

**Why it happens:** The existing HTTP adapters use requests' `timeout=(connect, read)` tuple; a developer might assume the same pattern.

**How to avoid:** Set `resolver.lifetime = 5.0` — a single float in seconds for the total query lifetime across all nameserver attempts.

**Warning signs:** `TypeError: float() argument must be a string or a number, not 'tuple'`

### Pitfall 2: TXT Record Binary Strings

**What goes wrong:** Calling `str(rdata)` or `rdata.to_text()` on TXT records returns quoted strings with escape sequences (e.g., `"v=spf1 include:..."` with surrounding double-quotes from DNS wire format).

**Why it happens:** `to_text()` produces DNS zone file format, which wraps TXT data in double quotes.

**How to avoid:** Use `b''.join(rdata.strings).decode('utf-8', errors='replace')` to get the raw value without DNS quoting. Alternatively, `rdata.to_text().strip('"')` removes outer quotes for simple cases (but fails for multi-string records).

**Warning signs:** Values displayed in the UI with leading/trailing `"` quotes.

### Pitfall 3: crt.sh Response Size

**What goes wrong:** For high-traffic domains (e.g., `google.com`), crt.sh may return thousands of certificate records, causing the 1 MB `read_limited()` cap to be hit, returning `EnrichmentError`.

**Why it happens:** The 1 MB cap in `http_safety.py` is a security control, not a soft limit.

**How to avoid:** This is acceptable behavior — the error message will be shown in the UI. No workaround needed; analysts querying `google.com` domains are edge cases. Document this as a known limitation.

**Warning signs:** `EnrichmentError` with "Response exceeded size limit" for very large domains.

### Pitfall 4: crt.sh HTTP 502 / Slow Response

**What goes wrong:** crt.sh frequently returns HTTP 502 or takes >30 seconds to respond under load.

**Why it happens:** crt.sh is a community-run service that gets overloaded, especially at the top of each hour.

**How to avoid:** The existing `TIMEOUT = (5, 30)` — 5s connect, 30s read — is reasonable. HTTP 502 triggers `raise_for_status()` which leads to `EnrichmentError("HTTP 502")`. This is the correct behavior — show the error in the UI without blocking the enrichment job.

**Warning signs:** Tests that make real HTTP calls will be flaky. All tests MUST mock `requests.get`.

### Pitfall 5: NXDOMAIN Treated as Error

**What goes wrong:** `dns.resolver.NXDOMAIN` exception propagates to the adapter's outer except clause, returning `EnrichmentError` for domains that simply don't exist (e.g., sinkholed domains).

**Why it happens:** Forgetting that NXDOMAIN is an expected, informative DNS response.

**How to avoid:** Catch `dns.resolver.NXDOMAIN` and return `EnrichmentResult(verdict="no_data", raw_stats={})` — same pattern as HashlookupAdapter's 404 handling.

**Warning signs:** Domain IOCs that show "DNS Records: error — NXDOMAIN" in the UI.

### Pitfall 6: createContextRow() Hardcoded Provider Name

**What goes wrong:** `createContextRow()` currently sets `nameSpan.textContent = "IP Context"` — hardcoded. Using it for DNS Records or Cert History rows shows wrong label.

**Why it happens:** The function was written for a single use case (IP Context).

**How to avoid:** Change `nameSpan.textContent = "IP Context"` to `nameSpan.textContent = result.provider` — a one-line fix that generalizes the function for all context providers.

**Warning signs:** Domain context rows showing "IP Context" as provider label.

---

## Code Examples

### DnsAdapter lookup() skeleton

```python
# Pattern: HashlookupAdapter / IPApiAdapter — same project, zero-auth, no HTTP
import dns.resolver
import dns.exception
import logging
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

class DnsAdapter:
    name = "DNS Records"
    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # allowed_hosts accepted for API compatibility but unused (DNS is not HTTP)
        pass

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = 5.0   # seconds total per record type query

        raw_stats: dict = {"a": [], "mx": [], "ns": [], "txt": [], "lookup_errors": []}

        for rdtype, key in [("A", "a"), ("MX", "mx"), ("NS", "ns"), ("TXT", "txt")]:
            try:
                answers = resolver.resolve(ioc.value, rdtype)
                if rdtype == "MX":
                    raw_stats[key] = [
                        f"{r.preference} {r.exchange.to_text()}" for r in answers
                    ]
                elif rdtype == "TXT":
                    raw_stats[key] = [
                        b"".join(r.strings).decode("utf-8", errors="replace")
                        for r in answers
                    ]
                else:
                    raw_stats[key] = [r.to_text() for r in answers]
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass  # expected — domain exists but lacks this record type
            except dns.resolver.NoNameservers:
                raw_stats["lookup_errors"].append(f"{rdtype}: no nameservers")
            except dns.exception.Timeout:
                raw_stats["lookup_errors"].append(f"{rdtype}: timeout")
            except Exception:
                logger.exception("Unexpected DNS error for %s %s", rdtype, ioc.value)
                raw_stats["lookup_errors"].append(f"{rdtype}: error")

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats=raw_stats,
        )
```

### CrtShAdapter _parse_response() skeleton

```python
# Source: crt.sh API (verified via live JSON query 2026-03-13)
def _parse_response(ioc: IOC, body: list, provider_name: str) -> EnrichmentResult:
    if not body:
        return EnrichmentResult(
            ioc=ioc, provider=provider_name, verdict="no_data",
            detection_count=0, total_engines=0, scan_date=None, raw_stats={}
        )

    cert_count = len(body)

    # Collect dates (not_before field, skip nulls)
    dates = [
        entry["not_before"][:10]  # YYYY-MM-DD prefix of ISO 8601
        for entry in body
        if entry.get("not_before")
    ]
    earliest = min(dates) if dates else ""
    latest = max(dates) if dates else ""

    # Collect unique subdomains from name_value SANs
    subdomain_set: set[str] = set()
    for entry in body:
        name_value = entry.get("name_value") or ""
        for name in name_value.split("\n"):
            name = name.strip().lstrip("*.").lower()
            if name:
                subdomain_set.add(name)

    # Limit to 50 to prevent data explosion on high-traffic domains
    subdomains = sorted(subdomain_set)[:50]

    return EnrichmentResult(
        ioc=ioc, provider=provider_name, verdict="no_data",
        detection_count=0, total_engines=0, scan_date=None,
        raw_stats={
            "cert_count": cert_count,
            "earliest": earliest,
            "latest": latest,
            "subdomains": subdomains,
        }
    )
```

### createContextRow() generalization (TypeScript)

```typescript
// Change ONE line in enrichment.ts (line 364):
// BEFORE: nameSpan.textContent = "IP Context";
// AFTER:
nameSpan.textContent = result.provider;  // works for "IP Context", "DNS Records", "Cert History"
```

### renderEnrichmentResult() routing (TypeScript)

```typescript
// In renderEnrichmentResult(), extend the context provider check:
// BEFORE: if (result.provider === "IP Context") {
// AFTER:
const CONTEXT_PROVIDERS = new Set(["IP Context", "DNS Records", "Cert History"]);
if (CONTEXT_PROVIDERS.has(result.provider)) {
    // ... existing createContextRow() path, unchanged
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `dns.resolver.query()` | `dns.resolver.resolve()` | dnspython 2.0 | `query()` is a deprecated alias; `resolve()` is canonical |
| Manual UDP socket DNS | dnspython | n/a | Handle retries, CNAME, nameserver fallback automatically |
| Custom CT log parsers | crt.sh API | n/a | crt.sh aggregates all major CT logs; no local parsing needed |

**Deprecated/outdated:**
- `dns.resolver.query()`: Deprecated since dnspython 2.0. Use `resolve()`.
- `dns.resolver.Resolver.nameservers` mutation across threads: Not thread-safe (configuration is not locked). Don't mutate shared Resolver state.

---

## Open Questions

1. **DnsAdapter `allowed_hosts` parameter**
   - What we know: All existing adapters accept `allowed_hosts` for the Provider protocol; DNS adapter doesn't use it
   - What's unclear: Should we accept but ignore the parameter, or change the protocol?
   - Recommendation: Accept and ignore (with a docstring note) — preserves uniform constructor signature across all adapters and simplifies `setup.py` registration

2. **crt.sh subdomain limit (50)**
   - What we know: Large domains can have thousands of CT-logged subdomains
   - What's unclear: What's the right cap for analyst usability?
   - Recommendation: Start at 50 unique values; this covers most domains' interesting subdomains without overwhelming the UI

3. **DNS lookup failures — partial vs total**
   - What we know: If A record lookup succeeds but MX times out, we have partial data
   - What's unclear: Should partial results be shown or suppressed?
   - Recommendation: Always return `EnrichmentResult` with whatever records succeeded; populate `lookup_errors` list for failed record types; analyst sees partial data with error notes

4. **TXT record SPF/DMARC filtering**
   - What we know: TXT records can include arbitrary data (ownership verification, DKIM, etc.)
   - What's unclear: Should we filter to SPF/DMARC only or return all TXT?
   - Recommendation: Return all TXT records — analysts may find non-SPF/DMARC values informative

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no config file) |
| Config file | none — see existing conftest.py |
| Quick run command | `python -m pytest tests/test_dns_lookup.py tests/test_crtsh.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DINT-01 | DnsAdapter returns A/MX/NS/TXT in raw_stats | unit | `python -m pytest tests/test_dns_lookup.py -x -q` | ❌ Wave 0 |
| DINT-01 | DnsAdapter.supported_types == {IOCType.DOMAIN} | unit | `python -m pytest tests/test_dns_lookup.py -x -q` | ❌ Wave 0 |
| DINT-01 | NXDOMAIN returns no_data (not EnrichmentError) | unit | `python -m pytest tests/test_dns_lookup.py::TestEdgeCases -x -q` | ❌ Wave 0 |
| DINT-01 | NoAnswer returns no_data (not EnrichmentError) | unit | `python -m pytest tests/test_dns_lookup.py::TestEdgeCases -x -q` | ❌ Wave 0 |
| DINT-01 | DnsAdapter satisfies Provider protocol | unit | `python -m pytest tests/test_dns_lookup.py::TestProtocolConformance -x -q` | ❌ Wave 0 |
| DINT-02 | CrtShAdapter returns cert_count, earliest, latest, subdomains | unit | `python -m pytest tests/test_crtsh.py -x -q` | ❌ Wave 0 |
| DINT-02 | Empty crt.sh array returns no_data with empty raw_stats | unit | `python -m pytest tests/test_crtsh.py::TestEmptyResponse -x -q` | ❌ Wave 0 |
| DINT-02 | CrtShAdapter uses all SEC controls (timeout, stream, no_redirects, SSRF) | unit | `python -m pytest tests/test_crtsh.py::TestHTTPSafetyControls -x -q` | ❌ Wave 0 |
| DINT-02 | HTTP 502 returns EnrichmentError | unit | `python -m pytest tests/test_crtsh.py::TestErrorHandling -x -q` | ❌ Wave 0 |
| DINT-02 | CrtShAdapter satisfies Provider protocol | unit | `python -m pytest tests/test_crtsh.py::TestProtocolConformance -x -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_dns_lookup.py tests/test_crtsh.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_dns_lookup.py` — covers DINT-01 (DnsAdapter unit tests, all mocked via `unittest.mock.patch("dns.resolver.Resolver")`)
- [ ] `tests/test_crtsh.py` — covers DINT-02 (CrtShAdapter unit tests, all mocked via `unittest.mock.patch("requests.get")`)

*(Existing test infrastructure — pytest, conftest.py, mock patterns — already covers the scaffolding needs. Only the two new test files need to be created.)*

---

## Sources

### Primary (HIGH confidence)
- dnspython 2.8.0 official docs (`https://dnspython.readthedocs.io/en/stable/`) — resolver API, exceptions, thread safety, TXT record strings
- dnspython 2.8.0 official docs (`https://dnspython.readthedocs.io/en/latest/threads.html`) — thread safety guarantees
- crt.sh live API query (`https://crt.sh/?q=example.com&output=json`) — verified JSON structure and `name_value` format
- Existing project code (`app/enrichment/adapters/ip_api.py`, `hashlookup.py`) — adapter pattern template
- Existing project code (`app/static/src/ts/modules/enrichment.ts`) — `createContextRow()`, `PROVIDER_CONTEXT_FIELDS`, rendering paths

### Secondary (MEDIUM confidence)
- GitHub rthalley/dnspython README — version 2.8.0 confirmed; Python 3.10+ support confirmed; `pip install dnspython`
- crt.sh Google Groups (`https://groups.google.com/g/crtsh/c/NZJntKrBdmg`) — rate limit of 5 req/min per IP; frequent 502s under load

### Tertiary (LOW confidence — noted)
- WebSearch community examples for TXT/MX extraction — LOW; cross-verified against dnspython docs for `rdata.strings` and `rdata.preference`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — dnspython version from official GitHub; requests already in project
- Architecture: HIGH — two-adapter split, no-HTTP DNS path, HTTP crt.sh path, verified against existing codebase patterns
- Pitfalls: HIGH — DNS exception semantics from official docs; crt.sh reliability from operator communications; TXT multi-string from RFC + dnspython source

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable ecosystem — dnspython and crt.sh API format change infrequently)
