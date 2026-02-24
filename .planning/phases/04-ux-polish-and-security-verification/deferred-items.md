# Deferred Items

## Pre-existing Issues (Out of Scope)

### E2E test failure: test_online_mode_indicator[chromium]

- **Found during:** Plan 04-02, Task 1 (verifying full test suite)
- **Status:** Pre-existing — confirmed by running before changes were staged
- **Test:** `tests/e2e/test_extraction.py::test_online_mode_indicator[chromium]`
- **Error:** `AssertionError: Locator expected to contain text 'Online Mode'` — `.mode-indicator` element not found
- **Impact:** E2E test only; all 224 unit/integration tests pass
- **Action needed:** Fix `.mode-indicator` element rendering in results page before release
