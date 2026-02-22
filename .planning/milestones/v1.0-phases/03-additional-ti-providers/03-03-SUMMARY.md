---
phase: 03-additional-ti-providers
plan: "03"
subsystem: enrichment-ui
tags: [multi-provider, routes, javascript, css, suspicious-verdict, worst-verdict, human-verify]

# Dependency graph
requires:
  - phase: 03-additional-ti-providers
    plan: "01"
    provides: MBAdapter, multi-adapter EnrichmentOrchestrator
  - phase: 03-additional-ti-providers
    plan: "02"
    provides: TFAdapter, suspicious verdict

provides:
  - Multi-provider /analyze route: VTAdapter + MBAdapter + TFAdapter wired into orchestrator
  - enrichable_count computed from actual dispatched lookups (IOC x matching adapters)
  - Multi-provider JS polling: per-provider result rows stacked vertically per IOC
  - Worst-verdict logic: copy/export uses most severe verdict across all providers per IOC
  - .verdict-suspicious CSS class: amber badge distinct from malicious/clean/error

affects:
  - 04-display-and-ux (Phase 4 UX polish if applicable)
  - All future adapter integrations (pattern established)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Multi-adapter wiring in routes: adapters_list = [vt, mb, tf]; orchestrator(adapters=adapters_list)
    - enrichable_count from multi-adapter dispatch: sum 1 for ioc for adapter if ioc.type in adapter.supported_types
    - Dedup key ioc_value+"|"+provider for per-provider result tracking in JS
    - Worst-verdict severity order: error < no_data < clean < suspicious < malicious
    - Spinner in .spinner-wrapper div for clean first-result removal

key-files:
  created: []
  modified:
    - app/routes.py
    - app/static/main.js
    - app/static/style.css
    - app/templates/results.html
    - tests/test_routes.py

key-decisions:
  - "Routes wire all three adapters (VT, MB, TF) in online mode — MalwareBazaar and ThreatFox need no API key"
  - "enrichable_count sums dispatched lookups across adapters — accurately reflects multi-provider progress denominator"
  - "ENDPOINT_MAP import removed from routes — decoupled via adapter.supported_types property"
  - "Dedup key is ioc_value+provider — each provider result appended separately, not replacing"
  - "Worst-verdict for copy/export: severity order error<no_data<clean<suspicious<malicious; most severe wins"
  - "Spinner wrapped in .spinner-wrapper div for clean DOM removal on first provider result"

requirements-completed: [ENRC-02, ENRC-03]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 3 Plan 03: Multi-Provider Route Wiring and UI Integration Summary

**All three TI providers (VirusTotal, MalwareBazaar, ThreatFox) wired into /analyze route; JS polling renders stacked per-provider results with worst-verdict copy/export and amber suspicious badge.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-21T10:49:38Z
- **Completed:** 2026-02-21T10:52:38Z (Tasks 1+2; Task 3 awaiting human verification)
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint, approved)
- **Files modified:** 5

## Accomplishments

- `/analyze` route now creates VTAdapter, MBAdapter, and TFAdapter and passes all three to the orchestrator
- `enrichable_count` accurately reflects total dispatched lookups (sum of IOC x adapter matches), not just IOC count
- Removed `ENDPOINT_MAP` import from routes — enrichable_count now computed via `adapter.supported_types`
- JS polling loop uses `ioc_value+"|"+provider` dedup key — each provider result rendered as its own row stacked vertically
- First provider result removes spinner wrapper cleanly; subsequent results append to same slot
- Worst-verdict tracking: per-IOC provider verdicts accumulated with severity ordering (malicious > suspicious > clean > no_data > error); copy button `data-enrichment` reflects worst verdict
- Export uses same worst-verdict logic via `data-enrichment` attribute on copy buttons
- `.verdict-suspicious` CSS badge added with amber (#f59e0b), visually distinct from `.verdict-error`
- 221 tests passing (3 new route tests added)

## Task Commits

Each task committed atomically:

1. **Task 1: Wire multi-provider adapters into routes and update enrichable_count** - `9fca183` (feat)
2. **Task 2: Update JS polling for multi-provider display and add suspicious verdict CSS** - `c7987c6` (feat)
3. **Task 3: Visual verification** — checkpoint approved by user (human-verify gate passed)

## Files Created/Modified

- `/home/chris/projects/sentinelx/app/routes.py` - Added MBAdapter + TFAdapter imports, created all three adapters in online mode, multi-adapter enrichable_count, removed ENDPOINT_MAP
- `/home/chris/projects/sentinelx/app/static/main.js` - Multi-provider dedup key, append vs replace rendering, spinner-wrapper removal, worst-verdict copy/export, suspicious verdict text
- `/home/chris/projects/sentinelx/app/static/style.css` - Added .verdict-suspicious (amber), .provider-result-row, .spinner-wrapper, .enrichment-slot flex-direction column
- `/home/chris/projects/sentinelx/app/templates/results.html` - Wrapped spinner in .spinner-wrapper div
- `/home/chris/projects/sentinelx/tests/test_routes.py` - Updated existing mock test for all three adapters; added 3 new tests: creates_all_three_adapters, enrichable_count_multi_provider, enrichable_count_domain_two_providers

## Decisions Made

- All three adapters always created in online mode — MalwareBazaar and ThreatFox need no API key, so no conditional gating needed
- enrichable_count decoupled from ENDPOINT_MAP via adapter.supported_types — cleaner separation, adapter knows its own capabilities
- Worst-verdict rather than all-verdicts in copy/export — analyst gets the most actionable single verdict per IOC for ticket pasting
- Spinner wrapped in .spinner-wrapper to enable targeted removal (querySelector) on first provider result arrival

## Deviations from Plan

None — plan executed exactly as written. Tasks 1 and 2 completed without auto-fixes needed.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. VirusTotal API key (configured in Phase 2) is the only credential needed. MalwareBazaar and ThreatFox use public endpoints.

## Next Phase Readiness

- Phase 3 complete: all three TI providers (VT, MB, TF) wired and human-verified end-to-end
- Phase 4 (Display and UX) can build on the stable multi-provider enrichment foundation
- No blockers — all SSRF controls, rate limits, and test coverage in place
- 221 tests passing (100% new-path coverage for routes and adapters)

---
*Phase: 03-additional-ti-providers*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: app/routes.py
- FOUND: app/static/main.js
- FOUND: app/static/style.css
- FOUND: app/templates/results.html
- FOUND: tests/test_routes.py
- FOUND: commit 9fca183 (Task 1 feat)
- FOUND: commit c7987c6 (Task 2 feat)
- Human verification: approved by user (Task 3 checkpoint)
- Test suite: 221 passed, 0 failed
