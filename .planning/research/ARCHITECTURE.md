# Architecture Research

**Domain:** Threat intelligence enrichment platform — DNSBL checks, public threat feeds, RDAP registration, ASN/BGP intelligence, annotations removal (SentinelX v7.0)
**Researched:** 2026-03-15
**Confidence:** HIGH for DNSBL/ASN (DNS-native, same dnspython already in use), HIGH for annotations removal (all touchpoints fully mapped), MEDIUM for RDAP (boot-strapping service stable but rate-limit policies undocumented), MEDIUM for public threat feeds (Feodo datasets currently empty due to takedowns)

---

## Context: What This Research Covers

This is a SUBSEQUENT MILESTONE research document. The full existing architecture (Provider Protocol, ProviderRegistry, EnrichmentOrchestrator, CacheStore, Flask routes, 14 TypeScript modules) is locked in. This document covers HOW the v7.0 capabilities integrate with that architecture — specifically:

1. DNSBL reputation checks (new zero-auth provider — DNS-native)
2. Public threat feed lookups (new zero-auth provider — HTTP bulk-feed pattern)
3. RDAP registration data (new zero-auth provider — HTTP REST)
4. ASN/BGP intelligence (new zero-auth provider — DNS-native)
5. Annotations removal (destructive change — all touchpoints fully mapped)

**Existing enrichment pipeline (unchanged):**

```
POST /analyze  ->  run_pipeline(text)  ->  EnrichmentOrchestrator.enrich_all()
                                                 |
                                   ProviderRegistry.providers_for_type()
                                                 |
                                   [adapter.lookup(ioc) x N providers]
                                                 |
                         GET /enrichment/status/<job_id>  ->  polling  ->  browser renders cards
```

---

## Standard Architecture: How New Providers Integrate

The Provider Protocol makes new provider addition mechanical. Every new provider is ONE new file + ONE `register()` call. No orchestrator, route, or registry changes needed.

### Provider Protocol Contract (from `app/enrichment/provider.py`)

```python
class Provider(Protocol):
    name: str
    supported_types: set[IOCType] | frozenset[IOCType]
    requires_api_key: bool

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError: ...
    def is_configured(self) -> bool: ...
```

All four new providers satisfy this contract with `requires_api_key = False` and `is_configured()` returning `True` always (zero-auth).

### System Overview (v7.0 target state)

```
+-------------------------------------------------------------+
|                     Flask Routes                            |
|  POST /analyze   GET /settings   GET /ioc/<type>/<value>    |
+------------------------------+------------------------------+
                               |
+------------------------------v------------------------------+
|               EnrichmentOrchestrator                        |
|  enrich_all() -> ThreadPoolExecutor -> cache -> results     |
+------------------------------+------------------------------+
                               |
+------------------------------v------------------------------+
|               ProviderRegistry (17 providers)               |
+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
    |   |   |   |   |   |   |   |   |   |   |   |   |   |
[ existing 13 providers ]  [NEW v7.0 providers]
                            |           |           |       |
                      DNSBLAdapter  ThreatFeedAdapter  RDAPAdapter  ASNAdapter
                      (DNS-native)  (HTTP bulk feed)  (HTTP REST)  (DNS-native)
+-------------------------------------------------------------+
|                       Data Stores                           |
|  CacheStore (cache.db)     [AnnotationStore REMOVED]        |
+-------------------------------------------------------------+
```

---

## New Components Required

### 1. DNSBLAdapter — `app/enrichment/adapters/dnsbl.py`

**What it does:** Checks IPs and domains against DNS-based reputation blocklists (Spamhaus ZEN for IPs, SURBL multi for domains) by constructing reversed DNS queries.

**Mechanism:** Pure DNS — uses the existing `dnspython` dependency. No HTTP calls. No API key. Same pattern as `DnsAdapter` (port 53 direct, `allowed_hosts` accepted but unused for SSRF purposes).

**Supported types:** `{IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN}`

**Verdict logic:**
- Any DNSBL hit → `"malicious"` with `detection_count = count_of_listed_zones`
- All zones return NXDOMAIN → `"clean"` (explicitly checked, not present)
- DNS timeout / failure → `EnrichmentError`

**Query patterns:**

For IP (`1.2.3.4`):
```
# Reverse octets + append zone
4.3.2.1.zen.spamhaus.org  (A record lookup)
4.3.2.1.bl.spamhaus.org   (A record lookup)
```

For domain (`evil.com`):
```
# Prepend domain + append zone
evil.com.multi.surbl.org  (A record lookup)
evil.com.dbl.spamhaus.org (A record lookup)
```

**Return codes:** Any `127.x.x.x` A record = listed. NXDOMAIN = not listed.

**DNSBL zones to query (verified):**

| Zone | Covers | Type |
|------|--------|------|
| `zen.spamhaus.org` | Combined SBL+XBL+PBL | IPs |
| `dbl.spamhaus.org` | Domain blocklist | Domains |
| `multi.surbl.org` | URI DNSBL (phishing/spam domains) | Domains |

**Spamhaus free-tier note:** MEDIUM confidence. Spamhaus operates a fair-use policy for non-commercial, low-volume use. A local analyst tool making per-IOC queries on demand (not bulk automated) is within fair use. The risk is if an analyst pastes very large batches frequently — the system resolver may be rate-limited. Mitigations: cap retries, treat `SERVFAIL` as no-data rather than malicious.

**Implementation pattern (mirrors `DnsAdapter`):**

```python
class DNSBLAdapter:
    name = "DNSBL"
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        pass  # DNS-native, no SSRF surface

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        ...
```

**raw_stats shape:**
```python
{
    "listed_on": ["zen.spamhaus.org"],  # zones that returned a hit
    "checked": ["zen.spamhaus.org", "dbl.spamhaus.org"],  # all zones queried
    "lookup_errors": [],  # timeout/failure entries per zone
}
```

---

### 2. ThreatFeedAdapter — `app/enrichment/adapters/threat_feed.py`

**What it does:** Checks IPs against the Feodo Tracker botnet C2 IP blocklist (JSON format). Uses a bulk-download-and-search pattern: downloads the full JSON feed, builds an in-memory set, then answers lookup calls by set membership.

**Mechanism:** HTTP GET to `https://feodotracker.abuse.ch/downloads/ipblocklist.json` — one download per cache TTL window, not per IOC.

**Important context:** The Feodo Tracker JSON feed currently shows empty datasets due to successful law enforcement takedowns (Emotet 2021, Operation Endgame 2024). The feed infrastructure is maintained but active C2 entries are absent at time of research. This means the provider will typically return `"clean"` with no detections — which is a correct and useful signal for analysts (confirms IP is not in a known C2 list). The feed URL and format are stable.

**Supported types:** `{IOCType.IPV4}` — Feodo Tracker is IP-only.

**Verdict logic:**
- IP found in feed → `"malicious"` with `detection_count=1`, `raw_stats` includes malware family + C2 port
- IP not in feed → `"clean"` (confirmed absent from known C2 list)
- Feed download failure → `EnrichmentError`

**Feed JSON schema (from research):**
```json
[
  {
    "ip_address": "1.2.3.4",
    "port": 443,
    "malware_malpedia": "Dridex",
    "as_number": 12345,
    "as_name": "ISP Name",
    "country": "US",
    "first_seen": "2024-01-01 00:00:00",
    "last_online": "2024-12-01"
  }
]
```

**Key architectural decision:** This is NOT a per-call HTTP adapter like the others. It requires a feed-refresh strategy. Two options:

- **Option A (simpler, recommended):** Download on each `lookup()` call, rely on the existing `CacheStore` to avoid repeated downloads. The result gets cached like any other provider result — the full feed is never stored in app memory, only the per-IOC lookup result is cached. Downside: every cache-miss triggers a full 100KB+ JSON download.

- **Option B (efficient, complex):** Module-level feed cache with TTL — load the full feed into memory once, refresh every N minutes. Requires a background thread or lazy refresh. Adds shared state that violates the stateless-per-request pattern used by all other adapters.

**Recommendation:** Option A. The `CacheStore` TTL (default 24h) means the full download happens at most once per IOC per day. The feed is ~100KB. The SentinelX "one analyst, local tool" context makes Option B premature optimization. Mark for future optimization if batch-size grows.

**SSRF allowlist change required:** Add `feodotracker.abuse.ch` to `ALLOWED_API_HOSTS` in `app/config.py`.

**raw_stats shape (hit):**
```python
{
    "malware": "Dridex",
    "port": 443,
    "first_seen": "2024-01-01 00:00:00",
    "last_online": "2024-12-01",
}
```

---

### 3. RDAPAdapter — `app/enrichment/adapters/rdap.py`

**What it does:** Retrieves registration data (registrar, creation date, nameservers) for domains and IPs via the RDAP protocol using `rdap.org` as a bootstrap service.

**Mechanism:** HTTP GET to `https://rdap.org/domain/{domain}` or `https://rdap.org/ip/{ip}`. The bootstrap service returns a `302 redirect` to the authoritative RDAP server (IANA-registered). The adapter must follow this redirect (one hop only — `allow_redirects=True` or handle manually).

**Important design note:** RDAP redirects go to registry-specific servers (e.g., `https://rdap.verisign.com/com/v1/domain/example.com`). These authoritative servers are NOT in `ALLOWED_API_HOSTS`. The redirect-follow requirement conflicts with `SEC-06` (no redirects). Resolution: use `allow_redirects=True` but validate the redirect destination hostname is an `rdap.*` or registry subdomain — OR use the `rdap.org` bootstrap which itself resolves and proxies the response without redirecting to third-party hosts.

**Verification needed:** Confirm whether `rdap.org` proxies responses or issues redirects. From research: OpenRDAP's `rdap.net` "will redirect queries to the authoritative RDAP server via a HTTP 302 redirect." The `rdap.org` bootstrap appears to proxy (returns the authoritative response directly). This needs validation during implementation.

**Rate limits:** `rdap.org` limits clients to 10 requests per 10 seconds (429 on violation). For a single-analyst tool with cache, this is fine.

**Supported types:** `{IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6}`

**Verdict logic:** Always `"no_data"` — registration data is informational context, not a threat signal. Domain age is a useful triage indicator (newly registered = higher suspicion) but the adapter does not make that judgment.

**RDAP JSON response fields (from RFC 9083):**
- `events[].eventAction == "registration"` → `eventDate` = creation date
- `events[].eventAction == "expiration"` → `eventDate` = expiry date
- `nameservers[].ldhName` → nameserver hostnames
- `entities[role=="registrar"].vcardArray` → registrar name

**SSRF allowlist change required:** Add `rdap.org` to `ALLOWED_API_HOSTS`. If redirect-follow is needed, this must also allow the resolved authoritative server hostname — which is registry-dependent and not enumerable. This is a security tradeoff that needs phase-level decision: either use `rdap.org` as a true proxy (single allowlist entry) or flag this as MEDIUM risk and limit to domain RDAP only.

**raw_stats shape:**
```python
{
    "registrar": "GoDaddy.com, LLC",
    "created": "2015-03-01",
    "expires": "2026-03-01",
    "nameservers": ["ns1.example.com", "ns2.example.com"],
}
```

---

### 4. ASNAdapter — `app/enrichment/adapters/asn.py`

**What it does:** Returns ASN number, prefix, country, registry, and allocation date for IPs using the Team Cymru DNS-based IP-to-ASN mapping service.

**Mechanism:** Pure DNS — uses existing `dnspython` dependency. Zero-auth. Free forever (Team Cymru's stated policy). No HTTP calls. No SSRF surface. Same pattern as `DnsAdapter`.

**Query format (verified):**
```
# IPv4: reverse octets, append .origin.asn.cymru.com, query TXT
dig +short 31.108.90.216.origin.asn.cymru.com TXT
# Returns: "23028 | 216.90.108.0/24 | US | arin | 1998-09-25"

# IPv6: reverse nibbles, append .origin6.asn.cymru.com
```

**ASN description lookup:**
```
dig +short AS23028.asn.cymru.com TXT
# Returns: "23028 | US | arin | 1998-09-25 | TEAM-CYMRU, US"
```

**Supported types:** `{IOCType.IPV4, IOCType.IPV6}`

**Verdict logic:** Always `"no_data"` — ASN data is contextual, not a threat verdict. The analyst uses it to identify hosting providers, cloud ASNs (AWS/Azure/GCP = likely cloud/C2 infrastructure), or known-bad ASNs.

**Implementation pattern (mirrors `DnsAdapter`):**

```python
class ASNAdapter:
    name = "ASN Info"
    supported_types = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        pass  # DNS-native, no SSRF surface

    def is_configured(self) -> bool:
        return True
```

**raw_stats shape:**
```python
{
    "asn": "AS23028",
    "prefix": "216.90.108.0/24",
    "country": "US",
    "registry": "arin",
    "allocated": "1998-09-25",
    "as_name": "TEAM-CYMRU, US",
}
```

**Note on `ip-api.com` overlap:** The existing `IPApiAdapter` already returns `as` (ASN number) and `asname` in its `raw_stats`. The `ASNAdapter` provides BGP-level precision: prefix, registry, allocation date, and peer ASNs — context not available from ip-api.com. These are complementary, not redundant. The analyst sees both.

---

## Annotations Removal: All Touchpoints

This is a destructive change. Every file that imports or uses `AnnotationStore` must be modified. Full touchpoint map:

### Python — Files to Modify or Remove

| File | Change Type | Detail |
|------|-------------|--------|
| `app/annotations/__init__.py` | **Delete module** | Empty init file |
| `app/annotations/store.py` | **Delete module** | AnnotationStore class |
| `app/routes.py` | **Modify** | Remove: `from app.annotations.store import AnnotationStore`, all AnnotationStore() calls, `annotations_map` variable, `annotations_map=annotations_map` template arg, `annotations=annotations` in ioc_detail, 3 API routes (`/api/ioc/.../notes`, `/api/ioc/.../tags`, `/api/ioc/.../tags/<tag>`) |

### TypeScript — Files to Remove

| File | Change Type | Detail |
|------|-------------|--------|
| `app/static/src/ts/modules/annotations.ts` | **Delete module** | Notes + tags UI logic |

### Templates — Files to Modify

| File | Change Type | Detail |
|------|-------------|--------|
| `app/templates/results.html` | **Modify** | Remove: tag display on cards, tag filter bar, `annotations_map` variable references |
| `app/templates/ioc_detail.html` | **Modify** | Remove: notes textarea, tags section, annotation-related JS calls |

### TypeScript Entry Point

| File | Change Type | Detail |
|------|-------------|--------|
| `app/static/src/ts/main.ts` | **Modify** | Remove `annotations.ts` import/initialization |

### Tests to Remove

- All unit tests in `tests/unit/test_annotations_store.py` (or equivalent)
- All E2E tests testing notes/tags UI
- Integration tests calling `/api/ioc/.../notes` and `/api/ioc/.../tags`

**Impact on detail page:** `ioc_detail()` in `routes.py` passes `annotations=annotations` to `ioc_detail.html`. After removal, this variable disappears from both the route and template. The graph and tabbed provider results remain unchanged.

---

## Data Flow Changes

### Existing Flow (v6.0)

```
POST /analyze
   -> run_pipeline()
   -> AnnotationStore().get_all_for_ioc_values()   [READ: annotations for tag display]
   -> render results.html with annotations_map

GET /ioc/<type>/<value>
   -> CacheStore.get_all_for_ioc()                  [READ: cached results]
   -> AnnotationStore().get()                        [READ: notes + tags]
   -> render ioc_detail.html with annotations

POST /api/ioc/.../notes                             [WRITE: save notes]
POST /api/ioc/.../tags                              [WRITE: add tag]
DELETE /api/ioc/.../tags/<tag>                      [WRITE: remove tag]
```

### New Flow (v7.0)

```
POST /analyze
   -> run_pipeline()
   -> render results.html                            [annotations_map REMOVED]

GET /ioc/<type>/<value>
   -> CacheStore.get_all_for_ioc()                  [unchanged]
   -> render ioc_detail.html                         [annotations REMOVED]

[notes/tags API routes: ALL DELETED]
```

### Provider Lookup Flow (same as before, new providers added)

```
EnrichmentOrchestrator.enrich_all(job_id, iocs)
   -> for each ioc:
        providers = registry.providers_for_type(ioc.type)
        for provider in providers:
            result = provider.lookup(ioc)           [new: DNSBL, ThreatFeed, RDAP, ASN]
            cache.set(ioc.value, provider.name, result)
```

---

## SSRF Allowlist Changes Required

`app/config.py` `ALLOWED_API_HOSTS` must be updated:

| New Entry | Provider | Notes |
|-----------|----------|-------|
| `feodotracker.abuse.ch` | ThreatFeedAdapter | HTTP bulk feed |
| `rdap.org` | RDAPAdapter | Bootstrap RDAP service |

DNS-based adapters (DNSBLAdapter, ASNAdapter) do NOT require allowlist entries — they use port 53 directly and have no SSRF surface, matching the DnsAdapter pattern.

**RDAP redirect concern:** If `rdap.org` issues a 302 redirect to registry-specific servers (e.g., `rdap.verisign.com`), the allowlist cannot enumerate all possible registry hostnames. Recommended resolution: test empirically during implementation. If `rdap.org` proxies responses (likely), one entry suffices. If it redirects, consider disabling RDAP domain lookups and restricting to IP-only via a known set of RIR RDAP servers (ARIN, RIPE, APNIC, LACNIC, AFRINIC — 5 known hostnames).

---

## Recommended Project Structure (New Files Only)

```
app/enrichment/adapters/
├── dnsbl.py          # NEW: DNSBLAdapter (IP+domain DNSBL via DNS)
├── threat_feed.py    # NEW: ThreatFeedAdapter (Feodo C2 bulk JSON)
├── rdap.py           # NEW: RDAPAdapter (domain+IP registration via HTTP)
└── asn.py            # NEW: ASNAdapter (IP ASN/BGP via DNS)

app/enrichment/
└── setup.py          # MODIFY: add 4 new register() calls
app/config.py         # MODIFY: add 2 new ALLOWED_API_HOSTS entries
app/routes.py         # MODIFY: strip all AnnotationStore references + 3 API routes
app/annotations/      # DELETE: entire module
app/static/src/ts/modules/
└── annotations.ts    # DELETE: annotations TypeScript module
```

---

## Architectural Patterns

### Pattern 1: DNS-Native Provider (for DNSBLAdapter and ASNAdapter)

**What:** Use `dnspython` for all query logic — no HTTP, no `http_safety.py`, `allowed_hosts` accepted but unused.
**When to use:** Any provider that communicates via DNS (port 53) rather than HTTP/HTTPS.
**Precedent:** `DnsAdapter` (dns_lookup.py) — already in codebase.

**Key implementation notes:**
- Create a fresh `dns.resolver.Resolver(configure=True)` per `lookup()` call — no shared state
- Set `resolver.lifetime = 5.0` for consistent timeout
- `NXDOMAIN` = negative result (not listed) — never an error
- `SERVFAIL` / timeout = `EnrichmentError` or `lookup_errors` entry (partial failure)

### Pattern 2: HTTP Bulk-Feed Provider (for ThreatFeedAdapter)

**What:** Download a full feed JSON file, extract the relevant record by set membership or dict lookup.
**When to use:** Provider has no per-IOC query API, only bulk downloads.
**Trade-off:** Full feed downloaded on each cache-miss. Acceptable for local single-user tool with 24h cache TTL.

**Key implementation notes:**
- Follow standard HTTP safety pattern: `TIMEOUT`, `read_limited()`, `validate_endpoint()`, `allow_redirects=False`
- Parse feed into a `dict[str, dict]` keyed by IP for O(1) lookups after parsing
- If feed body exceeds `MAX_RESPONSE_BYTES` (1 MB), return `EnrichmentError` — do NOT increase the cap for this provider
- Feodo feed is ~100KB — within existing 1 MB cap with room to grow

### Pattern 3: HTTP REST Provider (for RDAPAdapter)

**What:** Standard single-resource HTTP GET, parse structured JSON response.
**When to use:** Provider has a per-resource REST endpoint.
**Precedent:** Every existing HTTP adapter (ip_api.py, crtsh.py, hashlookup.py, etc.)

**Key implementation notes:**
- Follow standard HTTP safety pattern exactly
- RDAP response is deeply nested — extract fields defensively with `.get()` at every level
- `events` is a list — must filter by `eventAction`, not index by position
- `entities` is a list — filter by `roles` list containing `"registrar"`
- `vcard` inside entities is a nested array-of-arrays format — use `vcardArray` carefully

---

## Build Order

The four providers are largely independent of each other. The build order is driven by:
1. Annotations removal first — eliminates dead code before adding new code
2. DNS-native providers first — zero new dependencies, same pattern as existing `DnsAdapter`
3. HTTP providers after — require SSRF allowlist changes

**Recommended phase order:**

| Phase | Work | Rationale |
|-------|------|-----------|
| 1 | Annotations removal | Clean slate — removes ~500 LOC, 3 API routes, 1 TS module, DB coupling |
| 2 | ASNAdapter | Pure DNS, no new deps, supplements existing ip-api.com data |
| 3 | DNSBLAdapter | Pure DNS, verdict-producing (first new malicious-capable zero-auth provider) |
| 4 | ThreatFeedAdapter | HTTP bulk-feed, SSRF allowlist change, new download pattern |
| 5 | RDAPAdapter | HTTP REST, SSRF concern to resolve, most complex JSON parsing |

**Reasoning:**
- Phase 1 (annotations) is purely destructive — low risk of breaking enrichment flow, high payoff in code clarity
- Phases 2-3 (DNS providers) can be built and tested without any allowlist or HTTP changes
- Phase 4 (threat feed) introduces the bulk-download pattern — new territory but simpler JSON than RDAP
- Phase 5 (RDAP) is last because it has the most uncertainty (redirect behavior, nested JSON, registry variability)

---

## Anti-Patterns

### Anti-Pattern 1: Per-IOC Feed Download

**What people do:** Call `requests.get(FEODO_FEED_URL)` inside every `ThreatFeedAdapter.lookup()` call regardless of cache status.
**Why it's wrong:** Each enrichment batch downloads the full feed N times (once per IP IOC). At 100KB per download, a 20-IP paste downloads 2MB unnecessarily.
**Do this instead:** Accept CacheStore's TTL as the feed refresh mechanism. Each unique IOC is only looked up once per TTL window. The feed is downloaded once per cache-miss per IOC, not once per IOC per request.

### Anti-Pattern 2: Treating NXDOMAIN as an Error in DNSBL

**What people do:** Catch `dns.resolver.NXDOMAIN` and return `EnrichmentError`.
**Why it's wrong:** NXDOMAIN in a DNSBL context means "not listed" — it is the expected clean-result response. Treating it as an error produces false negatives and floods error logs.
**Do this instead:** NXDOMAIN in DNSBL queries = clean result. Only `SERVFAIL`, `NoNameservers`, and `Timeout` are errors.

### Anti-Pattern 3: Allowing Unlimited Redirects for RDAP

**What people do:** Set `allow_redirects=True` without validation to handle RDAP bootstrap redirects.
**Why it's wrong:** Violates SEC-06. A malicious RDAP response could redirect to an internal network host, bypassing the SSRF allowlist.
**Do this instead:** Either (a) use `rdap.org` if it proxies without redirecting, or (b) allow exactly one redirect to a hostname that matches a whitelist of known RIR RDAP servers. Never allow unlimited redirects.

### Anti-Pattern 4: Using `innerHTML` for RDAP/DNSBL Results

**What people do:** Insert registration data or DNSBL listings directly into DOM with innerHTML.
**Why it's wrong:** RDAP responses include registrar names and nameservers from untrusted third parties (registries, registrars). These could contain XSS payloads.
**Do this instead:** The existing `createContextRow()` / `textContent` pattern already handles this correctly. Use it.

### Anti-Pattern 5: Module-Level Mutable State for Feed Cache

**What people do:** Add a module-level `_feed_cache: dict = {}` and `_feed_loaded_at: datetime` to ThreatFeedAdapter to avoid repeated downloads.
**Why it's wrong:** Creates shared mutable state across threads (Flask runs in threaded mode). Requires a lock, a TTL check, and a manual invalidation mechanism. All this complexity exists to optimize a 100KB download that CacheStore already handles.
**Do this instead:** Let CacheStore handle cache invalidation. Keep adapters stateless.

---

## Integration Points

### New Providers → ProviderRegistry

All four adapters registered in `app/enrichment/setup.py` in `build_registry()`:

```python
# v7.0: DNSBL, Threat Feed, RDAP, ASN
registry.register(DNSBLAdapter(allowed_hosts=allowed_hosts))
registry.register(ThreatFeedAdapter(allowed_hosts=allowed_hosts))
registry.register(RDAPAdapter(allowed_hosts=allowed_hosts))
registry.register(ASNAdapter(allowed_hosts=allowed_hosts))
```

No other orchestrator or route code changes for enrichment.

### New Providers → Frontend Rendering

New providers return `raw_stats` in the same shape as existing context providers. The existing `createContextRow()` function in the TypeScript layer handles arbitrary `raw_stats` key-value pairs. No TypeScript changes are needed to display the new provider data.

**Verdict-producing providers (DNSBL, ThreatFeed)** will participate in the `computeWorstVerdict()` consensus logic automatically — no TypeScript changes needed.

**Context-only providers (RDAP, ASN)** will use the existing `CONTEXT_PROVIDERS` set pattern — add their names to `CONTEXT_PROVIDERS` in the orchestrator or frontend to route them through `createContextRow()`.

### Annotations Removal → `ioc_detail` Route

After removal, `ioc_detail()` no longer needs `AnnotationStore`. The route simplifies to:

```python
@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
def ioc_detail(ioc_type, ioc_value):
    cache = CacheStore()
    provider_results = cache.get_all_for_ioc(ioc_value, ioc_type)
    # [graph node/edge building unchanged]
    return render_template("ioc_detail.html", ...)  # annotations vars removed
```

### Annotations Removal → TypeScript Module Count

14 modules → 13 modules. `annotations.ts` deleted, `main.ts` updated to remove its initialization call.

---

## Sources

- Team Cymru IP-to-ASN DNS service: https://www.team-cymru.com/ip-asn-mapping (HIGH confidence — verified format and free-forever policy)
- SURBL implementation guidelines: https://surbl.org/guidelines (HIGH confidence — verified query format for domains)
- Spamhaus ZEN DNSBL: https://www.spamhaus.org/blocklists/zen-blocklist/ (HIGH confidence — verified zone name and return code format)
- Spamhaus fair use policy: https://www.spamhaus.org/blocklists/dnsbl-fair-use-policy/ (MEDIUM confidence — page failed to load, policy stated as non-commercial fair use from secondary sources)
- Feodo Tracker blocklist: https://feodotracker.abuse.ch/blocklist/ (HIGH confidence for URL/format, MEDIUM confidence for feed activity — currently empty due to takedowns)
- RDAP.org bootstrap service: https://about.rdap.org/ (MEDIUM confidence — rate limits documented, redirect vs proxy behavior unconfirmed)
- OpenRDAP API: https://openrdap.org/api (MEDIUM confidence — confirmed redirect behavior, not proxy)
- RFC 9083 (RDAP JSON responses): https://datatracker.ietf.org/doc/rfc9083/ (HIGH confidence — authoritative spec for response structure)
- Existing SentinelX codebase: `app/enrichment/adapters/dns_lookup.py`, `ip_api.py`, `crtsh.py`, `hashlookup.py` (HIGH confidence — direct code inspection)

---
*Architecture research for: SentinelX v7.0 Free Intel*
*Researched: 2026-03-15*
