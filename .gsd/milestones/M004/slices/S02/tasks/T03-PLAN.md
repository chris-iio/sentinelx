---
estimated_steps: 4
estimated_files: 3
---

# T03: Migrate ip-api adapter from HTTP ip-api.com to HTTPS ipinfo.io

**Slice:** S02 — IO Performance & Polling Protocol
**Milestone:** M004

## Description

The ip-api.com adapter uses cleartext HTTP (`http://ip-api.com/json/{ip}`), leaking analyst IOC lookups to network observers. Decision D032 selected ipinfo.io free tier (`https://ipinfo.io/{ip}/json`) as the HTTPS replacement. This task rewrites the adapter, updates the SSRF allowlist, and rewrites all 49 test fixtures.

**Depends on T02:** The adapter will already have `self._session` from T02's session work. This task uses `self._session.get()` (not bare `requests.get()`).

**Known scope reduction (D032):** ipinfo.io free tier does NOT provide `proxy`, `hosting`, `mobile` flags or `reverse` DNS. The adapter's `raw_stats` will include these keys with default values (`reverse: ""`, `proxy: False`, `hosting: False`, `mobile: False`, `flags: []`). The frontend already handles empty fields gracefully.

**ipinfo.io response format:**
```json
{
  "ip": "8.8.8.8",
  "hostname": "dns.google",
  "city": "Mountain View",
  "region": "California",
  "country": "US",
  "loc": "37.4056,-122.0775",
  "org": "AS15169 Google LLC",
  "postal": "94043",
  "timezone": "America/Los_Angeles"
}
```

The `org` field contains "AS{number} {name}" — same split logic as ip-api.com's `as` field works.

## Steps

1. **Rewrite `app/enrichment/adapters/ip_api.py`**
   - Change `IP_API_BASE = "http://ip-api.com/json"` to `IPINFO_BASE = "https://ipinfo.io"` (or keep the variable name as `IP_API_BASE` for minimal diff — either works)
   - Remove the `_FIELDS` constant (ipinfo.io doesn't use a fields param)
   - Remove the `_FLAG_FIELDS` tuple (ipinfo.io doesn't provide flags)
   - Update URL construction: `url = f"{IPINFO_BASE}/{ioc.value}/json"` (no query string)
   - In `lookup()`, the HTTP call is already `self._session.get(url, ...)` from T02 — no change needed there
   - Rewrite `_parse_response()` to map ipinfo.io fields:
     - `body.get("country", "")` → `country_code` (ipinfo.io uses `country` not `countryCode`)
     - `body.get("city", "")` → `city` (same field name)
     - `body.get("org", "")` → split on first space for ASN+ISP (same logic as current `as` field split)
     - `body.get("hostname", "")` → `reverse` (ipinfo.io provides `hostname` instead of `reverse`, but only for some IPs — may be absent)
     - `proxy`, `hosting`, `mobile` → hardcode `False` (not available)
     - `flags` → hardcode `[]` (not available)
     - `geo` string → same format: `"CC · City · ASN (ISP)"`
   - Update error handling: ipinfo.io returns HTTP 404 for invalid/private IPs (not 200+status="fail"). Adjust the `_parse_response()` to handle missing fields gracefully. For 404 responses, return `verdict=no_data` with empty `raw_stats` (same semantics as ip-api.com's "fail" status).
   - Update the success detection: ipinfo.io does NOT have a `status` field. If the response has a `country` field, treat it as success. If 404 or missing `country`, treat as no-data private IP.
   - Update docstrings throughout the file (module docstring, class docstring, method docstrings) to reference ipinfo.io instead of ip-api.com
   - Update the `logger.exception` message from "ip-api.com lookup" to "ipinfo.io lookup"
   - **Keep class name as `IPApiAdapter`** — renaming would require changes in `setup.py` and test imports. The class serves the same purpose (IP context); the name is acceptable.

2. **Update `app/config.py` ALLOWED_API_HOSTS**
   - Replace `"ip-api.com"` with `"ipinfo.io"` in the `ALLOWED_API_HOSTS` list
   - Update the comment from "ip-api.com GeoIP (zero-auth)" to "ipinfo.io GeoIP (zero-auth, HTTPS)"

3. **Rewrite `tests/test_ip_api.py` fixtures and assertions**
   - Update module docstring to reference ipinfo.io
   - Rewrite the mock response factory (`_make_mock_response` or equivalent) to return ipinfo.io-format JSON: `{"ip": "...", "city": "...", "country": "US", "org": "AS15169 Google LLC", ...}`
   - Update all URL assertions from `http://ip-api.com` to `https://ipinfo.io`
   - Update ALLOWED_API_HOSTS in test fixtures: `"ipinfo.io"` instead of `"ip-api.com"`
   - Update field assertions:
     - Tests asserting `raw_stats["countryCode"]` → `raw_stats["country_code"]` (field name stays the same in raw_stats, the source field changes)
     - Tests asserting `reverse` with a value → `reverse` may be from `hostname` or `""`
     - Tests asserting `flags` like `["proxy", "hosting"]` → `flags` is always `[]`
     - Tests asserting `proxy: True` → `proxy: False`
     - Tests for "fail" status response → change to 404 HTTP response for private IPs
   - The mock pattern is `adapter._session = MagicMock(); adapter._session.get.return_value = mock_resp` (from T02)
   - Keep the same test count (49 tests) — adapt each test, don't delete
   - Tests for `validate_endpoint` SSRF check should use `ipinfo.io` in allowed_hosts

4. **Run tests** — `python3 -m pytest tests/test_ip_api.py -v` all 49 pass; `python3 -m pytest tests/ --ignore=tests/e2e -x -q` ≥936 pass.

## Must-Haves

- [ ] `IP_API_BASE` (or renamed constant) uses `https://ipinfo.io`, not `http://`
- [ ] URL is `https://ipinfo.io/{ip}/json`
- [ ] `_parse_response()` correctly maps ipinfo.io fields to existing `raw_stats` shape
- [ ] `ALLOWED_API_HOSTS` in config.py has `ipinfo.io`, no `ip-api.com`
- [ ] All 49 tests in test_ip_api.py pass with ipinfo.io fixtures
- [ ] Zero `http://` URLs in ip_api.py
- [ ] Full unit test suite passes (≥936)

## Verification

- `grep 'http://' app/enrichment/adapters/ip_api.py` — 0 hits
- `grep 'ipinfo.io' app/enrichment/adapters/ip_api.py` — ≥1 hit
- `grep 'ipinfo.io' app/config.py` — present
- `! grep 'ip-api.com' app/config.py` — removed (exits 1 = good)
- `python3 -m pytest tests/test_ip_api.py -v` — all 49 pass
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — ≥936 pass

## Inputs

- `app/enrichment/adapters/ip_api.py` — current adapter with `self._session` (from T02), using `http://ip-api.com`
- `app/config.py` — `ALLOWED_API_HOSTS` list containing `"ip-api.com"` (line ~48)
- `tests/test_ip_api.py` — 49 tests mocking `adapter._session.get` (from T02), with ip-api.com fixtures

## Expected Output

- `app/enrichment/adapters/ip_api.py` — rewritten for ipinfo.io HTTPS endpoint, new `_parse_response()` mapping
- `app/config.py` — `ALLOWED_API_HOSTS` updated: `ipinfo.io` replaces `ip-api.com`
- `tests/test_ip_api.py` — all 49 tests rewritten with ipinfo.io response format, HTTPS URLs, updated field assertions
