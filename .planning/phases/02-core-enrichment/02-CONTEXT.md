# Phase 2: Core Enrichment - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire VirusTotal enrichment into the existing offline pipeline. Analyst submits in online mode and receives per-IOC VirusTotal results with source attribution, parallel execution, and graceful error handling. All HTTP safety controls (no redirect following, no IOC-value URLs) are enforced. MalwareBazaar and ThreatFox are Phase 3 — not in scope here.

</domain>

<decisions>
## Implementation Decisions

### Results presentation
- Minimal verdict display: one line per provider showing provider name, verdict (malicious/clean/unknown), and scan date
- Color-coded verdict badges: red for malicious, green for clean, gray for unknown/no-data
- Light summary count at IOC level: e.g., "1/1 malicious" — a tally, not a combined score
- Copy button on each IOC copies the IOC value plus enrichment summary in compact text format
- Add a full export button to export all IOCs + enrichment at once (clipboard or file)

### Error & loading states
- Dual loading indicators: global progress bar at top ("3/7 IOCs enriched") plus per-IOC spinners
- Auto-retry once on enrichment failure, then show error if still failing
- On API key invalid or rate-limited: warn the analyst before submitting ("API key issue detected — continue with offline only?") rather than blocking or silently degrading

### API key handling
- Settings page in the app where the analyst pastes their VT API key — no env var requirement
- When no API key is configured, online mode is visible but clicking it redirects to the settings page to add the key

### Claude's Discretion
- Enrichment results layout approach (inline under IOC vs side panel vs other) — pick what fits the existing accordion template
- Error display approach (inline badges, toasts, or combination)
- "No data" vs "Clean" visual distinction strategy
- IOC row visual state when flagged (subtle color accent or neutral)
- API key storage mechanism (config file vs .env vs other secure approach)
- API key validation behavior on save (test call vs accept as-is)

</decisions>

<specifics>
## Specific Ideas

- Copy button should produce a compact text format useful for pasting into tickets or chat (IOC value + provider verdicts)
- The full export should cover all IOCs + enrichment in one action — format at Claude's discretion
- Loading should feel responsive: results appearing incrementally as each IOC's enrichment completes, not all-at-once after the last one finishes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-core-enrichment*
*Context gathered: 2026-02-21*
