---
estimated_steps: 5
estimated_files: 8
skills_used:
  - review
  - test
---

# T04: Convert POST adapters, ThreatMiner, and trim SEC-XX docstrings

**Slice:** S01 — Adapter Simplification
**Milestone:** M002

## Description

Complete the slice by converting the remaining 3 HTTP adapters (MalwareBazaar, URLhaus, ThreatMiner) and removing redundant SEC-XX docstring references from all 12 HTTP adapter files. After this task, every HTTP adapter uses `safe_request()` and the slice is done.

## Steps

1. **Convert `app/enrichment/adapters/malwarebazaar.py`:**
   - Replace inline `requests.post(MB_BASE, data=..., headers=..., timeout=TIMEOUT, allow_redirects=False, stream=True)` + `raise_for_status()` + `read_limited(resp)` with: `body = safe_request("POST", MB_BASE, self._allowed_hosts, data={"query": "get_info", "hash": ioc.value}, headers={"Auth-Key": self._api_key, "Accept": "application/json"})`.
   - Move `_parse_response` from instance method (`self._parse_response`) to module-level function: change `def _parse_response(self, ioc, body)` to `def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult`. Remove `self` parameter. Update the call site in `lookup()` from `self._parse_response(ioc, body)` to `_parse_response(ioc, body)`.
   - Update imports: `from app.enrichment.http_safety import safe_request`.

2. **Convert `app/enrichment/adapters/urlhaus.py`:**
   - Same pattern as MalwareBazaar — POST with form data. Replace inline HTTP block with `safe_request("POST", ...)`.
   - Update imports.

3. **Convert `app/enrichment/adapters/threatminer.py`:**
   - Replace the internal `_call()` method body with `safe_request()`. The `_call()` method currently does: `validate_endpoint()` + `requests.get(base_url, params={"q": ioc.value, "rt": rt}, ...)` + `raise_for_status()` + `read_limited()`.
   - Replace with: `return safe_request("GET", base_url, self._allowed_hosts, params={"q": ioc.value, "rt": rt})`.
   - Keep the try/except wrapper in `_call()` that catches exceptions → `EnrichmentError`.
   - **Critical:** Do NOT use `no_data_on_404=True`. ThreatMiner always returns HTTP 200. The body-level `status_code == "404"` check happens in `_lookup_ip`/`_lookup_domain`/`_lookup_hash` AFTER `_call()` returns. This is ThreatMiner-specific and correct.
   - Update imports: `from app.enrichment.http_safety import safe_request`.

4. **Trim SEC-XX references from all 12 HTTP adapter files:**
   - Remove SEC-04, SEC-05, SEC-06, SEC-07, SEC-16 references from module docstrings, class docstrings, method docstrings, and inline comments in: `shodan.py`, `virustotal.py`, `threatfox.py`, `malwarebazaar.py`, `urlhaus.py`, `threatminer.py`, `crtsh.py`, `hashlookup.py`, `ip_api.py`, `abuseipdb.py`, `greynoise.py`, `otx.py`.
   - Leave references intact in `http_safety.py` (that's where the controls live now).
   - Leave `dns_lookup.py` and `asn_cymru.py` untouched (out of scope — no HTTP).
   - Use targeted edits — don't rewrite entire docstrings. Remove just the SEC-XX lines/bullets.

5. **Run full test suite and final verification:**
   - `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/ -q --tb=short` → 924 passed, 0 failed
   - `grep -c 'SEC-' app/enrichment/adapters/*.py` → 0 for all HTTP adapter files
   - `grep -c 'validate_endpoint\|stream=True\|allow_redirects=False' app/enrichment/adapters/*.py` → 0 for all HTTP adapter files (dns_lookup/asn_cymru may have validate_endpoint — that's fine, they're not HTTP adapters)
   - `grep -c 'requests.Session' app/enrichment/adapters/*.py` → 0 for every file

## Must-Haves

- [ ] MalwareBazaar uses `safe_request()` with `_parse_response` as module-level function
- [ ] URLhaus uses `safe_request()`
- [ ] ThreatMiner's `_call()` uses `safe_request()` — body-level 404 check preserved in lookup methods
- [ ] SEC-XX references removed from all 12 HTTP adapter files
- [ ] 924/924 tests pass

## Verification

- `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/ -q --tb=short` → 924 passed, 0 failed
- `grep -c 'SEC-' app/enrichment/adapters/shodan.py app/enrichment/adapters/virustotal.py app/enrichment/adapters/threatfox.py app/enrichment/adapters/malwarebazaar.py app/enrichment/adapters/urlhaus.py app/enrichment/adapters/threatminer.py app/enrichment/adapters/crtsh.py app/enrichment/adapters/hashlookup.py app/enrichment/adapters/ip_api.py app/enrichment/adapters/abuseipdb.py app/enrichment/adapters/greynoise.py app/enrichment/adapters/otx.py` → 0 for every file
- `grep -c 'validate_endpoint\|stream=True\|allow_redirects=False' app/enrichment/adapters/*.py | grep -v ':0$' | grep -v 'dns_lookup\|asn_cymru'` → empty (no matches)

## Inputs

- `app/enrichment/http_safety.py` — contains `safe_request()` (from T01)
- `app/enrichment/adapters/malwarebazaar.py` — POST adapter with instance-method `_parse_response`
- `app/enrichment/adapters/urlhaus.py` — POST adapter
- `app/enrichment/adapters/threatminer.py` — multi-call GET adapter with internal `_call()` method
- `app/enrichment/adapters/shodan.py` — already converted (T01), needs SEC-XX trim
- `app/enrichment/adapters/crtsh.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/hashlookup.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/ip_api.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/abuseipdb.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/greynoise.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/otx.py` — already converted (T02), needs SEC-XX trim
- `app/enrichment/adapters/virustotal.py` — already converted (T03), needs SEC-XX trim
- `app/enrichment/adapters/threatfox.py` — already converted (T03), needs SEC-XX trim

## Expected Output

- `app/enrichment/adapters/malwarebazaar.py` — refactored to use `safe_request()`, `_parse_response` is module-level
- `app/enrichment/adapters/urlhaus.py` — refactored to use `safe_request()`
- `app/enrichment/adapters/threatminer.py` — `_call()` uses `safe_request()`
- `app/enrichment/adapters/shodan.py` — SEC-XX references removed
- `app/enrichment/adapters/virustotal.py` — SEC-XX references removed
- `app/enrichment/adapters/threatfox.py` — SEC-XX references removed
- `app/enrichment/adapters/crtsh.py` — SEC-XX references removed
- `app/enrichment/adapters/hashlookup.py` — SEC-XX references removed
- `app/enrichment/adapters/ip_api.py` — SEC-XX references removed
- `app/enrichment/adapters/abuseipdb.py` — SEC-XX references removed
- `app/enrichment/adapters/greynoise.py` — SEC-XX references removed
- `app/enrichment/adapters/otx.py` — SEC-XX references removed
