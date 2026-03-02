# SentinelX v4.0 — Universal Threat Intel Hub

**Date:** 2026-03-02
**Status:** Approved
**Scope:** Expand SentinelX from 3 providers to 8+, with provider registry architecture and unified results UX

## Vision

Transform SentinelX from a paste-and-extract IOC triage tool into a universal threat intelligence hub. An analyst pastes text (or types an IOC), and SentinelX searches across all configured providers simultaneously — VirusTotal, MalwareBazaar, ThreatFox, Shodan, OTX, URLhaus, GreyNoise, AbuseIPDB — presenting a unified summary with expandable per-provider details.

## What Stays

- Paste text -> extract IOCs -> enrich flow (core UX unchanged)
- All existing providers (VirusTotal, MalwareBazaar, ThreatFox)
- TypeScript frontend, Flask backend, existing security model
- CSP-safe IIFE bundle, esbuild pipeline
- Localhost-only binding, strict timeouts, SSRF allowlists

## Architecture: Provider Registry

### Current State

Three hardcoded adapters (VT, MB, TF), each independently implementing `lookup()`. The `EnrichmentOrchestrator` dispatches IOCs to adapters based on `supported_types`.

### Target State

A provider registry pattern where:

- Each provider is a self-contained adapter module implementing a common `Provider` protocol
- A registry maps provider names -> adapter instances, auto-discovered at startup
- The orchestrator queries the registry for "which providers support this IOC type?" instead of hardcoding
- New providers are added by dropping in an adapter file — zero changes to orchestrator code

### Provider Protocol

```python
class Provider(Protocol):
    name: str
    supported_types: set[IocType]
    requires_api_key: bool

    def lookup(self, ioc_value: str, ioc_type: str) -> EnrichmentResult | EnrichmentError: ...
    def is_configured(self) -> bool: ...
```

## New Providers

### Priority 1: Zero-Auth

| Provider | Endpoint | IOC Types | Verdict Logic |
|----------|----------|-----------|---------------|
| Shodan InternetDB | `GET https://internetdb.shodan.io/{ip}` | IP | has vulns -> suspicious; known-bad tags -> malicious; else informational |

### Priority 2: Free-Key

| Provider | Endpoint | IOC Types | Verdict Logic |
|----------|----------|-----------|---------------|
| URLhaus | `POST https://urlhaus-api.abuse.ch/v1/{type}/` | URL, Hash, IP, Domain | is_listed -> malicious; else no_data |
| OTX AlienVault | `GET https://otx.alienvault.com/api/v1/indicators/{type}/{value}/general` | IP, Domain, URL, Hash, **CVE** | pulse_count 1-5 -> suspicious; 5+ -> malicious; 0 -> no_data |
| GreyNoise Community | `GET https://api.greynoise.io/v3/community/{ip}` | IP | riot -> clean; malicious classification -> malicious; noise -> suspicious |
| AbuseIPDB | `GET https://api.abuseipdb.com/api/v2/check?ipAddress={ip}` | IP | score >= 75 -> malicious; 25-74 -> suspicious; < 25 w/reports -> clean; 0 reports -> no_data |

### Provider Coverage Matrix (after v4.0)

| IOC Type | Providers |
|----------|-----------|
| IPv4/IPv6 | VT, TF, OTX, GreyNoise, AbuseIPDB, Shodan, URLhaus |
| Domain | VT, TF, OTX, URLhaus |
| URL | VT, TF, OTX, URLhaus |
| MD5/SHA1/SHA256 | VT, MB, TF, OTX, URLhaus |
| CVE | **OTX** (first CVE provider) |

## Results UX: Unified Summary + Expandable Details

### Tier 1 — Summary (always visible per IOC card)

- IOC value + type badge
- Worst verdict across all providers (MALICIOUS / SUSPICIOUS / CLEAN / NO DATA)
- Provider agreement: "3/5 providers flagged" or "0/8 providers flagged"
- Confidence signal based on consensus

### Tier 2 — Provider details (expandable)

- Click to expand individual provider results
- Each provider row: name, verdict badge, key details (detection ratio, abuse score, pulse count, etc.)
- Providers returning "no data" shown greyed out
- Timestamp per lookup

### Dashboard

- Verdict counts (existing) + provider coverage ("8 providers active, 3 need API keys")

### Filtering

- Existing filter bar filters on unified worst-verdict (unchanged behavior, new data)

## Settings: Provider Management

- List all registered providers with status indicators
- **Active**: configured and working
- **Needs Key**: requires API key, not yet configured
- **No Key Required**: always active (Shodan InternetDB, MalwareBazaar, ThreatFox)
- API key input field per provider that needs one
- "Test Connection" button per provider
- All keys stored in `~/.sentinelx/config.ini` with `0o600` permissions (existing pattern)

## Security Model

All existing security controls extend to new providers:

- SSRF allowlist per adapter (`ALLOWED_API_HOSTS`)
- Strict HTTP timeouts (5s connect, 30s read)
- 1MB response size cap
- No redirect following
- API keys from config file only (never hardcoded, never logged)
- All API responses treated as untrusted (validated before rendering)

## Phasing

1. **v3.0 Phase 23**: Finish TypeScript type hardening (already planned)
2. **v4.0 Phase 1**: Provider registry refactor — extract protocol, build registry, refactor existing 3 adapters
3. **v4.0 Phase 2**: Zero-auth providers — Shodan InternetDB (immediate value, no config)
4. **v4.0 Phase 3**: Free-key providers — URLhaus, OTX, GreyNoise, AbuseIPDB + settings page expansion
5. **v4.0 Phase 4**: Results UX upgrade — unified summary, expandable details, provider consensus

## Future (out of scope for v4.0)

- File upload (hash-and-search, optional submit to providers)
- Paid-tier providers (Shodan full API, GreyNoise Enterprise)
- Search history / bookmarks
- IOC relationship graphs
- WHOIS/RDAP enrichment
