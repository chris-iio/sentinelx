---
estimated_steps: 4
estimated_files: 24
---

# T02: Add persistent requests.Session to all 12 adapters and update test mocks

**Slice:** S02 — IO Performance & Polling Protocol
**Milestone:** M004

## Description

Each of the 12 requests-based adapters currently creates a new TCP+TLS connection on every `lookup()` call via bare `requests.get()` or `requests.post()`, or by creating an ephemeral `requests.Session()` inside `lookup()` (VirusTotal, ThreatFox). This wastes 50–150ms per call in handshake overhead. This task adds `self._session = requests.Session()` to each adapter's `__init__` and routes all HTTP calls through it. All 12 test files must update their mock targets accordingly. Covers requirement R020.

**Important context from S01:** S01 added `SSLError` and `ConnectionError` exception handlers to all 12 adapters. The exception handler chain is: `Timeout → HTTPError → SSLError → ConnectionError → Exception`. This ordering must be preserved. The session change only affects the HTTP call site — exception handlers are unchanged.

**Thread safety:** `requests.Session.get()`/`.post()` is thread-safe for concurrent read-only use. All adapters set headers once in `__init__` (via `self._session.headers.update(...)` for API key adapters) and never mutate after. The orchestrator calls `adapter.lookup()` from multiple threads, but each call only reads session state.

## Steps

1. **Adapters using `requests.get()` (10 adapters: abuseipdb, crtsh, greynoise, hashlookup, ip_api, otx, shodan, threatminer, plus the `.get()` usage in virustotal and threatfox which currently create ephemeral sessions)**

   For each of these 12 adapters, apply the same pattern:
   - In `__init__`, add `self._session = requests.Session()` after existing initialization
   - For adapters with API keys that currently set headers per-call (abuseipdb, greynoise, otx, malwarebazaar, urlhaus), move the header dict to `self._session.headers.update({...})` in `__init__`
   - For adapters that currently pass headers in the `requests.get(headers=...)` call but have no per-call variation, move to session-level headers
   - Replace `requests.get(url, ...)` with `self._session.get(url, ...)` in `lookup()` (keep all other kwargs: timeout, stream, allow_redirects)
   - Replace `requests.post(url, ...)` with `self._session.post(url, ...)` for malwarebazaar, urlhaus
   - For **virustotal.py**: remove `session = requests.Session()` from inside `lookup()` (line ~208); add `self._session = requests.Session()` to `__init__`; move `session.headers.update({"x-apikey": self._api_key})` to `__init__` as `self._session.headers.update(...)`; replace `session.get(...)` with `self._session.get(...)`
   - For **threatfox.py**: same pattern as VT — remove ephemeral session from `lookup()` (line ~176), move to `__init__`, move `session.headers.update({"Auth-Key": ...})` to `__init__`
   - Update the thread-safety docstring in each file (e.g., "Thread safety: uses a persistent requests.Session created in __init__; concurrent lookup() calls are safe as session state is read-only after initialization.")

2. **Test files using `patch("requests.get", ...)` (10 test files)**

   The pattern change for test files with `with patch("requests.get", return_value=mock_resp):`:
   ```python
   # BEFORE:
   with patch("requests.get", return_value=mock_resp):
       result = adapter.lookup(ioc)

   # AFTER:
   adapter._session = MagicMock()
   adapter._session.get.return_value = mock_resp
   result = adapter.lookup(ioc)
   ```

   For test files using `with patch("requests.get") as mock_get:` (crtsh, threatminer — these inspect call args):
   ```python
   # BEFORE:
   with patch("requests.get") as mock_get:
       mock_get.return_value = mock_resp
       result = adapter.lookup(ioc)
       mock_get.assert_called_once()

   # AFTER:
   adapter._session = MagicMock()
   adapter._session.get.return_value = mock_resp
   result = adapter.lookup(ioc)
   adapter._session.get.assert_called_once()
   ```

   For POST adapters (malwarebazaar, urlhaus): same but `.post` instead of `.get`.

3. **Test files using `patch("requests.Session")` (VT and ThreatFox)**

   These test files currently mock the Session class constructor. After the change, the session is already on the adapter instance:
   ```python
   # BEFORE (test_vt_adapter.py):
   with patch("requests.Session") as mock_session_cls:
       mock_session = MagicMock()
       mock_session_cls.return_value = mock_session
       mock_session.get.return_value = mock_resp
       result = adapter.lookup(ioc)

   # AFTER:
   adapter._session = MagicMock()
   adapter._session.get.return_value = mock_resp
   result = adapter.lookup(ioc)
   ```
   Same pattern for test_threatfox.py but with `.post`.

4. **Run full unit test suite** — `python3 -m pytest tests/ --ignore=tests/e2e -x -q` must pass ≥936 tests.

## Must-Haves

- [ ] All 12 adapters have `self._session = requests.Session()` in `__init__`
- [ ] Zero occurrences of bare `requests.get()` or `requests.post()` in any adapter file
- [ ] Zero occurrences of `session = requests.Session()` inside `lookup()` (VT, ThreatFox)
- [ ] All 12 test files updated to mock `adapter._session` instead of `requests.get`/`requests.post`/`requests.Session`
- [ ] SSLError → ConnectionError handler ordering preserved in all 12 adapters
- [ ] All unit tests pass (≥936)

## Verification

- `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py` — 0 hits (exclude `__pycache__`)
- `grep -rl 'self._session' app/enrichment/adapters/*.py | wc -l` — returns 12
- `grep -rn 'session = requests.Session()' app/enrichment/adapters/*.py` — 0 hits (no ephemeral sessions)
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — ≥936 passed

## Inputs

- `app/enrichment/adapters/abuseipdb.py` — `requests.get()` at line ~127, `__init__` at line ~80
- `app/enrichment/adapters/crtsh.py` — `requests.get()` at line ~109, `__init__` at line ~68
- `app/enrichment/adapters/greynoise.py` — `requests.get()` at line ~120, `__init__` at line ~73
- `app/enrichment/adapters/hashlookup.py` — `requests.get()` at line ~118, `__init__` at line ~74
- `app/enrichment/adapters/ip_api.py` — `requests.get()` at line ~130, `__init__` at line ~86
- `app/enrichment/adapters/malwarebazaar.py` — `requests.post()` at line ~96, `__init__` at line ~57
- `app/enrichment/adapters/otx.py` — `requests.get()` at line ~136, `__init__` at line ~93
- `app/enrichment/adapters/shodan.py` — `requests.get()` at line ~113, `__init__` at line ~68
- `app/enrichment/adapters/threatfox.py` — `session = requests.Session()` at line ~176, `__init__` at line ~137
- `app/enrichment/adapters/threatminer.py` — `requests.get()` at line ~154, `__init__` at line ~97
- `app/enrichment/adapters/urlhaus.py` — `requests.get()` at line ~130, `__init__` at line ~84
- `app/enrichment/adapters/virustotal.py` — `session = requests.Session()` at line ~208, `__init__` at line ~172
- `tests/test_abuseipdb.py` — 33 tests, mocks `requests.get`
- `tests/test_crtsh.py` — 37 tests, mocks `requests.get` (uses `as mock_get` pattern)
- `tests/test_greynoise.py` — 29 tests, mocks `requests.get`
- `tests/test_hashlookup.py` — 34 tests, mocks `requests.get`
- `tests/test_ip_api.py` — 49 tests, mocks `requests.get`
- `tests/test_malwarebazaar.py` — 12 tests, mocks `requests.post`
- `tests/test_otx.py` — 42 tests, mocks `requests.get`
- `tests/test_shodan.py` — 25 tests, mocks `requests.get`
- `tests/test_threatfox.py` — mocks `requests.Session` class
- `tests/test_threatminer.py` — 69 tests, mocks `requests.get` (uses `as mock_get` pattern)
- `tests/test_urlhaus.py` — 33 tests, mocks `requests.post`
- `tests/test_vt_adapter.py` — mocks `requests.Session` class

## Expected Output

- `app/enrichment/adapters/abuseipdb.py` — `self._session` in `__init__`, `self._session.get()` in `lookup()`
- `app/enrichment/adapters/crtsh.py` — same pattern
- `app/enrichment/adapters/greynoise.py` — same pattern
- `app/enrichment/adapters/hashlookup.py` — same pattern
- `app/enrichment/adapters/ip_api.py` — same pattern
- `app/enrichment/adapters/malwarebazaar.py` — `self._session.post()`
- `app/enrichment/adapters/otx.py` — same pattern
- `app/enrichment/adapters/shodan.py` — same pattern
- `app/enrichment/adapters/threatfox.py` — ephemeral session removed, `self._session` in `__init__`
- `app/enrichment/adapters/threatminer.py` — same pattern
- `app/enrichment/adapters/urlhaus.py` — `self._session.post()`
- `app/enrichment/adapters/virustotal.py` — ephemeral session removed, `self._session` in `__init__`
- `tests/test_abuseipdb.py` — mocks `adapter._session` instead of `requests.get`
- `tests/test_crtsh.py` — same
- `tests/test_greynoise.py` — same
- `tests/test_hashlookup.py` — same
- `tests/test_ip_api.py` — same
- `tests/test_malwarebazaar.py` — mocks `adapter._session.post`
- `tests/test_otx.py` — same
- `tests/test_shodan.py` — same
- `tests/test_threatfox.py` — mocks `adapter._session.post` directly (no Session class mock)
- `tests/test_threatminer.py` — same
- `tests/test_urlhaus.py` — mocks `adapter._session.post`
- `tests/test_vt_adapter.py` — mocks `adapter._session.get` directly (no Session class mock)
