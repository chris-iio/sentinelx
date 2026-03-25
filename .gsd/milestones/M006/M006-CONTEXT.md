# M006: Analyst Workflow & Coverage — Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

## Project Description

SentinelX is a self-hosted, zero-infrastructure threat intelligence hub. Analysts paste free-form text and get extracted, classified, enriched IOCs against 14 providers in parallel. Five milestones complete (960 tests, 28 validated requirements, 42 architectural decisions). The codebase is clean — no tech debt backlog.

## Why This Milestone

Competitive research against Pulsedive, SOCRadar IOC Radar, IntelOwl, MISP, and the VirusTotal ecosystem revealed SentinelX's unique strength (paste-and-go bulk extraction, self-hosted, transparent verdicts) and its gaps. M006 closes the gaps that matter for a lightweight local tool while explicitly avoiding enterprise platform features.

User's driving constraint: **"not to overscope what we should build and optimize and refactor"** — and when asked what would disappoint them most, they said **"complexity / heaviness."** Every feature in this milestone must add value without adding weight.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Submit IOCs, close the tab, return later, and reload past results from stored data
- See WHOIS data (registrar, creation date, expiry) for domain IOCs alongside existing DNS/VT/OTX results
- Paste text containing URLs and see them extracted, enriched, and displayed as a distinct IOC type
- Experience a visually consistent app where the home page matches the results page design language

### Entry point / environment

- Entry point: `http://localhost:5000` (Flask dev server)
- Environment: local dev / browser
- Live dependencies involved: WHOIS protocol (port 43), existing TI provider APIs

## Completion Class

- Contract complete means: all analysis history round-trips (save → list → reload), WHOIS returns structured data for common TLDs, URL IOCs pass E2E tests end-to-end, input page visual consistency verified
- Integration complete means: WHOIS adapter integrates into enrichment orchestrator with existing per-provider semaphore and backoff patterns
- Operational complete means: none — local dev tool, no service lifecycle concerns

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Analyst can submit IOCs in online mode, see results, close the tab, reopen the app, click a past analysis, and see the same full results page with all enrichment data
- Domain IOC enrichment includes WHOIS data (registrar, creation date) alongside DNS records and other provider results
- URL IOC pasted in free-form text is extracted, enriched by at least one provider (URLhaus), and displayed correctly with verdict badge and filter pill
- Home page and results page share the same design language (zinc tokens, Inter Variable, consistent spacing)

## Risks and Unknowns

- python-whois library reliability across TLDs — WHOIS data quality varies widely by registrar. Some return structured data, others return free-text that's hard to parse. The adapter must degrade gracefully.
- Analysis history storage size — storing full enrichment results per run could grow the SQLite DB. Need a sensible retention policy or at least awareness of growth rate.
- URL IOCs containing slashes — the detail page route `/detail/<ioc_type>/<path:ioc_value>` should handle this via Flask's path converter, but needs verification.

## Existing Codebase / Prior Art

- `app/enrichment/config_store.py` — SQLite WAL-mode pattern for CacheStore. History storage should follow this pattern.
- `app/enrichment/adapters/dns_lookup.py` — Non-HTTP adapter pattern (direct protocol, no safe_request()). WHOIS adapter should follow this.
- `app/pipeline/classifier.py` — URL classification already implemented (precedence 5, `_RE_URL` regex).
- `app/pipeline/extractor.py` — URL extraction via `iocextract.extract_urls()` already wired.
- `app/enrichment/adapters/urlhaus.py` — URLhaus already supports `IOCType.URL`.
- `app/enrichment/adapters/otx.py` — OTX already supports `IOCType.URL`.
- `app/enrichment/adapters/virustotal.py` — VT already supports `IOCType.URL`.
- `app/enrichment/adapters/threatfox.py` — ThreatFox already supports `IOCType.URL`.
- `tailwind.config.js` — CSS classes `filter-pill--url` and `ioc-type-badge--url` already safelisted.
- `app/templates/index.html` — Current input page: textarea, mode toggle, submit button. Minimal template.
- `app/templates/partials/_filter_bar.html` — Filter pills generated dynamically from `grouped.keys()`.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R030 — Analysis history persistence (primary M006 capability)
- R031 — Recent analyses list on home page (primary user loop)
- R032 — WHOIS enrichment for domains (coverage gap)
- R033 — URL IOC end-to-end polish (coverage gap)
- R013 — Input page redesign (design consistency, deferred since M002)

## Scope

### In Scope

- SQLite-backed analysis history with full enrichment result storage
- Recent analyses list on home page with click-to-reload
- WHOIS adapter using python-whois (no API key, direct protocol)
- URL IOC E2E test coverage and edge case handling
- Input page redesign to match quiet precision design language

### Out of Scope / Non-Goals

- REST API / programmatic access (explicitly deferred by user)
- STIX/TAXII export format
- SOAR/SIEM integration
- File upload or sandboxing
- Threat actor attribution / MITRE ATT&CK mapping
- IOC feed ingestion
- Community sharing features
- Multi-user authentication

## Technical Constraints

- Zero new infrastructure dependencies beyond python-whois pip package
- Must not slow startup or the core paste-and-go flow
- History storage must use existing SQLite WAL-mode pattern
- WHOIS adapter must follow Provider protocol exactly (like DnsAdapter)
- All new code must follow existing security patterns (textContent-only DOM, CSP, CSRF)

## Integration Points

- python-whois library — direct WHOIS protocol queries to registrar servers (port 43)
- Existing enrichment orchestrator — WHOIS adapter registered alongside 14 existing providers
- Existing CacheStore — history storage follows the same SQLite pattern
- Existing Tailwind/esbuild build pipeline — input page CSS changes via existing `make css`/`make js`

## Open Questions

- History retention policy — should old analyses auto-purge after N days, or grow indefinitely? Leaning toward no auto-purge for a local tool (analysts can delete the DB if it gets large).
- WHOIS timeout — python-whois can be slow (1-3s). Should it have a shorter timeout than HTTP adapters, or same 10s?
