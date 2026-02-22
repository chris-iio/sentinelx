---
phase: 02-core-enrichment
plan: 01
subsystem: api
tags: [virustotal, requests, configparser, tdd, enrichment, security]

# Dependency graph
requires:
  - phase: 01-foundation-and-offline-pipeline
    provides: "IOC and IOCType models from app/pipeline/models.py; ALLOWED_API_HOSTS scaffold in app/config.py"

provides:
  - "EnrichmentResult and EnrichmentError frozen dataclasses (app/enrichment/models.py)"
  - "VTAdapter with ENDPOINT_MAP, lookup(), full HTTP safety controls (app/enrichment/adapters/virustotal.py)"
  - "ConfigStore for API key persistence to ~/.sentinelx/config.ini (app/enrichment/config_store.py)"
  - "ALLOWED_API_HOSTS populated with ['www.virustotal.com'] (app/config.py)"
  - "32 passing tests with 98% enrichment package coverage"

affects:
  - "02-02 (EnrichmentOrchestrator depends on VTAdapter and EnrichmentResult/Error)"
  - "02-03 (routing layer depends on VTAdapter and ConfigStore)"
  - "02-04 (settings UI depends on ConfigStore)"

# Tech tracking
tech-stack:
  added:
    - "pytest-cov (coverage reporting)"
  patterns:
    - "VT adapter pattern: ENDPOINT_MAP lambda dict mapping IOCType to URL builder"
    - "base64url encoding for VT URL IOC identifiers (no padding)"
    - "raise_for_status() after 404 check to avoid JSON parse on error bodies"
    - "Fresh requests.Session per lookup() call for thread safety"
    - "ConfigStore accepts optional config_path for test isolation via tmp_path"

key-files:
  created:
    - app/enrichment/__init__.py
    - app/enrichment/models.py
    - app/enrichment/adapters/__init__.py
    - app/enrichment/adapters/virustotal.py
    - app/enrichment/config_store.py
    - tests/test_enrichment_models.py
    - tests/test_vt_adapter.py
    - tests/test_config_store.py
  modified:
    - app/config.py

key-decisions:
  - "Fresh requests.Session per lookup() call (not shared) — avoids thread safety issues under ThreadPoolExecutor (Pitfall 3)"
  - "raise_for_status() called AFTER 404 check — VT 404 means 'no data' not error; calling before avoids JSONDecodeError on empty error bodies (Pitfall 1)"
  - "ALLOWED_API_HOSTS passed explicitly to VTAdapter.__init__() rather than reading from Flask context — allows adapter use outside request context"
  - "ConfigStore accepts config_path param for test isolation; defaults to ~/.sentinelx/config.ini in production"
  - "98% enrichment package coverage achieved (target >90%); 3 uncovered lines are dead-code paths"

patterns-established:
  - "EnrichmentResult: frozen dataclass with ioc, provider, verdict, detection_count, total_engines, scan_date, raw_stats"
  - "EnrichmentError: frozen dataclass with ioc, provider, error"
  - "VT adapter: validate endpoint against allowlist BEFORE making network call"
  - "HTTP safety pattern: timeout=(5,30), allow_redirects=False, stream=True on all enrichment requests"
  - "ConfigStore: read with cfg.get(section, key, fallback=None); write creates parent dir if needed"

requirements-completed: [ENRC-01, SEC-04, SEC-05, SEC-06, SEC-07]

# Metrics
duration: 5min
completed: 2026-02-21
---

# Phase 2 Plan 01: VT Adapter, Enrichment Models, and ConfigStore Summary

**VirusTotal API v3 adapter with full HTTP safety controls (timeout, stream+size-cap, no-redirect, SSRF allowlist), frozen EnrichmentResult/Error models, and configparser-based API key store — all TDD-verified at 98% coverage**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-21T09:43:19Z
- **Completed:** 2026-02-21T09:48:06Z
- **Tasks:** 2 (RED + GREEN/REFACTOR)
- **Files modified:** 9

## Accomplishments

- VTAdapter maps all 7 supported IOC types (IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256) to correct VT API v3 endpoints; CVE returns EnrichmentError("Unsupported type")
- All four HTTP safety controls implemented and independently tested: SEC-04 (timeout), SEC-05 (stream+1MB cap), SEC-06 (no redirects), SEC-07/SEC-16 (SSRF allowlist)
- VT 404 returns EnrichmentResult(verdict="no_data") not an error — correct semantic ("VT has never seen this IOC")
- ConfigStore reads/writes API key to ~/.sentinelx/config.ini (outside repo tree, no accidental commits)
- 32 new tests pass, 195 total suite passes, zero regressions, 98% enrichment coverage

## Task Commits

1. **Task 1: RED — Write failing tests** - `08c1e1f` (test)
2. **Task 2: GREEN + REFACTOR — Implement production code** - `8b01647` (feat)

## Files Created/Modified

- `app/enrichment/__init__.py` - Package init
- `app/enrichment/models.py` - EnrichmentResult and EnrichmentError frozen dataclasses
- `app/enrichment/adapters/__init__.py` - Adapters sub-package init
- `app/enrichment/adapters/virustotal.py` - VTAdapter, ENDPOINT_MAP, all safety controls, response parsing
- `app/enrichment/config_store.py` - ConfigStore: configparser INI wrapper with test isolation support
- `app/config.py` - ALLOWED_API_HOSTS updated to ["www.virustotal.com"]
- `tests/test_enrichment_models.py` - 9 model tests (frozen dataclass properties)
- `tests/test_vt_adapter.py` - 17 VT adapter tests (endpoint mapping, error handling, 4 HTTP safety controls)
- `tests/test_config_store.py` - 6 ConfigStore tests (read/write/persistence/directory creation)

## Decisions Made

- **Fresh Session per lookup():** requests.Session is not documented as thread-safe for concurrent use. Creating a new Session inside each lookup() call avoids race conditions when VTAdapter is used under ThreadPoolExecutor.
- **raise_for_status() after 404 check:** Calling raise_for_status() before reading the body causes JSONDecodeError on 4xx/5xx responses that have no valid body. The fix: check status_code == 404 first (return no_data), then raise_for_status() for other error codes, then read body on success only.
- **ALLOWED_API_HOSTS as constructor argument:** Passing allowed_hosts to VTAdapter.__init__() rather than reading from Flask's current_app context makes the adapter testable without a Flask app context and usable from background threads.
- **configparser to ~/.sentinelx/config.ini:** Satisfies user decision ("no env var requirement"). Outside repo tree so never accidentally committed. Human-readable INI format matches the settings UI use case.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed execution order: raise_for_status() before _read_limited()**

- **Found during:** Task 2 (GREEN implementation)
- **Issue:** The research pattern called `_read_limited()` before `raise_for_status()`. For 4xx/5xx mock responses with no body, `json.loads()` inside `_read_limited()` raises JSONDecodeError, which gets caught by the generic `except Exception` clause — returning the wrong error message ("Expecting value...") instead of the correct HTTP error message.
- **Fix:** Reordered: check status_code == 404 first (special semantic), then `raise_for_status()` for other errors, then `_read_limited()` only on success responses.
- **Files modified:** app/enrichment/adapters/virustotal.py
- **Verification:** test_lookup_429_returns_rate_limit_error and test_lookup_401_returns_auth_error now pass
- **Committed in:** 8b01647 (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in execution order from research pattern)
**Impact on plan:** Essential correctness fix. The wrong error message would have made 429/401 errors unidentifiable in the UI.

## Issues Encountered

- Initial test run showed 29/32 pass; 2 failures on 429 and 401 tests due to JSON parse order bug. Fixed in same task (GREEN phase). Self-correcting.

## User Setup Required

None - no external service configuration required for this plan. The VT API key is stored via ConfigStore by the settings UI (built in a later plan).

## Next Phase Readiness

- VTAdapter ready for EnrichmentOrchestrator (Plan 02) — accepts IOC, returns EnrichmentResult | EnrichmentError
- ConfigStore ready for settings route (Plan 03/04) — get_vt_api_key() / set_vt_api_key()
- ALLOWED_API_HOSTS populated — SEC-16 SSRF protection active for VT calls
- No blockers for Phase 2 Plan 02

---
*Phase: 02-core-enrichment*
*Completed: 2026-02-21*
