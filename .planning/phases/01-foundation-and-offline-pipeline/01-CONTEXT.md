# Phase 1: Foundation and Offline Pipeline - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Flask app delivering the complete offline IOC triage workflow: analyst pastes free-form text, app extracts all IOCs (IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE), normalizes defanged patterns, classifies by type, deduplicates, and displays results grouped by type. Zero outbound network calls in offline mode. Security scaffold (CSP, CSRF, host validation, input size cap, no subprocess/eval, autoescaping) is established here and never retrofitted.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User explicitly deferred all implementation decisions to Claude for MVP velocity. The following are Claude's calls:

**Results layout:**
- Collapsible accordion sections per IOC type with count badges (e.g., "IPv4 (12)")
- All sections expanded by default on first load
- Clean table inside each section: normalized IOC value, type classification, one-click copy button for refanged value
- Show original defanged form as a subtle secondary column where it differs from normalized

**Visual direction:**
- Dark theme — standard for security tooling, easier on analyst eyes during long sessions
- Minimal, clinical aesthetic — no gradients, no decoration, just data
- Monospace font for IOC values, system sans-serif for labels/UI
- Muted color palette with type-specific accent colors for IOC group headers (e.g., blue for IPs, orange for hashes, green for domains)

**Input experience:**
- Single large textarea with placeholder text showing example mixed IOC input (defanged examples)
- Offline/online toggle as a simple switch above the submit button, defaulting to offline
- Submit button labeled "Extract IOCs" (not "Submit" or "Analyze")
- Clear button to reset the textarea

**Error and empty states:**
- No IOCs found: friendly message "No IOCs detected in the pasted text" with a hint about supported types
- Size limit exceeded: rejection message before extraction with the size limit stated
- Empty input: disable submit button when textarea is empty
- Validation errors: inline, not modal

</decisions>

<specifics>
## Specific Ideas

- MVP focus — get functional first, polish later (Phase 4)
- Analyst should be able to paste and see results in seconds, no friction
- Security posture is non-negotiable even for MVP — all SEC requirements in Phase 1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-and-offline-pipeline*
*Context gathered: 2026-02-21*
