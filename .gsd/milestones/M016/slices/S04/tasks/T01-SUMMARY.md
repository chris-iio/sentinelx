---
id: T01
parent: S04
milestone: M016
key_files:
  - tests/e2e/conftest.py
  - tests/e2e/pages/results_page.py
key_decisions:
  - Kept the existing IP route helper as the canonical fake-job/status-route implementation and made the EmailRep helper delegate to it to preserve route ordering and backwards compatibility.
  - Used a deep copy of the canned EmailRep payload inside the helper so tests can override the submitted email without mutating shared fixture state.
duration: 
verification_result: passed
completed_at: 2026-05-10T06:08:29.853Z
blocker_discovered: false
---

# T01: Added a deterministic EmailRep Online E2E fixture and helper for email IOC browser tests.

**Added a deterministic EmailRep Online E2E fixture and helper for email IOC browser tests.**

## What Happened

Added `EMAILREP_E2E_EMAIL`, `MOCK_ENRICHMENT_RESPONSE_EMAILREP`, and `setup_emailrep_enrichment_route_mock()` to `tests/e2e/conftest.py`. The new fixture returns a complete single-result EmailRep status payload for `analyst@example.com`, includes suspicious verdict metadata, scalar detection fields, and flattened `raw_stats` for all EmailRep context fields used by the row factory. It also includes script-like strings in allowed scalar/list fields plus an unsupported nested object under an unknown raw_stats key so downstream browser tests can assert safe DOM rendering. The helper deep-copies the canned payload, updates `ioc_value` for custom submitted emails, delegates through the existing fake-job arm/status-route helper, and returns the deterministic fake job id for `.page-results[data-job-id]` assertions. Existing `setup_enrichment_route_mock` and `mocked_enrichment` behavior remain unchanged for IP tests. Added narrow `ResultsPage` card-scoped helper locators for provider detail rows and provider context fields to support clearer T02 assertions without broad selector rewrites.

## Verification

Ran the required E2E verification covering the existing mocked IP enrichment summary row and settings key-save flow; both passed. Also ran a lightweight Python fixture-contract check confirming the EmailRep mock imports, matches the default email IOC, has complete status counters, includes all planned flattened EmailRep raw_stats fields, includes the safety sentinels, and does not embed API-key or EmailRep URL strings.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/e2e/test_results_page.py::test_enrichment_summary_row_created_after_polling tests/e2e/test_settings.py::test_save_key_shows_success_flash -q` | 0 | ✅ pass (2 passed) | 2396ms |
| 2 | `python3 - <<'PY'
from tests.e2e.conftest import EMAILREP_E2E_EMAIL, MOCK_ENRICHMENT_RESPONSE_EMAILREP

body = MOCK_ENRICHMENT_RESPONSE_EMAILREP
result = body['results'][0]
assert body['complete'] is True
assert body['total'] == 1
assert body['done'] == 1
assert body['next_since'] == 1
assert result['provider'] == 'EmailRep'
assert result['ioc_value'] == EMAILREP_E2E_EMAIL == 'analyst@example.com'
assert result['ioc_type'] == 'email'
assert result['verdict'] == 'suspicious'
raw = result['raw_stats']
for key in [
    'reputation', 'references', 'risk_flags', 'domain_reputation', 'profiles',
    'first_seen', 'last_seen', 'deliverable', 'valid_mx', 'spoofable',
    'spf_strict', 'dmarc_enforced'
]:
    assert key in raw, key
assert any('<script>' in str(item) for item in raw['risk_flags'])
assert isinstance(raw['unsupported_nested_object'], dict)
serialized = repr(body).lower()
assert 'api_key' not in serialized and 'emailrep.io' not in serialized and 'http://' not in serialized and 'https://' not in serialized
print('emailrep fixture contract ok')
PY` | 0 | ✅ pass (emailrep fixture contract ok) | 273ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/e2e/conftest.py`
- `tests/e2e/pages/results_page.py`
