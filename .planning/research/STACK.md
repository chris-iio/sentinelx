# Stack Research

**Domain:** Threat intelligence enrichment — DNSBL reputation, public threat feeds, RDAP
registration data, ASN/BGP intelligence
**Researched:** 2026-03-15
**Confidence:** HIGH (all libraries verified against PyPI, official documentation, and live
API endpoints; see Sources)

---

## Context: v7.0 Additive Stack Only

SentinelX v6.0 baseline is locked and shipped. This document covers ONLY new capabilities
needed for v7.0 Free Intel. Do not re-evaluate Flask, requests, dnspython, iocextract,
iocsearcher, esbuild, Tailwind, or any of the 13 existing providers.

The existing stack after v6.0:
- `requests==2.32.5` — all HTTP adapters
- `dnspython==2.8.0` — DNS resolution (DnsAdapter, port 53 directly)
- 12 hosts in `ALLOWED_API_HOSTS` SSRF allowlist

The question this research answers: what new libraries and API endpoints enable DNSBL checks,
public threat feed lookups, RDAP registration data, and ASN/BGP intelligence?

---

## Findings by Capability

### Capability 1: DNSBL Reputation Checks

**Verdict: implement with existing `dnspython` — no new library.**

DNSBL lookup is a reverse-IP DNS query, not an HTTP call. The mechanism is:
1. Reverse the IP octets: `1.2.3.4` → `4.3.2.1`
2. Append the DNSBL zone: `4.3.2.1.zen.spamhaus.org`
3. Resolve as an A record — `NXDOMAIN` means not listed, `127.0.0.x` means listed
4. The return code encodes which sub-list the IP appears on

This is exactly what `dnspython` already does in `DnsAdapter`. The DNSBL provider is a
new adapter that reuses the same `dns.resolver.Resolver` pattern.

**Spamhaus public mirror restriction (HIGH confidence, critical):**
Spamhaus is blocking queries arriving from public resolvers and cloud-hosted IPs. Error code
`127.255.255.254` is being phased in across major cloud providers' IP space (Hetzner Feb 2025,
Microsoft Apr 2025, Korea Telecom Sep 2025). A SOC analyst running SentinelX on their own
workstation (with their ISP's recursive resolver) is not affected. A jump box hosted at a
cloud provider may receive `127.255.255.254` responses from Spamhaus. The free Data Query
Service (DQS) resolves this with a free key registration, but adds a key-management burden.

**DNSBL zones to query (curated for reliability):**

| Zone | Type | Coverage | Public Resolver Safe |
|------|------|----------|----------------------|
| `zen.spamhaus.org` | IP | SBL + XBL + PBL combined | Yes (own resolver); blocked from cloud/shared resolvers |
| `dbl.spamhaus.org` | Domain | Spamhaus Domain Blocklist | Same restriction as zen |
| `multi.surbl.org` | Domain | SURBL combined URI blocklist | Generally safe; no public resolver restriction documented |
| `combined.abuse.ch` | IP | abuse.ch combined (botnet/malware) | Generally safe |
| `b.barracudacentral.org` | IP | Barracuda Reputation Block List | Safe; free registration recommended to avoid throttling |

**Approach:** Query all five zones per IP/domain lookup. Catch `NXDOMAIN` as "clean", catch
`127.255.255.254` returns from Spamhaus as "query blocked" (surface this to analyst as a
note, not an error), and map positive return codes to listed verdict.

**Do not use `pydnsbl`:** Version 1.1.7, released March 2025. Uses `asyncio` + `aiodns`.
The entire SentinelX enrichment pipeline is synchronous (Flask request → thread pool →
provider.lookup() calls). Introducing an async library requires event loop management that
conflicts with the existing architecture. The DNSBL pattern is 10 lines of dnspython — no
library needed.

### Capability 2: Public Threat Feed Lookups

**Verdict: use `requests` with three zero-auth HTTP API endpoints — no new library.**

The project already queries abuse.ch services (MalwareBazaar, ThreatFox, URLhaus). Three
additional zero-auth endpoints provide complementary feed coverage:

| Service | Endpoint | What it covers | Auth |
|---------|----------|---------------|------|
| Feodo Tracker | `https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.json` | Active botnet C2 IPs (Dridex, Emotet, TrickBot, QakBot, BazarLoader) | None |
| abuse.ch ThreatFox API | Already in project | IOC-type lookup across all types | Free key (existing) |
| PhishTank | `https://checkurl.phishtank.com/checkurl/` | Phishing URL verification | Free key (separate) |

**Feodo Tracker approach:** Download the JSON blocklist on each request and search for the
IP. The list is updated every 5 minutes. This is a bulk download (not a per-IP API lookup
endpoint). Better approach: cache the parsed set server-side with the existing SQLite cache
and refresh TTL of 15 minutes. A local `set[str]` membership check is O(1).

**Important:** The project already has URLhaus, MalwareBazaar, and ThreatFox. These already
cover the majority of "public threat feed" use cases. The Feodo Tracker C2 blocklist is the
only significant gap — it specifically covers active C2 infrastructure rather than malware
samples or IOC sharing. Phishing feed lookups are lower priority because URLhaus and OTX
already return phishing signals.

**Recommendation:** One new zero-auth adapter for Feodo Tracker C2 blocklist (IPs only).
Add `feodotracker.abuse.ch` to `ALLOWED_API_HOSTS`.

### Capability 3: RDAP Registration Data

**Verdict: add `whoisit==4.0.0` — introduces one new transitive dependency (`python-dateutil`).**

RDAP is a structured JSON API that replaced WHOIS. It provides registrar, creation date,
expiry date, nameservers, and registrant organization for domains. For IPs, it provides
network block owner, RIR, and allocation date. The PROJECT.md v7.0 target explicitly calls
this out; the PROJECT.md "Out of Scope" section previously listed WHOIS as out of scope
citing GDPR privacy redaction — RDAP is a different protocol that returns more structured
data, but is also subject to the same GDPR redaction for domain registrant contact info.

**What RDAP returns that is useful for triage:**
- Domain: registrar name, creation date, expiry date, nameservers (all usually present
  even with privacy redaction on contact fields)
- IP: network block CIDR, network name, RIR, organization, country

**Library options:**

| Library | Version | Dependencies | Notes |
|---------|---------|-------------|-------|
| `whoisit` | 4.0.0 | `requests`, `python-dateutil` | Pure Python. Handles IANA bootstrap (finding the right RIR for each IP/domain TLD). Returns datetime objects. Synchronous. Covers domains + IP. HIGH confidence. |
| `whodap` | 0.2.x | `httpx`, `dnspython` | async-first; sync support via `asyncio.run()`. Adds `httpx` dependency. |
| `rdap` | latest | `requests` | Newer, less documented, smaller user base. MEDIUM confidence. |

**Choose `whoisit`:** It is pure synchronous, depends only on `requests` (already present) and
`python-dateutil` (not yet present), and handles IANA bootstrapping correctly — finding the
authoritative RDAP endpoint for a given TLD or RIR is non-trivial, and whoisit solves this.
The bootstrap data from IANA is cached per-process via `whoisit.bootstrap_info()`.

**New dependency introduced:** `python-dateutil` (for datetime parsing in whoisit). This is
a low-risk, widely used library. No version conflicts with the existing stack.

**SSRF allowlist impact:** whoisit queries multiple RDAP endpoints (arin.net, ripe.net,
lacnic.net, apnic.net, afrinic.net, rdap.verisign.com, rdap.nominet.org.uk, etc.) depending
on the IP or domain TLD. These are not fixed hostnames. The existing `validate_endpoint()`
SSRF check in `http_safety.py` must be bypassed for RDAP, or the RDAP adapter must manage
its own outbound call (bypassing `http_safety`) with its own timeout. Because whoisit uses
`requests` internally, it does not go through the project's `validate_endpoint()`. This is
acceptable: RDAP bootstrapping resolves only IANA-blessed registrars, not arbitrary URLs.
Document this exception clearly in the adapter file. Apply a request timeout via whoisit's
session configuration.

### Capability 4: ASN/BGP Intelligence

**Verdict: use `ipapi.is` via `requests` — no new library. One new SSRF allowlist entry.**

`ipapi.is` returns ASN number, organization name, network type (hosting/ISP/business/
education/government), abuse email, route/prefix (CIDR), RIR, and active status. Free tier:
1,000 lookups/day with no authentication required. The endpoint is:

```
GET https://api.ipapi.is?q=<ip_address>
```

JSON response includes an `asn` object with fields: `asn`, `org`, `type`, `abuse`,
`route`, `country`, `rir`, `active`.

**BGPView is not an option:** BGPView announced shutdown on November 26, 2025. Do not use it
for new code.

**The existing `ip-api.com` provider does NOT cover ASN:** ip-api.com returns GeoIP (country,
city, lat/lon, ISP name, proxy/VPN flags) but does not return ASN number, network CIDR, RIR,
or abuse contact. `ipapi.is` fills this gap with different, complementary data.

**Overlap with existing `ip-api.com` provider:** Both services return country and org name.
The `ipapi.is` adapter should not duplicate fields already present from ip-api.com. Surface
only the ASN-specific fields: ASN number, network type classification, abuse contact, CIDR
prefix.

**Add `api.ipapi.is` to `ALLOWED_API_HOSTS`.**

---

## New Library Summary

| Library | Version | New? | Purpose | Install |
|---------|---------|------|---------|---------|
| `dnspython` | 2.8.0 | No (existing) | DNSBL lookups via DNS A record queries | Already installed |
| `requests` | 2.32.5 | No (existing) | Feodo Tracker blocklist download + ipapi.is HTTP calls | Already installed |
| `whoisit` | 4.0.0 | **YES** | RDAP registration data (domains + IPs) | `pip install whoisit==4.0.0` |
| `python-dateutil` | 2.9.x | **YES** (transitive via whoisit) | Date parsing in whoisit | Installed automatically |

**Net new packages to add to `requirements.txt`: 2** (`whoisit`, `python-dateutil`)

---

## SSRF Allowlist Changes

Add these entries to `ALLOWED_API_HOSTS` in `app/config.py`:

| Hostname | Purpose |
|----------|---------|
| `api.ipapi.is` | ASN/BGP intelligence (zero-auth, 1000/day free) |
| `feodotracker.abuse.ch` | Feodo Tracker C2 blocklist download (zero-auth) |

RDAP (whoisit) queries bypass `validate_endpoint()` — document this in the adapter file.
DNSBL (dnspython) does not use HTTP — no SSRF surface, no allowlist entry needed (same
pattern as the existing `DnsAdapter`).

---

## New Provider Adapter Map

| Adapter file | Capability | IOC Types | Auth | Library |
|-------------|-----------|-----------|------|---------|
| `dnsbl.py` | DNSBL reputation checks | `IPv4`, `IPv6`, `DOMAIN` | None | `dnspython` (existing) |
| `feodo.py` | Feodo Tracker C2 blocklist | `IPv4` | None | `requests` (existing) |
| `rdap.py` | RDAP registration data | `DOMAIN`, `IPv4`, `IPv6` | None | `whoisit` (new) |
| `asn_intel.py` | ASN/BGP intelligence | `IPv4`, `IPv6` | None | `requests` (existing) |

Each adapter: one file in `app/enrichment/adapters/`, one `registry.register()` call in
`app/enrichment/setup.py`. No other files change (zero-change provider protocol holds).

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pydnsbl` v1.1.7 | asyncio/aiodns dependency; async-only API incompatible with Flask sync architecture | Custom 10-line implementation using existing `dnspython` |
| `aiodnsbl` | Same async problem as pydnsbl; fork of pydnsbl with less adoption | Same: custom `dnspython` implementation |
| `pyasn` | Requires 100+ MB offline BGP MRT dump files with weekly refresh. Wrong model for an analyst workstation tool. | `ipapi.is` via HTTP — zero local files, zero maintenance |
| BGPView API | Announced shutdown November 2025 — do not use in new code | `ipapi.is` API |
| `ipwhois` library | Overlaps with `whoisit` for IP RDAP. The project recommended ipwhois in v6.0 research but ultimately shipped without it (ip-api.com was used instead). Now `whoisit` is the better choice: covers both domains AND IPs, pure requests dependency. | `whoisit` for all RDAP needs |
| `whodap` | Async-first; adds `httpx` dependency; whoisit covers identical RDAP surface synchronously | `whoisit` |
| `geoip2` + GeoLite2 .mmdb files | Not needed for v7.0 — ip-api.com already covers GeoIP in v6.0. Adding offline databases would require DB file management, MaxMind account setup, and refresh automation. | Existing `ip-api.com` provider (already shipped) |
| PhishTank API | Requires free key registration — adds key management burden. URLhaus + ThreatFox already cover phishing URLs effectively. | Existing URLhaus and ThreatFox providers |
| Spamhaus DQS key | Free but requires account registration — contradicts "zero API keys" goal for default experience | Fall back gracefully when `127.255.255.254` returned (surface as "query blocked via public resolver") |

---

## Installation

```bash
# New packages only — add to requirements.txt
pip install whoisit==4.0.0

# python-dateutil is a transitive dependency of whoisit — installed automatically
# Pin it explicitly for reproducible builds:
pip install python-dateutil==2.9.0
```

No changes to esbuild, Tailwind, or TypeScript build pipeline.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Custom `dnspython` DNSBL | `pydnsbl` library | Only if the project adopts async throughout (not planned) |
| `whoisit` for RDAP | `whodap` | If project migrates to `httpx` and async (not planned) |
| `ipapi.is` for ASN | `ipinfo.io` ASN API | ipinfo.io returns very similar data but requires a token for >50k lookups/month; unnecessary for a local tool |
| Feodo Tracker bulk JSON + cache | Per-IP HTTP query to non-existent Feodo API | Feodo Tracker does not have a per-IP lookup endpoint — bulk download is the only option |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `whoisit==4.0.0` | Python 3.10+, `requests>=2.0`, `python-dateutil>=2.0` | Pure Python. Tested on Python 3.10–3.12. No known conflicts with Flask 3.1 or existing deps. |
| `python-dateutil==2.9.0` | Python 3.10+ | No conflicts with existing packages. Widely used (transitive dep of many libraries). |
| `dnspython==2.8.0` | Python 3.10+ | Already in requirements.txt. DNSBL queries use the same `dns.resolver.Resolver` already proven in `DnsAdapter`. |

---

## Sources

- [ipapi.is Developer Documentation](https://ipapi.is/developers.html) — Rate limits (1000/day free, no auth), ASN JSON fields confirmed (HIGH confidence)
- [ipapi.is ASN Database](https://ipapi.is/asn.html) — JSON example response with all ASN fields (HIGH confidence)
- [whoisit on PyPI](https://pypi.org/project/whoisit/) — Version 4.0.0, pure Python, requests + dateutil dependencies confirmed (HIGH confidence)
- [whoisit GitHub](https://github.com/meeb/whoisit) — Supported lookup types, field documentation, bootstrap mechanism (HIGH confidence)
- [pydnsbl on PyPI](https://pypi.org/project/pydnsbl/) — Version 1.1.7, asyncio/aiodns dependency confirmed (HIGH confidence)
- [Spamhaus DNSBL Fair Use Policy](https://www.spamhaus.org/blocklists/dnsbl-fair-use-policy/) — Public resolver blocking, error code 127.255.255.254 phased rollout 2025 confirmed (HIGH confidence)
- [Spamhaus Free DQS](https://www.spamhaus.com/data-access/free-data-query-service/) — Free key option available; requires account registration (HIGH confidence)
- [Feodo Tracker Blocklist](https://feodotracker.abuse.ch/blocklist/) — JSON download endpoint confirmed, zero-auth, CC0 license (HIGH confidence)
- [BGPView FAQ / shutdown notice](https://bgpview.io/) — BGPView shutting down November 26, 2025 (HIGH confidence)
- [SURBL multi.surbl.org](https://cwiki.apache.org/confluence/display/SPAMASSASSIN/DnsBlocklists) — Public resolver safe, no key required (MEDIUM confidence — SpamAssassin docs)
- [abuse.ch combined DNSBL](https://www.dnsbl.info/dnsbl-details.php?dnsbl=combined.abuse.ch) — Available, no public resolver restriction documented (MEDIUM confidence)

---

*Stack research for: SentinelX v7.0 Free Intel — DNSBL, threat feeds, RDAP, ASN/BGP*
*Researched: 2026-03-15*
