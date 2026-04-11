# Requirements: SentinelX

**Defined:** 2026-03-16
**Core Value:** Safe, correct, and transparent IOC extraction and enrichment

## v1.1 Requirements

Requirements for the Results Page Redesign. Each maps to roadmap phases.

### Visual Hierarchy

- [ ] **VIS-01**: Worst verdict is the dominant visual element in each IOC card header
- [ ] **VIS-02**: Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)
- [ ] **VIS-03**: Provider rows display distinct category labels distinguishing Reputation from Infrastructure

### Information Grouping

- [ ] **GRP-01**: Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data
- [ ] **GRP-02**: No-data providers are collapsed by default with a count summary ("5 had no record")

### Context Visibility

- [ ] **CTX-01**: Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding
- [ ] **CTX-02**: Cached results show a staleness indicator ("data from 4h ago") in the summary row

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Context Visibility

- **CTX-03**: Scan date from verdict providers shown on summary row
- **CTX-04**: Per-category expand/collapse toggle (collapse Infrastructure for clean IOCs)

### Results Organization

- **ORG-01**: IOC card sort by IOC type as alternative to severity sort (for mixed bulk input)

### DNSBL Reputation (from v7.0)

- **DNSBL-01**: IP reputation via Spamhaus ZEN + Barracuda + SpamCop
- **DNSBL-02**: Domain reputation via Spamhaus DBL + SURBL
- **DNSBL-03**: IPv6 DNSBL with nibble reversal

## Out of Scope

| Feature | Reason |
|---------|--------|
| Composite threat score | Core design philosophy: never invent scores — transparency over convenience |
| Provider logos in rows | Page weight (14 logos x N IOCs), licensing, textContent-only DOM constraint |
| Auto-expand all IOC cards | 10 IOCs x 14 providers = 140 rows — catastrophic for scan time |
| Tabs replacing accordion | Complex per-card tab state; breaks at-a-glance comparison across IOCs |
| Analyst verdict overrides | Annotations removed in v7.0; couples triage to case management |
| New providers | v1.1 is presentation-only — no new data sources |
| Detail page redesign | Architecturally independent (CSS-only tabs); defer to v1.2 if needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VIS-01 | Phase 3 | Pending |
| VIS-02 | Phase 3 | Pending |
| VIS-03 | Phase 3 | Pending |
| GRP-01 | Phase 4 | Pending |
| GRP-02 | Phase 3 | Pending |
| CTX-01 | Phase 5 | Pending |
| CTX-02 | Phase 5 | Pending |

**Coverage:**
- v1.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 — traceability populated after roadmap creation*
