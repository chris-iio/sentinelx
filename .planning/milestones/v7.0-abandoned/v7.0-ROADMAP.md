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
- ✅ **v6.0 Analyst Experience** — Phases 01-04 (shipped 2026-03-14)
- 🚧 **v7.0 Free Intel** — Phases 01-05 (in progress)

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

<details>
<summary>✅ v6.0 Analyst Experience (Phases 01-04) — SHIPPED 2026-03-14</summary>

- [x] Phase 01: Zero-Auth IP Intelligence + Known-Good (3/3 plans) — completed 2026-03-12
- [x] Phase 02: Domain Intelligence (3/3 plans) — completed 2026-03-12
- [x] Phase 03: Passive DNS Pivoting (2/2 plans) — completed 2026-03-12
- [x] Phase 04: Deep Analysis View (3/3 plans) — completed 2026-03-13

Full details: `milestones/v6.0-ROADMAP.md`

</details>

### v7.0 Free Intel (In Progress)

**Milestone Goal:** Provide actionable threat intelligence out of the box — useful triage with zero API keys configured, via annotations removal (codebase cleanup), ASN/BGP context, Feodo Tracker C2 feed, and RDAP registration data.

- [x] **Phase 01: Annotations Removal** — Strip notes, tags, AnnotationStore, and annotation API routes for a clean v7.0 baseline (completed 2026-03-14)
- [x] **Phase 02: ASN Intelligence** — Team Cymru DNS-based ASN/BGP context (CIDR prefix, RIR, allocation date) for IP IOCs (completed 2026-03-14)
- [ ] **Phase 03: Threat Feed Intelligence** — Feodo Tracker C2 blocklist for IP IOCs (malicious with malware family on hit)
- [ ] **Phase 04: RDAP Design Decision** — Resolve SEC-06 redirect conflict empirically before writing any RDAP adapter code
- [ ] **Phase 05: RDAP Registration Data** — Domain and IP registration data (registrar, creation date, network block) via RDAP

## Phase Details

### Phase 01: Annotations Removal
**Goal**: Remove the annotations feature entirely, establishing a clean codebase baseline before any new provider work begins
**Depends on**: Nothing (first phase)
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria** (what must be TRUE):
  1. No notes input, tag input, or tag filter UI appears on the results page or IOC detail page
  2. The `/api/annotations/*` routes return 404 (routes no longer exist)
  3. `flask --debug run` starts without import errors after annotations module is removed
  4. Full test suite passes with no annotation-related test failures
**Plans:** 1/1 plans complete
Plans:
- [x] 01-01-PLAN.md — Complete annotations removal (tests, Python, TypeScript)

### Phase 02: ASN Intelligence
**Goal**: Users see ASN/BGP context (CIDR prefix, RIR, allocation date, ASN number and org) for IP IOCs via Team Cymru DNS — zero new dependencies, zero SSRF surface changes
**Depends on**: Phase 01
**Requirements**: ASN-01
**Success Criteria** (what must be TRUE):
  1. Submitting an IP IOC in online mode shows an ASN context row with CIDR prefix, ASN number, org name, and RIR
  2. The ASN provider appears in the provider coverage dashboard as a zero-auth provider
  3. The ASN adapter has no `requires_api_key` and `is_configured()` always returns True
**Plans:** 1/1 plans complete
Plans:
- [ ] 02-01-PLAN.md — CymruASNAdapter + registration + frontend wiring

### Phase 03: Threat Feed Intelligence
**Goal**: Users see Feodo Tracker C2 blocklist verdict for IP IOCs — malicious with malware family name on hit, clean when confirmed absent from the feed
**Depends on**: Phase 01
**Requirements**: FEED-01
**Success Criteria** (what must be TRUE):
  1. Submitting an IP IOC known to be in Feodo Tracker shows a malicious verdict with the malware family name
  2. Submitting an IP IOC absent from the feed shows a clean verdict
  3. `feodotracker.abuse.ch` is in the SSRF allowlist and a unit test confirms `validate_endpoint()` passes for it
  4. The Feodo feed is cached (subsequent lookups within TTL do not re-download the full feed)
**Plans**: TBD

### Phase 04: RDAP Design Decision
**Goal**: Resolve the SEC-06 redirect conflict for RDAP before any adapter code is written — empirically confirm whether rdap.org proxies responses or issues redirects, and document the binding design decision
**Depends on**: Phase 01
**Requirements**: RDAP-03
**Success Criteria** (what must be TRUE):
  1. A documented test result exists showing the HTTP response status of `GET https://rdap.org/domain/google.com` with `allow_redirects=False`
  2. The RDAP implementation approach is chosen (requests + allowlist if 200, or whoisit library if 302) and recorded in PROJECT.md Key Decisions
  3. Any SEC-06 exception (if whoisit is chosen) is explicitly documented with rationale
**Plans**: TBD

### Phase 05: RDAP Registration Data
**Goal**: Users see domain registration data (registrar, creation date as "registered N days ago", nameservers) and IP registration data (network block name, org, CIDR, country) for applicable IOC types
**Depends on**: Phase 04
**Requirements**: RDAP-01, RDAP-02
**Success Criteria** (what must be TRUE):
  1. Submitting a domain IOC shows an RDAP context row with registrar name, creation date formatted as "registered N days ago", and nameservers
  2. Submitting an IP IOC shows an RDAP context row with network block name, org, CIDR, and country
  3. The RDAP provider appears in the provider coverage dashboard as a zero-auth provider
  4. No registrant contact fields (name, email, address) appear in RDAP output — GDPR-scoped data model only
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Annotations Removal | 1/1 | Complete    | 2026-03-14 | - |
| 02. ASN Intelligence | 1/1 | Complete    | 2026-03-14 | - |
| 03. Threat Feed Intelligence | v7.0 | 0/TBD | Not started | - |
| 04. RDAP Design Decision | v7.0 | 0/TBD | Not started | - |
| 05. RDAP Registration Data | v7.0 | 0/TBD | Not started | - |
