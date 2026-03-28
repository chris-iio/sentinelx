---
estimated_steps: 24
estimated_files: 6
skills_used: []
---

# T02: Migrate 6 larger adapter test files and remove local factory duplicates

Migrate 6 larger adapter test files (test_urlhaus, test_abuseipdb, test_crtsh, test_otx, test_ip_api, test_threatminer) to use shared helpers from tests/helpers.py. Remove local _make_*_ioc factory functions from test_threatminer.py (5 functions) and test_crtsh.py (1 function).

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

## Inputs

- ``tests/helpers.py` — shared helpers extended in T01 with mock_adapter_session and all IOC factories`
- ``tests/test_urlhaus.py` — 473 lines, 16 session mocks, 10 inline IOCs, POST adapter`
- ``tests/test_abuseipdb.py` — 502 lines, 18 session mocks, 20 inline IOCs`
- ``tests/test_crtsh.py` — 574 lines, 29 session mocks, 2 inline IOCs, 1 local _make_domain_ioc factory`
- ``tests/test_otx.py` — 623 lines, 26 session mocks, 24 inline IOCs`
- ``tests/test_ip_api.py` — 731 lines, 37 session mocks, 39 inline IOCs`
- ``tests/test_threatminer.py` — 1002 lines, 55 session mocks, 4 inline IOCs (uses local factories), 5 local _make_*_ioc functions to remove`

## Expected Output

- ``tests/test_urlhaus.py` — migrated to shared helpers`
- ``tests/test_abuseipdb.py` — migrated to shared helpers`
- ``tests/test_crtsh.py` — migrated to shared helpers, local factory removed`
- ``tests/test_otx.py` — migrated to shared helpers`
- ``tests/test_ip_api.py` — migrated to shared helpers`
- ``tests/test_threatminer.py` — migrated to shared helpers, 5 local factories removed`

## Verification

python3 -m pytest -x -q && grep -c 'adapter._session = MagicMock()' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py && grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py
