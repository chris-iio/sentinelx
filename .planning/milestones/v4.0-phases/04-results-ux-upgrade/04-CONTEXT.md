# Phase 4: Results UX Upgrade - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the IOC results page from flat per-provider result rows into a unified experience — each IOC card gets a summary header (worst verdict + source attribution + consensus badge) with expandable per-provider detail rows. Add provider coverage info to the verdict dashboard. No new backend endpoints or data models — this is a frontend UX refactor on existing data.

</domain>

<decisions>
## Implementation Decisions

### Summary card content
- Always-visible summary shows: worst verdict label + source attribution from the most detailed provider
- "Most detailed" = provider with richest stats (e.g., VirusTotal's "45/72 engines" over AbuseIPDB's confidence score)
- Format: `MALICIOUS — VirusTotal: 45/72 engines`
- Consensus pill badge at right edge of summary: `[3/5]` format showing flagged/responded count
- Pill badge color-coded by agreement level: green (0 flagged) → yellow (1-2 flagged) → red (3+ flagged)

### Consensus denominator
- "Responded" = providers that returned malicious, suspicious, or clean verdicts
- Excludes: unconfigured/skipped providers, error providers, and no-data providers
- No-data does NOT count as a vote — "3/5 flagged" means 3 of 5 providers with actual data flagged it

### Expand/collapse interaction
- Chevron icon (▶/▼) in card header next to verdict badge — compact accordion pattern
- Cards collapsed by default — summary-only view for scanning
- Smooth slide animation (~200ms) for expand/collapse — consistent with v1.3 motion design
- Multiple cards can be open simultaneously (independent state, not accordion)

### Provider detail rows (expanded section)
- One compact line per provider: `Name  [VERDICT]  key stat` (e.g., "VirusTotal  [MALICIOUS]  45/72 engines")
- Sorted by severity: malicious providers first, then suspicious, clean, no-data, errors last
- Error rows shown in red: `VirusTotal  [ERROR]  Request timed out` — analyst sees what failed
- Unconfigured/skipped providers NOT shown in detail rows — only providers that ran appear

### Dashboard provider coverage
- New static text row below existing verdict KPI cards
- Shows: "8 registered · 5 configured · 3 need API keys" (or similar)
- Not interactive — settings link already exists in header gear icon

### Claude's Discretion
- Exact CSS implementation of slide animation (CSS transition vs keyframes)
- Chevron icon implementation (SVG, Unicode, or CSS triangle)
- How to determine "most detailed provider" algorithmically (heuristic for picking the attribution source)
- Provider coverage row exact layout and typography
- How to handle edge case where all providers return no-data (no worst verdict to display)
- Whether to preserve the existing no-data collapsible `<details>` pattern or fold it into the new expandable section

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `computeWorstVerdict()` in enrichment.ts — already computes worst verdict across all providers per IOC
- `iocVerdicts[ioc_value]` accumulator — tracks `{provider, verdict, summaryText}` per provider per IOC
- `VERDICT_SEVERITY` array — `["error", "no_data", "clean", "suspicious", "malicious"]` for severity sorting
- Verdict color triples in CSS custom properties — `--verdict-{type}-{text|bg|border}` for all verdict types
- `.verdict-badge` CSS component — ready for use in both summary and detail rows
- `.enrichment-detail` CSS class — 0.78rem font, secondary color, for provider context text
- `.enrichment-nodata-section` — existing collapsible `<details>` pattern for no-data grouping
- Shimmer skeleton in `_enrichment_slot.html` — loading state before results arrive
- `getProviderCounts()` — reads provider counts from DOM data attribute (dynamic, not hardcoded)

### Established Patterns
- **DOM updates**: All dynamic content uses `createElement + textContent` (never innerHTML) — SEC-08 XSS prevention
- **Polling loop**: 750ms interval, incremental rendering as results arrive, dedup by ioc_value+provider key
- **Card updates**: `updateCardVerdict()` sets `data-verdict`, label text, CSS class — drives filtering + sorting
- **Dashboard**: `updateDashboardCounts()` queries all `.ioc-card` elements, counts by `data-verdict`
- **Debounced sort**: `sortCardsBySeverity()` debounced at 100ms to prevent jank during rapid result arrival
- **Discriminated union**: `result.type === "result"` vs `"error"` for safe narrowing

### Integration Points
- `_ioc_card.html` template — add summary section + expand toggle + details container
- `_enrichment_slot.html` — restructure to support summary-first, details-expandable layout
- `enrichment.ts` `renderEnrichmentResult()` — refactor to build summary + expandable detail rows
- `cards.ts` — may need new function to update consensus badge count as results arrive
- `_verdict_dashboard.html` — add provider coverage row
- `input.css` — add styles for summary section, chevron toggle, slide animation, provider detail rows
- `routes.py` — pass provider coverage data (registered/configured/needs-key counts) to template

</code_context>

<specifics>
## Specific Ideas

- Summary line reads like a SOC analyst's quick take: "MALICIOUS — VirusTotal: 45/72 engines [3/5]"
- The consensus pill sits at the right edge of the summary row, not inline with the text
- Detail rows sorted by severity mirrors how analysts triage — worst first
- Error rows should be visually distinct (red) so analysts know when a provider failed to check
- Provider coverage in dashboard helps new users discover they have unconfigured providers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-results-ux-upgrade*
*Context gathered: 2026-03-03*
