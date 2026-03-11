# Project Research Summary

**Project:** SentinelX v6.0 — Analyst Experience Expansion
**Domain:** Threat intelligence enrichment platform — zero-auth deep analysis
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

SentinelX v6.0 expands a working 8-provider threat intelligence tool into a richer analyst workstation platform by adding zero-auth enrichment depth, local offline databases, and a deeper per-IOC analysis experience. The core insight from research is that the analyst complaint ("can't we do more without API keys?") has a concrete, high-quality answer: seven additional data sources covering IP geolocation/ASN, reverse DNS, live DNS records, certificate transparency, NSRL known-good hash detection, and passive DNS pivoting — all zero-auth at query time, all fitting the existing Provider Protocol without model changes. After v6.0, a fully configured instance with zero API keys rivals what VirusTotal shows on its free public lookup page for most triage scenarios.

The recommended approach is additive and low-risk: all new capabilities are new Provider Protocol adapter files plus one `register()` call each. The existing orchestrator, cache, and TypeScript rendering pipeline are unchanged. The three new Python libraries required (`dnspython`, `geoip2`, `ipwhois`) have verified compatibility with the Python 3.10 baseline. The one significant setup wrinkle is GeoLite2: the databases are free but require a MaxMind account signup and cannot be bundled in the repository — this must be surfaced honestly in UX as "optional enhanced enrichment requiring one-time setup" rather than presented as seamlessly zero-auth.

The key risks are operational rather than architectural: GeoLite2 staleness (MaxMind EULA requires deletion of databases older than 30 days after a new release), DNS lookup timeouts stalling the ThreadPoolExecutor (mitigated by `dnspython` with explicit `lifetime=5.0` and `timeout=2.0`), and certificate transparency response volume (crt.sh returns thousands of records for popular domains — must be capped and aggregated before display). The security posture remains strong: new providers follow existing SSRF allowlist patterns, GeoIP lookups are offline (no HTTP), and DNS resolution does not introduce new SSRF surface. The `ipwhois` RDAP path should be deferred because its dynamic RIR endpoint URLs are incompatible with the static SSRF allowlist model.

## Key Findings

### Recommended Stack

The v5.0 stack (Python 3.10 + Flask 3.1, TypeScript + esbuild, Tailwind, SQLite) is not changing. Three libraries are additive for v6.0 zero-auth enrichment, all verified against PyPI and official documentation at Python 3.10+ compatibility.

**Core new libraries:**
- `dnspython==2.8.0`: Active DNS resolution (A, AAAA, MX, NS, TXT, PTR) — the only option for MX/TXT/NS queries; thread-safe with configurable `lifetime`/`timeout`; zero external dependencies
- `geoip2==5.2.0`: Offline IP geolocation (country, city, ASN, org) from local MaxMind `.mmdb` files — fully offline at query time; compatible with existing `requests==2.32.5`; official MaxMind Python client
- `ipwhois==1.3.0`: RDAP-based IP-to-ASN and netblock data — **deferred from v6.0** due to SSRF allowlist incompatibility with dynamic RIR endpoint URLs

**No new library needed for certificate transparency:** direct `requests.get()` to the crt.sh JSON API (`https://crt.sh/?q=<domain>&output=json`) covers all triage use cases. `pycrtsh` adds `psycopg2-binary` + `lxml` overhead for no additional benefit.

**Database dependencies (not Python packages):**
- `GeoLite2-City.mmdb` (~70 MB): country, region, city, lat/lon — stored at `~/.sentinelx/geoip/`
- `GeoLite2-ASN.mmdb` (~9 MB): ASN + organization name — stored at `~/.sentinelx/geoip/`
- Requires free MaxMind account registration; license key used for download only; runtime lookups are fully offline

### Expected Features

**Must have (table stakes) — analysts expect these in any "robust" IP/domain lookup tool:**
- GeoIP + ASN + ISP enrichment (ip-api.com zero-auth for instant country/city/ISP/ASN/proxy flags)
- Reverse DNS / PTR record lookup (standard IP context, zero network dependency beyond system resolver)
- Live DNS resolution for domains (A/MX/NS/TXT records via Cloudflare DoH — zero-auth)
- NSRL known-good hash detection (CIRCL hashlookup — reduces false-positive workload significantly)
- Enhanced Shodan card rendering (ports/CVEs/hostnames already in `raw_stats` — frontend-only, zero backend)

**Should have (competitive differentiators):**
- GeoIP proxy/VPN/hosting detection flags (ip-api.com includes `proxy`, `hosting`, `mobile` booleans at no extra cost)
- Certificate transparency via crt.sh (domain cert history + subdomain enumeration from SANs — MEDIUM complexity, powerful for infrastructure analysis)
- DNS record depth: MX, NS, TXT/SPF/DMARC (extends DNS provider — high value for phishing triage)
- ThreatMiner passive DNS (IP/domain/hash — the feature that turns SentinelX from lookup tool to investigation tool — MEDIUM complexity, 10 req/min rate limit)
- "KNOWN GOOD" badge treatment for CIRCL trust score >= 70 (unique differentiator — no competitor offers this)

**Defer to future milestone:**
- STIX/TAXII export (niche for triage tool; current JSON export covers most MISP workflows)
- Provider capability matrix UI in settings (low analyst data value)
- urlscan.io integration (URL screenshot/DOM scanning; requires API key for reliable access)
- WHOIS/RDAP domain registration data (explicitly out of scope in PROJECT.md — privacy redaction makes 90%+ of gTLD WHOIS useless post-2018)
- AI/LLM verdict explanation (hallucination risk, external service dependency, violates "no opaque scores" principle)
- `ipwhois` ASN enrichment (SSRF allowlist incompatibility — defer to Cymru WHOIS TCP approach in a later phase)

### Architecture Approach

All new capabilities integrate through the existing Provider Protocol (`typing.Protocol`) as new adapter files with a single `register()` call in `setup.py`. The orchestrator, registry, cache, and TypeScript pipeline are unchanged. Local providers (DNS via dnspython, GeoIP via geoip2) differ from remote providers only in that they skip `http_safety` SSRF validation (no outbound HTTP) and have near-instant execution. Remote zero-auth providers (crt.sh, ip-api.com) follow the existing ShodanAdapter pattern. Two new Flask routes are needed for the deeper per-IOC analysis view (`GET /ioc/<value>` and `GET /api/graph/<job_id>`), and a new `NoteStore` SQLite module parallel to `CacheStore` handles analyst annotations.

**Major new components:**
1. **Zero-auth provider adapters** (3-4 files): `dns_resolver.py`, `geoip.py`, `cert_transparency.py` — each ~150-250 LOC, following existing ShodanAdapter pattern
2. **NoteStore** (`app/notes/store.py`): SQLite `ioc_notes` table, separate from cache (notes survive cache clear), stores analyst tags and free-text notes per IOC
3. **Per-IOC detail page** (`GET /ioc/<value>`): server-rendered tabbed view aggregating all cached enrichment + local enrichment + notes; allows bookmarkable URLs for analyst ticket sharing
4. **Graph visualization** (`app/static/vendor/cytoscape.min.js` + `modules/graph.ts`): Cytoscape.js self-hosted (not CDN — CSP constraint), renders IOC-to-provider relationship topology; lazy-loaded within detail page

### Critical Pitfalls

1. **GeoLite2 license and staleness** — Never bundle `.mmdb` files in the repo (license violation) and never use `maxminddb-geolite2` from PyPI (unmaintained, stale database). Implement `is_configured()` to check `os.path.isfile(path)`. Display "GeoIP data from [file date]" on every result. Check file modification time at adapter init and warn if older than 30 days (MaxMind EULA requires deletion after 30 days post-release).

2. **DNS lookups blocking ThreadPoolExecutor** — Never use `socket.getaddrinfo()` (not thread-safe, no timeout). Create one module-level `dns.resolver.Resolver` instance with `lifetime=5.0` and `timeout=2.0`. Treat `NXDOMAIN` and `NoAnswer` as `verdict="no_data"` (not errors). Treat `dns.exception.Timeout` as `EnrichmentError`. Validate with a simulated-timeout unit test and a 50-domain batch timing test.

3. **Certificate transparency response volume** — crt.sh returns thousands of records for popular domains. Cap adapter response processing at 100 records. Aggregate to "X unique subdomains, Y certificates, date range" — never display raw certificate list. Apply existing `read_limited()` SEC-05 pattern. Treat crt.sh 504 as soft failure (`verdict="no_data"`).

4. **Zero-auth `is_configured()` must check actual readiness** — A provider that returns `is_configured() = True` unconditionally when its MMDB is missing will produce `EnrichmentError("MMDB file not found")` in normal result sets. `is_configured()` must call `os.path.isfile(configured_path)`, not just check config key presence.

5. **ipwhois SSRF allowlist incompatibility** — `ipwhois` makes RDAP queries to dynamic RIR endpoints (ARIN, RIPE, APNIC) that vary by IP range and include redirects. These cannot be statically allowlisted in `ALLOWED_API_HOSTS`. Defer ASN enrichment; extract what's available from existing Shodan `raw_stats`, or research a Cymru WHOIS TCP approach for a later phase.

## Implications for Roadmap

Based on research, the natural phase structure follows three dependency boundaries: (1) IP enrichment providers are independent of domain/hash providers, (2) domain providers (DNS, crt.sh) can be built in parallel with IP providers, (3) the per-IOC detail page depends on both provider sets and NoteStore, and (4) graph visualization depends on the detail page.

### Phase 1: Zero-Auth IP Enrichment + NSRL Known-Good

**Rationale:** Directly addresses the primary analyst complaint. All four deliverables fit the existing Provider Protocol with zero model changes, except for the new `known_good` verdict type required by CIRCL. Enhanced Shodan rendering is frontend-only and can be completed independently within this phase. These are the highest user-value, lowest implementation-risk items in the feature set.

**Delivers:** Country/city/ASN/ISP/proxy+hosting flags for all IP IOCs (via ip-api.com), PTR hostname for all IP IOCs (system resolver via dnspython), NSRL known-good detection for hashes (CIRCL hashlookup), and full Shodan data visible in UI (ports, CVEs, hostnames).

**Addresses:** GeoIP + ASN, rDNS, CIRCL hashlookup, Enhanced Shodan rendering (all P1 from FEATURES.md)

**Avoids:** GeoLite2 bundling pitfall (use ip-api.com, not MaxMind, for IP geolocation in this phase — MaxMind offline approach is a Phase 1 optional add-on), zero-auth `is_configured()` pitfall, DNS thread-pool starvation (PTR via dnspython with timeout guards)

**New verdict:** `known_good` verdict level — requires update to verdict severity ordering in both backend models and frontend badge rendering; budget for this cross-cutting change early

### Phase 2: Domain Intelligence (DNS + Certificate Transparency)

**Rationale:** Domains are currently the weakest IOC type in zero-auth context — they get only the 8 existing key-based providers. DNS resolution and cert transparency together transform domain cards from near-opaque to genuinely informative. Both providers cover `domain` IOC type exclusively and can be built in parallel without conflicts.

**Delivers:** Live A/AAAA/MX/NS/TXT (SPF, DMARC) records for domain IOCs (Cloudflare DoH), cert history + subdomain enumeration from SANs for domain IOCs (crt.sh). SSRF allowlist additions: `1.1.1.1` (Cloudflare DoH) and `crt.sh`.

**Addresses:** DNS Resolution Provider, crt.sh Certificate Provider (P2 from FEATURES.md)

**Avoids:** CT response volume pitfall (aggregate before display — design UI shape before writing adapter), `read_limited()` application to crt.sh, crt.sh 504 soft failure handling

**Note:** `crt.sh` queries use the existing `requests` dependency; no new library needed. Cloudflare DoH also uses `requests`.

### Phase 3: Infrastructure Pivoting (ThreatMiner Passive DNS)

**Rationale:** ThreatMiner is the most architecturally complex new provider: multiple endpoints per IOC type (different `rt=` parameter values for passive DNS vs related hashes vs subdomains), a strict 10 req/min rate limit requiring graceful throttling, and richer response data needing more complex rendering. It is also the highest-value differentiator — passive DNS pivoting is what distinguishes a "lookup tool" from an "investigation tool." Build after Phase 1 and 2 stabilize.

**Delivers:** Passive DNS history (what other domains pointed to this IP? what IPs has this domain used?), related malware samples for hashes, related infrastructure context for IPs and domains. Covers IP, domain, and hash IOC types.

**Addresses:** ThreatMiner Passive DNS Provider (P2 from FEATURES.md)

**Avoids:** Rate limit hang (10 req/min — implement per-request throttling or exponential backoff, not silent blocking), IOC-type-specific endpoint routing (different `rt=` values per type)

### Phase 4: Deeper Analysis View + Analyst Notes

**Rationale:** Once the zero-auth provider set is complete (Phases 1-3), the per-IOC detail page becomes the integration surface. This phase adds the `GET /ioc/<value>` route (server-rendered tabbed view aggregating all cached enrichment), NoteStore (analyst annotations), and graph visualization (Cytoscape.js topology). These are UI and persistence features that depend on all providers being present to show full value.

**Delivers:** Bookmarkable per-IOC detail page with tabbed sections (Network, DNS, Certificates, Threat Intel, Graph, Notes), analyst tag and note persistence in `~/.sentinelx/notes.db`, IOC-to-provider relationship graph via Cytoscape.js (self-hosted for CSP compliance).

**Addresses:** Per-IOC deep analysis views, IOC tagging and notes, relationship graph (from ARCHITECTURE.md)

**Avoids:** CDN Cytoscape.js pitfall (self-host at `app/static/vendor/` — no CSP change needed), `innerHTML` for IOC values in graph nodes (Cytoscape SVG/Canvas rendering is inherently safe), URL path IOC value injection (validate through normalization pipeline before any use)

### Phase Ordering Rationale

- Phases 1 and 2 are largely independent and could be parallelized by a team; for a solo developer, Phase 1 first because GeoIP + PTR (P1) has higher analyst impact than DNS/CT (P2)
- Phase 3 (ThreatMiner) should not precede Phase 2 (DNS/CT) because its response rendering complexity is easier to tackle after the simpler DNS adapter patterns are established
- Phase 4 (detail page) must come last — it is the integration surface for all prior phases and has little value before provider data exists
- The `known_good` verdict introduced in Phase 1 is the only cross-cutting change that touches both backend models and frontend badge rendering; address it first within Phase 1 to avoid retrofitting later
- GeoLite2 offline GeoIP (MaxMind) can be treated as a Phase 1 optional enhancement — ip-api.com covers the immediate zero-auth need; GeoLite2 adds offline capability for air-gapped deployments and richer city-level data

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 3 (ThreatMiner):** Rate limit behavior (10 req/min) needs concrete throttling strategy — decide whether to use a semaphore, a token bucket, or a simple sleep-based approach compatible with the ThreadPoolExecutor model. ThreatMiner has no SLA; downtime handling needs definition.
- **Phase 4 (Graph visualization):** Cytoscape.js layout algorithm selection (which of the 10+ built-in layouts renders a star/bipartite IOC-to-provider graph most clearly) needs a spike. NoteStore tag search UI is underspecified — decide between a dedicated search page and inline filtering before implementation.

Phases with standard patterns (skip research-phase):

- **Phase 1 (IP enrichment + NSRL):** All four adapters follow the existing ShodanAdapter pattern. ip-api.com, dnspython PTR, and CIRCL hashlookup are well-documented. The `known_good` verdict is additive and well-defined.
- **Phase 2 (DNS + CT):** Cloudflare DoH is a standard JSON HTTP call. crt.sh response aggregation is a data-shaping problem, not an architecture problem. Both follow documented adapter patterns in ARCHITECTURE.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI and official docs. Python 3.10 compatibility confirmed for all three new libraries. Version conflicts checked against existing `requirements.txt`. |
| Features | HIGH | Zero-auth service endpoints verified live. Analyst workflow patterns sourced from multiple vendor guides (ANY.RUN, SentinelOne, SOCRadar). Competitor feature matrix cross-checked against VirusTotal public docs. |
| Architecture | HIGH | Provider Protocol integration pattern verified against existing ShodanAdapter (zero-auth reference). SSRF allowlist conflict for ipwhois identified from direct codebase audit. Cytoscape.js vanilla JS + self-hosting confirmed. |
| Pitfalls | HIGH | MaxMind license terms confirmed from official MaxMind blog (2019 changes) and EULA. dnspython thread safety confirmed from official docs. Python-whois rate limit and hang issues confirmed from GitHub issue tracker. |

**Overall confidence:** HIGH

### Gaps to Address

- **ip-api.com vs GeoLite2 for Phase 1:** Research recommends ip-api.com (zero-auth, no setup) for immediate impact. MaxMind GeoLite2 adds offline capability. The plan should decide whether Phase 1 implements both (ip-api.com as primary, GeoLite2 as optional offline fallback) or one at a time. This is a scope/ordering decision, not a technical uncertainty.

- **ThreadPoolExecutor `max_workers` for DNS:** The existing executor handles 8 remote providers. Adding DNS lookups that can be near-instant or block for 5 seconds introduces a new profile. The plan should decide whether to increase `max_workers` globally, add a DNS-specific executor, or accept shared pool (acceptable for typical 1-20 IOC batch sizes).

- **ThreatMiner throttling approach:** 10 req/min is a hard community-reported limit with no SLA. Options are: (a) token bucket in the adapter, (b) semaphore limiting concurrent ThreatMiner lookups, or (c) a dedicated single-worker executor making ThreatMiner sequential. Option (c) is simplest but makes ThreatMiner always the last provider to complete.

- **Cytoscape.js vendoring:** ARCHITECTURE.md references v3.33.0 (July 2025). The plan needs a `make vendor` or `make vendor-install` target. Confirm the download source URL and add `cytoscape.min.js` to `.gitignore`.

## Sources

### Primary (HIGH confidence)
- [dnspython PyPI + ReadTheDocs](https://dnspython.readthedocs.io/en/latest/) — v2.8.0 confirmed, thread safety, `Resolver` lifecycle, exception hierarchy
- [geoip2 ReadTheDocs](https://geoip2.readthedocs.io/) — v5.2.0 confirmed, Reader creation cost, `AddressNotFoundError`
- [MaxMind GeoLite2 developer docs](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/) — free database confirmed; account + license key required for download; runtime offline
- [MaxMind GeoLite2 EULA](https://www.maxmind.com/en/geolite2/eula) — 30-day deletion requirement after new release
- [MaxMind blog — 2019 license changes](https://blog.maxmind.com/2019/12/significant-changes-to-accessing-and-using-geolite2-databases/) — account requirement since Dec 30, 2019
- [CIRCL hashlookup service](https://www.circl.lu/services/hashlookup/) — no auth required; NSRL + OS packages; trust score field confirmed
- [Cloudflare DoH API](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/) — no auth for DNS queries; JSON format confirmed
- [ip-api.com documentation](https://ip-api.com/) — no key required; 45 req/min; proxy/hosting/mobile fields confirmed
- [Cytoscape.js official site](https://js.cytoscape.org/) — CDN availability, vanilla JS usage, built-in graph algorithms; v3.33.0 release July 2025
- [SentinelX codebase audit] — Provider Protocol, ShodanAdapter zero-auth pattern, CacheStore, SSRF allowlist (`http_safety.py`), existing `ALLOWED_API_HOSTS`

### Secondary (MEDIUM confidence)
- [ThreatMiner API reference](https://www.threatminer.org/api.php) — no-auth public API; 10 req/min rate limit; endpoint parameters; community-operated, no formal SLA
- [crt.sh architecture and HTTP API](https://crt.sh/) — zero-auth JSON via `?output=json`; no formal rate limits; 504 behavior under load
- [ANY.RUN SOC triage analyst guide](https://any.run/cybersecurity-blog/triage-analyst-guide/) — analyst 2-minute triage workflow, escalation pattern
- [SOCRadar Top 20 Free Cybersecurity APIs](https://socradar.io/blog/top-20-free-apis-for-cybersecurity/) — zero-auth API landscape survey
- [ipwhois RDAP documentation](https://ipwhois.readthedocs.io/en/latest/RDAP.html) — RDAP endpoint behavior; SSRF conflict identified from ARCHITECTURE.md codebase analysis

### Tertiary (MEDIUM-LOW confidence)
- [ipwho.is API](https://www.ipwho.org/) — alternative zero-auth GeoIP; viable backup if ip-api.com rate limits become a problem
- [Cytoscape.js 3.33.0 release blog](https://blog.js.cytoscape.org/2025/07/28/3.33.0-release/) — active maintenance confirmed 2025
- [DNS rebinding SSRF bypass pattern](https://www.clear-gate.com/blog/ssrf-with-dns-rebinding-2/) — TOCTOU pattern; low risk for SentinelX given DNS adapters do not make HTTP to resolved IPs

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*
