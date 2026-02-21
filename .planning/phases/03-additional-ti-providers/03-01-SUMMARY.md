---
phase: 03-additional-ti-providers
plan: 01
subsystem: enrichment
tags: [malwarebazaar, abuse.ch, multi-adapter, orchestrator, hash-lookup, ssrf]

# Dependency graph
requires:
  - phase: 02-core-enrichment
    provides: EnrichmentOrchestrator (single adapter), VTAdapter, EnrichmentResult/EnrichmentError models

provides:
  - Multi-adapter EnrichmentOrchestrator dispatching IOCs to all matching providers
  - MBAdapter for hash lookups against MalwareBazaar (abuse.ch)
  - supported_types property on VTAdapter (replaces ENDPOINT_MAP coupling)

affects: [04-display-and-ux, any future TI adapter]

# Tech tracking
tech-stack:
  added: []
  patterns: [adapter-supported-types, multi-adapter-dispatch, hash-presence-maps-to-malicious]

key-files:
  created:
    - app/enrichment/adapters/malwarebazaar.py
    - tests/test_malwarebazaar.py
  modified:
    - app/enrichment/orchestrator.py
    - app/enrichment/adapters/virustotal.py
    - app/enrichment/adapters/__init__.py
    - app/config.py
    - tests/test_orchestrator.py
    - tests/test_routes.py

key-decisions:
  - "adapters list replaces single adapter in EnrichmentOrchestrator — each adapter declares supported_types set, orchestrator dispatches all matching (adapter, ioc) pairs"
  - "total in job status reflects dispatched lookups (IOC count x matching adapters), not just IOC count"
  - "MBAdapter uses standalone requests.post per lookup (no shared Session) for thread safety"
  - "MalwareBazaar found hash -> verdict=malicious (presence in sample repo = confirmed malware)"
  - "MalwareBazaar hash_not_found -> verdict=no_data (not clean, just absent from the database)"
  - "No API key required for MalwareBazaar public hash queries"
  - "mb-api.abuse.ch added to ALLOWED_API_HOSTS SSRF allowlist in config.py"

patterns-established:
  - "Adapter pattern: each adapter declares supported_types: set[IOCType] and lookup(ioc) method"
  - "Presence-based verdict: binary source (malware repo) maps found=malicious, absent=no_data"
  - "Shared helper isolation: _validate_endpoint and _read_limited copied per-module (not extracted to shared utils) — deliberate isolation matches adapter-per-file pattern"

requirements-completed: [ENRC-02]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 3 Plan 01: Multi-Adapter Orchestrator and MalwareBazaar Adapter Summary

**Multi-adapter EnrichmentOrchestrator dispatching each IOC to all matching providers in parallel, plus MalwareBazaar (abuse.ch) hash adapter returning verdict=malicious for confirmed malware samples**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T10:40:05Z
- **Completed:** 2026-02-21T10:44:18Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Refactored `EnrichmentOrchestrator` to accept a list of adapters; each IOC dispatched to all adapters whose `supported_types` includes that IOC's type
- New `MBAdapter` queries `https://mb-api.abuse.ch/api/v1/` via POST for MD5/SHA1/SHA256 hashes; found -> malicious, not-found -> no_data
- `total` in job status now reflects actual dispatched lookups (IOC count x matching adapters), enabling accurate UI progress tracking for multi-provider enrichment
- All HTTP safety controls enforced on MalwareBazaar: timeout=(5,30), stream=True, allow_redirects=False, SSRF allowlist validation, 1 MB response cap
- 218 tests passing, 100% coverage on new adapter and refactored orchestrator

## Task Commits

Each task committed atomically:

1. **Task 1: RED — Write failing tests for multi-adapter orchestrator and MalwareBazaar adapter** - `5b25189` (test)
2. **Task 2: GREEN + REFACTOR — Implement multi-adapter orchestrator and MalwareBazaar adapter** - `4d89f51` (feat)

## Files Created/Modified

- `/home/chris/projects/sentinelx/app/enrichment/adapters/malwarebazaar.py` - New: MBAdapter for abuse.ch hash lookups with full HTTP safety controls
- `/home/chris/projects/sentinelx/app/enrichment/orchestrator.py` - Refactored: accepts `adapters` list, dispatches (adapter, ioc) pairs, total = dispatched count
- `/home/chris/projects/sentinelx/app/enrichment/adapters/virustotal.py` - Added: `supported_types` class attribute to VTAdapter
- `/home/chris/projects/sentinelx/app/enrichment/adapters/__init__.py` - Updated: exports MBAdapter and VTAdapter
- `/home/chris/projects/sentinelx/app/config.py` - Updated: mb-api.abuse.ch in ALLOWED_API_HOSTS
- `/home/chris/projects/sentinelx/tests/test_orchestrator.py` - Updated: adapters=[adapter] interface, 4 new multi-adapter tests
- `/home/chris/projects/sentinelx/tests/test_malwarebazaar.py` - New: 12 tests covering all MB adapter behavior
- `/home/chris/projects/sentinelx/tests/test_routes.py` - Fixed: route test asserting exact old allowed_hosts list

## Decisions Made

- Adapters list replaces single adapter — each adapter declares its own `supported_types` set, no adapter type knowledge in orchestrator
- `total` counts dispatched lookups (not IOC count) so the UI progress bar accurately reflects multi-provider enrichment work
- MBAdapter uses standalone `requests.post` per call (no shared Session), matching VTAdapter's thread safety pattern
- MalwareBazaar presence-based semantics: found in sample repo = confirmed malware (`verdict=malicious`); absent = `verdict=no_data` (not clean)
- Helper functions (`_validate_endpoint`, `_read_limited`) copied into MBAdapter module for isolation — deliberate choice to keep adapters self-contained

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed route test asserting stale allowed_hosts value**
- **Found during:** Task 2 (GREEN — full test suite run)
- **Issue:** `test_analyze_online_with_api_key_returns_job_id` in `tests/test_routes.py` asserted `allowed_hosts=["www.virustotal.com"]` exactly. Config.py already included mb-api.abuse.ch and threatfox-api.abuse.ch (added by previous planning), so test failed with assertion mismatch.
- **Fix:** Replaced exact list assertion with flexible check: `assert "www.virustotal.com" in call_kwargs["allowed_hosts"]`
- **Files modified:** `tests/test_routes.py`
- **Verification:** `python3 -m pytest tests/ -x --tb=short` — 218 passed, 0 failed
- **Committed in:** `4d89f51` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (1 bug — stale test assertion)
**Impact on plan:** Required fix for correctness; no scope creep.

## Issues Encountered

None — plan executed cleanly after the auto-fixed test assertion.

## User Setup Required

None - no external service configuration required (MalwareBazaar hash queries are public, no API key needed).

## Next Phase Readiness

- Multi-adapter orchestrator ready to accept additional adapters (ThreatFox, etc.) in Phase 3 Plans 02+
- MBAdapter independently testable and verified
- ALLOWED_API_HOSTS allowlist already includes abuse.ch hostnames for future adapters
- Routes module still wires only VTAdapter — Phase 3 will update wiring to include MBAdapter

---
*Phase: 03-additional-ti-providers*
*Completed: 2026-02-21*
