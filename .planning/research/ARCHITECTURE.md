# Architecture Research

**Domain:** Threat intelligence enrichment platform — zero-auth sources, local enrichment, deeper analysis views, relationship graphs (SentinelX v6.0)
**Researched:** 2026-03-11
**Confidence:** HIGH for Provider Protocol integration, MEDIUM for graph visualization and local databases

---

## Context: What This Research Covers

This is a SUBSEQUENT MILESTONE research document. The full existing architecture (Provider Protocol, ProviderRegistry, EnrichmentOrchestrator, CacheStore, Flask routes, TypeScript modules) is locked in. This document covers HOW the new v6.0 capabilities integrate with that architecture — specifically:

1. Zero-auth enrichment sources (DNS, GeoIP, WHOIS/ASN, cert transparency)
2. Local vs remote enrichment distinction
3. Deeper per-IOC analysis views
4. Relationship/graph visualization
5. IOC tagging and notes

**Existing pipeline (do not change core flow):**

```
POST /analyze  →  run_pipeline(text)  →  EnrichmentOrchestrator.enrich_all()
                                              ↓
                                    ProviderRegistry.providers_for_type()
                                              ↓
                                    [adapter.lookup(ioc) × N providers]
                                              ↓
                          GET /enrichment/status/<job_id>  →  polling  →  browser renders cards
```

---

## System Overview: Current + New

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Flask Routes                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────┐    │
│  │  /analyze    │  │/enrichment/   │  │  /ioc/<value>  [NEW]  │    │
│  │  /settings   │  │status/<job>   │  │  /graph/<job>  [NEW]  │    │
│  └──────┬───────┘  └───────┬───────┘  └────────────┬──────────┘    │
├─────────┼───────────────────┼─────────────────────────┼─────────────┤
│         │      Enrichment Pipeline (existing + extended)            │
│         ↓                   ↓                         ↓             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 ProviderRegistry                              │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐     │   │
│  │  │   Remote Providers     │  │   Local Providers [NEW]│     │   │
│  │  │   (existing 8)         │  │                         │     │   │
│  │  │  VirusTotal            │  │  DNSProvider            │     │   │
│  │  │  MalwareBazaar         │  │  GeoIPProvider          │     │   │
│  │  │  ThreatFox             │  │  ASNProvider            │     │   │
│  │  │  Shodan InternetDB     │  │  CertProvider           │     │   │
│  │  │  URLhaus               │  │                         │     │   │
│  │  │  OTX AlienVault        │  └────────────────────────┘     │   │
│  │  │  GreyNoise             │                                   │   │
│  │  │  AbuseIPDB             │                                   │   │
│  │  └────────────────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        Storage Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  CacheStore  │  │  NoteStore   │  │  GeoLite2    │             │
│  │  (existing   │  │  [NEW]       │  │  .mmdb files │             │
│  │   SQLite)    │  │  SQLite      │  │  [NEW]       │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Architectural Question: Does the Provider Protocol Fit?

**Answer: Yes, with a critical extension for local providers.**

The existing `Provider` protocol has:

```python
name: str
supported_types: set[IOCType] | frozenset[IOCType]
requires_api_key: bool

def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError: ...
def is_configured(self) -> bool: ...
```

Zero-auth enrichment sources (DNS, GeoIP, ASN, cert transparency) all satisfy this protocol directly, following the same pattern as the existing `ShodanAdapter` (which is already zero-auth, always `is_configured() == True`). **No protocol changes are needed.**

However, local providers differ from remote providers in three ways that need architectural clarity:

| Dimension | Remote Providers | Local Providers (new) |
|-----------|-----------------|----------------------|
| Network calls | Yes — outbound HTTP | No — local library or mmdb file |
| SSRF allowlist | Required (SEC-16) | Not applicable |
| Rate limiting | Yes (varies by provider) | None |
| Setup requirement | API key or zero-auth | Python package + optional data file |
| Timeout behavior | (5, 30) timeout critical | Near-instant (sub-millisecond) |
| Caching value | High (API quota conservation) | Lower (local lookups are free) |
| Failure mode | Network error, HTTP error | Library error, missing file |

### Local Provider Pattern

Local providers implement the exact same protocol but skip `validate_endpoint()` and `http_safety` utilities entirely:

```python
class DNSProvider:
    name = "DNS Resolver"
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN})
    requires_api_key = False
    source_type = "local"  # informational — not part of Protocol

    def is_configured(self) -> bool:
        return True  # dnspython always available if installed

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        # No HTTP. No SSRF check. No timeout tuple.
        # Pure dnspython synchronous resolver call.
        ...
```

The `source_type = "local"` class attribute is informational for the settings page — it is NOT part of the Protocol and is not used by ProviderRegistry or EnrichmentOrchestrator.

**Confidence: HIGH** — verified against existing ShodanAdapter pattern which is already zero-auth with `is_configured() == True`.

---

## Zero-Auth Enrichment Sources

### 1. DNS Resolver (dnspython)

**What it provides:** Forward/reverse DNS lookups, MX records, TXT records (SPF, DMARC)
**IOC types:** IPv4 (PTR/reverse), IPv6 (PTR), domain (A, AAAA, MX, TXT, NS)
**Library:** `dnspython` (v2.9.0 as of 2025) — synchronous `dns.resolver.resolve()`

```python
import dns.resolver
import dns.reversename

class DNSProvider:
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN})

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        try:
            if ioc.type in {IOCType.IPV4, IOCType.IPV6}:
                rev_name = dns.reversename.from_address(ioc.value)
                answers = dns.resolver.resolve(rev_name, "PTR")
                hostnames = [str(r) for r in answers]
                raw_stats = {"ptr": hostnames, "record_type": "PTR"}
            else:
                # Domain: A/AAAA + MX + TXT
                ...
            return EnrichmentResult(ioc=ioc, provider=self.name, verdict="no_data",
                                    detection_count=0, total_engines=0, scan_date=None,
                                    raw_stats=raw_stats)
        except dns.exception.DNSException as e:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(e))
```

**Key consideration:** DNS lookups use the system's configured resolver. For a jump box or local analyst machine, this is the correct behavior. No SSRF risk — dnspython does not contact analyst-controlled infrastructure.

**Confidence: HIGH** — dnspython 2.9.0 official docs confirm synchronous `dns.resolver.resolve()` with `dns.reversename.from_address()` for PTR lookups.

---

### 2. GeoIP/ASN (geoip2 + GeoLite2 mmdb files)

**What it provides:** Country, city, ASN, organization for IP addresses
**IOC types:** IPv4, IPv6
**Library:** `geoip2` Python package + MaxMind GeoLite2 `.mmdb` files

**File placement:** `~/.sentinelx/geoip/GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb`

This is the most architecturally different new provider because it requires **local database files** that the analyst must provision. This is similar to `requires_api_key` but for files, not keys.

```python
import geoip2.database
import geoip2.errors

class GeoIPProvider:
    name = "GeoIP"
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False
    _db_path = Path.home() / ".sentinelx" / "geoip" / "GeoLite2-City.mmdb"

    def is_configured(self) -> bool:
        return self._db_path.exists()

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        try:
            with geoip2.database.Reader(str(self._db_path)) as reader:
                response = reader.city(ioc.value)
            ...
        except geoip2.errors.AddressNotFoundError:
            return EnrichmentResult(..., verdict="no_data", raw_stats={})
        except FileNotFoundError:
            return EnrichmentError(..., error="GeoLite2 database not found")
```

**Critical issue — Reader lifecycle:** The geoip2 docs warn that Reader creation is expensive. For a lookup-per-request pattern, this means caching the Reader as a class attribute or using `with` lazily. For low-volume analyst use, `with` per lookup is acceptable and simplest. High-frequency would warrant a module-level Reader.

**Database provisioning:** GeoLite2 requires a free MaxMind account for official downloads. The settings page should display `is_configured()` status and instructions. Do NOT bundle the mmdb files in the repo (license restriction: GeoLite2 requires attribution and cannot be redistributed without a license agreement).

**Confidence: HIGH** — geoip2 5.2.0 official docs confirm `geoip2.database.Reader`, `AddressNotFoundError`, and Reader creation cost warning.

---

### 3. ASN Lookup (ipwhois)

**What it provides:** ASN number, AS name, AS description, CIDR range, network owner
**IOC types:** IPv4, IPv6
**Library:** `ipwhois` — `IPWhois(ip).lookup_rdap()` method

```python
from ipwhois import IPWhois

class ASNProvider:
    name = "ASN Lookup"
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def is_configured(self) -> bool:
        return True  # pure RDAP — no local files needed

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        try:
            obj = IPWhois(ioc.value)
            result = obj.lookup_rdap(depth=1)
            raw_stats = {
                "asn": result.get("asn"),
                "asn_description": result.get("asn_description"),
                "asn_cidr": result.get("asn_cidr"),
                "network_name": result.get("network", {}).get("name"),
            }
            return EnrichmentResult(ioc=ioc, provider=self.name, verdict="no_data",
                                    detection_count=0, total_engines=0, scan_date=None,
                                    raw_stats=raw_stats)
        except Exception as e:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(e))
```

**Important constraint:** ipwhois performs RDAP lookups against RIR servers (ARIN, RIPE, APNIC, etc.) — these are outbound HTTP calls. The RIR endpoints must be added to `ALLOWED_API_HOSTS` in `config.py`. However, RIR RDAP endpoints have dynamic URLs that vary by IP range, making static allowlisting impractical.

**Architecture decision required:** ASN via ipwhois is effectively a "remote zero-auth" provider with variable endpoints — the SSRF allowlist model cannot safely accommodate it. Two options:

- **Option A:** Include RIR RDAP endpoints in allowlist (complex, fragile)
- **Option B:** Use Shodan InternetDB's `cpes`/`hostnames` fields (already in raw_stats) for basic ASN-adjacent context
- **Option C:** Defer ASN to a Cymru WHOIS-style TCP lookup (not HTTP — exempt from SSRF allowlist)

**Recommendation:** Option B for the first phase (extract more from existing Shodan data), Option C research for a subsequent phase. Skip ipwhois for v6.0.

**Confidence: MEDIUM** — ipwhois RDAP pattern confirmed, SSRF allowlist conflict identified from code analysis.

---

### 4. Certificate Transparency (crt.sh API)

**What it provides:** Historical SSL/TLS certificates for a domain, subdomain enumeration
**IOC types:** Domain
**Endpoint:** `https://crt.sh/?q=<domain>&output=json` — public JSON API, zero-auth

```python
class CertTransparencyProvider:
    name = "Cert Transparency"
    supported_types = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def is_configured(self) -> bool:
        return True  # zero-auth remote API

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        url = f"https://crt.sh/?q={ioc.value}&output=json"
        validate_endpoint(url, self._allowed_hosts)  # must add crt.sh to allowlist
        ...
```

**crt.sh endpoint:** `crt.sh` must be added to `ALLOWED_API_HOSTS`. The response can be large (thousands of certificates for popular domains) — the existing 1 MB response cap in `read_limited()` applies. Consider a `?limit=100` or filtering by most recent.

**What analysts get:** Issuer org, subject alt names (subdomains), validity period, issuer CA. Useful for domain IOCs to identify infrastructure relationships.

**Confidence: MEDIUM** — crt.sh JSON API confirmed via multiple sources, endpoint format verified, but response volume for popular domains is a known concern.

---

## Local vs Remote Enrichment: Architectural Distinction

The distinction matters for three things:

### 1. SSRF Allowlist (`config.py`)

Remote providers add hosts to `ALLOWED_API_HOSTS`. Local providers add nothing:

```python
# New additions for zero-auth remote providers
ALLOWED_API_HOSTS: list[str] = [
    ...existing 8 hosts...,
    "crt.sh",              # cert transparency (if included)
    # NOT: RIR RDAP endpoints (dynamic, complex)
]
```

Local providers (DNS, GeoIP) make no outbound HTTP calls — no allowlist entry needed.

### 2. Cache TTL Strategy

Local lookups (GeoIP mmdb) are near-instant and free — caching provides minimal benefit. Remote zero-auth lookups (DNS, crt.sh) benefit from caching to avoid redundant network calls:

| Provider | Cache Recommended | Suggested TTL |
|----------|------------------|---------------|
| DNS Resolver | Yes | 1 hour (DNS TTLs typically short) |
| GeoIP (mmdb) | No | — (sub-ms, no quota) |
| Cert Transparency | Yes | 24 hours (CT logs update slowly) |
| ASN (deferred) | Yes | 48 hours |

The existing `CacheStore` works unchanged — cache lookup is in `EnrichmentOrchestrator._do_lookup()` which wraps all adapters uniformly. Local providers can pass through the cache layer without harm.

### 3. Settings Page Display

The settings page currently shows only key-requiring providers. A new "Local Intelligence" section should show:

- **DNS Resolver:** Always available (green checkmark)
- **GeoIP:** Shows mmdb file status (configured/not configured with download instructions)
- **Cert Transparency:** Always available (zero-auth remote)

This requires extending `PROVIDER_INFO` in `setup.py` with a new `"source_type"` field: `"local"` | `"remote"` | `"remote_zero_auth"`.

---

## Deeper Per-IOC Analysis Views

### Architecture Decision: Server-Side Rendering via New Route

**Pattern:** Add a `GET /ioc/<ioc_value>` route that renders a detail page with all enrichment data from cache, plus local enrichment run on-demand.

**Why server-side, not client-side modal:**

1. The existing results page is rendered server-side with enrichment populated via polling. Deep analysis requires its own page-level navigation.
2. Per-IOC detail can be bookmarked/linked by analysts (copy URL for sharing in tickets).
3. The current single-page-ish flow doesn't need to change — the detail page is an optional drill-down.

**Data flow for detail page:**

```
Analyst clicks "View Details" on IOC card
    ↓
GET /ioc/<url-encoded-ioc-value>?type=<ioc_type>
    ↓
Route: query CacheStore for all cached results for this IOC
    ↓
Route: run local enrichment (DNS/GeoIP) synchronously (fast — sub-second)
    ↓
Route: render ioc_detail.html with all data
    ↓
Browser renders: tabbed detail view
```

**Tab structure for per-IOC detail:**

| Tab | Content | IOC Types |
|-----|---------|-----------|
| Overview | Summary verdict, provider consensus, key stats | All |
| Network | Reverse DNS, open ports, ASN, GeoIP, hostnames | IP |
| Certificates | CT log entries, issuer, SANs | Domain, URL |
| DNS Records | A/AAAA, MX, TXT (SPF/DMARC), NS | Domain |
| Threat Intel | All provider results, expandable raw data | All |
| Graph | IOC relationship visualization | All |
| Notes | Analyst tags and notes | All |

**New Flask route:**

```python
@bp.route("/ioc/<path:ioc_value>", methods=["GET"])
@limiter.limit("30 per minute")
def ioc_detail(ioc_value: str):
    ioc_type_str = request.args.get("type", "")
    # Validate ioc_type_str against IOCType enum — never trust query params
    # Load cached enrichment results from CacheStore
    # Run local enrichment synchronously
    # Render template
    return render_template("ioc_detail.html", ...)
```

**Security:** `ioc_value` from URL path must be validated against the same normalization pipeline — never use raw path value in any query, log, or display without validation. Use `IOCType` enum to validate the `type` param.

---

## Relationship Graph Visualization

### Architecture Decision: Cytoscape.js via CDN, Graph Data from Flask API

**Why Cytoscape.js over D3.js and Vis.js:**

| Criterion | D3.js | Vis.js | Cytoscape.js |
|-----------|-------|--------|--------------|
| Built-in graph algorithms | No | Partial | Yes (BFS, DFS, shortest path) |
| API complexity | High | Medium | Low |
| Performance | Medium | Low | High |
| CDN bundle size | Large | Large | ~87 KB minified |
| Vanilla JS compatible | Yes | Yes | Yes (no framework needed) |
| Analyst-appropriate interactivity | Manual | Auto | Auto |

Cytoscape.js is specifically designed for network/relationship graphs, works with vanilla JS (no npm), and is available via jsDelivr CDN. The project constraints exclude npm — Cytoscape.js can be loaded from CDN and included as a `<script>` tag, matching the project's no-Node-dependency philosophy.

**CDN delivery vs self-hosted:**

The project serves fonts from `app/static/fonts/` (self-hosted). For CSP compliance, Cytoscape.js should also be self-hosted:

```
tools/
├── esbuild          (existing binary)
├── tailwindcss      (existing binary)
app/static/
├── vendor/
│   └── cytoscape.min.js   [NEW — downloaded at setup time]
```

Add to `make vendor` target or manual install instructions. This avoids adding an external CDN to the CSP `script-src` directive.

**Graph data API:**

```python
@bp.route("/api/graph/<job_id>", methods=["GET"])
@limiter.limit("30 per minute")
def graph_data(job_id: str):
    """Return Cytoscape.js node/edge format for job results."""
    # Build graph from enrichment results
    # Nodes: IOC values + provider names
    # Edges: IOC → provider (with verdict weight)
    return jsonify({"nodes": [...], "edges": [...]})
```

**Graph node types:**

```
IOC node:      { id: "ioc:<value>", type: "ioc", ioc_type: "ipv4", verdict: "malicious" }
Provider node: { id: "provider:VirusTotal", type: "provider", name: "VirusTotal" }
Edge:          { source: "ioc:<value>", target: "provider:VirusTotal", verdict: "malicious" }
```

**Relationship enrichment for graph (future phase):** When DNS/cert data reveals that two IOCs share infrastructure (same IP, same cert SANs, same ASN), edges between IOC nodes can show these relationships — turning the graph from a "star topology" (IOC → providers) into a genuine relationship map.

**TypeScript module:** Add `modules/graph.ts` that imports Cytoscape.js via a declare module shim and wires the graph container on the detail page. The IIFE bundle approach works — Cytoscape.js is loaded as a global before main.js runs.

**Confidence: MEDIUM** — Cytoscape.js CDN delivery and vanilla JS confirmed. Graph data API pattern is standard Flask JSON pattern (HIGH). Relationship enrichment is future scope.

---

## IOC Tagging and Notes

### Architecture Decision: New SQLite Table in Separate NoteStore

**Pattern:** A new `NoteStore` class parallel to `CacheStore`, storing analyst annotations per IOC value.

```python
# app/notes/store.py
class NoteStore:
    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS ioc_notes (
        ioc_value   TEXT NOT NULL,
        ioc_type    TEXT NOT NULL,
        tags        TEXT NOT NULL DEFAULT '[]',   -- JSON array of tag strings
        note        TEXT NOT NULL DEFAULT '',
        updated_at  TEXT NOT NULL,
        PRIMARY KEY (ioc_value, ioc_type)
    )
    """

    def get(self, ioc_value: str, ioc_type: str) -> dict | None: ...
    def put(self, ioc_value: str, ioc_type: str, tags: list[str], note: str) -> None: ...
    def search_by_tag(self, tag: str) -> list[dict]: ...
```

**Database path:** `~/.sentinelx/notes.db` — separate from `cache.db` to allow independent clearing.

**Why separate from CacheStore:** Cache is ephemeral (TTL-driven, clearable). Notes are intentional analyst annotations — clearing cache must not destroy notes. Separate files make this semantically clear and operationally safe.

**API surface:** Notes are saved via a POST from the IOC detail page, displayed inline on results cards (tag badges), and searchable from a future notes/history page.

```python
@bp.route("/api/ioc/<path:ioc_value>/notes", methods=["POST"])
@limiter.limit("20 per minute")
def save_note(ioc_value: str): ...
```

**Inline display on results cards:** Add a `data-tags` attribute to `.ioc-card` elements populated from NoteStore at `/analyze` render time (for IOCs that have cached enrichment results with existing notes). The TypeScript `cards.ts` module renders tag badges from this attribute.

**Confidence: MEDIUM** — Pattern is a direct extension of the existing CacheStore architecture; SQLite schema is straightforward; API design is standard Flask POST.

---

## Recommended Project Structure (New Files Only)

```
app/
├── enrichment/
│   └── adapters/
│       ├── dns_resolver.py         # DNSProvider — dnspython
│       ├── geoip.py                # GeoIPProvider — geoip2 + mmdb
│       └── cert_transparency.py    # CertTransparencyProvider — crt.sh
├── notes/                          # [NEW module]
│   ├── __init__.py
│   └── store.py                    # NoteStore — SQLite ioc_notes table
├── templates/
│   ├── ioc_detail.html             # [NEW] per-IOC deep analysis page
│   └── graph.html                  # [NEW] or section in ioc_detail.html
└── static/
    ├── vendor/
    │   └── cytoscape.min.js        # [NEW] self-hosted Cytoscape.js
    └── src/ts/modules/
        ├── graph.ts                # [NEW] Cytoscape.js wiring
        └── notes.ts                # [NEW] inline tag/note UI
```

---

## Data Flow: Full v6.0 Enrichment

### Primary Flow (unchanged)

```
POST /analyze
    ↓
run_pipeline(text) → [IOC, ...]
    ↓
EnrichmentOrchestrator.enrich_all(job_id, iocs)
    → [VirusTotal, MalwareBazaar, ThreatFox, Shodan, URLhaus,
       OTX, GreyNoise, AbuseIPDB,
       DNSProvider, GeoIPProvider, CertTransparencyProvider]  ← new providers in registry
    ↓
GET /enrichment/status/<job_id>  (polling, 750ms interval)
    ↓
Browser renders cards with enrichment data (existing TypeScript pipeline)
```

### Detail View Flow (new)

```
Analyst clicks "View Details" link on IOC card
    ↓
GET /ioc/<value>?type=<type>
    ↓
CacheStore.get_all_for_ioc(value, type)  → existing enrichment results
NoteStore.get(value, type)               → analyst annotations
    ↓
Render ioc_detail.html with tabbed sections
    ↓
Browser: Cytoscape.js renders graph in "Graph" tab (lazy-loaded)
```

---

## Security Implications

### New Attack Surface: URL Path IOC Value

The `/ioc/<path:ioc_value>` route exposes IOC values in URLs. **Never trust path values** — always re-validate through the existing normalization pipeline before any use.

```python
# WRONG: use ioc_value directly
cache_results = cache.get_all_for_ioc(ioc_value, ...)  # path injection risk

# CORRECT: validate first
try:
    ioc_type = IOCType(ioc_type_str)  # validates against enum
    iocs = run_pipeline(ioc_value)   # runs full normalization
    if not iocs:
        abort(400)
    canonical = iocs[0].value        # use only the normalized form
except ValueError:
    abort(400)
```

### DNS Lookups: No SSRF Risk, But Timing

DNS resolution is synchronous in dnspython. The system resolver is used (no HTTP), so the SSRF allowlist is not relevant. However, DNS lookups can block the worker thread for up to the resolver timeout (typically 5 seconds per query). Since EnrichmentOrchestrator uses ThreadPoolExecutor, each DNS lookup consumes a thread slot. Keep the ThreadPoolExecutor `max_workers` consistent — DNS providers should not inflate thread count requirements significantly given their speed.

### GeoIP mmdb: File Path Validation

The GeoIP database path is configurable (future settings UI). Validate that any configurable path is under `~/.sentinelx/` — never allow arbitrary filesystem paths.

### Cytoscape.js: Self-Hosted, CSP Compliant

Loading Cytoscape.js from CDN would require adding `cdn.jsdelivr.net` to `script-src` in the CSP header — a security regression. Self-host the minified bundle at `app/static/vendor/cytoscape.min.js` and serve via Flask's existing static file handler. No CSP changes needed.

### NoteStore: User Input in SQLite

Tags and notes are analyst-controlled free text. Always use parameterized queries (existing CacheStore pattern). Never render notes via `innerHTML` — use `textContent` (SEC-08 pattern). Validate tag strings (length limit, character set) before storing.

---

## Build Order Considerations

Given inter-dependencies, phases should be ordered:

1. **Local enrichment providers** (DNS + GeoIP) — they integrate with existing ProviderRegistry/setup.py. No UI changes needed. Tests can verify `lookup()` behavior immediately.

2. **Settings page extension** — add "Local Intelligence" section showing provider status. Requires `source_type` metadata in `PROVIDER_INFO`.

3. **Cert transparency provider** — requires `ALLOWED_API_HOSTS` update and SSRF validation wiring. Straightforward adapter following existing ShodanAdapter pattern.

4. **NoteStore + tags API** — independent module, no dependencies on new providers. Can be parallelized with provider work.

5. **Per-IOC detail page** — depends on NoteStore (for notes tab) and local providers (for DNS/GeoIP content). Server-rendered template.

6. **Graph visualization** — depends on per-IOC detail page (the graph lives within it) and Cytoscape.js vendoring. TypeScript module addition.

**Deferred:** ASN lookup via ipwhois (SSRF allowlist conflict), MISP/STIX feed integration (high complexity, separate architectural pattern from Provider Protocol).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Treating Local Providers as "Not Real Providers"

**What people do:** Implement DNS/GeoIP as utility functions called directly in routes, bypassing the Provider Protocol.

**Why it's wrong:** Loses caching, loses the parallel execution model, loses the unified results rendering pipeline. DNS results would need separate rendering logic.

**Do this instead:** Implement as full Provider Protocol adapters registered in `build_registry()`. They integrate with the orchestrator and cache automatically.

---

### Anti-Pattern 2: Blocking the Main Thread with DNS Lookups

**What people do:** Call `dns.resolver.resolve()` directly in a Flask route handler.

**Why it's wrong:** Flask's threaded mode can handle this (each request is its own thread), but DNS timeouts (NXDOMAIN, SERVFAIL) block that thread. The existing pattern of background thread + polling handles this correctly.

**Do this instead:** DNS lookups run inside `EnrichmentOrchestrator.enrich_all()` via ThreadPoolExecutor — same as all other providers. The polling model already handles latency.

---

### Anti-Pattern 3: Adding WHOIS to `ALLOWED_API_HOSTS` with Wildcard

**What people do:** Add `"*.rdap.arin.net"`, `"rdap.ripe.net"` etc. to allowlist to support ipwhois RDAP.

**Why it's wrong:** RDAP endpoints are dynamic — different RIRs handle different IP ranges, and ipwhois performs redirects. Wildcards in the allowlist break the SEC-16 guarantee. The allowlist is a hostname check, not a wildcard matcher.

**Do this instead:** Defer ASN enrichment to Cymru WHOIS (TCP port 43) which is exempt from the HTTP SSRF model, or extract ASN data from Shodan InternetDB's existing `cpes` field.

---

### Anti-Pattern 4: CDN Script Tag for Cytoscape.js

**What people do:** Add `<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.x/dist/cytoscape.min.js">` to the template.

**Why it's wrong:** Requires `script-src cdn.jsdelivr.net` in the CSP header — weakens the `script-src 'self'` guarantee. Also breaks offline usage.

**Do this instead:** Download the minified bundle once (`make vendor-install` target) to `app/static/vendor/cytoscape.min.js`. Flask serves it from `'self'`. No CSP change needed.

---

### Anti-Pattern 5: Using `innerHTML` for Graph Node Labels

**What people do:** Use Cytoscape.js tooltip HTML with `innerHTML` to display IOC values in graph nodes.

**Why it's wrong:** IOC values come from analyst paste input, which is untrusted. Rendering via `innerHTML` breaks SEC-08.

**Do this instead:** Use Cytoscape.js `data()` method with `textContent` for any DOM elements showing IOC values. Cytoscape's built-in label rendering uses SVG/Canvas text — not HTML — so node labels are inherently safe.

---

## Integration Points

### Modified Existing Files

| File | Change | Risk |
|------|--------|------|
| `app/enrichment/setup.py` | Add 3 new adapter registrations + PROVIDER_INFO entries | Low — additive |
| `app/config.py` | Add `crt.sh` to `ALLOWED_API_HOSTS` | Low — additive |
| `app/routes.py` | Add `/ioc/<value>`, `/api/graph/<job_id>`, `/api/ioc/<value>/notes` routes | Medium — new routes, new imports |
| `app/templates/results.html` | Add "View Details" link on each IOC card | Low — template addition |
| `app/static/src/ts/modules/enrichment.ts` | Add `PROVIDER_CONTEXT_FIELDS` entries for new providers | Low — additive |

### New Files

| File | Purpose |
|------|---------|
| `app/enrichment/adapters/dns_resolver.py` | DNS Provider adapter |
| `app/enrichment/adapters/geoip.py` | GeoIP Provider adapter |
| `app/enrichment/adapters/cert_transparency.py` | Cert Transparency adapter |
| `app/notes/__init__.py` | Notes module init |
| `app/notes/store.py` | NoteStore — SQLite ioc_notes |
| `app/templates/ioc_detail.html` | Per-IOC deep analysis page |
| `app/static/vendor/cytoscape.min.js` | Self-hosted Cytoscape.js |
| `app/static/src/ts/modules/graph.ts` | Cytoscape.js graph wiring |
| `app/static/src/ts/modules/notes.ts` | Inline tag/note UI |

### Scaling Considerations

This is a single-user local tool. The relevant scaling concern is result volume, not concurrent users:

| IOC Count | Architecture Impact |
|-----------|---------------------|
| 1-10 IOCs | No change — existing ThreadPoolExecutor handles comfortably |
| 10-50 IOCs | DNS lookups add ~50 × N lookup latency — still within polling tolerance |
| 50+ IOCs | DNS lookups may saturate ThreadPoolExecutor slots — consider separate DNS thread pool with higher `max_workers` for local providers |

For the IOC detail page, all data is synchronous and local — no pagination or streaming needed at analyst-realistic volumes (< 1000 certs from crt.sh).

---

## Sources

- [dnspython 2.9.0 documentation — resolver-class](https://dnspython.readthedocs.io/en/latest/resolver-class.html) — synchronous resolve() and reversename.from_address() confirmed (HIGH confidence — official docs)
- [geoip2 5.2.0 Python API documentation](https://geoip2.readthedocs.io/) — Reader creation cost, AddressNotFoundError, city() method (HIGH confidence — official docs)
- [MaxMind GeoLite2 Free Geolocation Data](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/) — GeoLite2 license requires signup, cannot redistribute mmdb files (HIGH confidence — official MaxMind developer portal)
- [ipwhois RDAP documentation](https://ipwhois.readthedocs.io/en/latest/RDAP.html) — IPWhois.lookup_rdap() method, RDAP endpoint behavior (MEDIUM confidence — library docs, SSRF conflict is author's analysis)
- [Cytoscape.js — graph theory library](https://js.cytoscape.org/) — CDN availability, vanilla JS usage, built-in graph algorithms (HIGH confidence — official site)
- [Cytoscape.js 3.33.0 release blog](https://blog.js.cytoscape.org/2025/07/28/3.33.0-release/) — confirms active maintenance in 2025 (MEDIUM confidence — official blog)
- [crt.sh certificate transparency search](https://www.crt.sh/) — JSON API endpoint `?output=json` confirmed (MEDIUM confidence — public service, no formal API docs)
- [SentinelX existing code analysis] — Provider Protocol, ShodanAdapter zero-auth pattern, CacheStore pattern, SSRF allowlist, http_safety utilities (HIGH confidence — direct codebase inspection)

---

*Architecture research for: v6.0 Analyst Experience — zero-auth enrichment, local providers, deeper analysis views*
*Researched: 2026-03-11*
