# S03: Test DRY-up

**Goal:** Adapter test files use shared make_mock_response/make_*_ioc factories and mock_adapter_session() helper. Inline MagicMock setup and IOC() construction eliminated from all 12 HTTP adapter test files.
**Demo:** After this: Adapter test files use shared make_mock_response/make_*_ioc factories. Inline MagicMock setup eliminated.

## Tasks
- [x] **T01: Added make_sha1_ioc, make_cve_ioc, make_email_ioc, and mock_adapter_session() to tests/helpers.py; migrated all 6 smaller adapter test files to zero inline IOC construction and zero adapter._session = MagicMock() blocks** — Add make_sha1_ioc, make_cve_ioc, make_email_ioc, and mock_adapter_session() to tests/helpers.py. Then migrate 6 smaller adapter test files (test_malwarebazaar, test_vt_adapter, test_threatfox, test_shodan, test_greynoise, test_hashlookup) to use the shared helpers instead of inline IOC() construction and adapter._session = MagicMock() blocks.

## Steps

1. Add three missing IOC factories to `tests/helpers.py`:
   - `make_sha1_ioc(value="b"*40)` → `make_ioc(IOCType.SHA1, value)`
   - `make_cve_ioc(value="CVE-2021-44228")` → `make_ioc(IOCType.CVE, value)`
   - `make_email_ioc(value="user@evil.com")` → `make_ioc(IOCType.EMAIL, value)`

2. Add `mock_adapter_session()` helper to `tests/helpers.py`:
   ```python
   def mock_adapter_session(adapter, *, method="get", response=None, side_effect=None):
       adapter._session = MagicMock()
       target = getattr(adapter._session, method)
       if side_effect is not None:
           target.side_effect = side_effect
       elif response is not None:
           target.return_value = response
       return adapter
   ```

3. For each of the 6 files (test_malwarebazaar.py, test_vt_adapter.py, test_threatfox.py, test_shodan.py, test_greynoise.py, test_hashlookup.py):
   a. Update the `from tests.helpers import` line to include `mock_adapter_session` and the relevant `make_*_ioc` factories used in that file.
   b. Remove the `from app.pipeline.models import IOC, IOCType` import if no longer needed (IOCType may still be needed for unsupported-type assertions).
   c. Replace every `IOC(type=IOCType.XXX, value=val, raw_match=val)` with the appropriate `make_xxx_ioc(val)` call.
   d. Replace every `adapter._session = MagicMock(); adapter._session.get.return_value = resp` (or `.post` for malwarebazaar/threatfox) block with `mock_adapter_session(adapter, response=resp)` or `mock_adapter_session(adapter, method="post", response=resp)`. For side_effect patterns: `mock_adapter_session(adapter, side_effect=exc)`.
   e. Run `python3 -m pytest tests/test_<file>.py -x -q` after each file to verify.

4. Run full test suite: `python3 -m pytest -x -q`

**POST adapters in this batch:** test_malwarebazaar.py and test_threatfox.py use `adapter._session.post` — use `method="post"` in mock_adapter_session().

**Important edge cases:**
- Some tests check `adapter._session.get.assert_called_once()` or inspect `adapter._session.post.call_args` — these assertions still work after mock_adapter_session() since it creates a MagicMock session with the same structure.
- Some tests use `IOCType.XXX` in assertions about `supported_types` or in unsupported-type test cases — keep `IOCType` import if needed for those.
- Some tests construct IOCs with specific values that differ from the factory defaults — pass the value explicitly: `make_sha256_ioc("a"*64)`.

## Must-Haves

- [ ] tests/helpers.py has make_sha1_ioc, make_cve_ioc, make_email_ioc, mock_adapter_session
- [ ] All 6 files have zero `adapter._session = MagicMock()` occurrences
- [ ] All 6 files have zero (or near-zero) `IOC(type=IOCType` occurrences
- [ ] All tests pass: `python3 -m pytest -x -q`

## Verification

- `python3 -m pytest -x -q` — 1057 tests pass
- `grep -c 'adapter._session = MagicMock()' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py` — all 0
- `grep -c 'IOC(type=IOCType' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py` — all 0 or near-zero
- `grep -c 'def mock_adapter_session' tests/helpers.py` — 1
- `grep -c 'def make_sha1_ioc\|def make_cve_ioc\|def make_email_ioc' tests/helpers.py` — 3
  - Estimate: 45m
  - Files: tests/helpers.py, tests/test_malwarebazaar.py, tests/test_vt_adapter.py, tests/test_threatfox.py, tests/test_shodan.py, tests/test_greynoise.py, tests/test_hashlookup.py
  - Verify: python3 -m pytest -x -q && grep -c 'adapter._session = MagicMock()' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py && grep -c 'def mock_adapter_session' tests/helpers.py
- [ ] **T02: Migrate 6 larger adapter test files and remove local factory duplicates** — Migrate 6 larger adapter test files (test_urlhaus, test_abuseipdb, test_crtsh, test_otx, test_ip_api, test_threatminer) to use shared helpers from tests/helpers.py. Remove local _make_*_ioc factory functions from test_threatminer.py (5 functions) and test_crtsh.py (1 function).

## Steps

1. For each of the 6 files (test_urlhaus.py, test_abuseipdb.py, test_crtsh.py, test_otx.py, test_ip_api.py, test_threatminer.py):
   a. Update the `from tests.helpers import` line to include `mock_adapter_session` and all `make_*_ioc` factories used in that file.
   b. Remove the `from app.pipeline.models import IOC, IOCType` import if no longer needed (keep `IOCType` if used for unsupported-type assertions or supported_types checks).
   c. Replace every `IOC(type=IOCType.XXX, value=val, raw_match=val)` with the appropriate `make_xxx_ioc(val)` call.
   d. Replace every `adapter._session = MagicMock(); adapter._session.get.return_value = resp` (or `.post` for urlhaus) block with `mock_adapter_session(adapter, response=resp)` or `mock_adapter_session(adapter, method="post", response=resp)`. For side_effect patterns: `mock_adapter_session(adapter, side_effect=exc)` or `mock_adapter_session(adapter, method="post", side_effect=exc)`.
   e. Run `python3 -m pytest tests/test_<file>.py -x -q` after each file to verify.

2. **test_threatminer.py specific:** Remove the 5 local factory functions (`_make_ioc`, `_make_ip_ioc`, `_make_domain_ioc`, `_make_sha256_ioc`, `_make_md5_ioc` around lines 96-115). Replace all calls to `_make_ip_ioc()` with `make_ipv4_ioc()`, `_make_domain_ioc()` with `make_domain_ioc()`, etc. Note: the local `_make_ip_ioc` default value is "1.2.3.4" which matches `make_ipv4_ioc`'s default. The local `_make_sha256_ioc` default is a full 64-char hex string — pass it explicitly when called without args.

3. **test_crtsh.py specific:** Remove the local `_make_domain_ioc` function (line ~69). Replace calls to `_make_domain_ioc()` with `make_domain_ioc()`. Note: local default is "example.com" but shared helper default is "evil.com" — tests that call `_make_domain_ioc()` without args need `make_domain_ioc("example.com")` instead, OR verify the tests pass with any domain value (most crtsh tests pass the value explicitly).

4. **test_urlhaus.py specific:** This is a POST adapter — use `method="post"` in mock_adapter_session().

5. Run full test suite: `python3 -m pytest -x -q`

**Large file strategy:** test_ip_api.py (731 lines, 37 session mocks, 39 inline IOCs) and test_threatminer.py (1002 lines, 55 session mocks) are the biggest. Work through them methodically — the pattern is identical to batch 1 but there are more occurrences.

## Must-Haves

- [ ] All 6 files have zero `adapter._session = MagicMock()` occurrences
- [ ] All 6 files have zero (or near-zero) `IOC(type=IOCType` occurrences
- [ ] test_threatminer.py has zero local `_make_*_ioc` factory functions
- [ ] test_crtsh.py has zero local `_make_domain_ioc` factory functions
- [ ] All tests pass: `python3 -m pytest -x -q`

## Verification

- `python3 -m pytest -x -q` — 1057 tests pass
- `grep -c 'adapter._session = MagicMock()' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py` — all 0
- `grep -c 'IOC(type=IOCType' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py` — all 0 or near-zero
- `grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py` — both 0
  - Estimate: 60m
  - Files: tests/test_urlhaus.py, tests/test_abuseipdb.py, tests/test_crtsh.py, tests/test_otx.py, tests/test_ip_api.py, tests/test_threatminer.py
  - Verify: python3 -m pytest -x -q && grep -c 'adapter._session = MagicMock()' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py && grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py
