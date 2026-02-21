# oneshot-ioc

## What This Is

A security-focused local web application for SOC analysts to quickly triage indicators of compromise. The analyst pastes a single IOC or a block of alert/email text, and the app extracts, normalizes, classifies, and optionally enriches IOCs against external threat intelligence APIs — presenting transparent, source-attributed results for fast decision-making.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Single-page web interface with large paste input, submit button, and offline/online toggle
- [ ] IOC extraction from free-form text (alert snippets, email headers/body, raw IOCs)
- [ ] Defanging normalization (hxxp, [.], {.}, and common obfuscation patterns)
- [ ] Deterministic IOC classification: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE
- [ ] Offline mode: extraction + classification only, zero network calls
- [ ] Online mode: parallel queries to VirusTotal + researched additional providers
- [ ] Structured results page grouped by IOC type
- [ ] Clear source attribution on every enrichment result (provider name, timestamp, raw verdict)
- [ ] No opaque combined "threat score" — show provider verdicts as-is
- [ ] Visual indicator when external lookups are in progress
- [ ] Localhost-only binding by default
- [ ] API keys read exclusively from environment variables
- [ ] Strict HTTP timeouts and max response size on all outbound requests
- [ ] No redirect following on outbound requests (unless explicitly justified)
- [ ] Never fetch/crawl the target URL itself — only call intelligence APIs
- [ ] HTML output sanitization to prevent injection from untrusted IOC strings or API responses
- [ ] No subprocess calls, no shell execution, no dynamic code execution
- [ ] No persistent storage of raw pasted blobs

### Out of Scope

- Public internet exposure — this is a local/jump-box tool only
- User authentication — single-user, local access assumed
- Historical analysis or trending — v1 is single-shot triage
- Automated response/blocking actions — read-only enrichment
- Mobile or responsive design — desktop browser on analyst workstation
- Custom branding or theming — functional UI only

## Context

- **Users:** SOC analysts performing initial triage of alerts, emails, and threat reports
- **Environment:** Runs on analyst's local machine or an internal jump box (not internet-facing)
- **Input variety:** Analysts paste anything — a single IP, a SIEM alert snippet, full email headers, or a block of defanged IOCs from a threat report
- **Tech stack:** Python + Flask (chosen for rapid development and rich parsing ecosystem)
- **Threat intel APIs:** VirusTotal confirmed; additional providers to be determined via domain research
- **Persistence:** To be determined by research — likely in-memory or local cache with TTL for API results
- **IOC extraction depth:** To be determined by research — starting with standard defanging patterns, may expand

## Constraints

- **Security model**: All user input and all API responses treated as untrusted at every layer
- **Network**: Localhost binding only; no outbound calls in offline mode; strict timeouts in online mode
- **Dependencies**: Minimal — prefer well-audited libraries; no unnecessary attack surface
- **Secrets**: API keys via environment variables only; never logged, never rendered
- **Execution**: No subprocess, no shell, no eval/exec — deterministic code paths only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + Flask | Analyst-friendly, rich parsing ecosystem, fast to iterate | — Pending |
| VirusTotal as primary API | Most widely used, comprehensive coverage across IOC types | — Pending |
| No combined threat score | Transparency for analysts — show raw verdicts, let humans decide | — Pending |
| Localhost-only by default | Defense in depth — tool is not designed for multi-user or public access | — Pending |
| Additional APIs via research | Let domain research identify practical, high-value integrations | — Pending |
| IOC extraction patterns via research | Let research determine optimal defanging/extraction approach | — Pending |

---
*Last updated: 2026-02-21 after initialization*
