# Phase 3: Additional TI Providers - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add MalwareBazaar (hash lookups) and ThreatFox (hash, domain, IP, URL lookups) as enrichment providers alongside the existing VirusTotal adapter. The orchestrator already supports parallel execution and per-provider error isolation — this phase adds two new adapters that plug into the existing pattern. No changes to extraction, classification, or offline mode.

</domain>

<decisions>
## Implementation Decisions

### Provider result fields
- MalwareBazaar: show malware family, tags, file type, and first/last seen dates (skip reporter, file size, signature — less useful for quick triage)
- ThreatFox: show threat type, malware family, confidence level, and C2 indicator status (skip reporter and first seen — confidence and C2 flag carry more weight)
- No-data results: always show "No data found" for every provider queried — analyst needs confirmation that the lookup was attempted, not ambiguity about which providers ran

### Multi-provider display
- Stacked vertically: provider results listed one below the other under each IOC
- Results appear as they arrive (fastest first) — more responsive feel, positions are additive (new results append, don't reorder)
- Copy/export: worst verdict only — export includes the most concerning result across all providers for each IOC

### Verdict mapping
- MalwareBazaar: found = malicious (it's a malware sample repo — existence means malware), not found = no_data
- ThreatFox: threshold-based — confidence level determines verdict
- New 'suspicious' verdict level added to the system: malicious, suspicious, clean, no_data
- ThreatFox low-confidence hits map to suspicious, high-confidence to malicious

### Claude's Discretion
- Exact MalwareBazaar/ThreatFox field selection within the guidelines above
- ThreatFox confidence threshold value (likely 75, but research the data quality first)
- Whether to add a 'suspicious' verdict or keep 3 verdicts — decide based on implementation complexity vs. analyst value
- Data model approach: generic metadata dict vs typed per-provider structures — fit the existing codebase pattern
- Visual identity per provider (subtle color accents vs uniform labels) — whatever serves scannability best
- Provider result ordering when multiple arrive simultaneously

</decisions>

<specifics>
## Specific Ideas

- Results should feel additive — as each provider responds, its result slots in below any existing results for that IOC without disrupting the page
- The existing polling loop already handles incremental rendering; new providers should plug into the same mechanism
- Both MalwareBazaar and ThreatFox are public APIs (no API key required) — they should always run when online mode is active

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-additional-ti-providers*
*Context gathered: 2026-02-21*
