# oneshot-ioc

## What This Is

A security-first local web application for SOC analysts to triage indicators of compromise. The analyst pastes free-form text (alerts, email headers, threat reports, raw IOCs), and the app extracts, normalizes, classifies, and optionally enriches IOCs against VirusTotal, MalwareBazaar, and ThreatFox — presenting transparent, source-attributed per-provider verdicts with no opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Requirements

### Validated

- ✓ Single-page web interface with large paste input, submit button, and offline/online toggle — v1.0
- ✓ IOC extraction from free-form text (alert snippets, email headers/body, raw IOCs) — v1.0
- ✓ Defanging normalization (hxxp, [.], {.}, and 20 common obfuscation patterns) — v1.0
- ✓ Deterministic IOC classification: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE — v1.0
- ✓ Offline mode: extraction + classification only, zero network calls — v1.0
- ✓ Online mode: parallel queries to VirusTotal, MalwareBazaar, ThreatFox — v1.0
- ✓ Structured results page grouped by IOC type — v1.0
- ✓ Clear source attribution on every enrichment result (provider name, timestamp, raw verdict) — v1.0
- ✓ No opaque combined "threat score" — show provider verdicts as-is — v1.0
- ✓ Visual indicator when external lookups are in progress — v1.0
- ✓ Verdict clarity: "NO RECORD" vs "CLEAN" instantly distinguishable — v1.0
- ✓ Localhost-only binding by default — v1.0
- ✓ API keys read exclusively from environment variables — v1.0
- ✓ Strict HTTP timeouts and max response size on all outbound requests — v1.0
- ✓ No redirect following on outbound requests — v1.0
- ✓ Never fetch/crawl the target URL itself — only call intelligence APIs — v1.0
- ✓ HTML output sanitization (Jinja2 autoescaping, no |safe on untrusted data) — v1.0
- ✓ CSP: default-src 'self'; script-src 'self' — v1.0
- ✓ No subprocess calls, no shell execution, no dynamic code execution — v1.0
- ✓ No persistent storage of raw pasted blobs — v1.0
- ✓ Card-based results layout with severity borders and summary dashboard — v1.1
- ✓ Verdict/type/text filtering with sticky filter bar — v1.1
- ✓ Toggle switch, paste feedback, contextual submit button — v1.1
- ✓ Tailwind CSS standalone CLI build integration — v1.1
- ✓ Dark-first design token system (zinc/emerald/teal CSS custom properties) — v1.2
- ✓ Self-hosted Inter Variable + JetBrains Mono Variable fonts — v1.2
- ✓ WCAG AA verified contrast for all token pairs — v1.2
- ✓ Shared component elevation (verdict badges, focus rings, buttons, form elements) — v1.2
- ✓ Heroicons v2 Jinja2 macro for inline SVG icons — v1.2
- ✓ Header/footer redesign with emerald brand accent — v1.2

### Active (v2.0 Home Page Modernization)

Requirements being defined — see `.planning/REQUIREMENTS.md` when complete.

### Out of Scope

- Export/copy features (EXPORT-01 through EXPORT-04) — dropped from v1.1, superseded by v1.2 redesign
- Settings test connection / accessibility / perf verification (POLISH-01 through POLISH-03) — dropped from v1.1, folded into v1.2
- New threat intelligence providers — frontend-only milestones
- Backend route changes or new API endpoints
- Public internet exposure — this is a local/jump-box tool only
- User authentication — single-user, local access assumed
- Historical analysis or trending — v1 is single-shot triage
- Automated response/blocking actions — read-only enrichment
- Mobile or responsive design — desktop browser on analyst workstation
- Custom branding or theming — functional UI only
- WHOIS / RDAP enrichment — high complexity, often privacy-redacted
- Malware sandbox detonation — fundamentally different capability
- Persistent session history — requires persistence design decision

## Context

- **Users:** SOC analysts performing initial triage of alerts, emails, and threat reports
- **Environment:** Runs on analyst's local machine or an internal jump box (not internet-facing)
- **Tech stack:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests for HTTP
- **Frontend stack (v1.2):** Tailwind CSS (standalone CLI) + vanilla JS, Inter Variable + JetBrains Mono Variable self-hosted, dark-first zinc/emerald/teal design tokens, Heroicons v2 inline SVG via Jinja2 macro
- **Codebase:** ~1,674 LOC app Python, ~1,534 LOC frontend (HTML/CSS/JS), ~3,893 LOC tests
- **Test suite:** 224 tests, 97% coverage
- **Threat intel providers:** VirusTotal (API key required), MalwareBazaar (public), ThreatFox (public)
- **Security posture:** All defenses established in Phase 1, verified by automated regression guards (CSP, XSS, SSRF)
- **Known issue:** Pre-existing E2E test `test_online_mode_indicator[chromium]` fails in Playwright (environment issue, not a code bug)

## Constraints

- **Security model**: All user input and all API responses treated as untrusted at every layer
- **Network**: Localhost binding only; no outbound calls in offline mode; strict timeouts in online mode
- **Dependencies**: Minimal — prefer well-audited libraries; no unnecessary attack surface
- **Secrets**: API keys via environment variables only; never logged, never rendered
- **Execution**: No subprocess, no shell, no eval/exec — deterministic code paths only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Flask | Analyst-friendly, rich parsing ecosystem, fast to iterate | ✓ Good — 14 plans in 4 days, Flask well-suited |
| VirusTotal as primary API | Most widely used, comprehensive coverage across IOC types | ✓ Good — solid baseline for IP/domain/URL/hash |
| MalwareBazaar + ThreatFox | abuse.ch public APIs, no API key needed, complementary coverage | ✓ Good — hash/domain/IP coverage with zero config |
| No combined threat score | Transparency for analysts — show raw verdicts, let humans decide | ✓ Good — verdict labels (MALICIOUS/CLEAN/NO RECORD) clear |
| Localhost-only by default | Defense in depth — tool is not designed for multi-user or public access | ✓ Good — 127.0.0.1 binding + TRUSTED_HOSTS |
| iocextract + iocsearcher | Dual-library extraction for coverage, two-stage dedup | ✓ Good — broad pattern match + validation |
| Security-first (Phase 1) | All defenses before any network code | ✓ Good — CSP/CSRF/host-validation from day one |
| No flask-talisman | Manual after_request headers for full control | ✓ Good — simpler, no dependency, easy to audit |
| ThreadPoolExecutor parallel | max_workers=4 respects VT free tier rate limit | ✓ Good — parallel without API abuse |
| textContent only (no innerHTML) | Prevent XSS from API responses in dynamic DOM | ✓ Good — SEC-08 maintained throughout |

| Tailwind CSS standalone CLI | No Node.js needed, generates CSS from utility classes, theme extends existing CSS vars | Pending — v1.1 Phase 6 |
| Alpine.js CSP build | Declarative reactivity (~15KB), CSP-compatible (no eval), served from /static/ | Pending — v1.1 Phase 6 |
| Keep vanilla JS for enrichment | Polling and clipboard code works well, no reason to rewrite into Alpine | Pending — v1.1 Phase 6 |
| Zero backend changes in v1.1 | All v1.1 is frontend-only — same routes, same data models | Pending — v1.1 |

## Current Milestone: v2.0 Home Page Modernization

**Goal:** Modernize the home page into a clean, minimal, contemporary experience — compact auto-growing textarea, stripped-down header, and simplified footer.

**Target features:**
- Minimal header bar (logo icon + "SentinelX" + settings gear icon, no tagline, thinner)
- Compact auto-growing textarea (~5 rows default, expands on paste)
- Cleaner inline controls (toggle + buttons with tighter spacing)
- Simplified footer matching the minimal header aesthetic

---
*Last updated: 2026-02-28 after v1.3 work landed, v2.0 milestone started*
