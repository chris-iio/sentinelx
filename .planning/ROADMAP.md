# Roadmap: oneshot-ioc

## Overview

sentinelx is built in four phases, each delivering a complete, verifiable capability. Phase 1 delivers a fully functional offline pipeline — the analyst can paste text, see extracted and classified IOCs, and trust that no network calls are made. Phase 2 wires in VirusTotal enrichment through a parallel orchestrator, proving the full online request flow end-to-end. Phase 3 adds MalwareBazaar and ThreatFox as additive provider adapters with no changes to existing code. Phase 4 sharpens analyst UX (verdict clarity, visual affordances) and verifies the security posture before shipping. Security defenses are established in Phase 1 — they are never retrofitted.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Offline Pipeline** - Flask app with security scaffold, IOC extraction/normalization/classification, and complete offline mode
- [ ] **Phase 2: Core Enrichment** - VirusTotal enrichment via parallel orchestrator, full online mode end-to-end
- [ ] **Phase 3: Additional TI Providers** - MalwareBazaar and ThreatFox adapters completing the v1 provider set
- [ ] **Phase 4: UX Polish and Security Verification** - Verdict clarity, analyst UX refinements, and full security checklist confirmation

## Phase Details

### Phase 1: Foundation and Offline Pipeline
**Goal**: Analyst can paste free-form text and receive extracted, classified, deduplicated IOCs — with zero outbound network calls and a hardened security posture
**Depends on**: Nothing (first phase)
**Requirements**: EXTR-01, EXTR-02, EXTR-03, EXTR-04, EXTR-05, UI-01, UI-02, UI-04, UI-07, SEC-01, SEC-02, SEC-03, SEC-08, SEC-09, SEC-10, SEC-11, SEC-12, SEC-13, SEC-14, SEC-15, SEC-16
**Success Criteria** (what must be TRUE):
  1. Analyst pastes a block of mixed defanged text and the app extracts all IOCs, correctly normalized and classified by type, with duplicates collapsed to one entry
  2. In offline mode, submitting a paste makes zero outbound network calls — verified by a test that asserts no HTTP calls occur
  3. Results page groups IOCs by type (IPv4, IPv6, domain, URL, hash, CVE) and clearly indicates offline mode was used
  4. Submitting a POST request with a Host header not on the trusted list returns HTTP 400
  5. Pasting a 600 KB blob is rejected before extraction runs with a clear error message
**Plans:** 2/4 plans executed
Plans:
- [ ] 01-01-PLAN.md — Project scaffold, app factory with security config, models, test fixtures
- [ ] 01-02-PLAN.md — TDD: IOC normalizer (defanging) and classifier (type detection)
- [ ] 01-03-PLAN.md — TDD: IOC extractor (iocextract + iocsearcher) and pipeline integration
- [ ] 01-04-PLAN.md — Routes, templates, static assets, and visual verification

### Phase 2: Core Enrichment
**Goal**: Analyst can submit in online mode and receive VirusTotal enrichment results for all supported IOC types, displayed with source attribution and no combined score, while all HTTP safety controls are in force
**Depends on**: Phase 1
**Requirements**: ENRC-01, ENRC-04, ENRC-05, ENRC-06, UI-03, UI-05, SEC-04, SEC-05, SEC-06, SEC-07
**Success Criteria** (what must be TRUE):
  1. Online mode submission shows VirusTotal results for IP, domain, URL, and hash IOCs, each attributed with provider name, timestamp, and raw verdict
  2. All VirusTotal queries for a multi-IOC paste fire in parallel, not sequentially — verified by timing or mock call order
  3. A loading indicator is visible while enrichment calls are in progress
  4. When VirusTotal is unreachable, the result for that IOC shows a clear per-provider error rather than crashing or blocking other results
  5. No outbound request follows a redirect, and no outbound request targets an IOC value as a URL — verified by HTTP client configuration test
**Plans**: TBD

### Phase 3: Additional TI Providers
**Goal**: Analyst receives enrichment from MalwareBazaar (for hashes) and ThreatFox (for hashes, domains, IPs, URLs) alongside VirusTotal, completing the v1 provider set
**Depends on**: Phase 2
**Requirements**: ENRC-02, ENRC-03
**Success Criteria** (what must be TRUE):
  1. Submitting a SHA256 hash returns enrichment results from all three providers (VirusTotal, MalwareBazaar, ThreatFox) in the same results view
  2. A MalwareBazaar or ThreatFox failure returns a per-provider error result without affecting VirusTotal results or other providers
  3. Each provider adapter is independently testable with mocked HTTP — no shared state between adapters
**Plans**: TBD

### Phase 4: UX Polish and Security Verification
**Goal**: Analyst can clearly distinguish "no record found" from "explicitly clean verdict" for every provider result, the UI communicates enrichment state without blocking, and the full security posture is confirmed before shipping
**Depends on**: Phase 3
**Requirements**: UI-06
**Success Criteria** (what must be TRUE):
  1. Results explicitly label "No data found" (provider has no record) separately from "Clean" (provider explicitly reports benign) — an analyst can tell the difference at a glance
  2. A curl check on the app's security headers confirms CSP is set to `default-src 'self'; script-src 'self'`
  3. A grep of the codebase finds zero uses of `|safe` on any field sourced from user input or API responses
  4. A grep of the codebase finds zero outbound HTTP calls where the URL is constructed from an IOC value
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Offline Pipeline | 2/4 | In Progress|  |
| 2. Core Enrichment | 0/TBD | Not started | - |
| 3. Additional TI Providers | 0/TBD | Not started | - |
| 4. UX Polish and Security Verification | 0/TBD | Not started | - |
