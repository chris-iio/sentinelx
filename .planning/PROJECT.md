# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 13 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). No opaque combined scores.

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
- ✓ SQLite-backed enrichment result cache with configurable TTL and settings UI — v5.0
- ✓ Client-side export menu (JSON/CSV/clipboard) replacing single copy button — v5.0
- ✓ Bulk IOC input mode with one-per-line parser and toggle UI — v5.0
- ✓ Provider context fields (VT top detections/reputation) with generic field rendering — v5.0
- ✓ Zero-auth IP intelligence: GeoIP, rDNS, proxy/VPN/hosting flags via ip-api.com — v6.0
- ✓ Known-good hash detection: CIRCL hashlookup with visually distinct KNOWN GOOD verdict — v6.0
- ✓ Live DNS records (A/MX/NS/TXT) for domains via dnspython — v6.0
- ✓ Certificate transparency history for domains via crt.sh — v6.0
- ✓ Passive DNS pivoting via ThreatMiner for all IOC types — v6.0
- ✓ Shodan InternetDB full field rendering (ports, CVEs, hostnames, CPEs) — v6.0
- ✓ Bookmarkable per-IOC detail page with tabbed provider results — v6.0
- ✓ Analyst notes on IOCs persisted in SQLite — v6.0
- ✓ Custom tags on IOCs with tag-based filtering — v6.0
- ✓ SVG relationship graph showing IOC-provider connections and verdicts — v6.0
- ✓ 13 threat intel providers (5 zero-auth + 1 public + 7 key-auth) — v6.0

### Active

(No active milestone — run `/gsd:new-milestone` to start next cycle)

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

## Context

- **Users:** SOC analysts performing initial triage of alerts, emails, and threat reports
- **Environment:** Runs on analyst's local machine or an internal jump box (not internet-facing)
- **Tech stack:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend stack:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc/emerald/teal design tokens
- **Codebase:** ~4,923 LOC Python, ~2,459 LOC TypeScript, ~635 LOC templates, ~12,350 LOC tests
- **Test suite:** 757+ unit/integration + 91 E2E (up from 483 at v5.0)
- **Threat intel providers (13):** VirusTotal (API key), MalwareBazaar (public), ThreatFox (public), Shodan InternetDB (zero-auth), URLhaus (free key), OTX AlienVault (free key), GreyNoise Community (free key), AbuseIPDB (free key), ip-api.com (zero-auth), CIRCL hashlookup (zero-auth), DNS Records (zero-auth), crt.sh (zero-auth), ThreatMiner (zero-auth)
- **Architecture:** Provider Protocol + ProviderRegistry — adding a provider = one adapter file + one `register()` call. AnnotationStore for per-IOC notes/tags (separate SQLite DB). CacheStore for enrichment result caching.
- **Security posture:** All defenses from v1.0 maintained — CSP, CSRF, SSRF allowlist (12 HTTP hosts), host validation, automated regression guards. CSRF meta tag for client-side fetch.
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`
- **Frontend modules:** 14 TypeScript modules (was 12 at v5.0 — added annotations.ts, graph.ts)

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
| v5.0 | Quality-of-Life | 2026-03-09 | 1 | Cache + export + bulk input + context fields |
| v6.0 | Analyst Experience | 2026-03-14 | 4 | 5 zero-auth providers + detail page + annotations |

See `.planning/MILESTONES.md` for full details.

---
*Last updated: 2026-03-14 after v6.0 Analyst Experience milestone*
