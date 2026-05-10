---
id: T02
parent: S02
milestone: M016
key_files:
  - tests/test_emailrep_online_coverage.py
key_decisions:
  - None.
duration: 
verification_result: passed
completed_at: 2026-05-09T16:42:29.608Z
blocker_discovered: false
---

# T02: Added route-level EmailRep settings and Online email provider-count coverage tests.

**Added route-level EmailRep settings and Online email provider-count coverage tests.**

## What Happened

Created `tests/test_emailrep_online_coverage.py` to pin the EmailRep route contracts at the Flask client/HTML level. The tests cover `/settings` GET metadata/status, `/settings` POST persistence through `ConfigStore.set_provider_key("emailrep", ...)`, raw-key redaction on the redirected settings page, empty-key validation, unknown-provider rejection, and `/analyze` Online provider-count rendering with and without an EmailRep key. The route tests use an explicit single `IOCType.EMAIL` pipeline fixture while keeping background enrichment patched via `app.routes.analysis._setup_orchestrator`, avoiding unrelated domain extraction noise from email domains. No production source changes were needed because the existing settings save path, registry rebuild, and results-page `data-provider-counts` behavior already satisfied the task contract.

## Verification

Focused route tests and the required task command passed. `python3 -m pytest tests/test_emailrep_online_coverage.py -q` passed with 6 tests in the original task run. Fresh slice verification ran `python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_settings.py tests/test_routes.py -q` and passed with 68 tests. LSP diagnostics in the original task run reported no diagnostics for `tests/test_emailrep_online_coverage.py`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_settings.py tests/test_routes.py -q` | 0 | ✅ pass (68 passed in 17.40s) | 17400ms |

## Deviations

None. The planned production files were inspected by the task executor, but no source fixes were required after adding the route-level tests.

## Known Issues

None.

## Files Created/Modified

- `tests/test_emailrep_online_coverage.py`
