# Deferred Items — Phase 03

## Pre-existing Issues (Out of Scope)

### E2E test_page_title fails: case mismatch

- **Discovered during:** 03-02 Task 1 (full test suite run)
- **Test:** `tests/e2e/test_homepage.py::test_page_title[chromium]`
- **Issue:** Test expects title "SentinelX" (mixed case) but app renders "sentinelx" (lowercase). Verified pre-existing — fails on main before 03-02 changes.
- **Impact:** E2E test suite fails at first test; unit/integration tests all pass (725/725)
- **Action needed:** Fix HTML `<title>` element casing in the base template, then update or confirm the test expectation
- **Deferred because:** Pre-existing, unrelated to Phase 03 ThreatMiner work
