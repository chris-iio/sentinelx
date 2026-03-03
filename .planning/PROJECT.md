# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 8 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Requirements

### Validated

- ✓ Single-page web interface with large paste input, submit button, and offline/online toggle — v1.0
- ✓ IOC extraction from free-form text (alert snippets, email headers/body, raw IOCs) — v1.0
- ✓ Defanging normalization (hxxp, [.], {.}, and 20 common obfuscation patterns) — v1.0
- ✓ Deterministic IOC classification: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE — v1.0
- ✓ Offline mode: extraction + classification only, zero network calls — v1.0
- ✓ Online mode: parallel queries to threat intelligence providers — v1.0
- ✓ Structured results page grouped by IOC type — v1.0
- ✓ Clear source attribution on every enrichment result — v1.0
- ✓ No opaque combined "threat score" — show provider verdicts as-is — v1.0
- ✓ Verdict clarity: "NO RECORD" vs "CLEAN" instantly distinguishable — v1.0
- ✓ Card-based results layout with severity borders and summary dashboard — v1.1
- ✓ Verdict/type/text filtering with sticky filter bar — v1.1
- ✓ Dark-first design token system (zinc/emerald/teal) with WCAG AA contrast — v1.2
- ✓ Self-hosted Inter Variable + JetBrains Mono Variable fonts — v1.2
- ✓ Minimal header bar, compact auto-growing textarea, tighter controls — v2.0
- ✓ TypeScript build pipeline (esbuild + tsc) with strict type checking — v3.0
- ✓ 11 typed ES modules extracted from monolithic JS IIFE — v3.0
- ✓ Provider protocol + registry architecture for plugin-style provider addition — v4.0
- ✓ 8 threat intel providers: VirusTotal, MalwareBazaar, ThreatFox, Shodan, URLhaus, OTX, GreyNoise, AbuseIPDB — v4.0
- ✓ Unified results UX: summary rows with consensus badges, expandable per-provider details — v4.0
- ✓ Multi-provider settings page with dynamic provider cards and API key management — v4.0

### Active

(No active milestone — next milestone TBD)

### Out of Scope

- Public internet exposure — this is a local/jump-box tool only
- User authentication — single-user, local access assumed
- Historical analysis or trending — single-shot triage tool
- Automated response/blocking actions — read-only enrichment
- Mobile or responsive design — desktop browser on analyst workstation
- WHOIS / RDAP enrichment — high complexity, often privacy-redacted
- Malware sandbox detonation — fundamentally different capability
- Persistent session history — requires persistence design decision
- Node.js / npm dependency — esbuild + tsc installed as standalone binaries
- Framework adoption (React, Vue) — vanilla TS sufficient for this complexity

## Context

- **Users:** SOC analysts performing initial triage of alerts, emails, and threat reports
- **Environment:** Runs on analyst's local machine or an internal jump box (not internet-facing)
- **Tech stack:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests for HTTP
- **Frontend stack:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc/emerald/teal design tokens
- **Codebase:** ~3,127 LOC Python, ~3,072 LOC frontend (TS+CSS), ~386 LOC templates, ~8,006 LOC tests
- **Test suite:** 542 tests (up from 224 at v1.0)
- **Threat intel providers (8):** VirusTotal (API key), MalwareBazaar (public), ThreatFox (public), Shodan InternetDB (zero-auth), URLhaus (free key), OTX AlienVault (free key), GreyNoise Community (free key), AbuseIPDB (free key)
- **Architecture:** Provider Protocol + ProviderRegistry — adding a provider = one adapter file + one `register()` call
- **Security posture:** All defenses from v1.0 maintained — CSP, CSRF, SSRF allowlist, host validation, automated regression guards
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`

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

## Shipped Milestones

| Version | Name | Shipped | Phases | Key Feature |
|---------|------|---------|--------|-------------|
| v1.0 | MVP | 2026-02-24 | 5 | Core IOC extraction + enrichment |
| v1.1 | UX Overhaul | 2026-02-25 | 3 | Card layout + filtering |
| v1.2 | Modern UI Redesign | 2026-02-28 | 2 | Design tokens + components |
| v1.3 | Visual Experience | 2026-02-28 | 3 | Page-level polish + animations |
| v2.0 | Home Page Modernization | 2026-02-28 | 1 | Minimal header + compact controls |
| v3.0 | TypeScript Migration | 2026-03-01 | 4 | JS→TS with strict types |
| v4.0 | Universal Threat Intel Hub | 2026-03-03 | 4 | 8 providers + registry + unified UX |

See `.planning/MILESTONES.md` for full details.

---
*Last updated: 2026-03-04 after v3.0 + v4.0 milestones completed*
