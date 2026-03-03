# Milestones

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
