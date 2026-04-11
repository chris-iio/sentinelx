# SentinelX

## What This Is

A security analyst toolkit combining threat intelligence enrichment with SSH login anomaly detection. Paste free-form text to extract and enrich IOCs against 14 providers, or upload SSH auth.log files to detect suspicious login behavior (new IPs, new countries, impossible travel, unusual hours). Built for SOC analysts performing triage on local workstations or jump boxes.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Requirements

### Validated

Everything built through 9 milestones (2026-02-21 to 2026-03-14). See `.planning/MILESTONES.md` for full history.

- ✓ IOC extraction from free-form text with 20-pattern defanging normalizer and 8-type classifier
- ✓ 14 threat intel providers (6 zero-auth, 1 public, 7 key-auth) via Provider Protocol + Registry
- ✓ Results page: summary rows with worst verdict + consensus badges, expandable per-provider details
- ✓ Bookmarkable per-IOC detail page with tabbed provider results + SVG relationship graph
- ✓ Dark-first design system (zinc/emerald/teal), TypeScript 5.8 + esbuild, Tailwind CSS standalone
- ✓ SQLite cache, client-side export (JSON/CSV/clipboard), bulk input mode
- ✓ Security-first: CSP, CSRF, SSRF allowlist, textContent-only DOM, no innerHTML

### Active

<!-- v1.2 SSH Login Anomaly Detection — scope defined in REQUIREMENTS.md -->

### Out of Scope

- Public internet exposure — this is a local/jump-box tool only
- User authentication — single-user, local access assumed
- Historical analysis or trending — single-shot triage tool
- Automated response/blocking actions — read-only enrichment
- Mobile or responsive design — desktop browser on analyst workstation
- WHOIS / RDAP enrichment — GDPR redaction returns low-signal "REDACTED FOR PRIVACY" strings
- Malware sandbox detonation — fundamentally different capability (analysis vs execution)
- Node.js / npm dependency — esbuild + tsc installed as standalone binaries
- Framework adoption (React, Vue) — vanilla TS sufficient for this complexity
- STIX/TAXII threat feed import — deferred to future milestone
- File upload for hash extraction — deferred to future milestone
- Generic SIEM / security platform — SSH detection is a focused addition, not a platform pivot
- Other log types (Apache, nginx, syslog) — SSH auth.log only for v1.2
- ML/AI anomaly models — simple rule-based detection only
- Real-time log streaming / tailing — upload-based batch analysis only
- Results page visual redesign (v1.1 Phases 3-5) — deferred, Phase 1-2 infrastructure retained

## Context

- **Users:** SOC analysts performing initial triage of alerts, emails, and threat reports
- **Environment:** Runs on analyst's local machine or an internal jump box (not internet-facing)
- **Tech stack:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend stack:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc/emerald/teal design tokens
- **Codebase:** ~4,923 LOC Python, ~2,459 LOC TypeScript, ~635 LOC templates, ~12,350 LOC tests
- **Test suite:** 757+ unit/integration + 91 E2E (up from 483 at v5.0)
- **Threat intel providers (14):** VirusTotal (API key), MalwareBazaar (public), ThreatFox (public), Shodan InternetDB (zero-auth), URLhaus (free key), OTX AlienVault (free key), GreyNoise Community (free key), AbuseIPDB (free key), ip-api.com (zero-auth), CIRCL hashlookup (zero-auth), DNS Records (zero-auth), crt.sh (zero-auth), ThreatMiner (zero-auth), ASN Intel/Team Cymru (zero-auth)
- **Architecture:** Provider Protocol + ProviderRegistry — adding a provider = one adapter file + one `register()` call. CacheStore for enrichment result caching.
- **Security posture:** All defenses from v1.0 maintained — CSP, CSRF, SSRF allowlist (12 HTTP hosts), host validation, automated regression guards. CSRF meta tag for client-side fetch.
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`
- **Frontend modules:** 13 TypeScript modules (annotations.ts removed in v7.0 partial, graph.ts added in v6.0)
- **v1.2 additions:** SSH log parser module, anomaly detector module, GeoIP via ip-api.com (reuse existing adapter), new Flask blueprint for SSH routes

## Constraints

- **Security model**: All user input and all API responses treated as untrusted at every layer
- **Network**: Localhost binding only; no outbound calls in offline mode; strict timeouts in online mode
- **Dependencies**: Minimal — prefer well-audited libraries; no unnecessary attack surface
- **Secrets**: API keys via ConfigStore (`~/.sentinelx/config.ini`) or environment variables; never logged, never rendered
- **Execution**: No subprocess, no shell, no eval/exec — deterministic code paths only
- **DOM safety**: All dynamic content via createElement + textContent — never innerHTML (SEC-08)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Flask | Analyst-friendly, rich parsing ecosystem, fast to iterate | ✓ Good — 14 plans in 4 days, Flask well-suited |
| VirusTotal as primary API | Most widely used, comprehensive coverage across IOC types | ✓ Good — solid baseline for IP/domain/URL/hash |
| No combined threat score | Transparency for analysts — show raw verdicts, let humans decide | ✓ Good — consensus badges [flagged/responded] added in v4.0 as transparent alternative |
| Localhost-only by default | Defense in depth — not designed for multi-user or public access | ✓ Good — 127.0.0.1 binding + TRUSTED_HOSTS |
| Security-first (Phase 1) | All defenses before any network code | ✓ Good — CSP/CSRF/host-validation from day one |
| textContent only (no innerHTML) | Prevent XSS from API responses in dynamic DOM | ✓ Good — SEC-08 maintained through v4.0 enrichment refactor |
| Tailwind CSS standalone CLI | No Node.js needed, generates CSS from utility classes | ✓ Good — dark-first design system, efficient build |
| esbuild standalone binary | No Node.js/npm, fast compilation, source maps for debugging | ✓ Good — 11 modules compiled to 13KB IIFE in <100ms |
| TypeScript strict mode | Catch type errors at compile time, safer DOM interactions | ✓ Good — null guards, discriminated unions, no `any` |
| Provider Protocol (typing.Protocol) | Plugin-style provider addition, zero orchestrator changes | ✓ Good — 5 new providers added with zero route/orchestrator edits |
| Summary-first results UX | Analyst triage speed — worst verdict + consensus at a glance | ✓ Good — expand for details only when needed |
| ConfigStore multi-provider | Central `~/.sentinelx/config.ini` for all API keys | ✓ Good — settings page manages all providers dynamically |
| Zero-auth provider strategy | Maximize value with no API keys | ✓ Good — 5 zero-auth providers give rich context out of the box |
| known_good verdict type | NSRL files need distinct visual treatment from clean/malicious | ✓ Good — early-return override in computeWorstVerdict, dedicated CSS tokens |
| Separate AnnotationStore DB | Notes/tags must survive cache clears | ✓ Good — annotations.db independent from cache.db |
| CSS-only tabs on detail page | No JavaScript needed for tab switching | ✓ Good — radio inputs + adjacent sibling selectors |
| SVG hub-and-spoke graph | Show IOC-provider relationships visually | ✓ Good — verdict-colored nodes, createElement (SEC-08 safe) |
| CONTEXT_PROVIDERS set pattern | Route zero-verdict context rows through shared renderer | ✓ Good — generalized createContextRow() for all context providers |
| path converter for IOC URLs | URL IOCs contain slashes that break standard routing | ✓ Good — `<path:ioc_value>` handles all IOC formats |
| Flask for SSH detection | Shared UI shell, no migration cost, SSH routes are simple sync work | — Pending |
| ip-api.com for GeoIP | Already integrated as zero-auth provider, avoids GeoLite2 download requirement | — Pending |
| Rule-based detection over ML | Simple, explainable, no training data needed, matches "clear logic over complex modeling" | — Pending |
| Configurable hour window | Default 6am–10pm, deployable without per-user learning period | — Pending |

## Current Milestone: v1.2 SSH Login Anomaly Detection

**Goal:** Extend SentinelX with SSH auth.log parsing and behavioral anomaly detection — upload a log file, get clear alerts for suspicious logins.

**Target features:**
- SSH log parser extracting structured login events from auth.log
- Per-user behavioral anomaly detection (new IP, new country, impossible travel, unusual hours)
- GeoIP country lookup via ip-api.com (already integrated, zero-auth)
- Configurable normal-hours window (default 6am–10pm)
- Flask routes with shared UI shell (upload form, alerts table, JSON API)

## Shipped Milestones

| Version | Name | Shipped | Key Feature |
|---------|------|---------|-------------|
| v1.0 | Foundation | 2026-03-14 | 14 providers, detail pages, cache, export, bulk input, relationship graphs |
| v1.1 | Results Page Redesign (partial) | 2026-03-17 | CSS contracts catalog, enrichment.ts module extraction (Phases 1-2 only; Phases 3-5 dropped) |

See `.planning/MILESTONES.md` for full history.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-12 after starting v1.2 SSH Login Anomaly Detection*
