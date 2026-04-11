# Requirements: SentinelX

**Defined:** 2026-04-12
**Core Value:** Safe, correct, and transparent IOC extraction and enrichment

## v1.2 Requirements

Requirements for SSH Login Anomaly Detection. Each maps to roadmap phases.

### Parsing

- [ ] **PARSE-01**: Parser extracts structured login events from auth.log lines containing "Accepted password" or "Accepted publickey" — each event has username, source IP, and timestamp
- [ ] **PARSE-02**: Parser detects BSD syslog and RFC3339 timestamp formats per-line and handles year rollover for BSD timestamps (December→January boundary)
- [ ] **PARSE-03**: Parser supports both IPv4 and IPv6 source addresses
- [ ] **PARSE-04**: Parser handles hostname entries when sshd UseDNS is enabled — skip GeoIP for non-IP values

### Detection

- [ ] **DETECT-01**: Detector flags login from an IP never seen before for that user (low risk)
- [ ] **DETECT-02**: Detector flags login from a country never seen before for that user (medium risk)
- [ ] **DETECT-03**: Detector flags login outside configurable hour window (default 6am–10pm) as unusual hour (medium risk)
- [ ] **DETECT-04**: Detector flags impossible travel — different country with less than 3 hours elapsed since last login from a different country (high risk)
- [ ] **DETECT-05**: Detector deduplicates alerts — one alert per (user, IP, rule_type) combination, not per log line
- [ ] **DETECT-06**: Each alert includes username, timestamp, IP address, country, human-readable reason, and risk level (low/medium/high)

### GeoIP

- [ ] **GEO-01**: GeoIP lookup maps IP addresses to country codes via ipinfo.io using existing http_safety infrastructure
- [ ] **GEO-02**: GeoIP deduplicates IPs before lookup — one request per unique IP, not per log line
- [ ] **GEO-03**: GeoIP degrades gracefully if ipinfo.io is unavailable — skip country-based rules (DETECT-02, DETECT-04), still run IP and hour rules
- [ ] **GEO-04**: GeoIP returns latitude/longitude for impossible travel distance calculation

### Web Interface

- [ ] **WEB-01**: GET /ssh route shows an upload form for auth.log files with file size guidance
- [ ] **WEB-02**: POST /ssh/upload accepts file upload, parses it, runs detection, and displays flagged alerts in a table
- [ ] **WEB-03**: GET /ssh/events returns all flagged alerts as JSON
- [ ] **WEB-04**: SSH section appears as a navigation item in existing SentinelX UI shell (shared base.html)
- [ ] **WEB-05**: Alerts table shows username, timestamp, IP, country, reason, and risk level with risk-appropriate visual styling
- [ ] **WEB-06**: MAX_CONTENT_LENGTH increased from 512KB to 5MB to accommodate auth.log file uploads

### Configuration

- [ ] **CFG-01**: Normal hours window is configurable via ConfigStore [ssh] section (default 6am–10pm)

## Previous Milestone Requirements (v1.1 — partial)

v1.1 Phases 1-2 completed; Phases 3-5 dropped. Completed work retained as infrastructure.

### Completed (v1.1 Phases 1-2)

- ✓ **CSS-CONTRACTS**: CSS contract catalog documenting all E2E-locked selectors — Phase 1
- ✓ **TS-EXTRACT**: enrichment.ts split into verdict-compute.ts, row-factory.ts, enrichment.ts — Phase 2

### Deferred (v1.1 Phases 3-5)

- **VIS-01**: Worst verdict as dominant visual element — deferred
- **VIS-02**: Visual count bar replacing text consensus badge — deferred
- **VIS-03**: Category labels on provider rows — deferred
- **GRP-01**: Three-section grouping (Reputation, Infrastructure, No Data) — deferred
- **GRP-02**: No-data collapse with count summary — deferred
- **CTX-01**: Context fields in card header — deferred
- **CTX-02**: Staleness indicator — deferred

## Future Requirements

### DNSBL Reputation (from v7.0)

- **DNSBL-01**: IP reputation via Spamhaus ZEN + Barracuda + SpamCop
- **DNSBL-02**: Domain reputation via Spamhaus DBL + SURBL
- **DNSBL-03**: IPv6 DNSBL with nibble reversal

### Results Organization

- **ORG-01**: IOC card sort by IOC type as alternative to severity sort

## Out of Scope

| Feature | Reason |
|---------|--------|
| Other log types (Apache, nginx, syslog) | SSH auth.log only for v1.2 — focused scope |
| ML/AI anomaly models | Simple rule-based detection per spec — explainable over complex |
| Real-time log streaming/tailing | Upload-based batch analysis only |
| Generic SIEM platform | SSH detection is a focused addition, not a platform pivot |
| Failed login / brute-force detection | v1.2 scope is successful login anomalies only |
| Persistent history across uploads | In-memory per-upload only; no cross-session learning |
| GeoLite2 local database | ipinfo.io reuse avoids download requirement |
| Composite threat score | Core design philosophy: transparency over convenience |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (populated after roadmap creation) | | |

**Coverage:**
- v1.2 requirements: 17 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-04-12*
*Last updated: 2026-04-12 after v1.2 milestone initialization*
