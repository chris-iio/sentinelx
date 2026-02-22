---
phase: 03-additional-ti-providers
plan: "02"
subsystem: enrichment
tags: [threatfox, abuse.ch, confidence-verdict, tdd, http-safety, ssrf]

# Dependency graph
requires:
  - phase: 02-core-enrichment
    provides: EnrichmentResult, EnrichmentError models; VTAdapter pattern; orchestrator thread pool
provides:
  - TFAdapter: ThreatFox adapter for hash/domain/IP/URL lookups with confidence-based verdicts
  - suspicious verdict: new verdict level for low-confidence ThreatFox hits (confidence < 75)
  - test_threatfox.py: 15 TDD-verified tests with mocked HTTP coverage
affects:
  - 03-03-PLAN (UI display for suspicious verdict badge)
  - any plan that integrates TFAdapter into orchestrator

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Shared HTTP safety: _validate_endpoint and _read_limited initially per-adapter; extracted to app/enrichment/http_safety.py (commit a716378)
    - Confidence-based verdict: ThreatFox confidence_level >=75 -> malicious, <75 -> suspicious
    - Multi-record selection: max() by confidence_level when ThreatFox returns multiple records
    - Hash vs IOC routing: MD5/SHA1/SHA256 use search_hash; domain/IP/URL use search_ioc

key-files:
  created:
    - app/enrichment/adapters/threatfox.py
    - tests/test_threatfox.py
  modified:
    - app/config.py

key-decisions:
  - "CONFIDENCE_THRESHOLD=75: >=75 maps to malicious, <75 maps to suspicious (per user decision from plan context)"
  - "suspicious verdict is a plain string in verdict: str field — no model changes needed (not an enum)"
  - "ThreatFox POST API: search_hash for hashes, search_ioc for domain/IP/URL (per API v1 docs)"
  - "Multiple ThreatFox records: select highest confidence_level entry before applying threshold"
  - "No API key required for ThreatFox basic search queries (public endpoint)"
  - "Add both mb-api.abuse.ch and threatfox-api.abuse.ch to ALLOWED_API_HOSTS in config.py"

patterns-established:
  - "Confidence-based verdict: >=75 malicious, <75 suspicious, no_result no_data"
  - "Max-select pattern: when API returns array of results, use max(data, key=lambda r: r.get('confidence_level', 0))"

requirements-completed: [ENRC-03]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 3 Plan 02: ThreatFox Adapter Summary

**ThreatFox (abuse.ch) adapter with confidence-based verdict mapping: >=75 confidence -> malicious, <75 -> suspicious, introducing the 'suspicious' verdict level to the enrichment system.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T10:40:37Z
- **Completed:** 2026-02-21T10:44:12Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3 (threatfox.py created, test_threatfox.py created, config.py modified)

## Accomplishments

- TFAdapter supports all 7 enrichable IOC types: hashes (search_hash) and domain/IP/URL (search_ioc)
- Confidence-based verdict mapping with threshold at 75 (per user decision)
- Multi-record handling: selects highest-confidence entry when ThreatFox returns multiple records
- All HTTP safety controls enforced: timeout, 1 MB response cap, no redirects, SSRF allowlist
- 15 TDD-verified tests covering type coverage, boundary conditions, error handling, SSRF validation
- Zero regressions — 218 unit tests pass (up from 187 before this plan)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for ThreatFox adapter** - `9b81dd6` (test)
2. **Task 2: GREEN + REFACTOR — Implement ThreatFox adapter** - `a64de73` (feat)

_TDD: test commit (RED) then implementation commit (GREEN). Both in main branch._

## Files Created/Modified

- `app/enrichment/adapters/threatfox.py` - TFAdapter class with search_hash/search_ioc routing, confidence threshold, multi-record selection, HTTP safety controls
- `tests/test_threatfox.py` - 15 TDD tests: 5 IOC type tests, 7 edge case tests, 2 confidence boundary tests, 1 size limit test, 1 multi-record test
- `app/config.py` - Added `mb-api.abuse.ch` and `threatfox-api.abuse.ch` to ALLOWED_API_HOSTS

## Decisions Made

- **CONFIDENCE_THRESHOLD=75**: >=75 confidence level maps to malicious, <75 maps to suspicious. Exact boundary (75) is malicious. Decision from plan context based on ThreatFox score semantics.
- **suspicious verdict as plain string**: The EnrichmentResult model uses `verdict: str` (not an enum), so "suspicious" requires zero model changes. CSS class `verdict-suspicious` will be added in Plan 03.
- **Shared HTTP safety module**: Helper functions `_validate_endpoint` and `_read_limited` were initially per-adapter copies; subsequently extracted to `app/enrichment/http_safety.py` (commit a716378). Adapters now import from the shared module.
- **Search routing**: Hashes (MD5/SHA1/SHA256) use `{"query": "search_hash", "hash": value}`; all others use `{"query": "search_ioc", "search_term": value}` per ThreatFox API v1.
- **Both abuse.ch hosts in config**: Plan note that Plan 01 and 02 both modify ALLOWED_API_HOSTS was resolved by adding both `mb-api.abuse.ch` and `threatfox-api.abuse.ch` in this commit since mb-api.abuse.ch was already present from the MalwareBazaar adapter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MalwareBazaar adapter was already implemented (pre-existing)**
- **Found during:** Task 2 verification (running full test suite)
- **Issue:** `test_malwarebazaar.py` was committed in plan 03-01 RED phase but the GREEN (adapter implementation) had also been completed. The full test suite `tests/ --ignore=tests/e2e` passed with 218 tests.
- **Fix:** No action required — malwarebazaar.py already existed at `/app/enrichment/adapters/malwarebazaar.py`. The test suite passed without modification.
- **Files modified:** None
- **Verification:** `python3 -m pytest tests/ --ignore=tests/e2e -q` shows 218 passed

---

**Total deviations:** 1 (pre-existing implementation discovered, no action needed)
**Impact on plan:** No scope creep. ThreatFox plan executed exactly as written.

## Issues Encountered

None — plan executed cleanly. The pre-existing MalwareBazaar implementation (from an earlier 03-01 run) meant 218 tests passed instead of the expected 187+15=202 (there were already 16 MB adapter tests in the baseline count).

## User Setup Required

None — ThreatFox basic search queries are public. No API key configuration required.

## Next Phase Readiness

- TFAdapter ready for integration into orchestrator alongside VTAdapter and MBAdapter (Plan 03-03)
- 'suspicious' verdict introduced — Plan 03-03 needs to add `verdict-suspicious` CSS class and badge to UI
- All SSRF controls enforced — no additional security configuration needed

---
*Phase: 03-additional-ti-providers*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: app/enrichment/adapters/threatfox.py
- FOUND: tests/test_threatfox.py
- FOUND: .planning/phases/03-additional-ti-providers/03-02-SUMMARY.md
- FOUND: commit 9b81dd6 (test RED)
- FOUND: commit a64de73 (feat GREEN)
- Test suite: 218 passed, 0 failed
