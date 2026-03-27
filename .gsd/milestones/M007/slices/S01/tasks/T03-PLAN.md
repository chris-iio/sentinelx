---
estimated_steps: 50
estimated_files: 6
skills_used: []
---

# T03: Migrate remaining 6 adapters (abuseipdb, greynoise, virustotal, malwarebazaar, threatfox, urlhaus) and run final verification

Migrate the second batch of 6 adapters — these have more variation: POST methods, per-request headers to remove, VT's custom HTTP error handling, and AbuseIPDB's 429 pre-raise hook. Final slice-level verification at the end.

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

## Inputs

- ``app/enrichment/http_safety.py` — safe_request() function from T01`
- ``app/enrichment/adapters/abuseipdb.py` — adapter to migrate (has redundant per-request headers + 429 hook)`
- ``app/enrichment/adapters/greynoise.py` — adapter to migrate (has redundant per-request headers + 404 hook)`
- ``app/enrichment/adapters/virustotal.py` — adapter to migrate (has _map_http_error + 404 hook)`
- ``app/enrichment/adapters/malwarebazaar.py` — adapter to migrate (POST with data=)`
- ``app/enrichment/adapters/threatfox.py` — adapter to migrate (POST with json_payload=)`
- ``app/enrichment/adapters/urlhaus.py` — adapter to migrate (POST with data=)`

## Expected Output

- ``app/enrichment/adapters/abuseipdb.py` — migrated to safe_request(), per-request headers removed`
- ``app/enrichment/adapters/greynoise.py` — migrated to safe_request(), per-request headers removed`
- ``app/enrichment/adapters/virustotal.py` — migrated to safe_request(), _map_http_error removed`
- ``app/enrichment/adapters/malwarebazaar.py` — migrated to safe_request() with method='POST', data=`
- ``app/enrichment/adapters/threatfox.py` — migrated to safe_request() with method='POST', json_payload=`
- ``app/enrichment/adapters/urlhaus.py` — migrated to safe_request() with method='POST', data=`

## Verification

python3 -m pytest -x -q && for f in app/enrichment/adapters/{abuseipdb,crtsh,greynoise,hashlookup,ip_api,malwarebazaar,otx,shodan,threatfox,threatminer,urlhaus,virustotal}.py; do echo "$f: safe_request=$(grep -c safe_request $f) requests.exceptions=$(grep -c 'requests.exceptions' $f || echo 0) validate_endpoint=$(grep -c validate_endpoint $f || echo 0)"; done
