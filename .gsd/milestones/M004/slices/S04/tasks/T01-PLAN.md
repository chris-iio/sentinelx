---
estimated_steps: 4
estimated_files: 11
skills_used: []
---

# T01: Create tests/helpers.py and migrate 10 adapter test files

**Slice:** S04 — Test DRY-up — shared adapter fixtures
**Milestone:** M004

## Description

10 adapter test files each define an identical mock-response factory function (`_make_mock_get_response`, `_make_mock_post_response`, or `_make_mock_response`). The function body is byte-for-byte the same across all 10 files — only the name and docstring differ. This task extracts that function into a shared `tests/helpers.py` module and updates all 10 files to import from it. Additionally, IOC factory helpers are added to reduce the ~195 inline `IOC(type=IOCType.XXX, value="...", raw_match="...")` constructions.

**Baseline: 944 tests passing. Final count must be ≥944 with 0 failures.**

## Steps

1. **Create `tests/helpers.py`** with these exports:
   - `make_mock_response(status_code: int, body: dict | None = None) -> MagicMock` — exact same body as the existing `_make_mock_get_response` in any of the 10 files:
     ```python
     def make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
         """Build a mock requests.Response with status code and optional JSON body."""
         mock_resp = MagicMock()
         mock_resp.status_code = status_code
         if body is not None:
             raw_bytes = json.dumps(body).encode()
             mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
         if status_code >= 400:
             http_err = requests.exceptions.HTTPError(response=mock_resp)
             mock_resp.raise_for_status = MagicMock(side_effect=http_err)
         else:
             mock_resp.raise_for_status = MagicMock()
         return mock_resp
     ```
   - IOC factory helpers:
     ```python
     from app.enrichment.models import IOC, IOCType
     
     def make_ioc(ioc_type: IOCType, value: str) -> IOC:
         return IOC(type=ioc_type, value=value, raw_match=value)
     
     def make_ipv4_ioc(value: str = "1.2.3.4") -> IOC:
         return make_ioc(IOCType.IPV4, value)
     
     def make_ipv6_ioc(value: str = "2001:db8::1") -> IOC:
         return make_ioc(IOCType.IPV6, value)
     
     def make_domain_ioc(value: str = "evil.com") -> IOC:
         return make_ioc(IOCType.DOMAIN, value)
     
     def make_sha256_ioc(value: str = "abc123def456") -> IOC:
         return make_ioc(IOCType.SHA256, value)
     
     def make_md5_ioc(value: str = "d41d8cd98f00b204e9800998ecf8427e") -> IOC:
         return make_ioc(IOCType.MD5, value)
     
     def make_url_ioc(value: str = "http://evil.com/path") -> IOC:
         return make_ioc(IOCType.URL, value)
     ```
   - Required imports at top: `import json`, `import requests`, `from unittest.mock import MagicMock`, `from app.enrichment.models import IOC, IOCType`

2. **Update each of the 10 adapter test files.** For each file:
   - Delete the local `_make_mock_get_response` / `_make_mock_post_response` / `_make_mock_response` function definition (typically ~10-13 lines)
   - Add `from tests.helpers import make_mock_response` to imports
   - Find-and-replace all calls: `_make_mock_get_response(` → `make_mock_response(`, `_make_mock_post_response(` → `make_mock_response(`, `_make_mock_response(` → `make_mock_response(`
   - For files with 5+ inline `IOC(type=IOCType.XXX, value="...", raw_match="...")` constructions, also import the relevant IOC factory helpers and replace inline constructions. Match the exact `value` strings used in each test — many tests use specific values that assertions depend on.
   
   The 10 files (with their local function names):
   - `tests/test_abuseipdb.py` — `_make_mock_get_response` (16 call sites)
   - `tests/test_shodan.py` — `_make_mock_get_response` (12 call sites)
   - `tests/test_otx.py` — `_make_mock_get_response` (25 call sites)
   - `tests/test_greynoise.py` — `_make_mock_get_response` (13 call sites)
   - `tests/test_ip_api.py` — `_make_mock_get_response` (32 call sites)
   - `tests/test_hashlookup.py` — `_make_mock_get_response` (19 call sites)
   - `tests/test_threatfox.py` — `_make_mock_response` (11 call sites)
   - `tests/test_vt_adapter.py` — `_make_mock_response` (14 call sites)
   - `tests/test_urlhaus.py` — `_make_mock_post_response` (15 call sites)
   - `tests/test_malwarebazaar.py` — `_make_mock_post_response` (6 call sites)

3. **Do NOT modify** these files (different mock patterns or not requests-based):
   - `tests/test_crtsh.py` — uses `read_limited` patching, not `iter_content`
   - `tests/test_threatminer.py` — uses `read_limited` patching, not `iter_content`
   - `tests/test_asn_cymru.py` — dns.resolver-based
   - `tests/test_dns_lookup.py` — dns.resolver-based
   - `tests/conftest.py` — Flask app fixtures, not adapter test helpers

4. **Run full test suite** to confirm zero regressions.

**Important constraints:**
- Do NOT rename any test classes or test methods
- Do NOT change assertion logic — only change how mock responses and IOCs are constructed
- IOC factory helpers are optional per file — only adopt them where there are 5+ identical inline `IOC(type=...)` constructions and the value string matches the factory default or is passed explicitly
- When replacing IOC constructions, verify that `raw_match=value` is the pattern used (i.e., `raw_match` equals `value`). If any test uses a different `raw_match`, do NOT replace that construction.

## Must-Haves

- [ ] `tests/helpers.py` exists with `make_mock_response()` and IOC factory functions
- [ ] All 10 adapter test files import `from tests.helpers import make_mock_response`
- [ ] No local `_make_mock_*_response` function definitions remain in any of the 10 files
- [ ] All 944+ tests pass with 0 failures
- [ ] No test class or method names changed

## Verification

- `python3 -m pytest tests/ -x -q` — must show ≥944 passed, 0 failed
- `grep -rl "from tests.helpers import" tests/test_*.py | wc -l` — must return 10
- `grep -l "def _make_mock_.*response" tests/test_*.py` — must return empty (0 matches)
- `grep -c "def make_mock_response" tests/helpers.py` — must return 1

## Inputs

- `tests/test_abuseipdb.py` — contains `_make_mock_get_response` to extract
- `tests/test_shodan.py` — contains `_make_mock_get_response` to extract
- `tests/test_otx.py` — contains `_make_mock_get_response` to extract
- `tests/test_greynoise.py` — contains `_make_mock_get_response` to extract
- `tests/test_ip_api.py` — contains `_make_mock_get_response` to extract
- `tests/test_hashlookup.py` — contains `_make_mock_get_response` to extract
- `tests/test_threatfox.py` — contains `_make_mock_response` to extract
- `tests/test_vt_adapter.py` — contains `_make_mock_response` to extract
- `tests/test_urlhaus.py` — contains `_make_mock_post_response` to extract
- `tests/test_malwarebazaar.py` — contains `_make_mock_post_response` to extract

## Expected Output

- `tests/helpers.py` — new shared test helper module with `make_mock_response()` and IOC factories
- `tests/test_abuseipdb.py` — imports from helpers, local factory removed
- `tests/test_shodan.py` — imports from helpers, local factory removed
- `tests/test_otx.py` — imports from helpers, local factory removed
- `tests/test_greynoise.py` — imports from helpers, local factory removed
- `tests/test_ip_api.py` — imports from helpers, local factory removed
- `tests/test_hashlookup.py` — imports from helpers, local factory removed
- `tests/test_threatfox.py` — imports from helpers, local factory removed
- `tests/test_vt_adapter.py` — imports from helpers, local factory removed
- `tests/test_urlhaus.py` — imports from helpers, local factory removed
- `tests/test_malwarebazaar.py` — imports from helpers, local factory removed

## Observability Impact

- **New signal**: `tests/helpers.py` becomes the single-source-of-truth for mock HTTP response construction. Any adapter test failure will trace to either the adapter code or this shared helper.
- **Inspection**: `grep -rn "from tests.helpers import" tests/` reveals which tests adopted shared helpers and which specific factories they use.
- **Failure diagnosis**: When a mock doesn't match adapter expectations, pytest failure output shows the shared factory call site in the test file, making it straightforward to compare the mock shape with what the adapter expects.
