# Requirements: SentinelX

**Defined:** 2026-03-15
**Core Value:** Safe, correct, and transparent IOC extraction and enrichment

## v7.0 Requirements

Requirements for v7.0 Free Intel. Each maps to roadmap phases.

### Cleanup

- [ ] **CLEAN-01**: Annotations feature (notes, tags, tag filtering, AnnotationStore) is fully removed — no notes/tags UI on any page
- [ ] **CLEAN-02**: Annotation API routes (/api/annotations/*) no longer exist

### RDAP Registration

- [ ] **RDAP-01**: User sees domain registration data (registrar, creation date as "registered N days ago", nameservers) for domain IOCs
- [ ] **RDAP-02**: User sees IP registration data (network block name, org, CIDR, country) for IP IOCs
- [ ] **RDAP-03**: RDAP provider resolves SEC-06 redirect conflict with documented design decision before implementation

### Threat Feeds

- [ ] **FEED-01**: User sees Feodo Tracker C2 verdict for IP IOCs — malicious with malware family on hit, clean when absent

### ASN/BGP Intelligence

- [ ] **ASN-01**: User sees ASN/BGP context (CIDR prefix, RIR, allocation date) for IP IOCs via Team Cymru DNS

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### DNSBL Reputation

- **DNSBL-01**: IP reputation via Spamhaus ZEN + Barracuda + SpamCop
- **DNSBL-02**: Domain reputation via Spamhaus DBL + SURBL
- **DNSBL-03**: IPv6 DNSBL with nibble reversal

### RDAP Extensions

- **RDAP-04**: RDAP abuse contact email extraction

## Out of Scope

| Feature | Reason |
|---------|--------|
| WHOIS in any form | Sunsetted by ICANN January 2025; RDAP is the sole standard |
| RDAP registrant contact fields | 58%+ return "REDACTED FOR PRIVACY" due to GDPR; noise not signal |
| BGP path visualization | Dynamic data misleading as static snapshot; high frontend cost for low triage value |
| PhishTank | New user registration closed since 2020; cannot obtain API key |
| BGPView | Service shut down November 2025 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEAN-01 | — | Pending |
| CLEAN-02 | — | Pending |
| RDAP-01 | — | Pending |
| RDAP-02 | — | Pending |
| RDAP-03 | — | Pending |
| FEED-01 | — | Pending |
| ASN-01 | — | Pending |

**Coverage:**
- v7.0 requirements: 7 total
- Mapped to phases: 0
- Unmapped: 7

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after initial definition*
