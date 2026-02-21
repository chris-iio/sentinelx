# Requirements: oneshot-ioc

**Defined:** 2026-02-21
**Core Value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Extraction

- [ ] **EXTR-01**: User can paste free-form text (single IOC, SIEM alert snippet, email headers/body, threat report) into a single large input field
- [ ] **EXTR-02**: Application extracts all IOCs from pasted text, supporting IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, and CVE types
- [ ] **EXTR-03**: Application normalizes common defanging patterns (hxxp, hxxps, [.], {.}, (.), [dot], _dot_, [@], [at], [://]) before classification
- [ ] **EXTR-04**: Application classifies each extracted IOC by type using deterministic logic (no ML, no heuristics)
- [ ] **EXTR-05**: Application deduplicates extracted IOCs before enrichment (same normalized value = one lookup)

### Enrichment

- [ ] **ENRC-01**: Application queries VirusTotal API v3 for IP, domain, URL, and hash IOC types and displays detection count, category, and last analysis date
- [ ] **ENRC-02**: Application queries MalwareBazaar API for MD5, SHA1, and SHA256 hashes and displays file type, malware family, tags, and first/last seen
- [ ] **ENRC-03**: Application queries ThreatFox API for hash, domain, IP, and URL IOCs and displays threat type, malware family, confidence level, and C2 indicator status
- [ ] **ENRC-04**: Application executes all provider queries in parallel per IOC (not sequentially)
- [ ] **ENRC-05**: Each enrichment result displays the provider name, lookup timestamp, and raw provider verdict with no transformation or score blending
- [ ] **ENRC-06**: Provider failures return a clear error result per-provider without blocking other providers' results

### UI

- [ ] **UI-01**: Single-page web interface with a large text input field, a submit button, and a visible offline/online mode toggle
- [ ] **UI-02**: In offline mode, only extraction, normalization, and classification are performed — zero outbound network calls
- [ ] **UI-03**: In online mode, enrichment queries fire after extraction and classification complete
- [ ] **UI-04**: Results page groups extracted IOCs by type (IPv4, IPv6, domain, URL, hash, CVE)
- [ ] **UI-05**: Visual loading indicator is displayed while enrichment API calls are in progress
- [ ] **UI-06**: Results clearly distinguish between "no data found" (provider has no record) and "clean verdict" (provider explicitly reports benign)
- [ ] **UI-07**: UI visually indicates whether the current submission used offline or online mode

### Security

- [ ] **SEC-01**: Application binds to 127.0.0.1 only by default
- [ ] **SEC-02**: API keys are read exclusively from environment variables, never from config files, CLI args, or query parameters
- [ ] **SEC-03**: Application fails fast at startup with a clear error if required API keys are missing (when online mode is configured)
- [ ] **SEC-04**: All outbound HTTP requests enforce strict per-request timeouts (no indefinite hangs)
- [ ] **SEC-05**: All outbound HTTP requests enforce a maximum response size limit (streaming + byte counting)
- [ ] **SEC-06**: Outbound HTTP requests do not follow redirects unless explicitly justified per-provider
- [ ] **SEC-07**: Application never fetches, crawls, or makes HTTP requests to the IOC URL itself — only calls TI API endpoints
- [ ] **SEC-08**: All IOC strings and API response fields are HTML-escaped before rendering (Jinja2 autoescaping, no |safe on untrusted data)
- [ ] **SEC-09**: Content Security Policy header blocks inline scripts (default-src 'self'; script-src 'self')
- [ ] **SEC-10**: CSRF protection is enabled on all POST endpoints
- [ ] **SEC-11**: Host header validation rejects requests from unexpected origins (TRUSTED_HOSTS for DNS rebinding prevention)
- [ ] **SEC-12**: Input size is capped (MAX_CONTENT_LENGTH) to prevent ReDoS and memory exhaustion
- [ ] **SEC-13**: No subprocess calls, no shell execution, no eval/exec anywhere in the codebase
- [ ] **SEC-14**: No persistent storage of raw pasted text blobs
- [ ] **SEC-15**: Debug mode is hardcoded to False in all non-development entry points
- [ ] **SEC-16**: Outbound API calls only target hostnames on an explicit allowlist (SSRF prevention)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Additional Providers

- **ENRC-07**: Application queries AbuseIPDB for IPv4/IPv6 IOCs and displays abuse confidence score, ISP, country, and total reports
- **ENRC-08**: Application queries Shodan InternetDB for IPv4 IOCs and displays open ports, CPEs, CVEs, hostnames, and tags (no API key required)
- **ENRC-09**: Application queries AlienVault OTX for IP, domain, URL, and hash IOCs and displays associated pulses/campaigns and geo data
- **ENRC-10**: Application queries GreyNoise for IPv4 IOCs and displays noise/RIOT classification and last seen date
- **ENRC-11**: Application queries URLhaus for URL and hash IOCs and displays URL status, tags, and associated payloads

### Caching & UX

- **CACH-01**: API results are cached in-memory with per-provider TTL to avoid redundant quota usage
- **UX-01**: IOC count summary is displayed after extraction, before enrichment API calls fire (confirmation step)
- **UX-02**: Copy-to-clipboard button per IOC (refanged form)
- **UX-03**: Result freshness display shows provider's first_seen/last_seen timestamps where available

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Combined threat score / risk rating | Hides conflicting signals, creates false confidence; analysts need raw per-provider verdicts |
| Fetching or crawling target URLs | Exposes analyst IP to adversary, contaminates forensic evidence, serious SSRF vector |
| Email sending of results | SMTP config creates data exfiltration path; single-user local tool |
| Automated blocking/response actions | Read-only enrichment scope; write actions require auth, audit logs, rollback |
| User authentication / multi-user | Single-user local tool; auth system adds complexity with no benefit |
| Real-time monitoring / scheduled lookups | Single-shot triage by design; persistent monitoring requires different architecture |
| WHOIS / RDAP enrichment | High complexity, often privacy-redacted; SecurityTrails free tier too restrictive (50/month) |
| Malware sandbox detonation | Fundamentally different capability requiring containerization |
| Mobile / responsive UI | Desktop analyst workstation only |
| Persistent session history | Requires persistence design decision; defer to v2+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXTR-01 | — | Pending |
| EXTR-02 | — | Pending |
| EXTR-03 | — | Pending |
| EXTR-04 | — | Pending |
| EXTR-05 | — | Pending |
| ENRC-01 | — | Pending |
| ENRC-02 | — | Pending |
| ENRC-03 | — | Pending |
| ENRC-04 | — | Pending |
| ENRC-05 | — | Pending |
| ENRC-06 | — | Pending |
| UI-01 | — | Pending |
| UI-02 | — | Pending |
| UI-03 | — | Pending |
| UI-04 | — | Pending |
| UI-05 | — | Pending |
| UI-06 | — | Pending |
| UI-07 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| SEC-03 | — | Pending |
| SEC-04 | — | Pending |
| SEC-05 | — | Pending |
| SEC-06 | — | Pending |
| SEC-07 | — | Pending |
| SEC-08 | — | Pending |
| SEC-09 | — | Pending |
| SEC-10 | — | Pending |
| SEC-11 | — | Pending |
| SEC-12 | — | Pending |
| SEC-13 | — | Pending |
| SEC-14 | — | Pending |
| SEC-15 | — | Pending |
| SEC-16 | — | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 0
- Unmapped: 34 ⚠️

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after initial definition*
