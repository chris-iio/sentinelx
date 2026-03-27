---
estimated_steps: 39
estimated_files: 6
skills_used: []
---

# T02: Migrate 6 GET adapters to safe_request() (crtsh, threatminer, shodan, hashlookup, ip_api, otx)

Migrate the first batch of 6 GET adapters to use safe_request(). These are the simpler adapters — no per-request headers, no POST, no complex pre-raise hooks beyond 404→no_data.

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

## Inputs

- ``app/enrichment/http_safety.py` — safe_request() function from T01`
- ``app/enrichment/adapters/crtsh.py` — adapter to migrate`
- ``app/enrichment/adapters/threatminer.py` — adapter to migrate`
- ``app/enrichment/adapters/shodan.py` — adapter to migrate`
- ``app/enrichment/adapters/hashlookup.py` — adapter to migrate`
- ``app/enrichment/adapters/ip_api.py` — adapter to migrate`
- ``app/enrichment/adapters/otx.py` — adapter to migrate`

## Expected Output

- ``app/enrichment/adapters/crtsh.py` — migrated to safe_request()`
- ``app/enrichment/adapters/threatminer.py` — migrated to safe_request()`
- ``app/enrichment/adapters/shodan.py` — migrated to safe_request()`
- ``app/enrichment/adapters/hashlookup.py` — migrated to safe_request()`
- ``app/enrichment/adapters/ip_api.py` — migrated to safe_request()`
- ``app/enrichment/adapters/otx.py` — migrated to safe_request()`

## Verification

python3 -m pytest tests/test_crtsh.py tests/test_threatminer.py tests/test_shodan.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v && python3 -m pytest -x -q
