# Phase 01: Zero-Auth IP Intelligence + Known-Good - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add zero-auth IP intelligence (GeoIP, rDNS, proxy/VPN/hosting flags) to every IP IOC result card, implement NSRL known-good detection for hash IOCs via CIRCL hashlookup, and complete Shodan InternetDB card rendering (CPEs and tags currently fetched but not displayed). All new providers are zero-auth — no API key configuration required.

</domain>

<decisions>
## Implementation Decisions

### Known-Good Verdict Design
- New verdict value: `known_good` with **blue** badge color — outside the red/amber/green threat spectrum entirely
- Badge text: "KNOWN GOOD" (matches requirements language)
- **Override behavior**: If CIRCL hashlookup confirms NSRL match, summary verdict becomes KNOWN GOOD regardless of other provider verdicts (e.g., VT false positives on calc.exe get overridden)
- Detail rows still show individual provider verdicts normally — override is summary-level only
- Add "Known Good" as a filter chip in the verdict filter bar (between Clean and No Data)

### IP Enrichment Display
- **Single combined "IP Context" row** — GeoIP + rDNS + proxy flags together in one row, not separate provider rows
- **Context-only, no verdict badge** — IP Context is factual metadata, not a threat assessment
- **First in detail row order** — appears above all provider detail rows (VT, Shodan, GreyNoise, etc.)
- Compact inline geo format: `DE · Frankfurt · AS24940 (Hetzner Online GmbH)` — country code + city + ASN with ISP name in one line
- rDNS on its own line: `PTR: tor-exit.example.com`
- Flags on their own line as tags: `[hosting] [tor-exit]`

### Proxy Flag Presentation
- **Neutral tags** — same visual styling as Shodan ports/vulns context tags. No color-coding by risk category
- **Only show true flags** — if proxy/VPN/hosting/mobile are false, that flag is not rendered. Clean residential IPs show no flags line at all
- **Purely informational** — IP Context never participates in summary verdict calculation. Context for analysts, not a threat vote
- **Keep separate from Shodan tags** — IP Context flags (from ip-api.com) and Shodan tags (from Shodan) each stay in their own provider row. No merging, clear source attribution

### Shodan Card Completeness
- Add CPEs and tags to the existing Shodan InternetDB context fields (both already fetched in `raw_stats`, just not rendered)
- CPEs render as tags (same as ports/vulns/hostnames)
- Shodan tags render as tags (same styling)

### Claude's Discretion
- Exact CSS/Tailwind classes for the blue KNOWN GOOD badge
- rDNS lookup implementation approach (built into ip-api.com adapter or separate)
- CIRCL hashlookup adapter internals (API endpoint, response parsing, error handling)
- CPE string truncation or formatting in Shodan card (if needed for readability)
- How to handle ip-api.com rate limits or failures gracefully
- Whether IP Context row has a subtle visual separator from provider rows

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ShodanAdapter` (`app/enrichment/adapters/shodan.py`): Canonical zero-auth provider pattern — copy for new adapters
- `PROVIDER_CONTEXT_FIELDS` (`app/static/src/ts/modules/enrichment.ts` lines 224-267): Lookup table driving context field rendering — add entries for new providers
- `createContextFields()` in enrichment.ts: Renders `"text"` and `"tags"` field types — both needed for IP Context
- `http_safety.py`: Shared `validate_endpoint()`, `read_limited()`, `TIMEOUT` — all new adapters must use these
- `computeWorstVerdict()` in enrichment.ts: Verdict hierarchy function — needs modification for known_good override logic

### Established Patterns
- Provider Protocol: `name`, `supported_types`, `requires_api_key`, `lookup()`, `is_configured()` — structural typing, no inheritance
- Zero-auth registration: No `PROVIDER_INFO` entry needed (settings UI only shows key-requiring providers)
- `raw_stats` dict: Extensibility point for provider-specific data — arbitrary key/value pairs passed through to frontend
- SEC-08: All dynamic DOM via `createElement + textContent` — never `innerHTML`
- SSRF protection: All provider hostnames must be in `ALLOWED_API_HOSTS` in `config.py`

### Integration Points
- New adapters: `app/enrichment/adapters/<name>.py` + `registry.register()` in `setup.py` + hostname in `config.py`
- New context fields: Entry in `PROVIDER_CONTEXT_FIELDS` record in `enrichment.ts`
- New verdict: Add to `VerdictKey` type in `types/ioc.ts`, update `VERDICT_LABELS`, `VERDICT_CLASSES`, update `computeWorstVerdict()`, update filter bar, update CSS
- Shodan EPROV-01: Frontend-only — add `cpes` and `tags` entries to existing `PROVIDER_CONTEXT_FIELDS["Shodan InternetDB"]`

</code_context>

<specifics>
## Specific Ideas

- IP Context row should feel like "card-level metadata" even though it's technically a detail row — geographic context before threat verdicts
- The KNOWN GOOD override is philosophically aligned with the project's "show raw verdicts, let humans decide" principle — NSRL is a factual database, not an opinion
- ip-api.com already chosen over MaxMind GeoLite2 (STATE.md decision) — zero-auth, no setup, JSON API

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-zero-auth-ip-intelligence-known-good*
*Context gathered: 2026-03-12*
