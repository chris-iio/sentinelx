# Project Research Summary

**Project:** sentinelx (oneshot-ioc)
**Domain:** Security-focused local IOC triage web application for SOC analysts
**Researched:** 2026-02-21
**Confidence:** HIGH (core stack, architecture, security pitfalls); MEDIUM (TI API rate limits, defanging edge cases)

## Executive Summary

sentinelx is a localhost-only Flask web application that accepts free-form text pastes (SIEM snippets, threat reports, email headers), extracts and classifies IOCs across eight types (IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE), and enriches them in parallel against curated free-tier threat intelligence APIs. The expert approach for this class of tool — as validated by IntelOwl, Cortex, and Pulsedive — is a strict pipeline architecture: extraction feeds normalization, normalization feeds classification, and only then does enrichment fan out concurrently. The tool must never combine verdicts into a score; SOC analysts require per-source attribution to make triage decisions. The offline/online mode split is not optional — many analyst environments have restricted outbound access.

The recommended stack is intentionally minimal: Flask 3.1 on Python 3.12, iocextract as the primary extraction library (with iocsearcher supplementing for CVE and additional types), httpx for parallel outbound calls via asyncio, cachetools TTLCache for in-memory result caching, Flask-WTF for CSRF, and flask-talisman for security headers. For five concurrent providers and a single-user local tool, this stack avoids the operational overhead of Redis, Celery, or a full async web framework while still executing all enrichment calls concurrently. The only provider without an official Python client (AbuseIPDB) is trivially called via direct httpx — ten lines of code beats an unmaintained PyPI dependency.

The dominant risk class for this type of tool is security, not scalability. Three vulnerabilities are particularly well-documented and easy to introduce accidentally: SSRF (using the IOC value as an HTTP target instead of passing it as an API parameter), XSS (using Jinja2's `|safe` filter on IOC strings or API response fields), and DNS rebinding (failing to validate the `Host` header against a trusted list). All three must be designed out at the foundation layer — they cannot be retrofitted safely. A fourth risk, ReDoS from complex IOC-extraction regex on adversarially crafted input, is mitigated by enforcing a 50 KB input cap at the Flask route level before extraction runs. These risks are well-understood and the mitigations are straightforward; they simply must be built first.

## Key Findings

### Recommended Stack

The stack is driven by two non-negotiable constraints: no persistent storage and parallel API execution. In-memory TTLCache replaces any database or disk cache. httpx with asyncio (or ThreadPoolExecutor) replaces synchronous `requests`. Flask wins over FastAPI because the sync-by-default model is simpler to reason about for 3-5 concurrent I/O-bound calls, and over Django because the ORM and admin machinery adds attack surface with zero benefit for a no-persistence tool.

Two IOC extraction libraries are recommended together: `iocextract` (battle-tested, handles defanged variants natively, broad ecosystem adoption) as the primary layer, plus `iocsearcher` (released December 2025, more accurate on 11 of 13 shared types per peer-reviewed comparison) for CVE identifiers and supplementary types. Do not use `ioc-fanger` (inactive since September 2022) or `cyobstract` (unmaintained). AbuseIPDB should be called directly via httpx — the third-party PyPI wrapper is inactive.

**Core technologies:**
- Python 3.12 + Flask 3.1.3: web framework — lightest viable option, Jinja2 autoescape on by default, no ORM or auth surface to audit
- iocextract 1.16.1 + iocsearcher 2.7.2: IOC extraction — proven defanging support; iocextract for breadth, iocsearcher for CVE and accuracy
- httpx 0.28.1: async HTTP client — supports both sync (tests) and async (parallel API calls) in one library; strict timeout config
- vt-py 0.22.0: VirusTotal API v3 client — official, async-native, released October 2025
- greynoise 3.0.1: GreyNoise API client — official, released June 2025; note: major version bump from 2.x, breaking changes
- cachetools 7.0.1: in-memory TTL cache — zero external dependencies, auto-evicts stale entries; wrap with threading.RLock
- Flask-WTF 1.2.2: CSRF protection — single call protects all POST endpoints; required even for localhost tools
- flask-talisman 1.1.0: security headers — CSP, X-Frame-Options, X-Content-Type-Options; low activity but stable
- python-dotenv 1.2.1: .env loading — development convenience; production should use environment variables directly
- ruff 0.15.2 + bandit: linting and security scanning — ruff covers most Bandit rules but run both for full security output

### Expected Features

The full feature research is in `.planning/research/FEATURES.md`. Key decisions: five providers are viable for v1 (VT, AbuseIPDB, Shodan InternetDB, MalwareBazaar, ThreatFox). Shodan InternetDB requires no API key — it is the easiest provider to include. GreyNoise's 50 lookups/week community limit makes it a v1.x addition rather than v1 core.

**Must have (table stakes):**
- Free-form text paste with multi-IOC extraction and defanging normalization — analysts never paste single IOCs
- IOC classification by type (IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE) — gates enrichment routing
- Deduplication before enrichment — prevents wasted API quota
- VirusTotal enrichment across all four IOC types — the universal SOC baseline
- AbuseIPDB enrichment for IPs — best crowdsourced IP reputation not in VT
- Shodan InternetDB for IPs — open ports + CVEs, no key required
- MalwareBazaar for file hashes — deepest file hash context of any free provider
- ThreatFox for hashes/domains/IPs/URLs — C2 and malware family attribution from abuse.ch
- Parallel enrichment execution — sequential is unusably slow with 5+ providers
- Results grouped by IOC type with source attribution per verdict — non-negotiable analyst expectation
- Offline mode (extract + classify only) — required for air-gapped environments
- Localhost-only binding with API keys from environment variables

**Should have (v1.x additions):**
- AlienVault OTX enrichment — campaign/pulse context; adds registration friction, defer until core is validated
- GreyNoise enrichment — reduces false positives on IP alerts; 50/week limit constrains regular use
- URLhaus for URLs — supplements VT for malware distribution URL context
- Per-provider TTL caching — add when repeated same-session lookups become a pain point
- Copy-to-clipboard per IOC (refanged)
- IOC count confirmation step before API calls fire

**Defer (v2+):**
- Pulsedive enrichment — rate limits unverified; validate free tier first
- WHOIS / RDAP — SecurityTrails free tier too restrictive (50/month) for regular use
- CVE CVSS lookup via NVD — moderate value, moderate complexity
- IOC history across sessions — requires persistence design decision

**Never build:**
- Combined threat score or risk rating — hides conflicting signals, creates false confidence
- Fetching or crawling target URLs — exposes analyst IP to adversary, contaminates forensics
- Email sending of results — SMTP config + data exfiltration path

### Architecture Approach

The architecture is a linear pipeline with a fan-out enrichment layer and a clean offline/online fork. The key invariant is that the extraction pipeline (Extractor → Normalizer → Classifier) is implemented as pure functions independent of Flask — no request context, no side effects, no HTTP calls. This makes the offline mode a first-class output of the pipeline rather than a special case, and makes the entire extraction layer testable without a running server. Each TI provider is a separate adapter implementing `BaseEnricher.lookup(ioc) -> EnricherResult`, registered in an orchestrator that fans out with ThreadPoolExecutor. All failures are caught at the adapter level and returned as error EnricherResults — the orchestrator never fails due to a single provider's misbehavior.

**Major components:**
1. Flask Route Layer (`routes.py`) — receives POST, validates input length/content-type, dispatches to pipeline, renders results
2. IOC Pipeline (`pipeline/`) — Extractor → Normalizer → Classifier as pure functions; returns typed `IOC` dataclasses; independent of Flask
3. Enricher Orchestrator (`enrichers/__init__.py`) — fans out parallel lookups using ThreadPoolExecutor; collects results with per-enricher timeouts; handles failures gracefully
4. Provider Adapters (`enrichers/virustotal.py`, etc.) — one class per API provider implementing `BaseEnricher`; each independently testable with mocked HTTP
5. Config Reader (`config.py`) — reads env vars at startup; fails fast with clear error if required key is missing; never exposes keys downstream
6. Jinja2 Template Layer (`templates/`) — autoescape always on; `|safe` never used on untrusted data; CSP blocks inline scripts

**Recommended build order (from ARCHITECTURE.md):**
1. Config + models — foundational types used by everything
2. Extractor + Normalizer — core pipeline, pure functions
3. Classifier — depends on extractor output types
4. Routes (offline mode) — full request flow without enrichment
5. BaseEnricher + VirusTotal adapter — first enrichment path
6. Parallel orchestrator — fan-out with working adapter
7. Additional provider adapters — additive, each independently testable
8. Security hardening — CSP headers, response size limits, input caps; validate whole system

### Critical Pitfalls

1. **SSRF via IOC value used as HTTP target** — Never pass a user-submitted IOC value as the URL in any HTTP request. Always call the fixed TI API endpoint with the IOC as an encoded parameter. Disable redirect following unconditionally. Enforce a hostname allowlist before any outbound call. Must be built into the HTTP client wrapper before any provider integration begins.

2. **XSS from unescaped IOC strings or API response data** — Never use `|safe`, `Markup()`, or `render_template_string()` on user input or API response fields. Jinja2 autoescape covers most cases but must be defended by discipline: every template field for IOC values or API data must use `{{ var }}` bare. CSP header set to `default-src 'self'` provides the second layer. URL-type IOCs rendered as links must have scheme validated to `http://` or `https://` — `javascript:` scheme runs on click.

3. **API key exposure via debug mode or logging** — `DEBUG=False` must be hardcoded in the production app factory. API keys passed as URL query parameters appear in server logs — always use request headers. Log only status codes and timing, never response bodies or headers that contain keys.

4. **DNS rebinding attack against the localhost Flask server** — Configure `TRUSTED_HOSTS = ['localhost', '127.0.0.1']` in Flask so requests with other `Host` headers are rejected with HTTP 400. Bind only to `127.0.0.1`. This is not theoretical: CVE-2025-49596 (Anthropic MCP Inspector, CVSS 9.4, 2025) was exactly this attack against a localhost tool.

5. **ReDoS from crafted IOC input hitting extraction regex** — Enforce `MAX_CONTENT_LENGTH = 512 * 1024` at the Flask route before extraction runs. Audit all custom regex patterns with `regexploit`. Consider `re2` binding for extraction patterns on untrusted input.

## Implications for Roadmap

Based on research, the architecture's build order dependency chain maps cleanly to a four-phase structure. The key forcing function is that security defenses must be established in Phase 1 — retrofitting SSRF protection and host header validation after API integration is built is a recovery operation, not development.

### Phase 1: Foundation and Security Scaffold

**Rationale:** All downstream components depend on Config, models, and security decisions. SSRF protection, host header validation, debug mode lockdown, and CSP headers must exist before any HTTP client code is written — they cannot be added safely after the fact. The offline pipeline can be fully functional and tested before any network code exists.
**Delivers:** Running Flask application with security headers, input validation, CSRF protection, TRUSTED_HOSTS, `MAX_CONTENT_LENGTH`, and a complete offline pipeline (extract + normalize + classify) that returns IOCs grouped by type.
**Addresses:** Offline mode (table stakes), IOC extraction, classification, deduplication, localhost binding, env var key management.
**Avoids:** Debug mode exposure, DNS rebinding, SSRF foundations set wrong from the start.

### Phase 2: Core Enrichment (VirusTotal + Parallel Orchestrator)

**Rationale:** VirusTotal is the universal baseline — if the enrichment architecture works for VT, it works for any provider. The parallel orchestrator with ThreadPoolExecutor must be built with a single working adapter before additional adapters are added. This phase validates the full request flow end-to-end.
**Delivers:** Full online mode with VirusTotal enrichment across IP, domain, URL, and hash types. Parallel orchestrator with per-enricher timeout handling. Error results (not exceptions) for failed providers. Working UI with results grouped by IOC type and source-attributed verdicts.
**Uses:** httpx 0.28.1, vt-py 0.22.0, ThreadPoolExecutor, cachetools TTLCache (per-provider keying).
**Avoids:** Sequential API calls (performance trap), API key exposure in logs, SSRF via IOC-as-URL, trusting API response structure without safe field access.

### Phase 3: Additional TI Providers

**Rationale:** Each provider adapter is additive — a new file implementing `BaseEnricher`, registered in the orchestrator. No changes to existing code. This phase delivers the full v1 feature set. Provider order: Shodan InternetDB first (no key required, validates adapter pattern), then AbuseIPDB (IP-only, simple REST), MalwareBazaar (hash-only), ThreatFox (multi-type).
**Delivers:** Full five-provider enrichment: VT + AbuseIPDB + Shodan InternetDB + MalwareBazaar + ThreatFox. Each provider independently tested with mocked HTTP. Rate limit handling (429 + exponential backoff) for providers that document limits.
**Avoids:** Unmaintained AbuseIPDB PyPI package (use direct httpx), URL crawling (all outbound calls to allowlisted TI hostnames only), partial defanging failures (test corpus of 30+ variants).

### Phase 4: UX Polish and Security Hardening Validation

**Rationale:** Security hardening is verified here, not added — it was built in Phase 1. This phase runs the "looks done but isn't" checklist from PITFALLS.md, adds the UX features that reduce analyst friction, and validates the full attack surface before shipping.
**Delivers:** Visual loading indicator during enrichment, clear "not found" vs "clean" verdict distinction, unclassified IOC display (analysts see what was dropped), mode indicator (offline/online), URL scheme validation before rendering as links, and full security checklist verification (CSP curl check, API key log grep, redirect following grep, allowlist integration test).
**Avoids:** Opaque combined threat score (never built, confirmed absent), blocking UI during API calls, silently dropping unclassified IOCs.

### Phase Ordering Rationale

- Security scaffold precedes all network code — SSRF allowlist and TRUSTED_HOSTS must be in the HTTP client wrapper and Flask app factory before any TI API integration is written
- Offline pipeline (Phase 1) is fully functional before any HTTP code exists — validates extraction quality and gives a testable baseline
- Single-provider enrichment (Phase 2) before multi-provider (Phase 3) — the parallel orchestrator is proven with one adapter before it must handle five simultaneous failure modes
- Security verification (Phase 4) is an explicit phase, not a checkbox — ensures the "looks done but isn't" list from PITFALLS.md is addressed before shipping

### Research Flags

Phases with standard patterns (research-phase not needed):
- **Phase 1:** Flask app factory, Blueprint, security headers, CSRF — all well-documented in official Flask 3.1 docs. ThreadPoolExecutor is stdlib. Pattern is established.
- **Phase 2:** VirusTotal API v3 via official vt-py client — official docs are comprehensive. Parallel orchestrator pattern is documented in ARCHITECTURE.md with working code examples.
- **Phase 4:** UX patterns for results display — standard HTML/Jinja2 work.

Phases that may benefit from targeted research during planning:
- **Phase 3:** Individual provider API schemas — ThreatFox and MalwareBazaar response structures should be validated against live API docs before building adapters. Rate limit documentation for MalwareBazaar and URLhaus is "fair use" with no stated limits; verify before building backoff logic. GreyNoise 3.0.1 has breaking changes from 2.x — review migration guide before integration.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core stack (Flask, httpx, cachetools) verified against official PyPI and docs. iocextract MEDIUM (last release Sept 2023, but widely used). flask-talisman MEDIUM (low activity, last release August 2023, no known Flask 3.1 incompatibilities). |
| Features | HIGH (core) / MEDIUM (API limits) | Core feature set validated against IntelOwl, Cortex, Pulsedive comparisons. API rate limits for MalwareBazaar, ThreatFox, URLhaus are "fair use" without documented limits — treat as unverified until tested against live APIs. |
| Architecture | HIGH | Patterns (Application Factory, Pipeline as Pure Functions, Provider Adapter, ThreadPoolExecutor fan-out, Defense-in-Depth rendering) all verified against official Flask docs, Python stdlib docs, and security tooling references. |
| Pitfalls | HIGH | Security pitfalls are well-documented with CVE references (CVE-2025-49596 for DNS rebinding) and OWASP sources. IOC extraction nuances (defanging edge cases, ReDoS) are MEDIUM — arxiv paper cited but specific regex patterns need adversarial testing to confirm. |

**Overall confidence:** HIGH for build decisions. MEDIUM for provider-specific API behaviors (rate limits, response schemas) — validate during Phase 3 implementation.

### Gaps to Address

- **GreyNoise 3.0.1 breaking changes from 2.x:** Review migration guide before Phase 3 integration begins. The 50 lookup/week community limit may make this a v1.x addition rather than v1 core.
- **MalwareBazaar and ThreatFox "fair use" rate limits:** No documented numeric limits. Test against live APIs early in Phase 3 to avoid surprise quota enforcement. Plan graceful degradation if limits hit.
- **iocextract vs iocsearcher accuracy for domain/URL types:** The peer-reviewed accuracy comparison is MEDIUM confidence (paper-based). Recommend building extraction tests with a real-world corpus early in Phase 1 to validate before shipping.
- **Defanging edge cases beyond documented patterns:** Unicode lookalike characters, mixed-case protocol strings, and analyst-invented shorthand cannot be enumerated in advance. The 30+ variant test corpus should be built incrementally and expanded based on analyst feedback.
- **Pulsedive rate limits:** Entirely unverified. Do not include in any roadmap phase without confirming free tier practicality first.

## Sources

### Primary (HIGH confidence)
- https://flask.palletsprojects.com/en/stable/ — Flask 3.1 official docs (app factory, blueprints, security, Jinja2 autoescape)
- https://pypi.org/project/iocsearcher/ — version 2.7.2, released December 2025
- https://pypi.org/project/vt-py/ — version 0.22.0, released October 2025
- https://pypi.org/project/greynoise/ — version 3.0.1, released June 2025
- https://pypi.org/project/httpx/ — version 0.28.1, released December 2024
- https://pypi.org/project/cachetools/ — version 7.0.1, released February 2026
- https://pypi.org/project/Flask-WTF/ — version 1.2.2, released October 2024
- https://pypi.org/project/python-dotenv/ — version 1.2.1, released October 2025
- https://pypi.org/project/ruff/ — version 0.15.2, released February 2026
- https://internetdb.shodan.io/ — Shodan InternetDB, no-key endpoint verified
- https://docs.python.org/3/library/concurrent.futures.html — ThreadPoolExecutor, Python 3 stdlib
- https://www.python-httpx.org/advanced/ — httpx timeouts, resource limits, async support
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html — SSRF prevention
- https://www.oligo.security/blog/critical-rce-vulnerability-in-anthropic-mcp-inspector-cve-2025-49596 — CVE-2025-49596 DNS rebinding reference

### Secondary (MEDIUM confidence)
- https://pypi.org/project/iocextract/ — version 1.16.1, last release September 2023; widely used but not recently updated
- https://pypi.org/project/flask-talisman/ — version 1.1.0, last release August 2023; low activity
- https://docs.virustotal.com/reference/public-vs-premium-api — VT rate limits (500/day, 4/min for public)
- https://www.abuseipdb.com/pricing — AbuseIPDB 1,000 checks/day free tier
- https://bazaar.abuse.ch/api/ — MalwareBazaar community API, "fair use" limits
- https://threatfox.abuse.ch/api/ — ThreatFox community API, IOC expiry since 2025-05-01
- https://docs.greynoise.io/docs/using-the-greynoise-community-api — 50 lookups/week verified
- https://snyk.io/advisor/python/ioc-fanger — ioc-fanger inactive status
- ScienceDirect peer-reviewed paper — iocextract vs iocsearcher accuracy comparison

### Tertiary (LOW confidence)
- https://upskilld.com/article/free-cybersecurity-apis-for-ioc-lookups/ — third-party API aggregation; verify rate limits independently
- Defanging edge case patterns beyond documented variants — practitioner observation; validate with test corpus

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
