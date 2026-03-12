# Roadmap: SentinelX

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-24)
- ✅ **v1.1 UX Overhaul** — Phases 6-8 (shipped 2026-02-25, reduced scope)
- ✅ **v1.2 Modern UI Redesign** — Phases 11-12 (shipped 2026-02-28)
- ✅ **v1.3 Visual Experience Overhaul** — Phases 15-17 (shipped 2026-02-28)
- ✅ **v2.0 Home Page Modernization** — Phase 18 (shipped 2026-02-28)
- ✅ **v3.0 TypeScript Migration** — Phases 19-22, Phase 23 skipped (shipped 2026-03-01)
- ✅ **v4.0 Universal Threat Intel Hub** — Phases 1-4 (shipped 2026-03-03)
- ✅ **v5.0 Quality-of-Life** — Phase 1 retroactive (shipped 2026-03-09)
- 🚧 **v6.0 Analyst Experience** — Phases 01-04 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-24</summary>

- [x] Phase 1: Foundation and Offline Pipeline (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Core Enrichment (4/4 plans) — completed 2026-02-21
- [x] Phase 3: Additional TI Providers (3/3 plans) — completed 2026-02-21
- [x] Phase 3.1: Integration Fixes and Git Hygiene (1/1 plan) — completed 2026-02-22 *(INSERTED)*
- [x] Phase 4: UX Polish and Security Verification (2/2 plans) — completed 2026-02-24

Full details: `milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 UX Overhaul (Phases 6-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 6: Foundation — Tailwind + Alpine + Card Layout — completed 2026-02-24
- [x] Phase 7: Filtering & Search — completed 2026-02-25
- [x] Phase 8: Input Page Polish — completed 2026-02-25

Phases 9-10 dropped: EXPORT and POLISH requirements superseded by v1.2 full redesign.

Full details: `milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Modern UI Redesign (Phases 11-12) — SHIPPED 2026-02-28</summary>

- [x] Phase 11: Foundation — Design Tokens & Base CSS (3/3 plans) — completed 2026-02-28
- [x] Phase 12: Shared Component Elevation (3/3 plans) — completed 2026-02-27

Phases 13-14 superseded by v1.3 Visual Experience Overhaul.

</details>

<details>
<summary>✅ v1.3 Visual Experience Overhaul (Phases 15-17) — SHIPPED 2026-02-28</summary>

- [x] Phase 15: Results Page Visual Overhaul — completed 2026-02-28
- [x] Phase 16: Input Page and Global Motion — completed 2026-02-28
- [x] Phase 17: Settings Page Polish — completed 2026-02-28

</details>

<details>
<summary>✅ v2.0 Home Page Modernization (Phase 18) — SHIPPED 2026-02-28</summary>

- [x] Phase 18: Home Page Modernization — completed 2026-02-28

</details>

<details>
<summary>✅ v3.0 TypeScript Migration (Phases 19-22) — SHIPPED 2026-03-01</summary>

- [x] Phase 19: Build Pipeline Infrastructure (2/2 plans) — completed 2026-02-28
- [x] Phase 20: Type Definitions Foundation (1/1 plan) — completed 2026-02-28
- [x] Phase 21: Simple Module Extraction (3/3 plans) — completed 2026-02-28
- [x] Phase 22: Enrichment Module and Entry Point (2/2 plans) — completed 2026-03-01
- [ ] Phase 23: Type Hardening and Verification — skipped (SAFE-01, SAFE-02 deferred)

Full details: `milestones/v3.0-ROADMAP.md`

</details>

<details>
<summary>✅ v4.0 Universal Threat Intel Hub (Phases 1-4) — SHIPPED 2026-03-03</summary>

- [x] Phase 1: Provider Registry Refactor (2/2 plans) — completed 2026-03-02
- [x] Phase 2: Shodan InternetDB (2/2 plans) — completed 2026-03-02
- [x] Phase 3: Free-Key Providers (3/3 plans) — completed 2026-03-03
- [x] Phase 4: Results UX Upgrade (2/2 plans) — completed 2026-03-03

Full details: `milestones/v4.0-ROADMAP.md`

</details>

<details>
<summary>✅ v5.0 Quality-of-Life (Phase 1) — SHIPPED 2026-03-09</summary>

- [x] Phase 1: Quality-of-Life Features (retroactive, no PLANs) — completed 2026-03-09

Ad-hoc work adopted into GSD tracking. See `.planning/phases/01-quality-of-life/01-SUMMARY.md`.

</details>

### v6.0 Analyst Experience (In Progress)

**Milestone Goal:** Expand SentinelX from a lookup tool into a genuine analyst workstation — zero-auth enrichment depth for IP/domain/hash IOCs, full Shodan data visibility, passive DNS pivoting, and a bookmarkable per-IOC analysis page with notes, tags, and relationship graphs.

- [ ] **Phase 01: Zero-Auth IP Intelligence + Known-Good** - GeoIP/rDNS/proxy flags for all IPs; NSRL known-good detection for hashes; full Shodan card data visible
- [x] **Phase 02: Domain Intelligence** - Live DNS records and certificate transparency history for domain IOCs (completed 2026-03-12)
- [ ] **Phase 03: Passive DNS Pivoting** - ThreatMiner passive DNS, related samples, and infrastructure context for all IOC types
- [ ] **Phase 04: Deep Analysis View** - Per-IOC detail page with tabbed enrichment, analyst notes and tags, IOC relationship graph

## Phase Details

### Phase 01: Zero-Auth IP Intelligence + Known-Good
**Goal**: Analysts can understand any IP IOC's geography, infrastructure, and threat context without API keys, and can immediately identify known-good file hashes to reduce false-positive workload
**Depends on**: Nothing (first phase of v6.0)
**Requirements**: IPINT-01, IPINT-02, IPINT-03, HINT-01, HINT-02, EPROV-01
**Success Criteria** (what must be TRUE):
  1. User sees country, city, ASN, and ISP for any IP IOC result card with no API key configured
  2. User sees PTR hostname in the IP result card for any IP that has a reverse DNS entry
  3. User sees proxy/VPN/hosting/mobile flags for any IP, allowing instant datacenter vs residential classification
  4. User sees a "KNOWN GOOD" verdict badge (visually distinct from CLEAN/MALICIOUS/UNKNOWN) on any hash IOC that CIRCL hashlookup confirms is in the NSRL
  5. User sees ports, CVEs, hostnames, and CPEs in the Shodan InternetDB card (data already fetched, now fully rendered)
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Backend adapters (CIRCL hashlookup + ip-api.com) and provider registration
- [x] 01-02-PLAN.md — known_good verdict type system (TS types, CSS, templates) + Shodan EPROV-01 field completion
- [x] 01-03-PLAN.md — IP Context row rendering (frontend display of GeoIP/rDNS/proxy flags)

### Phase 02: Domain Intelligence
**Goal**: Analysts can assess any domain IOC's live infrastructure and certificate history without API keys, transforming domain cards from near-opaque to genuinely informative
**Depends on**: Phase 01
**Requirements**: DINT-01, DINT-02
**Success Criteria** (what must be TRUE):
  1. User sees live A, MX, NS, and TXT (including SPF and DMARC) records for any domain IOC in the result card
  2. User sees certificate transparency history for any domain — count of certificates, date range, and enumerated subdomains from SANs
  3. Domain result cards display DNS and certificate data even when no API keys are configured
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — DnsAdapter for live DNS record lookups (A/MX/NS/TXT) via dnspython
- [x] 02-02-PLAN.md — CrtShAdapter for certificate transparency history via crt.sh API
- [x] 02-03-PLAN.md — Registry wiring, SSRF allowlist, and frontend context row rendering

### Phase 03: Passive DNS Pivoting
**Goal**: Analysts can pivot from any IOC to related infrastructure — what IPs a domain has resolved to, what domains point to an IP, what malware samples are associated with a hash — without API keys
**Depends on**: Phase 02
**Requirements**: DINT-03
**Success Criteria** (what must be TRUE):
  1. User sees passive DNS history (related hostnames or IPs) for any IP or domain IOC via ThreatMiner
  2. User sees related malware sample hashes for any hash IOC via ThreatMiner
  3. ThreatMiner results appear in result cards without blocking other providers — rate limiting is transparent (slow result, not error) when the 10 req/min limit is reached
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — ThreatMinerAdapter with TDD (passive DNS for IP/domain, related samples for hash)
- [ ] 03-02-PLAN.md — Registry wiring, SSRF allowlist, frontend context row rendering, human verification

### Phase 04: Deep Analysis View
**Goal**: Analysts can investigate a single IOC in depth — all enrichment in one place, annotated with personal notes and tags, with a visual relationship graph showing IOC-to-provider connections
**Depends on**: Phase 03
**Requirements**: DEEP-01, DEEP-02, DEEP-03, DEEP-04
**Success Criteria** (what must be TRUE):
  1. User can click any IOC in the results list to open a dedicated detail page at a bookmarkable URL showing all provider results in a tabbed layout
  2. User can add, edit, and delete free-text notes on any IOC; notes survive page refresh and cache clears (stored in SQLite)
  3. User can apply and remove custom text tags on any IOC; tags are visible in the results list and filterable
  4. User can view a relationship graph on the detail page showing which providers returned data for the IOC and what verdict each reported
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

## Progress

| Milestone | Phases | Plans | Status | Shipped |
|-----------|--------|-------|--------|---------|
| v1.0 MVP | 5 | 14 | ✅ Complete | 2026-02-24 |
| v1.1 UX Overhaul | 3 | 1/2 | In Progress|  |
| v1.2 Modern UI | 2 | 3/3 | Complete   | 2026-03-12 |
| v1.3 Visual Experience | 3 | — | ✅ Complete | 2026-02-28 |
| v2.0 Home Page | 1 | 3 | ✅ Complete | 2026-02-28 |
| v3.0 TypeScript | 4 | 8 | ✅ Complete | 2026-03-01 |
| v4.0 Threat Intel Hub | 4 | 9 | ✅ Complete | 2026-03-03 |
| v5.0 Quality-of-Life | 1 | 0 | ✅ Complete | 2026-03-09 |
| v6.0 Analyst Experience | 4 | 8 | 🚧 In progress | — |

**v6.0 Phase Progress:**

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 01. Zero-Auth IP Intelligence + Known-Good | 3/3 | Complete | 2026-03-12 |
| 02. Domain Intelligence | 3/3 | Complete    | 2026-03-12 |
| 03. Passive DNS Pivoting | 0/2 | Not started | - |
| 04. Deep Analysis View | 0/TBD | Not started | - |
