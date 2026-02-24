---
phase: 04-ux-polish-and-security-verification
plan: 01
subsystem: ui
tags: [javascript, css, jinja2, verdict-badges, enrichment-ui, ux]

# Dependency graph
requires:
  - phase: 03-additional-ti-providers
    provides: Multi-provider enrichment with VT/MB/TF, worst-verdict tracking, spinner-wrapper DOM pattern
  - phase: 03.1-integration-fixes-git-hygiene
    provides: CSP-compliant JS patterns, SEC-08 textContent-only DOM, initSettingsPage IIFE guard
provides:
  - VERDICT_LABELS map distinguishing NO RECORD from CLEAN in badge display
  - Collapsed no-data section (details/summary) grouping providers with no record
  - IOC_PROVIDER_COUNTS map for per-IOC provider count (hashes=3, others=2)
  - updatePendingIndicator showing remaining provider count after first result
  - Progress counter text "N/M providers complete" (correct semantics)
affects: [future enrichment UI changes, badge label consistency, provider count tracking]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "getOrCreateNodataSection(): idempotent get-or-create for collapsed details section"
    - "IOC_PROVIDER_COUNTS JS constant drives per-IOC expected provider count via data-ioc-type attribute"
    - "VERDICT_LABELS map as display layer between internal verdict strings and UI text"

key-files:
  created: []
  modified:
    - app/static/main.js
    - app/static/style.css
    - app/templates/results.html

key-decisions:
  - "VERDICT_LABELS map added inside IIFE — display strings (MALICIOUS/CLEAN/NO RECORD) decoupled from internal verdict strings"
  - "no_data results appended to collapsed <details> section, not main slot — reduces visual noise for clean results"
  - "IOC_PROVIDER_COUNTS uses data-ioc-type attribute on enrichment row — no Python route change needed"
  - "updatePendingIndicator uses slot.insertBefore to keep indicator above nodata section in DOM order"
  - "clean verdict detail text explicitly mentions engine count to visually distinguish from no_data"
  - "Pre-existing E2E test_online_mode_indicator failure confirmed as environment issue (pre-dates these changes)"

patterns-established:
  - "Badge text always via VERDICT_LABELS lookup — no raw verdict strings in UI (UI-06)"
  - "getOrCreateNodataSection() pattern: check for existing element before creating, idempotent"
  - "data-ioc-type on enrichment row drives JS behavior — no server-side template logic needed"

requirements-completed: [UI-06]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 4 Plan 01: Verdict Clarity UX Summary

**Verdict label map, collapsed no-data section, pending provider indicator, and corrected progress counter making NO RECORD vs CLEAN instantly distinguishable for SOC analysts**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-24T09:03:09Z
- **Completed:** 2026-02-24T09:06:13Z
- **Tasks:** 2 auto-executed (Task 3 is checkpoint:human-verify awaiting visual confirmation)
- **Files modified:** 3

## Accomplishments
- Added `VERDICT_LABELS` constant mapping internal verdict strings to analyst-readable display labels (MALICIOUS, SUSPICIOUS, CLEAN, NO RECORD, ERROR)
- Added `IOC_PROVIDER_COUNTS` constant so JS knows how many providers to expect per IOC type without a server round-trip
- Implemented `getOrCreateNodataSection()` / `updateNodataSummary()` to route `no_data` results into a collapsed `<details>` section per IOC, reducing visual noise
- Implemented `updatePendingIndicator()` showing remaining provider count ("N providers still loading...") after first result arrives
- Updated `updateProgressBar()` to read "N/M providers complete" (correct per-provider semantics, not "IOCs enriched")
- Updated clean verdict detail text to mention engine count ("Clean — scanned by N engines") making it distinct from no_data
- Added `data-ioc-type` attribute to enrichment row for JS provider count lookup
- Added CSS styles for `.enrichment-nodata-section` matching dark theme with collapsed triangle indicator

## Task Commits

Each task was committed atomically:

1. **Task 1: Verdict labels, no-data section, pending indicator in main.js** - `1630e48` (feat)
2. **Task 2: Progress text, data-ioc-type attribute, nodata CSS** - `7dfda6a` (feat)
3. **Task 3: Visual verification** - PENDING (checkpoint:human-verify)

## Files Created/Modified
- `app/static/main.js` - VERDICT_LABELS, IOC_PROVIDER_COUNTS, getOrCreateNodataSection, updateNodataSummary, updatePendingIndicator, updated renderEnrichmentResult and updateProgressBar
- `app/templates/results.html` - Progress counter text updated; data-ioc-type added to enrichment row
- `app/static/style.css` - .enrichment-nodata-section collapsed details/summary CSS with dark theme colors

## Decisions Made
- `VERDICT_LABELS` map uses `|| verdict.toUpperCase()` fallback for unknown verdicts — future-proof
- `IOC_PROVIDER_COUNTS` is JS-side constant (no Python route change needed) — data-ioc-type attribute bridges template data to JS
- `updatePendingIndicator` uses `slot.insertBefore(indicator, nodataSection)` to maintain DOM order: active results, then pending text, then nodata section
- `clean` verdict text now explicitly says "scanned by N engines" to make the distinction from `no_data` immediately obvious even without reading badge color

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing E2E test `test_online_mode_indicator[chromium]` fails (environment issue — Playwright cannot find the mode indicator element in the online mode flow, confirmed pre-existing by reverting changes and re-running). Out of scope — not caused by this plan's changes. Logged as pre-existing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- UI-06 automated implementation complete; awaiting human visual verification (Task 3 checkpoint)
- After visual verification confirmed, all v1.0 requirements fulfilled (UI-01 through UI-06)
- Ready for Phase 4 Plan 02 (security verification) once checkpoint cleared

---
*Phase: 04-ux-polish-and-security-verification*
*Completed: 2026-02-24*
