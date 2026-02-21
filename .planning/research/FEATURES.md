# Feature Research

**Domain:** IOC triage and enrichment tool (local web application for SOC analysts)
**Researched:** 2026-02-21
**Confidence:** HIGH (core feature set), MEDIUM (API-specific details), LOW (rate limits without direct verification)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features SOC analysts assume any IOC triage tool provides. Missing these means the tool is not usable as a daily driver.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Free-form text paste with multi-IOC extraction | Analysts paste SIEM snippets, email headers, threat reports — never single IOCs | MEDIUM | iocextract/iocsearcher are proven Python libs; handle defanged + plain |
| Defanging normalization (hxxp, [.], {.}, [dot], _dot_, [@]) | All threat reports defang IOCs; tool must refang before enrichment | MEDIUM | iocextract handles most; edge cases exist (custom analyst defangs) |
| IOC classification by type | Analysts need to know what they're looking at before enriching | LOW | Deterministic regex per type; IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE are standard |
| Deduplication of extracted IOCs | Pasted text often has repeats; duplicates in results are noise | LOW | Hash-based dedup before enrichment calls |
| VirusTotal enrichment (IP, domain, URL, hash) | VT is the industry baseline — every SOC has it | MEDIUM | Free tier: 500 req/day, 4 req/min; covers all four IOC types; returns detection verdicts |
| Results grouped by IOC type | Analysts scan results differently by type (IPs vs. hashes vs. domains) | LOW | Standard presentation in IntelOwl, Cortex, Pulsedive |
| Source attribution on every verdict | Analysts must know where a verdict came from to trust it | LOW | Critical for analyst decision-making; never aggregate without attribution |
| Offline mode (extraction only, zero network) | Jump boxes may have no outbound; offline extractions still valuable | LOW | Toggle that disables all API calls cleanly |
| Visual in-progress indicator during lookups | Parallel API calls can take 2–10 seconds; UI must show activity | LOW | Basic spinner or per-IOC status states |
| Timestamp on enrichment results | Analysts need to know if data is fresh or stale | LOW | Include API response timestamp, not just request time |
| CVE recognition and extraction | CVEs appear in alert text and threat reports constantly | LOW | Standard regex: CVE-YYYY-NNNNN+ |
| Localhost-only binding | Security requirement; analysts won't use a tool that exposes IOCs to the network | LOW | Flask default + explicit bind to 127.0.0.1 |

### Differentiators (Competitive Advantage)

Features that distinguish sentinelx from ad-hoc searches or a pile of browser tabs. Not table stakes, but meaningfully valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AbuseIPDB enrichment for IPs | Best-in-class crowdsourced IP reputation; 1,000 free checks/day; covers IPv4+IPv6; returns abuse confidence score, ISP, country, reports count | LOW | IP-only; complements VT which is weaker on raw IP reputation |
| Shodan InternetDB enrichment for IPs | No API key required; returns open ports, CPEs, CVEs, hostnames, tags; reveals infrastructure context VT doesn't provide | LOW | Updated weekly; rate limits generous for non-commercial; no banner data |
| ThreatFox enrichment for hashes/domains/IPs | abuse.ch community data on active C2 infrastructure; covers malware family attribution; free with auth key | MEDIUM | IOC expiration after 6 months (since 2025-05-01); good for active threats |
| MalwareBazaar enrichment for file hashes | Hash-specific: returns file type, malware family, tags, first/last seen, ClamAV verdict, imphash, TLSH, ssdeep; free community API | LOW | Hashes only; deepest file hash context of any free provider |
| URLhaus enrichment for URLs/hashes | Malware distribution URLs; returns tags, URL status (online/offline), associated payloads; free community API | LOW | URL and hash only; pairs well with VT for URL classification |
| AlienVault OTX enrichment | Reputation + geo data + associated pulse campaigns; free with API key; covers IP, domain, URL, hash | MEDIUM | 100k+ contributors; pulse-based context links IOC to threat campaigns |
| GreyNoise enrichment for IPs | Reduces false positives by labeling "internet background noise" scanners; community API: 50 lookups/week free | LOW | IP-only; noise/riot/classification fields tell analyst if IP is mass-scanner vs. targeted |
| Parallel enrichment execution | All API calls fire concurrently per IOC; results appear as they arrive | MEDIUM | Critical for speed; sequential lookups per IOC would be unusably slow |
| Result freshness display (first_seen / last_seen) | IOC age matters — an IP active 2 years ago may be irrelevant today | LOW | Surface provider timestamps, not just lookup timestamps |
| Raw verdict passthrough (no score blending) | Analysts distrust opaque combined scores; showing "VT: 34/72 engines" is more useful than "Risk: HIGH" | LOW | Deliberate design choice; per-PROJECT.md requirement |
| IOC count summary before enrichment | Analyst confirmation that extraction found what they expect before firing API calls | LOW | Prevents unnecessary API quota usage on bad paste |
| Copy-to-clipboard per IOC (refanged) | Analysts frequently need to paste IOCs into other tools | LOW | Browser clipboard API |
| API result caching with TTL | Prevents quota exhaustion when same IOC appears multiple times in a session; reduces latency on repeat lookups | MEDIUM | In-memory only; reasonable TTL varies by provider (1–24h); must not persist raw input |
| Pulsedive enrichment | Aggregates OSINT feeds; free tier covers IP, domain, URL; provides risk factors and feed-based context | MEDIUM | Rate limits unverified at time of research; confirm before shipping |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem helpful but are wrong for this tool's purpose and constraints.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Combined "threat score" or "risk rating" | Analysts want a quick green/red judgment | Hides which providers agree/disagree; forces analyst to trust tool's weighting; creates false confidence on split verdicts | Show raw per-provider verdicts; let analyst read the room |
| Fetching/crawling the target URL | "Can it check if the URL is live?" | Sending HTTP requests to potentially malicious URLs from analyst's machine is a serious security risk; explicitly prohibited in PROJECT.md | Never crawl; rely on URLhaus online/offline status from their API |
| Following HTTP redirects on outbound API calls | Some API endpoints redirect | Redirect chains can exfiltrate IOC data to unintended hosts; obscures actual endpoint | Disable redirect following; fail on redirect with clear error |
| Persistent storage of raw pasted text | "Save my sessions for review" | Raw paste blobs contain sensitive IOCs and potentially sensitive alert text; persistent storage creates data exposure risk | Cache API results with TTL only; never store raw input to disk |
| Email sending of results | "Share results with my team" | Tool is local/single-user; email requires SMTP config and creates data exfiltration path | Copy-to-clipboard or export-to-JSON for sharing |
| Automated blocking/response actions | "Auto-block the bad IP" | Read-only enrichment is the safe scope; write actions require auth, audit logs, rollback — entirely different security model | Document: this tool informs decisions, does not take actions |
| User authentication / multi-user support | "We have a team of analysts" | Multi-user requires auth system, RBAC, session management — major complexity with no benefit for local-use tool | One instance per analyst on their own machine |
| Real-time IOC monitoring / scheduled lookups | "Watch this IP over time" | Requires persistence, scheduler, alerting — out of scope; also creates ongoing API quota drain | Single-shot triage is the design; analysts re-paste when needed |
| Whois / RDAP enrichment | "Show domain registration" | High implementation complexity for limited signal; Whois data is often privacy-redacted; SecurityTrails free tier is 50/month | Defer to v2; OTX already includes some WHOIS-adjacent data |
| Malware sandbox detonation | "Can it run the sample?" | Fundamentally different capability; requires containerization, sandboxing, file storage | Link to Triage.io or ANY.RUN when hash is found in results |
| Mobile / responsive UI | "I want to use it on my phone" | Tool is for desktop analyst workflow; responsive design adds complexity without real-world benefit for a local tool | Out of scope; desktop browser only |
| Dark mode theming | Common request | UI polish is not the value proposition; every hour on theming is an hour not on enrichment accuracy | Use system prefers-color-scheme CSS if trivial; never as a feature |

---

## Feature Dependencies

```
IOC Extraction (text parsing + defanging)
    └──requires──> IOC Classification (type detection)
                       └──requires──> IOC Deduplication
                                          └──enables──> Enrichment (online mode)
                                                            └──requires──> API key config (per provider)

Offline Mode
    └──subset of──> IOC Extraction + Classification (no enrichment step)

Parallel enrichment
    └──requires──> IOC Classification (must know type to route to correct API)
    └──requires──> API key config
    └──enhances──> Result freshness (faster total time means results still relevant)

API result caching
    └──requires──> IOC Classification (cache key includes type + value)
    └──enhances──> Parallel enrichment (cache hit avoids network call)

Source attribution display
    └──requires──> Enrichment (data must arrive from providers)
    └──conflicts with──> Combined threat score (attribution forces per-source display)

Result grouping by IOC type
    └──requires──> IOC Classification
    └──enhances──> Parallel enrichment display (results slot into correct group as they arrive)
```

### Dependency Notes

- **Enrichment requires Classification:** The wrong API gets called if type is wrong (e.g., sending a domain to IP-only AbuseIPDB). Classification gates enrichment routing.
- **Offline mode is a strict subset:** Everything in offline mode must work without the enrichment path. Test independently.
- **Combined score conflicts with attribution:** These are architecturally incompatible. Picking one eliminates the other. PROJECT.md mandates attribution; never build the score.
- **Caching complicates TTL management:** Each provider has different data freshness. VT data ages faster than Shodan InternetDB (weekly updates). Cache TTL should be per-provider, not global.

---

## MVP Definition

### Launch With (v1)

Minimum viable product that delivers value to a SOC analyst on day one.

- [ ] Free-form text paste with extraction (iocextract or iocsearcher as backend) — without this the tool does nothing
- [ ] Defanging normalization across all standard patterns — analysts paste defanged text; un-defanged extraction is worthless
- [ ] IOC classification: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE — the eight types that appear in SOC work
- [ ] Deduplication before enrichment — prevents wasted API quota
- [ ] Offline mode: extract + classify only — zero network calls; required for air-gapped or restricted environments
- [ ] VirusTotal enrichment (IP, domain, URL, hash) — the universal baseline; if you only have one provider, have VT
- [ ] AbuseIPDB enrichment (IP only) — 1,000 free/day; best IP reputation signal not in VT
- [ ] Shodan InternetDB enrichment (IP only) — no API key needed; open ports + CVEs; unique data VT doesn't provide
- [ ] MalwareBazaar enrichment (hash only) — deepest file hash context of any free provider
- [ ] ThreatFox enrichment (hash, domain, IP, URL) — C2 and malware family context from abuse.ch
- [ ] Parallel enrichment execution — sequential would be unusably slow with 5+ providers
- [ ] Results grouped by IOC type — standard analyst expectation
- [ ] Source attribution on every result (provider name + timestamp + raw verdict) — non-negotiable per PROJECT.md
- [ ] No combined threat score — deliberate omission; show raw verdicts only
- [ ] Visual in-progress indicator during lookups
- [ ] Localhost-only binding, API keys from environment variables only

### Add After Validation (v1.x)

Add when core flow is working and analyst feedback identifies gaps.

- [ ] AlienVault OTX enrichment — campaign/pulse context; useful when analysts need "what threat actor used this?" but adds registration friction
- [ ] GreyNoise enrichment — valuable for reducing false positives on IP alerts; add when analysts report VT+AbuseIPDB combination is still noisy; 50 lookups/week free limit is constraining
- [ ] URLhaus enrichment for URLs — supplements VT for malware distribution URL context; low complexity to add
- [ ] API result caching with per-provider TTL — add when repeated same-session lookups become a pain point
- [ ] IOC count confirmation step — add if analysts report wasted API quota on large pastes with unexpected IOC counts
- [ ] Copy-to-clipboard per IOC (refanged) — quality of life; add when analysts report copy-paste friction

### Future Consideration (v2+)

Defer until product-market fit is established and v1 feedback drives priorities.

- [ ] Pulsedive enrichment — useful aggregator but rate limits unverified; validate free tier practicality first
- [ ] Export to JSON — useful for piping into other tools; low priority since tool is manual-use
- [ ] WHOIS / RDAP enrichment — limited signal for effort; SecurityTrails free tier too restrictive (50/month)
- [ ] CVE enrichment (NVD/CVSS lookup) — analysts want CVSS scores for CVEs in alert text; moderate complexity
- [ ] IOC history across sessions — store past results for "have I seen this before?"; requires persistence design decision

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| IOC extraction + defanging | HIGH | MEDIUM | P1 |
| IOC classification | HIGH | LOW | P1 |
| VirusTotal enrichment | HIGH | MEDIUM | P1 |
| Offline mode | HIGH | LOW | P1 |
| Parallel enrichment | HIGH | MEDIUM | P1 |
| Source attribution display | HIGH | LOW | P1 |
| AbuseIPDB enrichment | HIGH | LOW | P1 |
| Shodan InternetDB enrichment | HIGH | LOW | P1 |
| MalwareBazaar enrichment | HIGH | LOW | P1 |
| ThreatFox enrichment | HIGH | LOW | P1 |
| Results grouped by IOC type | MEDIUM | LOW | P1 |
| Deduplication | MEDIUM | LOW | P1 |
| Visual loading indicator | MEDIUM | LOW | P1 |
| AlienVault OTX enrichment | MEDIUM | MEDIUM | P2 |
| GreyNoise enrichment | MEDIUM | LOW | P2 |
| URLhaus enrichment | MEDIUM | LOW | P2 |
| API result caching | MEDIUM | MEDIUM | P2 |
| Copy-to-clipboard | LOW | LOW | P2 |
| IOC count confirmation | LOW | LOW | P2 |
| Pulsedive enrichment | LOW | MEDIUM | P3 |
| JSON export | LOW | LOW | P3 |
| WHOIS enrichment | LOW | HIGH | P3 |
| CVE CVSS lookup | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | CyberChef | IntelOwl | VirusTotal Web UI | sentinelx Approach |
|---------|-----------|----------|-------------------|--------------------|
| Multi-IOC extraction from paste | Manual per-recipe setup | No — requires structured input | No — one IOC at a time | Automatic from free-form text |
| Defanging normalization | Manual recipe chain | Partial | No | Automatic, all standard patterns |
| Multiple provider enrichment | No enrichment | Yes, 40+ providers | VT only | Curated 5–6 best free providers |
| Offline extraction mode | Yes (local app) | No (Docker service) | No | Yes, explicit offline toggle |
| Source attribution per result | N/A | Yes (per analyzer) | Yes (per AV engine) | Yes, required design constraint |
| Combined threat score | No | No | Partial (community score) | No — deliberate omission |
| Setup complexity | Minimal | High (Docker stack) | Zero (web service) | Minimal (Python + env vars) |
| API key management | N/A | Config file | Account-based | Environment variables only |
| Data sent to third parties | None | To analyzers | To VT | To analyst-chosen providers only |

---

## Threat Intelligence API Reference

Recommended providers for v1, ordered by implementation priority:

### Tier 1: Build First (v1 core)

| Provider | IOC Types | Free Tier | Key Data Points | Requires Key |
|----------|-----------|-----------|-----------------|--------------|
| **VirusTotal** | IPv4, IPv6, domain, URL, MD5, SHA1, SHA256 | 500 req/day, 4 req/min | Detection count (X/72 engines), category, last analysis date | Yes (free registration) |
| **AbuseIPDB** | IPv4, IPv6 | 1,000 checks/day | Abuse confidence score (0-100%), total reports, ISP, country, usage type | Yes (free registration) |
| **Shodan InternetDB** | IPv4 | No documented limit (weekly data) | Open ports, CPEs, CVEs, hostnames, tags | No — completely free, no key |
| **MalwareBazaar** | MD5, SHA1, SHA256 | Fair use (no stated limit) | File type, malware family, first/last seen, tags, imphash, TLSH, ssdeep | Yes (free registration) |
| **ThreatFox** | MD5, SHA256, domain, URL, IP:port | Fair use (no stated limit) | Threat type, malware family, confidence level, first seen, C2 indicator | Yes (free registration) |

### Tier 2: Add in v1.x

| Provider | IOC Types | Free Tier | Key Data Points | Requires Key |
|----------|-----------|-----------|-----------------|--------------|
| **AlienVault OTX** | IPv4, IPv6, domain, URL, MD5, SHA1, SHA256 | Unlimited (fair use) | Associated pulses/campaigns, geo data, malware samples, passive DNS | Yes (free registration) |
| **GreyNoise** | IPv4 | 50 lookups/week | Noise (mass scanner), RIOT (benign service), classification, last seen | Yes (free community registration) |
| **URLhaus** | URL, MD5, SHA256 | Fair use (175M API req/month community-wide) | URL status (online/offline), tags, payload hashes, reporter | Yes (free registration) |

### Tier 3: Evaluate Later

| Provider | IOC Types | Free Tier | Concern |
|----------|-----------|-----------|---------|
| **Pulsedive** | IP, domain, URL | Free plan exists; rate limits unverified | Confirm rate limits before committing |
| **SecurityTrails** | Domain, IP | 50 queries/month | Too restrictive for regular use |
| **Shodan full API** | IP, domain | Very limited without paid plan | Use InternetDB instead for free tier |

---

## IOC Extraction Pattern Reference

Standard defanging patterns that must be handled (MEDIUM confidence — from iocextract docs and IETF draft):

| Pattern Type | Examples | Normalization |
|-------------|----------|---------------|
| Protocol obfuscation | `hxxp://`, `hxxps://` | Replace with `http://`, `https://` |
| Dot replacement (brackets) | `example[.]com`, `1.2[.]3.4` | Replace `[.]` with `.` |
| Dot replacement (parens) | `example(.)com` | Replace `(.)` with `.` |
| Dot replacement (curly) | `example{.}com` | Replace `{.}` with `.` |
| Dot replacement (text) | `example[dot]com`, `example_dot_com`, `example DOT com` | Case-insensitive text replacement |
| At replacement | `user[@]example.com`, `user(@)domain.com`, `user[at]domain.com` | Restore `@` |
| Slash/colon replacement | `hxxp[://]`, `hxxp[:/]` | Restore `://` |
| Cisco ESA encoding | Spaces inserted into URLs | Strip injected whitespace |
| Hex/Base64 encoding | `%68%74%74%70`, base64 URL | Decode before extraction |

**Advanced patterns (LOW confidence — edge cases seen in practice):**

- Capital letter substitution: `HXXPS://` — must be case-insensitive
- Mixed bracket styles in same IOC: `hxxp[://]example[.]com` — multiple simultaneous replacements
- Custom analyst shorthand: `h__p://`, `ht*ps://` — cannot enumerate all; flag as unrecognized

---

## Sources

- [VirusTotal Public vs Premium API](https://docs.virustotal.com/reference/public-vs-premium-api) — MEDIUM confidence (official docs, verified rate limits)
- [AbuseIPDB Pricing/API](https://www.abuseipdb.com/pricing) — MEDIUM confidence (official site, 1,000/day free tier)
- [Shodan InternetDB API](https://internetdb.shodan.io/) — HIGH confidence (official, no-key endpoint verified)
- [MalwareBazaar Community API](https://bazaar.abuse.ch/api/) — MEDIUM confidence (official, rate limits unspecified "fair use")
- [ThreatFox Community API](https://threatfox.abuse.ch/api/) — MEDIUM confidence (official, fair use, IOC expiry since 2025-05-01)
- [URLhaus Community API](https://urlhaus.abuse.ch/api/) — MEDIUM confidence (official, fair use)
- [AlienVault OTX External API](https://otx.alienvault.com/assets/static/external_api.html) — MEDIUM confidence (official docs)
- [GreyNoise Community API](https://docs.greynoise.io/docs/using-the-greynoise-community-api) — HIGH confidence (official docs, 50 lookups/week verified)
- [iocextract GitHub](https://github.com/InQuest/iocextract) — HIGH confidence (maintained library, docs verified)
- [iocsearcher GitHub](https://github.com/malicialab/iocsearcher) — HIGH confidence (maintained library, 30+ IOC types verified)
- [ANY.RUN SOC Triage Guide](https://any.run/cybersecurity-blog/triage-analyst-guide/) — MEDIUM confidence (practitioner perspective)
- [Free Cybersecurity APIs for IOC Lookups](https://upskilld.com/article/free-cybersecurity-apis/) — LOW confidence (third-party aggregation, verify rate limits independently)

---

*Feature research for: IOC triage and enrichment tool (sentinelx / oneshot-ioc)*
*Researched: 2026-02-21*
