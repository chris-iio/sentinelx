# Milestones

## v7.0 Free Intel (Abandoned: 2026-03-16 — Partial)

**Phases:** 2 of 5 completed (01-02) | **Plans:** 2 | **Requirements:** 3/7 (4 abandoned)
**Timeline:** 1 day (2026-03-14 → 2026-03-14)

**Completed before abandonment:**
1. Annotations removal — stripped notes, tags, tag filtering, AnnotationStore, annotation API routes
2. ASN Intelligence — Team Cymru DNS-based IP-to-ASN adapter (14th provider, zero-auth)

**Abandoned phases:**
- Phase 03: Threat Feed Intelligence (Feodo Tracker)
- Phase 04: RDAP Design Decision
- Phase 05: RDAP Registration Data

**Reason:** User chose to start fresh with a new milestone direction.

**Archives:**
- `milestones/v7.0-abandoned/`

---

## v6.0 Analyst Experience (Shipped: 2026-03-14)

**Phases:** 4 (01-04) | **Plans:** 11 | **Tasks:** 13 | **Requirements:** 13/13
**Timeline:** 3 days (2026-03-11 → 2026-03-14)
**LOC:** ~4,923 app Python + ~2,459 TS + ~635 templates + ~12,350 tests
**Commits:** 58 in milestone range
**Tests:** 757+ unit/integration + 91 E2E (up from 483 at v5.0)

**Delivered:** Expanded SentinelX from a lookup tool into a genuine analyst workstation — 5 new zero-auth providers (ip-api, CIRCL hashlookup, DNS, crt.sh, ThreatMiner) bringing the total from 8 to 13, a bookmarkable per-IOC detail page with tabbed enrichment and SVG relationship graph, and SQLite-persisted analyst annotations (notes + tags) with tag-based filtering.

**Key accomplishments:**
1. Zero-auth IP intelligence — GeoIP, rDNS, and proxy/VPN/hosting flags for any IP via ip-api.com, no API key needed
2. Known-good hash detection — CIRCL hashlookup identifies NSRL-listed files with visually distinct "KNOWN GOOD" verdict
3. Domain intelligence — Live DNS records (A/MX/NS/TXT) via dnspython + certificate transparency history via crt.sh
4. Passive DNS pivoting — ThreatMiner integration for infrastructure relationships across all IOC types
5. Deep analysis view — Bookmarkable per-IOC detail page with tabbed provider results and SVG relationship graph
6. Analyst annotations — SQLite-persisted notes and tags on any IOC, with tag-based filtering in the results list

**Known Gaps:**
- IPINT-01, IPINT-02, IPINT-03, HINT-01, HINT-02, EPROV-01: Features implemented and tested but Phase 01 missing VERIFICATION.md (documentation gap, not feature gap)

**Git range:** `fded10d` (start v6.0) → `a7fb966` (audit)

**Archives:**
- `milestones/v6.0-ROADMAP.md`
- `milestones/v6.0-REQUIREMENTS.md`
- `milestones/v6.0-MILESTONE-AUDIT.md`

---

## v5.0 Quality-of-Life (Shipped: 2026-03-09)

**Phases:** 1 (01) | **Plans:** 0 (retroactive adoption) | **Requirements:** 4/4
**Timeline:** Ad-hoc (2026-03-03 to 2026-03-09)
**LOC:** ~3,515 app Python + ~3,619 frontend (TS+CSS) + ~8,408 tests
**Tests:** 483 unit/integration (up from 457 at v4.0)

**Delivered:** Four quality-of-life features built ad-hoc after v4.0 and adopted retroactively into GSD tracking. No prospective PLANs -- single SUMMARY-only phase.

**Key accomplishments:**
1. Enrichment Result Cache -- SQLite-backed with configurable TTL, thread-safe, settings UI for TTL and cache clearing
2. Export Menu -- JSON/CSV/clipboard client-side export replacing single copy button, dropdown UX
3. Bulk IOC Input Mode -- one-per-line parser, toggle UI, route branching, validation with skip
4. Provider Context Fields -- VT top_detections/reputation, generic context field rendering for all 8 providers

**Git range:** 2 logical commits (backend+tests, frontend+templates+docs)

**Archives:**
- `.planning/phases/01-quality-of-life/01-SUMMARY.md`

---

## v4.0 Universal Threat Intel Hub (Shipped: 2026-03-03)

**Phases:** 4 (01-04) | **Plans:** 9 | **Requirements:** 18/18
**Timeline:** 2 days (2026-03-02 to 2026-03-03)
**LOC:** ~3,127 app Python + ~3,072 frontend (TS+CSS) + ~8,006 tests
**Commits:** 28 feat commits
**Tests:** 542 (up from 224 at v1.0)

**Delivered:** Expanded SentinelX from 3 hardcoded providers to 8 via plugin-style registry architecture — Shodan InternetDB (zero-auth), URLhaus, OTX AlienVault, GreyNoise Community, and AbuseIPDB alongside existing VirusTotal, MalwareBazaar, and ThreatFox. Unified results UX with summary-first, details-on-demand layout.

**Key accomplishments:**
1. Provider Protocol + ProviderRegistry — `typing.Protocol` with `@runtime_checkable`, adding a provider requires one adapter file + one `register()` call
2. Shodan InternetDB as first zero-auth provider — proved the registry pattern works end-to-end with TDD (25 tests)
3. Four free-key providers (URLhaus, OTX, GreyNoise, AbuseIPDB) — 137 new adapter tests, all following the same TDD pattern
4. ConfigStore multi-provider key storage — expanded from single VT key to `[providers]` INI section, settings page loops over all registered providers
5. Unified results UX — summary rows with worst-verdict attribution + consensus badges `[flagged/responded]`, expandable per-provider detail rows sorted by severity
6. Dynamic provider coverage dashboard — registered/configured/needs-key counts in verdict dashboard

**Git range:** `feat(01-01)` .. `feat(04-02)`

**Archives:**
- `milestones/v4.0-ROADMAP.md`
- `milestones/v4.0-REQUIREMENTS.md`

---

## v3.0 TypeScript Migration (Shipped: 2026-03-01)

**Phases:** 4 (19-22), Phase 23 skipped | **Plans:** 8 | **Requirements:** 20/22 (2 deferred)
**Timeline:** 2 days (2026-02-28 to 2026-03-01)
**Stack:** esbuild standalone binary + TypeScript 5.8, IIFE output
**Scope:** Frontend-only — JS→TS conversion with zero functional changes

**Delivered:** Complete TypeScript migration of 856-line vanilla JS IIFE into 11 typed ES modules with strict type checking, source maps, and esbuild build pipeline — zero behavioral changes, same 224 tests passing.

**Key accomplishments:**
1. esbuild standalone binary build pipeline — `make js`, `make js-dev`, `make js-watch`, `make typecheck` integrated into Makefile
2. Strict TypeScript config — `strict: true`, `isolatedModules`, `noUncheckedIndexedAccess`, `"types": []` (no Node.js globals)
3. Domain type layer — `VerdictKey`, `IocType` union types, `EnrichmentItem` discriminated union, typed constants
4. 7 typed modules extracted — form, clipboard, cards, filter, settings, UI utilities, enrichment — each with `init()` export
5. Complex enrichment module (350+ lines) fully typed — polling loop, result rendering, verdict accumulation, warning banner
6. Original `main.js` deleted, `base.html` updated to `dist/main.js` — clean cutover

**Known Gaps:**
- SAFE-01: Full E2E verification deferred (Phase 23 skipped — E2E suite has pre-existing env issues)
- SAFE-02: CSP regression test against compiled bundle deferred (Phase 23 skipped)

**Git range:** `feat(19-01)` .. `feat(22-02)`

**Archives:**
- `milestones/v3.0-ROADMAP.md`
- `milestones/v3.0-REQUIREMENTS.md`
- `milestones/v3.0-MILESTONE-AUDIT.md`
- `milestones/v3.0-phases/` (phases 19-22)

---

## v1.0 MVP (Shipped: 2026-02-24)

**Phases:** 5 (1, 2, 3, 3.1, 4) | **Plans:** 14 | **Requirements:** 34/34
**Timeline:** 4 days (2026-02-21 to 2026-02-24)
**LOC:** ~3,200 app (Python + HTML/CSS/JS) + ~3,900 tests
**Commits:** 78 (20 feat)

**Delivered:** A security-first local IOC triage tool for SOC analysts — paste text, extract and classify 8 IOC types, enrich against 3 threat intelligence providers in parallel, and review transparent per-provider verdicts.

**Key accomplishments:**
1. Security-first Flask scaffold — TRUSTED_HOSTS, CSRF, CSP, input size cap established before any route code
2. Dual-library IOC extraction (iocextract + iocsearcher) with 20-pattern defanging normalizer and deterministic 8-type classifier
3. VirusTotal API v3 adapter with full HTTP safety controls (timeout, stream+size-cap, no-redirect, SSRF allowlist) and parallel enrichment orchestrator
4. Multi-provider threat intelligence — VirusTotal, MalwareBazaar, ThreatFox dispatched in parallel with per-provider error isolation
5. Verdict clarity UX — NO RECORD vs CLEAN instantly distinguishable, collapsed no-data sections, pending provider indicators
6. Automated security regression guards — CSP, template XSS safety, adapter SSRF safety codified as pytest tests (224 tests, 97% coverage)

**Git range:** `docs: initialize project` .. `docs(phase-04): complete phase execution`

**Archives:**
- `milestones/v1.0-ROADMAP.md`
- `milestones/v1.0-REQUIREMENTS.md`
- `milestones/v1.0-MILESTONE-AUDIT.md`
- `milestones/v1.0-phases/` (phases 1-3.1)

---

## v1.1 UX Overhaul (Shipped: 2026-02-25 — Reduced Scope)

**Phases:** 3 completed of 5 planned (6, 7, 8) | **Plans:** 6 | **Requirements:** 12/19 (7 dropped)
**Timeline:** 2 days (2026-02-24 to 2026-02-25)
**Stack:** Tailwind CSS standalone CLI + vanilla JS
**Scope:** Frontend-only — zero backend changes

**Delivered:** Card-based results layout with Tailwind CSS, filtering & search (verdict/type/text), input page polish (toggle switch, paste feedback, reactive submit label). Foundation for modern UI.

**Key accomplishments:**
1. Tailwind CSS standalone CLI integration with Makefile build
2. Card layout replacing table rows with severity-sorted display and summary dashboard
3. Filter bar with verdict buttons, IOC type pills, text search, and sticky positioning
4. Toggle switch replacing dropdown, paste feedback, contextual submit button

**Dropped to out-of-scope:** EXPORT-01 through EXPORT-04, POLISH-01 through POLISH-03 (superseded by v1.2 full redesign)

**Archives:**
- `milestones/v1.1-ROADMAP.md`
- `milestones/v1.1-REQUIREMENTS.md` (when archived)

---
