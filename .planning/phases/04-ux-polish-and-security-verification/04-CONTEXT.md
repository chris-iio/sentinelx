# Phase 4: UX Polish and Security Verification - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Sharpen verdict clarity so SOC analysts can distinguish "no data found" from "explicitly clean" at a glance for every provider result. Refine how the UI communicates enrichment state during and after provider queries. Confirm the full security posture (CSP, template safety, HTTP safety) before shipping. No new providers, no new extraction capabilities, no new enrichment features.

</domain>

<decisions>
## Implementation Decisions

### Verdict visual language
- Color + label badges to distinguish verdict states (no combined icon+color+label — color carries the distinction, label confirms)
- Gray/muted styling for "no data" results — de-emphasized so the analyst's eye is drawn to actual findings
- Per-provider verdict badges only — no aggregated IOC-level summary badge (aligns with the project's transparency principle of never inventing scores)

### Provider result density
- Summary view by default: verdict badge + provider name + timestamp — analyst sees the key signal at a glance
- Expandable for raw provider details when needed
- Providers with "no data" grouped into a separate collapsed section below active results — reduces noise when multiple providers return nothing

### Enrichment progress UX
- Results stream in as each provider completes — analyst can start reading early results while slower providers are still in flight
- Overall progress counter at the top ("2/3 providers complete") gives a quick sense of how much is left
- Per-provider loading indicators for providers still in flight

### Claude's Discretion
- Exact verdict label text (choosing between technical and descriptive phrasing based on existing UI style and SOC analyst expectations)
- Expand/detail interaction pattern (click-to-expand vs tooltip vs other)
- Provider error display prominence and styling
- Loading indicator type (skeleton placeholder vs spinner vs other)
- Completion signal when all providers finish (subtle transition vs brief toast vs other)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The key principle is transparency: never invent aggregate scores, always attribute results to their source provider, always make the distinction between "no data" and "clean" unambiguous.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-ux-polish-and-security-verification*
*Context gathered: 2026-02-24*
