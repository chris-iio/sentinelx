---
estimated_steps: 40
estimated_files: 7
skills_used: []
---

# T01: Extend tests/helpers.py and migrate 6 smaller adapter test files

Add make_sha1_ioc, make_cve_ioc, make_email_ioc, and mock_adapter_session() to tests/helpers.py. Then migrate 6 smaller adapter test files (test_malwarebazaar, test_vt_adapter, test_threatfox, test_shodan, test_greynoise, test_hashlookup) to use the shared helpers instead of inline IOC() construction and adapter._session = MagicMock() blocks.

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

## Inputs

- ``tests/helpers.py` — existing shared test helpers to extend`
- ``tests/test_malwarebazaar.py` — 225 lines, 8 session mocks, 9 inline IOCs, POST adapter`
- ``tests/test_vt_adapter.py` — 344 lines, 16 session mocks, 17 inline IOCs`
- ``tests/test_threatfox.py` — 361 lines, 13 session mocks, 14 inline IOCs, POST adapter`
- ``tests/test_shodan.py` — 387 lines, 14 session mocks, 16 inline IOCs`
- ``tests/test_greynoise.py` — 434 lines, 15 session mocks, 17 inline IOCs`
- ``tests/test_hashlookup.py` — 483 lines, 21 session mocks, 23 inline IOCs`

## Expected Output

- ``tests/helpers.py` — extended with make_sha1_ioc, make_cve_ioc, make_email_ioc, mock_adapter_session`
- ``tests/test_malwarebazaar.py` — migrated to shared helpers`
- ``tests/test_vt_adapter.py` — migrated to shared helpers`
- ``tests/test_threatfox.py` — migrated to shared helpers`
- ``tests/test_shodan.py` — migrated to shared helpers`
- ``tests/test_greynoise.py` — migrated to shared helpers`
- ``tests/test_hashlookup.py` — migrated to shared helpers`

## Verification

python3 -m pytest -x -q && grep -c 'adapter._session = MagicMock()' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py && grep -c 'def mock_adapter_session' tests/helpers.py
