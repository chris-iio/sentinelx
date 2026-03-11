# Stack Research

**Domain:** Threat intelligence enrichment — zero-auth/no-API-key deep analysis capabilities
**Researched:** 2026-03-11
**Confidence:** HIGH (all versions verified against PyPI and official documentation)

---

## Context: Additive Stack Only

SentinelX v5.0 baseline is locked and validated. This document covers ONLY new
libraries needed for v6.0 analyst experience expansion. Do not re-evaluate Flask,
requests, iocextract, iocsearcher, esbuild, Tailwind, or the existing 8 provider
adapters — they are not in scope.

The question this research answers: what Python libraries enable deep analysis without
API keys? Which free databases can be bundled or downloaded?

---

## New Library Recommendations

### Tier 1: Core Zero-Auth Enrichment

These three libraries enable the most analyst-valuable enrichment and should be added
immediately. All are zero-auth at query time.

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `dnspython` | 2.8.0 | Active DNS resolution (A, AAAA, MX, NS, TXT, PTR, SOA records) | The standard Python DNS toolkit — used by Ansible, MISP, and every serious Python security tool. Zero external dependencies beyond stdlib. Python 3.10+ (matches baseline). No API key, no rate-limit account, no database files. A single `dns.resolver.resolve(domain, "MX")` call returns mail server info. MX + NS + TXT records give analysts SPF, DMARC, mail infrastructure, and nameserver context in one shot. |
| `geoip2` | 5.2.0 | Offline IP geolocation (country, city, ASN, org name) from local .mmdb database | Official MaxMind Python client. Reads local .mmdb files — zero network calls at lookup time. Python 3.10+ required (matches baseline). GeoLite2 databases are free with a MaxMind account; the license key is only used for the initial download. Runtime lookups are fully offline. The GeoLite2-ASN database (9 MB) is particularly valuable: maps any IP to its Autonomous System Number and organization name without any API call. |
| `ipwhois` | 1.3.0 | IP-to-ASN, netblock owner, and network registration data via RDAP | No API key. Queries public IANA/RDAP registries directly. `lookup_rdap()` returns structured dicts with org name, ASN, CIDR, country, and RIR — richer ownership context than geoip2 for threat triage. Complements geoip2: geoip2 gives geographic location from a local file (fast, offline), ipwhois gives current netblock ownership from RDAP (slower, online, more authoritative). Both are needed. |

### Tier 2: Domain Intelligence

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| *(none — use requests directly)* | — | Certificate transparency log queries via crt.sh | The crt.sh service exposes a public JSON API (`https://crt.sh/?q=<domain>&output=json`) with zero authentication. It returns issued certificates, Subject Alternative Names (SANs), issuer details, and validity periods. A direct `requests.get()` call using the existing `requests` dependency is sufficient. No new library required. SAN enumeration from CT logs is high-value for phishing detection — typosquatters always issue certs. |

**Note on pycrtsh:** The `pycrtsh` library (version 0.3.14, October 2025) wraps crt.sh but
requires `psycopg2-binary` and `lxml` as transitive dependencies, which pull in C compilation
and PostgreSQL adapter complexity. The direct `requests` approach covers every use case needed
for triage enrichment. Reach for pycrtsh only if the direct HTTP API proves unreliable or if
PostgreSQL direct-connect to crt.sh's database is required for advanced filtering — neither
condition is likely for a single-shot triage tool.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pyasn` | Requires offline BGP MRT dump files (100+ MB) that need weekly refresh from RIPE/RouteViews. Significant operational burden for an analyst workstation tool. | `ipwhois` RDAP returns ASN with zero local database management. |
| `python-whois`, `whoisit`, `whodap` | WHOIS text is inconsistently formatted across TLDs and privacy-redacted for the majority of registrations since GDPR. PROJECT.md explicitly lists "WHOIS / RDAP enrichment — high complexity, often privacy-redacted" as out of scope. This constraint is correct. | Skip WHOIS for domains entirely. Use `ipwhois` RDAP for IPs (structured, reliable). |
| `certstream` | Live CT log streaming requires a persistent WebSocket connection. Fundamentally incompatible with SentinelX's single-shot triage model. | Direct crt.sh JSON API queries via `requests` for historical CT data. |
| `aiodns` | Async DNS requires event loop integration that conflicts with Flask's synchronous request handling and the existing thread-pool-based enrichment orchestrator. | `dnspython` synchronous interface — clean fit with current architecture. |
| Any GeoIP web service API (ipinfo.io, ipgeolocation.io, etc.) | All require API key registration. Adds another external dependency when GeoLite2 offline solves the same problem for a locally-deployed tool. | `geoip2` + locally downloaded GeoLite2 .mmdb files. |
| `IP2Location LITE` | Less accurate than GeoLite2, smaller Python ecosystem, less maintained. MaxMind GeoLite2 is the industry standard for free offline geolocation. | `geoip2` with GeoLite2 databases. |
| `pycrtsh` | psycopg2-binary + lxml C extension overhead for a task that `requests` handles equally well. | Direct `requests.get()` to crt.sh JSON API. |

---

## Database Dependencies (not Python packages)

### MaxMind GeoLite2 .mmdb Files

Required for `geoip2` offline lookups. These are binary database files, not Python packages.

| Database | Filename | Size | Content |
|----------|----------|------|---------|
| GeoLite2-City | `GeoLite2-City.mmdb` | ~70 MB | Country, region, city, postal code, lat/lon for IP |
| GeoLite2-ASN | `GeoLite2-ASN.mmdb` | ~9 MB | ASN number + organization name for IP |

**Acquisition:** Free download from MaxMind after free account registration at
`maxmind.com/en/geolite2/signup`. A license key is issued — used only in the download URL, not
at query time. Lookups are fully offline once the .mmdb files are on disk. MaxMind releases
database updates twice monthly; the EULA requires deletion within 30 days of a new release.

**Storage:** `~/.sentinelx/geoip/GeoLite2-City.mmdb` and `~/.sentinelx/geoip/GeoLite2-ASN.mmdb`

**Do NOT bundle in the repository.** The .mmdb files are 70+ MB binary assets with their own
EULA. Store the MaxMind license key in ConfigStore (`~/.sentinelx/config.ini`) and provide a
`make geoip-update` target or Flask CLI command to download/refresh the databases.

**Fallback behavior:** When .mmdb files are absent, the GeoIP provider adapter must return
`no_data` verdict (not error) — same pattern as API-key providers without configured keys.
The settings UI should display a download prompt with instructions.

---

## Integration with Existing Provider Architecture

All new libraries integrate as Provider Protocol adapters. Zero changes to the orchestrator,
registry, or routes. Each new capability = one adapter file + one `register()` call in `setup.py`.

### Adapter Map

| Adapter file | Library | Supported IOC Types | requires_api_key | Notes |
|-------------|---------|---------------------|------------------|-------|
| `dns_provider.py` | `dnspython` | `Domain`, `URL` | `False` | A/AAAA/MX/NS/TXT/PTR records; derive verdict from MX presence, SPF/DMARC in TXT records |
| `geoip_provider.py` | `geoip2` | `IPv4`, `IPv6` | `False` | Country, city, ASN from offline .mmdb; `is_configured()` returns `False` if .mmdb absent |
| `ipwhois_provider.py` | `ipwhois` | `IPv4`, `IPv6` | `False` | RDAP lookup: org, netblock CIDR, RIR, ASN; complements geoip2 for ownership context |
| `crtsh_provider.py` | `requests` (existing) | `Domain` | `False` | Direct HTTP to `crt.sh/?q=<domain>&output=json`; existing `http_safety` module applies |

**CrtShProvider reuses the existing `requests` dependency.** The `http_safety` module's SSRF
allowlist, timeout constant, and `read_limited()` stream reader apply directly to crt.sh queries.
Add `crt.sh` to the SSRF allowlist (`ALLOWED_API_HOSTS`).

---

## Installation

```bash
# Tier 1 — Core zero-auth enrichment libraries
pip install dnspython==2.8.0 geoip2==5.2.0 ipwhois==1.3.0

# GeoLite2 databases (not pip — downloaded separately via MaxMind)
# Requires a free MaxMind account and license key
# Store databases at: ~/.sentinelx/geoip/
# See MaxMind download documentation: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/
```

No Tier 2 pip installs are needed — crt.sh integration uses the existing `requests` package.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `dnspython` | stdlib `socket.getaddrinfo()` | Never — socket resolves only A/AAAA. dnspython is the only option for MX/TXT/NS/PTR queries. |
| `geoip2` + GeoLite2 (offline) | Online GeoIP APIs (ipinfo.io, ipgeolocation.io) | Only if the operator refuses to manage local database files and accepts API key registration and rate limits. Wrong model for a workstation-local tool. |
| `ipwhois` RDAP | `pyasn` + offline BGP dump | Never for this use case. pyasn requires 100+ MB BGP database files with weekly refresh and complex setup. `ipwhois` RDAP is simpler, zero local files, and free. |
| Direct `requests` to crt.sh JSON API | `pycrtsh` library | Only if direct HTTP proves unreliable for CT log queries or if PostgreSQL direct-connect is required for advanced filtering. Neither condition is likely for triage. |
| Skip WHOIS for domains | Any WHOIS library | Per PROJECT.md constraints. Privacy-redaction makes domain WHOIS low-signal for most real-world IOCs. The constraint is valid — hold it. |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `dnspython==2.8.0` | Python 3.10+ | Matches SentinelX baseline exactly. Released September 2025. No external dependencies. |
| `geoip2==5.2.0` | Python 3.10–3.14, `requests>=2.24.0` | `requests==2.32.5` already in requirements.txt — no version conflict. Released November 2025. |
| `ipwhois==1.3.0` | Python up to 3.12 | Tested through 3.12; no conflicts with Flask 3.1 or existing deps. Released October 2024. Note: last release does not yet formally list 3.13+ but no known breakage. |

---

## Stack Patterns

**If GeoLite2 databases are not present:**
- `GeoIpProvider.is_configured()` returns `False`
- Provider is excluded from enrichment (same pattern as API-key providers with no key set)
- Settings UI shows a download prompt with MaxMind account link and instructions

**If DNS lookup times out:**
- `DnsProvider` returns `EnrichmentError` with `"Timeout"` message (consistent with all existing providers)
- Set `dns.resolver.Resolver.timeout = 5` and `lifetime = 10` (align with existing `TIMEOUT = (5, 30)` constant in `http_safety.py`)

**If ipwhois RDAP hits rate limiting:**
- LACNIC (Latin American IPs) is the only RIR known to impose aggressive rate limits
- Return `EnrichmentError("Rate limited")` — do not retry automatically
- Analyst can re-query if needed; this is consistent with existing HTTP 429 handling

**For crt.sh queries:**
- Add `crt.sh` to `ALLOWED_API_HOSTS` in the SSRF allowlist
- Apply existing `TIMEOUT`, `read_limited()`, and `allow_redirects=False` controls
- 404 from crt.sh means no certs found — return `verdict="no_data"`, not an error

---

## Sources

- [dnspython PyPI](https://pypi.org/project/dnspython/) — Version 2.8.0 confirmed, Python 3.10+ (HIGH confidence)
- [dnspython Resolver docs](https://dnspython.readthedocs.io/en/latest/resolver-class.html) — Resolver API and supported record types (HIGH confidence)
- [geoip2 PyPI](https://pypi.org/project/geoip2/) — Version 5.2.0 confirmed, Python 3.10+ (HIGH confidence)
- [geoip2 ReadTheDocs](https://geoip2.readthedocs.io/) — Database reader API (HIGH confidence)
- [MaxMind GeoLite2 developer docs](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/) — Free databases confirmed; registration and license key required for download; runtime lookups are offline (HIGH confidence)
- [ipwhois PyPI](https://pypi.org/project/ipwhois/) — Version 1.3.0 confirmed (HIGH confidence)
- [ipwhois RDAP docs](https://ipwhois.readthedocs.io/en/latest/RDAP.html) — RDAP lookup API, structured dict output (HIGH confidence)
- [pycrtsh PyPI](https://pypi.org/project/pycrtsh/) — Version 0.3.14, October 2025, psycopg2-binary + lxml dependencies confirmed (HIGH confidence)
- [crt.sh JSON API](https://crt.sh/?q=example.com&output=json) — Zero-auth public API, JSON fields confirmed live (HIGH confidence)
- [GitHub rthalley/dnspython](https://github.com/rthalley/dnspython) — Active maintenance, September 2025 release (HIGH confidence)
- [GitHub maxmind/GeoIP2-python](https://github.com/maxmind/GeoIP2-python) — Official MaxMind Python client (HIGH confidence)

---

*Stack research for: SentinelX v6.0 zero-auth deep analysis capabilities*
*Researched: 2026-03-11*
