---
id: T01
parent: S04
milestone: M004
provides:
  - tests/helpers.py shared mock-response factory and IOC factory helpers
  - 10 adapter test files migrated to import from tests.helpers
key_files:
  - tests/helpers.py
  - tests/test_abuseipdb.py
  - tests/test_shodan.py
  - tests/test_otx.py
  - tests/test_greynoise.py
  - tests/test_ip_api.py
  - tests/test_hashlookup.py
  - tests/test_threatfox.py
  - tests/test_vt_adapter.py
  - tests/test_urlhaus.py
  - tests/test_malwarebazaar.py
key_decisions:
  - IOC factory helpers provided but not adopted yet — most test files use local variables for hash values, making inline replacement risky without value verification per call site
patterns_established:
  - Shared test helpers live in tests/helpers.py; adapter tests import make_mock_response from tests.helpers
observability_surfaces:
  - grep -rn "from tests.helpers import" tests/ shows adoption count and which factories each file uses
duration: 15m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T01: Create tests/helpers.py and migrate 10 adapter test files

**Extracted shared `make_mock_response()` into `tests/helpers.py` and migrated all 10 adapter test files to import from it, removing 10 duplicate factory definitions across ~130 lines.**

## What Happened

Created `tests/helpers.py` with `make_mock_response(status_code, body)` — the single shared factory for building mock `requests.Response` objects with status code, optional JSON body via `iter_content`, and proper `raise_for_status` behavior for error codes. Also added IOC factory helpers (`make_ioc`, `make_ipv4_ioc`, `make_ipv6_ioc`, `make_domain_ioc`, `make_sha256_ioc`, `make_md5_ioc`, `make_url_ioc`) for downstream adoption.

Migrated all 10 adapter test files:
- Removed local `_make_mock_get_response` / `_make_mock_post_response` / `_make_mock_response` definitions (each ~13 lines)
- Added `from tests.helpers import make_mock_response` import
- Replaced all 153 call sites with `make_mock_response(`

IOC factory helpers were intentionally **not** adopted in this task — most test files use local variables (`md5`, `sha1`, `sha256`, `ipv6`) assigned earlier in each test method, so the factory defaults don't apply and per-site verification would be needed. The factories are available in helpers.py for future adoption where appropriate.

## Verification

- `python3 -m pytest tests/ -x -q` → 944 passed, 0 failed (matches baseline exactly)
- `grep -rl "from tests.helpers import" tests/test_*.py | wc -l` → 10
- `grep -l "def _make_mock_.*response" tests/test_*.py` → no matches (empty)
- `grep -c "def make_mock_response" tests/helpers.py` → 1
- `python3 -c "from tests.helpers import make_mock_response; ..."` → helpers module importable and functional

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/ -x -q` | 0 | ✅ pass | 46.65s |
| 2 | `test $(grep -rl "from tests.helpers import" tests/test_*.py \| wc -l) -eq 10` | 0 | ✅ pass | <1s |
| 3 | `! grep -l "def _make_mock_.*response" tests/test_*.py` | 0 | ✅ pass | <1s |
| 4 | `grep -q "def make_mock_response" tests/helpers.py` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "from tests.helpers import make_mock_response; ..."` | 0 | ✅ pass | <1s |
| 6 | `grep -q '"incremental": true' tsconfig.json` | 1 | ⏳ pending T02 | <1s |
| 7 | `grep -q "ioc-type-badge--email" tailwind.config.js` | 1 | ⏳ pending T02 | <1s |
| 8 | `grep -q "style-src" app/__init__.py` | 1 | ⏳ pending T03 | <1s |
| 9 | `grep -q "object-src 'none'" app/__init__.py` | 1 | ⏳ pending T03 | <1s |

## Diagnostics

- **Adoption tracking**: `grep -rn "from tests.helpers import" tests/` shows which test files import which helpers.
- **Failure tracing**: When an adapter test fails on mock response shape, the shared `make_mock_response` in `tests/helpers.py` is the single place to inspect/debug.
- **IOC factory readiness**: `grep -c "make_ipv4_ioc\|make_domain_ioc\|make_sha256_ioc" tests/helpers.py` confirms factories are available for future adoption.

## Deviations

- **Import path fix**: Planner specified `from app.enrichment.models import IOC, IOCType` in helpers.py, but the actual location is `app.pipeline.models`. Fixed to match the real codebase. This caused the first test run to fail with ImportError, resolved immediately.
- **IOC factory adoption deferred**: The plan suggested adopting IOC factories "where files have 5+ identical inline constructions," but nearly all test files use local variables for hash/IP values rather than string literals matching factory defaults. Adopting factories would require per-call-site verification of exact values, which is risky with no benefit for this task. The factories are available in helpers.py for optional future use.
- **Call site counts differ slightly**: The plan estimated 163 total call sites; the actual migration script replaced 153 calls. The discrepancy is due to the plan counting references vs. actual function-call invocations.

## Known Issues

None.

## Files Created/Modified

- `tests/helpers.py` — new shared test helper module with `make_mock_response()` and 7 IOC factory functions
- `tests/test_abuseipdb.py` — removed local `_make_mock_get_response`, imports from helpers (15 call sites)
- `tests/test_shodan.py` — removed local `_make_mock_get_response`, imports from helpers (11 call sites)
- `tests/test_otx.py` — removed local `_make_mock_get_response`, imports from helpers (24 call sites)
- `tests/test_greynoise.py` — removed local `_make_mock_get_response`, imports from helpers (12 call sites)
- `tests/test_ip_api.py` — removed local `_make_mock_get_response`, imports from helpers (31 call sites)
- `tests/test_hashlookup.py` — removed local `_make_mock_get_response`, imports from helpers (18 call sites)
- `tests/test_threatfox.py` — removed local `_make_mock_response`, imports from helpers (10 call sites)
- `tests/test_vt_adapter.py` — removed local `_make_mock_response`, imports from helpers (13 call sites)
- `tests/test_urlhaus.py` — removed local `_make_mock_post_response`, imports from helpers (14 call sites)
- `tests/test_malwarebazaar.py` — removed local `_make_mock_post_response`, imports from helpers (5 call sites)
- `.gsd/milestones/M004/slices/S04/S04-PLAN.md` — added Observability / Diagnostics section and diagnostic verification step
- `.gsd/milestones/M004/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
