---
estimated_steps: 31
estimated_files: 6
skills_used: []
---

# T01: Migrate 5 simple GET adapters to BaseHTTPAdapter

Migrate abuseipdb, greynoise, hashlookup, ip_api, and otx to subclass BaseHTTPAdapter. Each adapter follows the proven Shodan recipe: remove `__init__`, `is_configured`, and `lookup` methods; add `class XAdapter(BaseHTTPAdapter)` inheritance; implement `_build_url(ioc)` and `_parse_response(ioc, body)` as bridges to existing module-level functions; override `_auth_headers()` for adapters with API keys; override `_make_pre_raise_hook(ioc)` for adapters with status code hooks.

## Steps

1. Read `app/enrichment/adapters/shodan.py` as the reference migration pattern.
2. Read `app/enrichment/adapters/base.py` to understand BaseHTTPAdapter's interface.
3. Migrate `app/enrichment/adapters/abuseipdb.py`:
   - Change class to `class AbuseIPDBAdapter(BaseHTTPAdapter)`
   - Add import: `from app.enrichment.adapters.base import BaseHTTPAdapter`
   - Remove `__init__`, `is_configured`, `lookup` methods
   - Add `_build_url(self, ioc)` returning `f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"`
   - Add `_parse_response(self, ioc, body)` bridging to module-level `_parse_response(ioc, body, self.name)`
   - Add `_auth_headers(self)` returning `{"Key": self._api_key, "Accept": "application/json"}`
   - Add `_make_pre_raise_hook(self, ioc)` returning a closure that checks for 429
   - Remove stale `import requests` if no longer used directly
   - Run: `python3 -m pytest tests/test_abuseipdb.py -v`
4. Migrate `app/enrichment/adapters/greynoise.py` — same pattern. Auth: `{"key": self._api_key}`. Hook: 404→no_data. Run tests.
5. Migrate `app/enrichment/adapters/hashlookup.py` — no auth (public API). Hook: 404→no_data. Run tests.
6. Migrate `app/enrichment/adapters/ip_api.py` — no auth (public API). Hook: 404→no_data. Run tests.
7. Migrate `app/enrichment/adapters/otx.py` — Auth: `{"X-OTX-API-KEY": self._api_key, "Accept": "application/json"}`. No hook. Run tests.
8. Run all 5 test files together: `python3 -m pytest tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v`

## Must-Haves

- [ ] All 5 adapters subclass BaseHTTPAdapter
- [ ] No `__init__`, `is_configured`, or inline `lookup` boilerplate remains in any of the 5
- [ ] All 188 tests across 5 files pass unchanged
- [ ] Module-level `_parse_response` functions preserved — adapter bridge methods delegate to them

## Pitfalls

- AbuseIPDB auth header uses capital `Key` (not `key`) — must match exactly in `_auth_headers()`
- GreyNoise auth header uses lowercase `key` (not `Key`)
- OTX `supported_types` is an explicit frozenset excluding EMAIL — preserve the exact set
- ip_api has no API key (`requires_api_key = False`) — no `_auth_headers()` override needed
- hashlookup has no API key — same as ip_api
- Each module-level `_parse_response` has slightly different signatures (some take `provider_name` arg, some don't) — the bridge method must match

## Inputs

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter abstract base class`
- ``app/enrichment/adapters/shodan.py` — reference migration (completed in S01)`
- ``app/enrichment/adapters/abuseipdb.py` — adapter to migrate`
- ``app/enrichment/adapters/greynoise.py` — adapter to migrate`
- ``app/enrichment/adapters/hashlookup.py` — adapter to migrate`
- ``app/enrichment/adapters/ip_api.py` — adapter to migrate`
- ``app/enrichment/adapters/otx.py` — adapter to migrate`

## Expected Output

- ``app/enrichment/adapters/abuseipdb.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/greynoise.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/hashlookup.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/ip_api.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/otx.py` — migrated to BaseHTTPAdapter subclass`

## Verification

python3 -m pytest tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py -v && grep -c 'class.*BaseHTTPAdapter' app/enrichment/adapters/abuseipdb.py app/enrichment/adapters/greynoise.py app/enrichment/adapters/hashlookup.py app/enrichment/adapters/ip_api.py app/enrichment/adapters/otx.py | grep -v ':1' | wc -l | xargs test 0 -eq
