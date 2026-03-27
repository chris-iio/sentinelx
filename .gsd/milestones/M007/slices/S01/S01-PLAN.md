# S01: safe_request() consolidation

**Goal:** Every HTTP adapter's lookup() is: build URL/params → call safe_request() → parse body. http_safety.py has the single canonical HTTP+exception path. All 1043+ tests pass unchanged.
**Demo:** After this: Every HTTP adapter's lookup() is: build URL/params → call safe_request() → parse body. http_safety.py has the single canonical HTTP+exception path. All tests pass.

## Tasks
- [x] **T01: Added safe_request() to http_safety.py with full exception chain, SSRF validation, pre_raise_hook support, and 14 unit tests** — Build the shared safe_request() function that all 12 HTTP adapters will delegate to, plus comprehensive unit tests. This is the foundation — T02 and T03 depend on it.

## Steps

1. Read `app/enrichment/http_safety.py` to understand existing primitives (validate_endpoint, read_limited, TIMEOUT, MAX_RESPONSE_BYTES).
2. Add `safe_request()` to `http_safety.py` with the exact signature from D040:
   - `session`, `url`, `allowed_hosts`, `ioc`, `provider` positional args
   - `method='GET'`, `data=None`, `json_payload=None`, `pre_raise_hook=None` keyword args
   - Returns `dict | EnrichmentError`
3. Implementation flow inside safe_request():
   a. Call `validate_endpoint(url, allowed_hosts)` — raises ValueError on SSRF
   b. HTTP dispatch via `getattr(session, method.lower())(url, timeout=TIMEOUT, allow_redirects=False, stream=True, data=data, json=json_payload)` — MUST use getattr dispatch, NOT session.request() (KNOWLEDGE.md constraint: existing test mocks depend on session.get/session.post)
   c. If `pre_raise_hook` provided, call it with response; if non-None return, return that value
   d. `resp.raise_for_status()`
   e. `body = read_limited(resp)` — byte-capped JSON read
   f. Return body
4. Exception chain (ordering is a correctness constraint per KNOWLEDGE.md):
   - `requests.exceptions.Timeout` → EnrichmentError(error='Request timed out')
   - `requests.exceptions.HTTPError` → EnrichmentError(error=f'HTTP {resp.status_code}')
   - `requests.exceptions.SSLError` → EnrichmentError(error='SSL/TLS error')  ← MUST be before ConnectionError
   - `requests.exceptions.ConnectionError` → EnrichmentError(error='Connection failed')
   - `ValueError` (from validate_endpoint SSRF rejection) → EnrichmentError(error='Endpoint validation failed')
   - `Exception` → EnrichmentError(error=str(e))
5. Create `tests/test_http_safety.py` with tests:
   - test_safe_request_get_success — mock session.get returns valid JSON via iter_content
   - test_safe_request_post_json — method='POST', json_payload={...}, verify session.post called
   - test_safe_request_post_data — method='POST', data={...}, verify session.post called with data=
   - test_safe_request_ssrf_rejection — url with disallowed host → EnrichmentError
   - test_safe_request_timeout → EnrichmentError with 'timed out'
   - test_safe_request_http_error → EnrichmentError with 'HTTP 500'
   - test_safe_request_ssl_error → EnrichmentError with 'SSL/TLS'
   - test_safe_request_connection_error → EnrichmentError with 'Connection failed'
   - test_safe_request_pre_raise_hook_returns_result — hook returns EnrichmentResult → short-circuit
   - test_safe_request_pre_raise_hook_returns_none — hook returns None → continues to raise_for_status
   - test_safe_request_stream_true — verify stream=True and allow_redirects=False passed
6. Run tests: `python3 -m pytest tests/test_http_safety.py -v` — all pass.
7. Run full suite: `python3 -m pytest -x -q` — 1043+ pass, 0 fail.

## Must-Haves

- [ ] safe_request() exists with correct signature matching D040
- [ ] Exception chain ordering: SSLError before ConnectionError
- [ ] Uses getattr dispatch (session.get/session.post), NOT session.request()
- [ ] All safe_request tests pass
- [ ] Full test suite still passes (1043+ tests)

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| validate_endpoint() | ValueError caught → EnrichmentError | N/A (sync check) | N/A |
| read_limited() | JSONDecodeError → caught by Exception handler | Bounded by TIMEOUT | Returns error via Exception handler |
| session.get/post | Each exception type has dedicated handler | Timeout handler | HTTPError handler |

## Negative Tests

- SSRF: url pointing to disallowed host → EnrichmentError, not a network call
- Each exception type: Timeout, HTTPError (various codes), SSLError, ConnectionError
- pre_raise_hook returning non-None → short-circuit before raise_for_status

## Verification

- `python3 -m pytest tests/test_http_safety.py -v` — all tests pass
- `python3 -m pytest -x -q` — 1043+ pass, 0 fail
- `grep -c 'def safe_request' app/enrichment/http_safety.py` returns 1
  - Estimate: 45m
  - Files: app/enrichment/http_safety.py, tests/test_http_safety.py
  - Verify: python3 -m pytest tests/test_http_safety.py -v && python3 -m pytest -x -q
- [ ] **T02: Migrate 6 GET adapters to safe_request() (crtsh, threatminer, shodan, hashlookup, ip_api, otx)** — Migrate the first batch of 6 GET adapters to use safe_request(). These are the simpler adapters — no per-request headers, no POST, no complex pre-raise hooks beyond 404→no_data.

## Steps

1. Read T01 summary to confirm safe_request() API and import path.
2. For each adapter, the migration is mechanical:
   a. Add import: `from app.enrichment.http_safety import safe_request`
   b. Remove imports: `from app.enrichment.http_safety import validate_endpoint, read_limited, TIMEOUT` and `import requests.exceptions` (or `from requests.exceptions import ...`)
   c. Replace the entire try/except block in lookup() with a single safe_request() call
   d. After safe_request() returns, check `isinstance(result, EnrichmentError)` → return it; otherwise parse the dict body as before

3. **crtsh** (`app/enrichment/adapters/crtsh.py`):
   - No auth, no pre-raise hook
   - `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name)`

4. **threatminer** (`app/enrichment/adapters/threatminer.py`):
   - No auth, no pre-raise hook. Note: makes 2 sequential GET calls (report + metadata). Each one becomes a safe_request() call.
   - Both calls: `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name)`

5. **shodan** (`app/enrichment/adapters/shodan.py`):
   - No auth headers (API key in URL params), has 404→no_data pre-raise hook
   - `pre_raise_hook=lambda resp: EnrichmentResult(..., verdict='no_data', ...) if resp.status_code == 404 else None`

6. **hashlookup** (`app/enrichment/adapters/hashlookup.py`):
   - No auth, has 404→no_data pre-raise hook
   - Same pattern as shodan

7. **ip_api** (`app/enrichment/adapters/ip_api.py`):
   - No auth, has 404→no_data pre-raise hook
   - Same pattern as shodan

8. **otx** (`app/enrichment/adapters/otx.py`):
   - Auth via session headers (X-OTX-API-KEY), has 404→no_data pre-raise hook
   - Same pattern as shodan — session headers handle auth, no per-request headers needed

9. After each adapter migration, run its specific test file to catch regressions immediately.
10. Run full test suite after all 6 are done.

## Must-Haves

- [ ] All 6 adapters call safe_request() instead of inlining HTTP boilerplate
- [ ] Zero of these 6 adapters import requests.exceptions
- [ ] Zero of these 6 adapters call validate_endpoint or read_limited directly
- [ ] All existing tests for these 6 adapters pass unchanged
- [ ] Full test suite passes

## Verification

- `python3 -m pytest tests/test_crtsh.py tests/test_threatminer.py tests/test_shodan.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v` — all pass
- `python3 -m pytest -x -q` — 1043+ pass, 0 fail
- `grep -c 'safe_request' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx}.py` — each returns >= 1
- `grep -c 'requests.exceptions' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx}.py` — each returns 0
  - Estimate: 45m
  - Files: app/enrichment/adapters/crtsh.py, app/enrichment/adapters/threatminer.py, app/enrichment/adapters/shodan.py, app/enrichment/adapters/hashlookup.py, app/enrichment/adapters/ip_api.py, app/enrichment/adapters/otx.py
  - Verify: python3 -m pytest tests/test_crtsh.py tests/test_threatminer.py tests/test_shodan.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v && python3 -m pytest -x -q
- [ ] **T03: Migrate remaining 6 adapters (abuseipdb, greynoise, virustotal, malwarebazaar, threatfox, urlhaus) and run final verification** — Migrate the second batch of 6 adapters — these have more variation: POST methods, per-request headers to remove, VT's custom HTTP error handling, and AbuseIPDB's 429 pre-raise hook. Final slice-level verification at the end.

## Steps

1. Read T02 summary to confirm the migration pattern worked for the first 6.

2. **abuseipdb** (`app/enrichment/adapters/abuseipdb.py`):
   - Has redundant per-request `headers=` that duplicates session headers → remove the per-request headers dict entirely
   - Has 429 pre-raise hook: `if resp.status_code == 429: return EnrichmentError(ioc=ioc, provider=self.name, error='Rate limit exceeded (429)')`
   - `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name, pre_raise_hook=lambda resp: EnrichmentError(...) if resp.status_code == 429 else None)`

3. **greynoise** (`app/enrichment/adapters/greynoise.py`):
   - Has redundant per-request `headers=` that duplicates session headers → remove
   - Has 404→no_data pre-raise hook
   - Same safe_request() pattern as shodan/otx from T02

4. **virustotal** (`app/enrichment/adapters/virustotal.py`):
   - Has 404→no_data pre-raise hook
   - Has `_map_http_error()` for 429/401/403 custom messages. Use pre_raise_hook to handle 404 AND 429/401/403:
     ```python
     def _vt_hook(resp):
         if resp.status_code == 404:
             return EnrichmentResult(ioc=ioc, provider=self.name, verdict='no_data', raw_stats={})
         if resp.status_code == 429:
             return EnrichmentError(ioc=ioc, provider=self.name, error='Rate limit exceeded')
         if resp.status_code in (401, 403):
             return EnrichmentError(ioc=ioc, provider=self.name, error='Authentication error')
         return None
     ```
   - After migration, `_map_http_error()` can be removed if all its cases are handled by the hook

5. **malwarebazaar** (`app/enrichment/adapters/malwarebazaar.py`):
   - POST with `data=` (form-encoded)
   - `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name, method='POST', data=payload)`

6. **threatfox** (`app/enrichment/adapters/threatfox.py`):
   - POST with `json_payload=` (JSON body)
   - `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name, method='POST', json_payload=payload)`

7. **urlhaus** (`app/enrichment/adapters/urlhaus.py`):
   - POST with `data=` (form-encoded)
   - Same pattern as malwarebazaar

8. After each adapter, run its test file to catch regressions.
9. Run full test suite.
10. Run slice-level verification checks:
    - `grep -c 'safe_request' app/enrichment/adapters/*.py` — all 12 HTTP adapters show >= 1
    - `grep -c 'requests.exceptions' app/enrichment/adapters/*.py` — all return 0 (use `|| true` for grep exit codes)
    - `grep -c 'validate_endpoint\|read_limited' app/enrichment/adapters/*.py` — all return 0
    - `grep -c 'headers={' app/enrichment/adapters/{abuseipdb,greynoise}.py` — both return 0

## Must-Haves

- [ ] All 6 adapters call safe_request() instead of inlining HTTP boilerplate
- [ ] AbuseIPDB and GreyNoise no longer pass per-request headers (redundant copies removed)
- [ ] Zero of all 12 HTTP adapters import requests.exceptions
- [ ] Zero of all 12 HTTP adapters call validate_endpoint or read_limited directly
- [ ] Full test suite passes: 1043+ tests, 0 failures

## Verification

- `python3 -m pytest -x -q` — 1043+ pass, 0 fail
- Slice-level grep checks (see step 10 above) all pass
  - Estimate: 1h
  - Files: app/enrichment/adapters/abuseipdb.py, app/enrichment/adapters/greynoise.py, app/enrichment/adapters/virustotal.py, app/enrichment/adapters/malwarebazaar.py, app/enrichment/adapters/threatfox.py, app/enrichment/adapters/urlhaus.py
  - Verify: python3 -m pytest -x -q && for f in app/enrichment/adapters/{abuseipdb,crtsh,greynoise,hashlookup,ip_api,malwarebazaar,otx,shodan,threatfox,threatminer,urlhaus,virustotal}.py; do echo "$f: safe_request=$(grep -c safe_request $f) requests.exceptions=$(grep -c 'requests.exceptions' $f || echo 0) validate_endpoint=$(grep -c validate_endpoint $f || echo 0)"; done
