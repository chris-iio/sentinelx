# S04 Research: Test DRY-up — Shared Adapter Fixtures

**Depth:** Light-to-targeted — this is straightforward extraction of known repetitive patterns into a shared helper module. No new technology, no ambiguous scope.

**Active requirements:** R024 (primary owner)

## Summary

All 12 requests-based adapter test files repeat the same mock-response factory function verbatim (10 files with named helpers, 2 inline). A shared `tests/helpers.py` module can extract this function once, along with IOC factory helpers and the `MAX_RESPONSE_BYTES` import. The SSRF/size-limit/timeout error tests follow nearly identical structures per adapter but are NOT good candidates for parameterized extraction — they differ just enough (provider name, HTTP method, IOC type) that extracting them would obscure what's being tested.

## Recommendation

**Create `tests/helpers.py`** with three shared utilities. Each adapter test file imports from it and deletes its local copy. This is a mechanical find-and-replace refactor with zero logic changes.

## Implementation Landscape

### Pattern 1: Mock Response Factory (HIGH VALUE — extract)

**10 files** have an identical `_make_mock_get_response` / `_make_mock_post_response` / `_make_mock_response` function (only docstring and name differ):

| File | Function Name | Call Sites |
|------|--------------|------------|
| test_abuseipdb.py | `_make_mock_get_response` | 16 |
| test_shodan.py | `_make_mock_get_response` | 12 |
| test_otx.py | `_make_mock_get_response` | 25 |
| test_greynoise.py | `_make_mock_get_response` | 13 |
| test_ip_api.py | `_make_mock_get_response` | 32 |
| test_hashlookup.py | `_make_mock_get_response` | 19 |
| test_threatfox.py | `_make_mock_response` | 11 |
| test_vt_adapter.py | `_make_mock_response` | 14 |
| test_urlhaus.py | `_make_mock_post_response` | 15 |
| test_malwarebazaar.py | `_make_mock_post_response` | 6 |

**Total: 163 call sites, 10 identical function bodies.**

The function body is byte-for-byte the same across all 10 files:

```python
def _make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
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

**crtsh and threatminer** use a different mock pattern — they mock `read_limited` and use inline `MagicMock(status_code=200, raise_for_status=MagicMock())`. These two files are NOT candidates for the shared factory. They can remain as-is.

**Extraction approach:** Create `make_mock_response(status_code, body)` in `tests/helpers.py`. In each of the 10 files:
1. Delete the local `_make_mock_*_response` function definition (lines ~8-13 each)
2. Add `from tests.helpers import make_mock_response`
3. Replace all calls: `_make_mock_get_response(` → `make_mock_response(`, etc.

### Pattern 2: IOC Factory Helpers (MEDIUM VALUE — extract)

195+ inline `IOC(type=IOCType.IPV4, value="X", raw_match="X")` calls across all adapter test files. Most adapters construct the same IOC inline in every test method. Two files (threatminer, crtsh) already have local `_make_ioc` / `_make_domain_ioc` helpers.

**Extraction approach:** Add to `tests/helpers.py`:

```python
def make_ioc(ioc_type: IOCType, value: str) -> IOC:
    return IOC(type=ioc_type, value=value, raw_match=value)
```

Plus convenience wrappers used across multiple files:
- `make_ipv4_ioc(value="1.2.3.4")` — used in ~10 files
- `make_ipv6_ioc(value="2001:db8::1")` — used in ~6 files
- `make_domain_ioc(value="evil.com")` — used in ~5 files
- `make_sha256_ioc(value="abc...123")` — used in ~4 files
- `make_md5_ioc(value="d41d8...")` — used in ~3 files
- `make_url_ioc(value="http://evil.com/path")` — used in ~3 files

**Note:** Each file can opt-in to the helpers it needs. Not every file needs to adopt them — only those with 5+ identical inline IOC constructions benefit meaningfully.

### Pattern 3: `adapter._session = MagicMock()` (LOW VALUE — do NOT extract)

268 occurrences across 12 files. However, this is a single line that's self-explanatory in context. Extracting it into a helper (e.g., `mock_adapter_session(adapter)`) would make tests less readable without meaningful LOC savings. **Leave as-is.**

### Pattern 4: Error/Safety Tests (LOW VALUE — do NOT extract)

SSRF, size-limit, timeout, and HTTP-500 tests are structurally similar but differ in:
- Provider name in assertions (`result.provider == "AbuseIPDB"` vs `"Shodan InternetDB"`)
- HTTP method (`.get` vs `.post`)
- IOC type and value used
- Provider-specific adapter construction

Extracting these into parameterized helpers would obscure what's being tested and create a coupling between adapter test files that doesn't exist today. Each adapter's error handling may diverge in the future. **Leave as-is.**

### Files Unchanged

- `tests/test_crtsh.py` — uses `read_limited` patching, not `iter_content` mock. Different pattern.
- `tests/test_threatminer.py` — uses `read_limited` patching, not `iter_content` mock. Different pattern.
- `tests/test_asn_cymru.py`, `tests/test_dns_lookup.py` — dns.resolver-based, not requests-based. Not in scope.
- `tests/conftest.py` — already has Flask app/client fixtures. Not modified.
- `tests/e2e/conftest.py` — E2E fixtures. Not modified.

## Task Decomposition Recommendation

This is a single task, not multiple. The work is:

1. Create `tests/helpers.py` with `make_mock_response()` + IOC factory helpers
2. Update 10 adapter test files to import from `tests/helpers.py` and delete local copies
3. Run full test suite — confirm 944 tests pass

The 10 file updates are independent of each other but trivially mechanical. Splitting into separate tasks per file would add overhead without reducing risk. A single task can handle all 10 files in sequence, running the test suite once at the end.

## Constraints

- **Baseline: 944 tests passing.** Final count must be ≥ 944, 0 failures.
- **`tests/helpers.py` is a new file** — no existing helper module to extend (only `conftest.py` exists at the tests root level, and it's for pytest fixtures, not test utility functions).
- **Import path:** `from tests.helpers import make_mock_response` — this works because pytest adds the project root to `sys.path`. No `__init__.py` needed in tests/.
- **crtsh and threatminer are out of scope** — their mock pattern is fundamentally different (mocking `read_limited` at module level, not `iter_content` on a response object).
- **Do NOT rename test functions or classes** — only change the mock-response factory source and IOC construction patterns. Test method names, class names, and assertion logic stay identical.

## Estimated LOC Impact

- `tests/helpers.py`: ~40 lines new
- 10 adapter test files: each loses ~12 lines (function definition) and gains ~1 line (import). Net: ~-110 lines across all files.
- IOC factory adoption (optional per file) saves an additional ~2-5 lines per file that adopts it.
- **Total net reduction: ~100-140 lines.**

## Verification

```bash
# Full test suite — must pass ≥944 with 0 failures
python3 -m pytest tests/ -x -q

# Confirm shared helpers are imported (10 files)
grep -l "from tests.helpers import" tests/test_*.py | wc -l
# Expected: 10

# Confirm no local _make_mock_*_response definitions remain in those 10 files
grep -l "def _make_mock_.*response" tests/test_*.py
# Expected: 0 matches (or only crtsh/threatminer if they had one, but they don't)

# Confirm helpers.py exists and has the shared function
grep -c "def make_mock_response" tests/helpers.py
# Expected: 1
```
