# Deferred Items — Phase 01 Annotations Removal

These are pre-existing test failures discovered during Phase 01 execution.
They were present before any Phase 01 changes and are out of scope for this plan.

## Pre-existing Test Failures

### 1. E2E page title case mismatch

**File:** `tests/e2e/test_homepage.py::test_page_title[chromium]`
**Issue:** Test expects title "SentinelX" but `app/templates/base.html` has `<title>sentinelx</title>` (lowercase).
**Status:** Pre-existing — confirmed failing on commit `06926ea` before Task 3 changes.
**Owner:** Separate fix needed in base.html or the test.

### 2. Deduplication count assertion

**File:** `tests/test_routes.py::test_analyze_deduplicates`
**Issue:** Test asserts `count < 10` but actual count is 12. Deduplication behavior changed.
**Status:** Pre-existing — confirmed failing on commit `06926ea` before Task 3 changes.
**Owner:** Separate investigation needed in the pipeline extractor or results template.
