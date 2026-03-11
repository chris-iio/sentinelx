# Feature Research

**Domain:** Threat intelligence enrichment platform (SOC analyst triage tool) — v6.0 Analyst Experience
**Researched:** 2026-03-11
**Confidence:** HIGH (zero-auth services verified via official docs; analyst workflow patterns from multiple sources)

---

## Context: What Already Exists

SentinelX v5.0 ships with:
- IOC extraction (8 types: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE)
- 8 enrichment providers (VirusTotal, MalwareBazaar, ThreatFox, Shodan InternetDB, URLhaus, OTX, GreyNoise, AbuseIPDB)
- 1 zero-auth provider (Shodan InternetDB — ports, vulns, tags for IPs only)
- SQLite enrichment cache with configurable TTL
- JSON/CSV/clipboard export
- Card-based results with verdict filtering
- Provider context fields (VT top detections/reputation)

**The analyst's complaint:** "Can't we do more without API keys?" and "Make this more robust like VirusTotal."

This research addresses: what to add in v6.0 to make the tool richer and competitive with paid platforms, with a focus on zero-auth enrichment that works with zero account setup.

---

## Zero-Auth Enrichment: What Is Actually Available

This is the highest-priority research question. All entries verified against official documentation.

### Confirmed Zero-Auth APIs (No Key, No Registration Required)

| Service | Endpoint Pattern | Data Returned | Rate Limit | IOC Types |
|---------|-----------------|--------------|-----------|-----------|
| ip-api.com | `http://ip-api.com/json/{ip}` | Country, region, city, lat/lon, ISP, org, ASN, timezone, proxy/VPN/hosting flags | 45 req/min | IPv4, IPv6 |
| ipwho.is | `https://ipwho.is/{ip}` | Country, city, lat/lon, ISP, ASN, org | 60 req/60s | IPv4, IPv6 |
| Shodan InternetDB | `https://internetdb.shodan.io/{ip}` | Open ports, CVEs, hostnames, CPEs, tags | ~10k/s burst | IPv4, IPv6 (already built) |
| crt.sh | `https://crt.sh/?q={domain}&output=json` | All SSL/TLS certs issued for domain, subdomains in SANs | Unspecified | domain |
| CIRCL hashlookup | `https://hashlookup.circl.lu/lookup/{algo}/{hash}` | NSRL match, filename, OS, product, trust score (0-100) | Best-effort | MD5, SHA1, SHA256 |
| Cloudflare DoH | `https://1.1.1.1/dns-query?name={domain}&type=A` (Accept: application/dns-json) | DNS A/MX/NS/TXT records, TTL | Unspecified | domain, URL |
| Google DoH | `https://dns.google/resolve?name={domain}&type=A` | DNS A/MX/NS/TXT records | Unspecified | domain, URL |
| rDNS (PTR) | Python `socket.gethostbyaddr(ip)` via system resolver | Hostname for IP | Local resolver | IPv4, IPv6 |
| ThreatMiner | `https://api.threatminer.org/v2/domain.php?q={domain}&rt=2` | Passive DNS, related hashes, WHOIS, subdomains, reports | 10 req/min | IP, domain, hash |

**Confidence: HIGH** for Shodan InternetDB (already running), ip-api.com, CIRCL hashlookup, Cloudflare/Google DoH.
**Confidence: MEDIUM** for crt.sh (no formal rate limits documented), ThreatMiner (no formal SLA, community-operated).

### Note on WHOIS (Explicitly Out of Scope per PROJECT.md)

WHOIS/RDAP is ruled out in PROJECT.md ("high complexity, often privacy-redacted"). This stands. ICANN sunset WHOIS for gTLDs in 2025; RDAP is the successor but registration data is heavily redacted under GDPR. The zero-auth alternatives (ip-api.com for IP org/ASN, crt.sh for domain cert history) provide more actionable analyst data with less implementation complexity.

### Note on IPinfo (Requires Free Registration)

IPinfo provides unlimited free country-level geolocation + ASN with a free account token. Without a token, the public endpoint is capped at 1,000 req/day shared across all users on the same IP. Given ip-api.com provides equivalent data truly key-free at 45 req/min, ip-api.com is the better choice for the zero-auth tier.

---

## How Analysts Actually Work: Daily Workflow Patterns

From research into SOC workflows, ANY.RUN analyst guides, VirusTotal blog posts, and SOCRadar documentation.

**Tier 1 triage (first 2 minutes on an alert):**
1. Paste IOCs from alert/email/SIEM into a lookup tool
2. Check verdict across multiple providers — is this known-bad?
3. Check GeoIP/ASN — is this a cloud provider? TOR exit node? Expected country?
4. Check open ports — what services is this IP running? Does it match what the alert claims?
5. Check "noise" classification — is this just an internet scanner, not an actual threat?

**Deeper investigation (Tier 2 escalation):**
6. Check cert history — what other domains share this certificate or infrastructure?
7. Check passive DNS — what else has resolved to this IP? What IPs has this domain pointed to?
8. For hashes — is this file known-good (NSRL)? If yes, close the alert. If flagged, what malware family?
9. For URLs — what's the actual hosting infrastructure? Is this a known phishing pattern?
10. Cross-reference: if IP is flagged, pivot to domains that pointed to it.

**Key finding from research:** The average analyst spends 2-4 hours/day sifting through threat intelligence (per SOCRadar/ANY.RUN research). The highest-value features are those that eliminate pivot steps — getting from one IOC to related infrastructure without opening separate browser tabs. This is the definition of "robust" that the analyst expressed.

---

## Feature Landscape

### Table Stakes (Analysts Expect These for a "Robust" Tool)

These are the features analysts see in every major TI platform. Their absence makes SentinelX feel incomplete compared to VirusTotal, Shodan's web UI, or even basic lookup tools.

| Feature | Why Expected | Complexity | Dependency on Existing Architecture |
|---------|--------------|------------|--------------------------------------|
| GeoIP + ASN + ISP enrichment (zero-auth) | Every IP lookup tool shows country/ISP/ASN — it is the first thing analysts check on an IP alert. Currently SentinelX shows nothing until an API key is configured. | LOW | Fits as new Provider adapter (requires_api_key=False). ip-api.com zero-auth endpoint. ~200 LOC adapter. |
| Reverse DNS (PTR record) | Standard IP context — "what hostname is this IP known by?" — seen in every IP lookup tool. Needed for distinguishing cloud provider ranges from residential/VPN IPs. | LOW | New Provider adapter using Python socket.gethostbyaddr(). Zero network dependency beyond system resolver. ~100 LOC. |
| Live DNS resolution (A records at minimum) | "What does this domain currently resolve to?" — basic infrastructure check that analysts perform for every domain IOC. Currently absent. | LOW | New Provider adapter using Cloudflare DoH JSON API (zero-auth). ~150 LOC. |
| Known-good hash detection (CIRCL NSRL) | Analysts need to know "is this hash a legit Windows/macOS/Linux file before I escalate?" — false positives from hashes matching system files waste significant analyst time. | LOW | New Provider adapter (zero-auth). CIRCL hashlookup.circl.lu. ~150 LOC. |
| Enhanced Shodan card rendering | Shodan InternetDB already runs and collects ports, CVEs, hostnames, CPEs — but the UI only renders a verdict badge. Analysts cannot see the actual data without exporting. | LOW | Frontend-only change. Data already in raw_stats field of EnrichmentResult. No backend changes needed. |

**Confidence: HIGH** — These features are present in every platform compared (VirusTotal, Shodan web, GreyNoise web, ANY.RUN).

### Differentiators (Competitive Advantage)

Features that would make analysts prefer SentinelX over opening multiple browser tabs. These go beyond table stakes.

| Feature | Value Proposition | Complexity | Dependency on Existing Architecture |
|---------|-------------------|------------|--------------------------------------|
| GeoIP proxy/VPN/hosting detection flags | ip-api.com returns boolean `proxy`, `hosting`, `mobile` flags at no extra cost. "Is this a cloud provider IP?" and "Is this behind a proxy?" are the two most common analyst questions after country/ASN. Answers them instantly. | LOW | Part of GeoIP provider adapter — no extra requests needed, fields already in ip-api.com response. |
| Certificate transparency via crt.sh | For domain IOCs: shows all SSL/TLS certificates ever issued, including certificate issuance history and Subject Alternative Names (SANs). Reveals hidden subdomains, phishing lookalikes, and certificate abuse patterns. | MEDIUM | New Provider adapter for domain IOC type only. crt.sh JSON API zero-auth. Response is a list of cert objects — needs subdomain deduplication and rendering. ~250 LOC. |
| DNS record depth (MX, NS, TXT/SPF/DMARC) | Email security analysts check MX records, SPF, DMARC, and DKIM records constantly when triaging phishing alerts. Cloudflare DoH supports all record types via ?type= parameter. One extra request per record type. | LOW | Extend DNS provider to make parallel requests for A, MX, NS, TXT. Response rendering needs labeled sections. ~+100 LOC to DNS adapter. |
| ThreatMiner passive DNS provider | "What other domains have pointed to this IP? What IPs has this domain used?" — passive DNS pivoting without leaving the tool. This is the feature that turns SentinelX from a "lookup tool" into an "investigation tool." Zero-auth, covers IP + domain + hash. | MEDIUM | New Provider adapter. ThreatMiner API has multiple endpoints per IOC type (rt= parameter controls data type). Rate limit: 10 req/min — needs handling. ~300 LOC adapter. |
| CIRCL hashlookup "known-good" badge treatment | When NSRL match returns a trust score >= 70, the UI should surface this prominently as a "KNOWN GOOD" verdict rather than "no_data" — gives analysts an immediate signal to de-prioritize or close the alert. Uniquely valuable because no current provider does this. | LOW | Verdict derivation logic in CIRCL adapter only. Frontend badge may need a new "known_good" verdict color. |

**Confidence: MEDIUM-HIGH** — Identified from VirusTotal blog posts, SOCRadar/ANY.RUN analyst guides, and confirmed against API documentation for each data source.

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Combined threat score | "Just give me a number" — analysts want fast decisions | Violates core SentinelX value (no opaque scores). Single score hides which provider flagged what, and analysts dismiss alerts when a low number is shown for genuinely malicious IOCs. | Consensus badge system already built (v4.0). Show "8/8 providers responded, 3 flagged" — transparent, not opaque. |
| WHOIS registration data | Analysts want to know who registered a domain | Privacy redaction makes 90%+ of gTLD WHOIS useless post-2018. High complexity, low yield. Already ruled out in PROJECT.md. | crt.sh cert transparency + ThreatMiner passive DNS provide more actionable infrastructure attribution. |
| Malware sandbox detonation | "Can I just see what the file does?" | Fundamentally different capability — requires VM isolation, file upload, detonation engine. Security surface explosion. Out of project scope in PROJECT.md. | Link out to ANY.RUN or Hybrid Analysis for detonation use cases. |
| Historical analysis/trending | "Show me if this IP is getting more dangerous over time" | Requires persistent storage design. SentinelX is a single-shot triage tool by design. Adds significant complexity with unclear local-tool value. | Direct analysts to SecurityTrails or VirusTotal for historical research. Export from SentinelX to CSV and track externally. |
| AI/LLM verdict explanation | "Explain why this is malicious in plain English" | LLM dependency, hallucination risk on novel threats, wrong for rare IOCs. Violates "never invent scores" principle. Adds external service dependency. | Clear per-provider source attribution already shows the reasoning transparently. |
| Real-time streaming results | "Show results as they come in" | WebSocket/SSE infrastructure overhead. Current concurrent futures model already returns all 8 providers in <5 seconds. Perceived improvement doesn't justify implementation cost. | Current parallel batch enrichment is already fast. Improve provider rendering speed instead. |
| STIX/TAXII export | "Integrate with MISP" | STIX serialization is non-trivial. SentinelX's IOC model doesn't map cleanly to STIX objects without a significant data model expansion. Niche use case for a triage tool. | Export to JSON (already built) provides enough structure for MISP manual import. Implement only if explicitly requested. |
| Persistent session history | "Save my lookups" | Single-user local tool — OS filesystem already provides that. Cache TTL provides short-term replay. Scope creep. | Existing SQLite cache covers re-lookup within TTL. Export to JSON/CSV for records. |

---

## Feature Dependencies

```
GeoIP Provider (ip-api.com)
    uses──> Provider Protocol (exists)
    uses──> HTTP safety controls (exists)
    returns──> country, city, ASN, ISP, proxy flag, hosting flag
    renders──> Enhanced IP card section

rDNS Provider (socket.gethostbyaddr)
    uses──> Provider Protocol (exists)
    no HTTP dependency──> system resolver only
    renders──> Enhanced IP card section

GeoIP Provider ──enhances──> rDNS Provider
    (both IP-only, share a "Network Context" card section)

DNS Resolution Provider (Cloudflare DoH)
    uses──> Provider Protocol (exists)
    supports──> domain, URL (extract domain from URL)
    returns──> A, MX, NS, TXT records
    renders──> DNS records section in domain card

Enhanced Shodan rendering
    depends on──> existing raw_stats already in EnrichmentResult (no backend change)
    is──> frontend card renderer change only

CIRCL Hashlookup Provider
    uses──> Provider Protocol (exists)
    supports──> MD5, SHA1, SHA256 only (not SHA512, not domain/IP)
    returns──> NSRL match + trust score
    new verdict──> "known_good" (requires new verdict handling in UI)

crt.sh Certificate Provider
    uses──> Provider Protocol (exists)
    supports──> domain only
    returns──> list of cert objects with SANs, issuers, dates
    renders──> cert history section in domain card

ThreatMiner Passive DNS Provider
    uses──> Provider Protocol (exists)
    supports──> IP, domain, hash (separate endpoints per type)
    rate limit──> 10 req/min (needs exponential backoff or graceful throttling)
    renders──> passive DNS section in IP/domain cards, related samples in hash card

"known_good" verdict
    required by──> CIRCL Hashlookup Provider
    requires──> new verdict color/badge in UI
    requires──> update verdict severity ordering (known_good < no_data < clean < suspicious < malicious)
```

### Dependency Notes

- **GeoIP and rDNS are independent adapters** but both IP-only. They should be built in the same phase and rendered together in a "Network Context" section within the IP result card.
- **Enhanced Shodan rendering is zero-backend** — all data is already in raw_stats. This is a frontend-only task and can be done independently of any new providers.
- **CIRCL hashlookup introduces a new verdict level ("known_good")** that does not exist in the current system. This requires a verdict severity update in both backend models and frontend rendering. Budget for this cross-cutting change.
- **crt.sh and DNS providers both cover domain IOCs** — can be built together in the same phase without conflicts.
- **ThreatMiner has the most complexity** due to: multiple endpoints per IOC type (different rt= values for passive DNS vs related hashes vs WHOIS), 10 req/min rate limit requiring per-request throttling, and richer response data needing more complex rendering. Build last.
- **All new zero-auth providers fit the existing Provider Protocol without model changes** — requires_api_key=False, is_configured() returns True unconditionally.

---

## Zero-Auth vs Key-Required Split Summary

This directly answers the analyst's "can't we do more without API keys?" question.

### What Works With Zero Accounts (After v6.0)

| Provider | IOC Types | New Data Unlocked |
|---------|-----------|-------------------|
| Shodan InternetDB (exists) | IPv4, IPv6 | Ports, CVEs, tags (already collected, needs better rendering) |
| ip-api.com (new) | IPv4, IPv6 | Country, city, ISP, ASN, proxy flag, hosting flag |
| rDNS (new) | IPv4, IPv6 | PTR hostname |
| Cloudflare DoH (new) | domain, URL | A, MX, NS, TXT records |
| CIRCL hashlookup (new) | MD5, SHA1, SHA256 | NSRL known-good detection, trust score |
| crt.sh (new) | domain | Cert history, subdomains via SANs |
| ThreatMiner (new) | IP, domain, hash | Passive DNS, related domains/IPs, related samples |

**Result with zero API keys configured:** IPs get country/city/ASN/ISP/proxy+hosting flags/ports/CVEs/rDNS; domains get live DNS records + cert history + subdomains + passive DNS; hashes get NSRL known-good check + related samples.

This is competitive with what VirusTotal shows on its free public lookup page for most analyst triage needs.

### What Still Requires API Keys (Already Supported)

All 8 existing providers (VirusTotal, MalwareBazaar, ThreatFox, URLhaus, OTX, GreyNoise, AbuseIPDB) remain available for analysts who register. Keys are free at each provider. The zero-auth tier supplements them; it does not replace them.

---

## MVP Definition for v6.0

### Phase 1: Zero-Auth IP Enrichment + NSRL (Highest Impact)

Directly addresses the primary analyst complaint. All fit existing Provider Protocol with no model changes except for the "known_good" verdict in CIRCL.

- [ ] GeoIP Provider (ip-api.com) — country, city, ISP, ASN, proxy/VPN/hosting flags — LOW complexity
- [ ] rDNS Provider — PTR record lookup via system resolver — LOW complexity
- [ ] CIRCL Hashlookup Provider — NSRL known-good detection for hashes — LOW complexity + "known_good" verdict
- [ ] Enhanced Shodan card rendering — expose ports, CVEs, hostnames already in raw_stats — LOW complexity (frontend only)

### Phase 2: Domain Intelligence (Fills Major Gap)

Domains currently only get VirusTotal + OTX + ThreatFox + URLhaus context. Zero-auth depth:

- [ ] DNS Resolution Provider (Cloudflare DoH) — live A/MX/NS/TXT records for domains — LOW complexity
- [ ] crt.sh Certificate Provider — cert history + subdomain discovery for domains — MEDIUM complexity

### Phase 3: Infrastructure Pivoting (The Differentiator)

The feature that makes analysts say "I don't need to leave this tool":

- [ ] ThreatMiner Provider — passive DNS, related domains/IPs, related samples for IP + domain + hash — MEDIUM complexity

### Defer to Future Milestone

- [ ] STIX/TAXII export format — useful for MISP integration but niche for triage tooling; current JSON export handles most workflows
- [ ] Provider capability matrix UI — nice visual improvement for settings page, low analyst impact
- [ ] urlscan.io integration — URL screenshot and DOM scanning capability; requires API key for consistent access, limited free tier; add when URL investigation becomes a stated pain point

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| GeoIP + ASN (ip-api.com) | HIGH — first context analysts check for any IP | LOW — ~200 LOC new adapter | P1 |
| rDNS (PTR lookup) | HIGH — standard IP hostname context | LOW — ~100 LOC, no HTTP | P1 |
| Enhanced Shodan rendering | HIGH — data already collected, just hidden from UI | LOW — frontend card change only | P1 |
| CIRCL hashlookup (NSRL known-good) | HIGH — reduces false-positive workload significantly | LOW — ~150 LOC adapter + new verdict type | P1 |
| DNS resolution (Cloudflare DoH) | HIGH — domains are nearly opaque without current DNS context | LOW — ~150 LOC adapter | P2 |
| crt.sh cert transparency | MEDIUM — powerful for infra analysis, less needed for routine triage | MEDIUM — list rendering, subdomain dedup | P2 |
| ThreatMiner passive DNS | HIGH — pivoting is the key differentiator for deeper analysis | MEDIUM — multi-endpoint, rate limiting | P2 |
| Provider capability matrix UI | LOW — visual improvement, does not add analyst data | LOW — settings page only | P3 |
| STIX export | LOW — triage tool analysts typically don't need MISP integration | MEDIUM | P3 |

**Priority key:** P1 = Phase 1 of v6.0 | P2 = Phase 2 of v6.0 | P3 = future milestone

---

## Competitor Feature Analysis

| Feature | VirusTotal (free) | VirusTotal (paid) | ANY.RUN (free) | SentinelX v5.0 | SentinelX v6.0 Target |
|---------|------------------|-------------------|----------------|----------------|----------------------|
| GeoIP / ASN / ISP | Limited | Full | Yes | No | Yes (zero-auth) |
| Reverse DNS | Limited | Full | Yes | No | Yes (zero-auth) |
| Live DNS records | Partial | Full | No | No | Yes (zero-auth) |
| Cert transparency | No | Yes | No | No | Yes (zero-auth) |
| NSRL known-good hash | No | No | No | No | Yes (zero-auth — unique differentiator) |
| Passive DNS history | No | Yes | No | No | Yes via ThreatMiner (zero-auth) |
| Multi-provider parallel enrichment | No | No | No | Yes (8 providers) | Yes (8 + up to 6 new zero-auth) |
| Local/private operation | No | No | No | Yes | Yes |
| No opaque combined scores | No | No | No | Yes | Yes |
| Proxy/VPN/hosting detection | Limited | Yes | No | No | Yes (zero-auth) |
| Export JSON/CSV | Yes (paid) | Yes | Yes | Yes | Yes |
| Open ports + CVE exposure | Via Shodan link | Via Shodan link | No | Yes (Shodan InternetDB) | Yes (enhanced rendering) |

**Positioning summary:** SentinelX's competitive position after v6.0 is the combination of: (1) zero-auth depth rivaling paid VirusTotal features for IP/domain/hash triage, (2) no opaque scoring, (3) local/private operation with no data leaving the analyst's machine to an external SAAS provider, and (4) multi-provider parallel enrichment with unified verdicts. No major competitor offers all four simultaneously.

---

## Sources

- [Shodan InternetDB API docs](https://internetdb.shodan.io/docs) — zero-auth confirmed, response schema (ports, vulns, tags, hostnames, cpes) verified (HIGH confidence)
- [ip-api.com documentation](https://ip-api.com/) — no key required confirmed, 45 req/min rate limit, proxy/hosting/mobile fields in free response (HIGH confidence)
- [CIRCL hashlookup service](https://www.circl.lu/services/hashlookup/) — no auth required confirmed, NSRL + Windows/Linux/macOS packages, trust score field (HIGH confidence)
- [Cloudflare DNS over HTTPS API docs](https://developers.cloudflare.com/1.1.1.1/encryption/dns-over-https/make-api-requests/) — no auth for DNS queries confirmed, JSON format via Accept header (HIGH confidence)
- [ThreatMiner API reference](https://www.threatminer.org/api.php) — no-auth public API, 10 req/min rate limit, endpoint parameters documented (MEDIUM confidence — community-operated, no formal SLA)
- [crt.sh certificate transparency tool](https://crt.sh/) — zero-auth JSON output via ?output=json parameter, subdomain enumeration via SANs (MEDIUM confidence — no formal rate limits published)
- [GreyNoise Community API docs](https://docs.greynoise.io/docs/using-the-greynoise-community-api) — free tier with key confirmed, trial without key available (HIGH confidence)
- [ANY.RUN SOC triage analyst guide](https://any.run/cybersecurity-blog/triage-analyst-guide/) — analyst workflow steps (2-minute triage, escalation pattern) (MEDIUM confidence — vendor source but specific and detailed)
- [SentinelOne VT analyst guide](https://www.sentinelone.com/labs/exploring-the-virustotal-dataset-an-analysts-guide-to-effective-threat-research/) — VT feature usage patterns for daily analyst work (MEDIUM confidence)
- [SOCRadar Top 20 Free Cybersecurity APIs](https://socradar.io/blog/top-20-free-apis-for-cybersecurity/) — zero-auth API landscape survey (MEDIUM confidence)
- [Open Source Threat Intel Feeds (GitHub)](https://github.com/Bert-JanP/Open-Source-Threat-Intel-Feeds) — no-key feed catalog (MEDIUM confidence)
- [ipwho.is API](https://www.ipwho.org/) — alternative zero-auth GeoIP, 60 req/60s (HIGH confidence — verified against official docs)

---

*Feature research for: SentinelX v6.0 Analyst Experience*
*Researched: 2026-03-11*
