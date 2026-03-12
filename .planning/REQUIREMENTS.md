# Requirements: SentinelX v6.0 Analyst Experience

**Defined:** 2026-03-12
**Core Value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## v6.0 Requirements

Requirements for the Analyst Experience milestone. Each maps to roadmap phases.

### IP Intelligence (Zero-Auth)

- [x] **IPINT-01**: User can see country, city, and ASN for any IP IOC without configuring an API key
- [x] **IPINT-02**: User can see reverse DNS (PTR) hostname for any IP IOC without an API key
- [x] **IPINT-03**: User can see proxy/VPN/hosting detection flags for any IP IOC without an API key

### Domain Intelligence (Zero-Auth)

- [x] **DINT-01**: User can see live DNS records (A, MX, NS, TXT) for any domain IOC without an API key
- [x] **DINT-02**: User can see certificate transparency history for any domain IOC without an API key
- [x] **DINT-03**: User can see passive DNS history and related IOCs via ThreatMiner for all IOC types without an API key

### Hash Intelligence (Zero-Auth)

- [x] **HINT-01**: User can see whether a file hash is a known-good (NSRL) file via CIRCL hashlookup without an API key
- [x] **HINT-02**: Known-good verdict is visually distinct from malicious/clean/unknown in summary rows and filter bar

### Enhanced Providers

- [x] **EPROV-01**: User can see ports, CVEs, hostnames, and CPEs in Shodan InternetDB result cards

### Deep Analysis

- [ ] **DEEP-01**: User can click any IOC to view a dedicated detail page with all enrichment results in a tabbed layout
- [ ] **DEEP-02**: User can add, edit, and delete notes on any IOC (persisted in SQLite)
- [ ] **DEEP-03**: User can tag IOCs with custom labels (persisted in SQLite)
- [ ] **DEEP-04**: User can view a relationship graph showing connections between IOCs on the detail page

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Workflow Integration

- **WFLOW-01**: User can link enrichment results to external SIEM/SOAR case IDs
- **WFLOW-02**: User can share enrichment results via shareable URL
- **WFLOW-03**: User can schedule recurring enrichment checks for watchlisted IOCs

### Advanced Analysis

- **ADV-01**: User can upload files for hash extraction and enrichment
- **ADV-02**: User can import STIX/TAXII threat feeds

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| WHOIS / RDAP enrichment | Privacy-redaction makes it low-signal; rate limiting causes silent hangs (existing PROJECT.md decision) |
| Domain WHOIS | GDPR redaction returns "REDACTED FOR PRIVACY" as string that looks like valid data |
| File sandbox detonation | Fundamentally different capability — analysis vs execution |
| User authentication | Single-user, local access assumed |
| Mobile / responsive design | Desktop browser on analyst workstation |
| CLI interface | Web is the right UX for paste-and-triage workflow |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| IPINT-01 | Phase 01 | Complete |
| IPINT-02 | Phase 01 | Complete |
| IPINT-03 | Phase 01 | Complete |
| DINT-01 | Phase 02 | Complete |
| DINT-02 | Phase 02 | Complete |
| DINT-03 | Phase 03 | Complete |
| HINT-01 | Phase 01 | Complete |
| HINT-02 | Phase 01 | Complete |
| EPROV-01 | Phase 01 | Complete |
| DEEP-01 | Phase 04 | Pending |
| DEEP-02 | Phase 04 | Pending |
| DEEP-03 | Phase 04 | Pending |
| DEEP-04 | Phase 04 | Pending |

**Coverage:**
- v6.0 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after roadmap creation — all requirements mapped*
