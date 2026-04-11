# Roadmap: SentinelX

## Milestones

- ✅ **v1.0 Foundation** — All prior work (shipped 2026-03-14)
- ✅ **v1.1 Results Page Redesign** — Phases 1-2 completed; Phases 3-5 dropped (shipped 2026-03-17)
- 🚧 **v1.2 SSH Login Anomaly Detection** — Phases 6-9 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation — SHIPPED 2026-03-14</summary>

All prior milestones (v1.0 MVP through v7.0 partial) collapsed into v1.0 Foundation at version reset.
Includes: IOC extraction, 14 providers, results page, detail pages, cache, export, bulk input, ASN intel, relationship graphs, security hardening.

See `.planning/MILESTONES.md` for full internal milestone history.

</details>

<details>
<summary>✅ v1.1 Results Page Redesign — Phases 1-2 SHIPPED 2026-03-17; Phases 3-5 DROPPED</summary>

### Phase 1: Contracts and Foundation
**Goal**: All preservation contracts are documented and enforced before a single line of visual code changes
**Depends on**: Nothing (first phase)
**Requirements**: (none — foundation work that enables all other phases safely)
**Success Criteria** (what must be TRUE):
  1. Every CSS class used by E2E selectors is catalogued with a "do not rename" rule and the catalog is committed to the repo
  2. The `data-ioc-value`, `data-ioc-type`, and `data-verdict` attribute contract on `.ioc-card` is documented in code comments in the template
  3. Information density acceptance criteria are written out (IOC value visible, verdict label always visible, consensus count not hover-only)
  4. A CSS layer ownership rule exists: component classes own all visual properties for existing elements; Tailwind utilities for new layout structures only
**Plans**: 1 plan
Plans:
- [x] 01-01-PLAN.md — CSS contract catalog, inline source annotations, and E2E baseline confirmation

### Phase 2: TypeScript Module Extractions
**Goal**: `enrichment.ts` is split into three focused modules with zero behavioral change — visual redesign work is now isolated to `row-factory.ts`
**Depends on**: Phase 1
**Requirements**: (none — architectural refactor that isolates the visual redesign)
**Success Criteria** (what must be TRUE):
  1. `verdict-compute.ts` exists (~80 LOC) with pure functions `computeWorstVerdict`, `computeConsensus`, `computeAttribution`, `findWorstEntry` and no DOM access
  2. `row-factory.ts` exists (~150 LOC) with unified `createProviderRow(result, kind, statText)` owning the `CONTEXT_PROVIDERS` set and all row-building DOM code
  3. `enrichment.ts` is trimmed to ~300 LOC as the polling orchestrator and state owner only
  4. All 91 E2E tests pass unchanged after extraction — zero behavioral change
**Plans**: 1 plan
Plans:
- [x] 02-01-PLAN.md — Extract verdict-compute.ts, row-factory.ts, and trim enrichment.ts

### Phase 3: Visual Redesign (DROPPED)
**Status**: Dropped — deferred to future milestone

### Phase 4: Template Restructuring (DROPPED)
**Status**: Dropped — deferred to future milestone

### Phase 5: Context and Staleness (DROPPED)
**Status**: Dropped — deferred to future milestone

</details>

### v1.2 SSH Login Anomaly Detection (In Progress)

**Milestone Goal:** Upload an SSH auth.log file and receive clear, deduplicated anomaly alerts for suspicious login behavior — new IPs, new countries, impossible travel, and unusual hours — with per-alert enrichment links into the existing SentinelX detail pages.

## Phase Details

### Phase 6: Models, Parser, and Foundation
**Goal**: A correct, fully-tested SSH log parser exists and all blocking infrastructure changes are in place before any detection logic is written
**Depends on**: Phase 2 (existing codebase; no cross-phase code dependency)
**Requirements**: PARSE-01, PARSE-02, PARSE-03, PARSE-04, WEB-06, CFG-01
**Success Criteria** (what must be TRUE):
  1. The parser extracts `LoginEvent` records (username, source IP, timestamp) from auth.log lines containing "Accepted password" or "Accepted publickey"
  2. The parser correctly handles BSD syslog timestamps (including December→January year rollover) and RFC3339 timestamps on the same file, line by line
  3. The parser extracts both IPv4 and IPv6 source addresses; hostname entries (when UseDNS is on) are retained in the event with a flag indicating GeoIP should be skipped
  4. File uploads up to 5 MB are accepted — a 30-day real auth.log no longer triggers a 413 error
  5. The `[ssh]` section is recognized in `~/.sentinelx/config.ini` and the normal hours window can be read from it with a default of 06:00-22:00 when absent
**Plans**: 3 plans
Plans:
- [ ] 06-01-PLAN.md — SSH package skeleton with LoginEvent and ParseSummary frozen dataclasses
- [ ] 06-02-PLAN.md — ConfigStore SSH normal-hours extension and MAX_CONTENT_LENGTH increase to 5 MB
- [ ] 06-03-PLAN.md — SSH auth.log parser with dual-format timestamp support and TDD
**UI hint**: no

### Phase 7: GeoIP Wrapper
**Goal**: IP addresses from parsed login events can be mapped to country codes and coordinates via ipinfo.io, with private IPs and unavailable service handled gracefully
**Depends on**: Phase 6
**Requirements**: GEO-01, GEO-02, GEO-03, GEO-04
**Success Criteria** (what must be TRUE):
  1. Given a list of login events with duplicate IPs, exactly one HTTP request is made per unique routable IP — private, loopback, and reserved IPs receive no request
  2. A `GeoLocation` result is returned containing country code and latitude/longitude (the `loc` field from ipinfo.io) for each resolved IP
  3. When ipinfo.io is unreachable, `lookup_country()` returns `None` for affected IPs — the caller can detect this and skip country-dependent rules while still running IP and hour rules
**Plans**: TBD
**UI hint**: no

### Phase 8: Anomaly Detector
**Goal**: A pure, network-free detector function applies all four anomaly rules to a list of login events and returns deduplicated, risk-labeled alerts
**Depends on**: Phase 7
**Requirements**: DETECT-01, DETECT-02, DETECT-03, DETECT-04, DETECT-05, DETECT-06
**Success Criteria** (what must be TRUE):
  1. A login from an IP address not previously seen for that user in the log produces a LOW risk alert; a login from a previously-seen IP produces no new-IP alert
  2. A login from a country not previously seen for that user produces a MEDIUM risk alert; country rules are silently skipped when `geo_map` has no entry for the IP
  3. A login outside the configured normal hours window (default 06:00-22:00) produces a MEDIUM risk alert with the actual login time in the reason text
  4. Two logins for the same user from different countries with less than 3 hours elapsed produce a HIGH risk impossible-travel alert with the distance and elapsed time in the reason text
  5. A log file with 8,000 lines from one IP for one rule produces exactly one alert — deduplication by `(username, source_ip, rule_type)` is applied before any alert is returned
  6. Each returned alert contains username, timestamp, IP address, country (or "unknown"), a human-readable reason string, and a risk level of low, medium, or high
**Plans**: TBD
**UI hint**: no

### Phase 9: Routes, Templates, and TypeScript
**Goal**: Analysts can upload an auth.log file from the SentinelX UI, view a table of anomaly alerts with risk-appropriate styling, and fetch alerts as JSON — the SSH section is fully integrated into the shared navigation
**Depends on**: Phase 8
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05
**Success Criteria** (what must be TRUE):
  1. Navigating to `/ssh` renders an upload form with file size guidance and a CSRF token; the SSH section appears as a navigation item in the shared `base.html` header
  2. Uploading a valid auth.log file via the form returns a results page showing all flagged alerts in a table with columns for username, timestamp, IP, country, reason, and risk level
  3. Each alert row links the IP address directly to `/ioc/ipv4/<ip>` for one-click SentinelX enrichment
  4. Risk levels are visually distinct in the alerts table — HIGH, MEDIUM, and LOW alerts use different colors or badge styles so severity is apparent at a glance
  5. `GET /ssh/events` returns the flagged alerts as JSON; uploading a file with no anomalies returns an empty alerts list, not an error page
  6. All dynamic content in the SSH TypeScript module uses `createElement + textContent` only — no `innerHTML` is used anywhere in `ssh.ts`
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Contracts and Foundation | v1.1 | 1/1 | Complete | 2026-03-16 |
| 2. TypeScript Module Extractions | v1.1 | 1/1 | Complete | 2026-03-17 |
| 3. Visual Redesign | v1.1 | 0/0 | Dropped | - |
| 4. Template Restructuring | v1.1 | 0/0 | Dropped | - |
| 5. Context and Staleness | v1.1 | 0/0 | Dropped | - |
| 6. Models, Parser, and Foundation | v1.2 | 0/3 | Not started | - |
| 7. GeoIP Wrapper | v1.2 | 0/TBD | Not started | - |
| 8. Anomaly Detector | v1.2 | 0/TBD | Not started | - |
| 9. Routes, Templates, and TypeScript | v1.2 | 0/TBD | Not started | - |
