# Deferred Items — Phase 01

## Pre-existing E2E Failures (Out of scope for Plan 01-01)

**Found during:** Task 3 full test suite run

**Tests:**
- `tests/e2e/test_homepage.py::test_page_title[chromium]`
- `tests/e2e/test_settings.py::test_settings_page_title_tag[chromium]`

**Issue:** Both tests expect `page.title == "SentinelX"` but the actual `<title>` tag
renders as `"sentinelx"` (lowercase). This is a case mismatch in the HTML template.

**Confirmed pre-existing:** Verified by stash check — failures existed before Plan 01-01 changes.

**Fix:** Update the `<title>` tag in the HTML template from `"sentinelx"` to `"SentinelX"`.
This is a trivial one-line template fix, not related to enrichment adapter work.
