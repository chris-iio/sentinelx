# S03: Test DRY-up — UAT

**Milestone:** M007
**Written:** 2026-03-28T03:03:46.968Z

## UAT: S03 Test DRY-up

### Preconditions
- Working directory: `/home/chris/projects/sentinelx`
- Python 3.10+ with pytest installed
- All project dependencies installed

### Test 1: Shared helpers exist in tests/helpers.py

**Steps:**
1. Run `grep -c 'def mock_adapter_session' tests/helpers.py`
2. Run `grep -c 'def make_sha1_ioc\|def make_cve_ioc\|def make_email_ioc' tests/helpers.py`

**Expected:**
- Step 1: Output `1`
- Step 2: Output `3`

### Test 2: Zero inline MagicMock session setup in T01 batch (6 smaller files)

**Steps:**
1. Run `grep -c 'adapter._session = MagicMock()' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py`

**Expected:** All 6 files report `0`.

### Test 3: Zero inline MagicMock session setup in T02 batch (6 larger files)

**Steps:**
1. Run `grep -c 'adapter._session = MagicMock()' tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py`

**Expected:** All 6 files report `0`.

### Test 4: Zero inline IOC construction across all 12 files

**Steps:**
1. Run `grep -c 'IOC(type=IOCType' tests/test_malwarebazaar.py tests/test_vt_adapter.py tests/test_threatfox.py tests/test_shodan.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_urlhaus.py tests/test_abuseipdb.py tests/test_crtsh.py tests/test_otx.py tests/test_ip_api.py tests/test_threatminer.py`

**Expected:** All 12 files report `0`.

### Test 5: No local _make_*_ioc factory functions remain

**Steps:**
1. Run `grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py`

**Expected:** Both files report `0`.

### Test 6: Full test suite passes

**Steps:**
1. Run `python3 -m pytest -x -q`

**Expected:** 1057 tests pass, 0 failures.

### Test 7: mock_adapter_session() handles POST adapters

**Steps:**
1. Run `grep -n 'mock_adapter_session.*method.*post' tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py`

**Expected:** Multiple occurrences in each POST-adapter test file confirming `method="post"` is used.

### Test 8: mock_adapter_session() handles side_effect patterns

**Steps:**
1. Run `grep -n 'mock_adapter_session.*side_effect' tests/test_abuseipdb.py tests/test_shodan.py tests/test_greynoise.py`

**Expected:** Occurrences showing `side_effect=` parameter used for exception simulation tests.

### Edge Cases

- **grep -c exit code 1 on all-zero counts:** The grep -c command exits with code 1 when every file has 0 matches. This is correct grep behavior (documented in KNOWLEDGE.md) — it confirms the migration succeeded. The counts (all 0) are the meaningful output, not the exit code.
