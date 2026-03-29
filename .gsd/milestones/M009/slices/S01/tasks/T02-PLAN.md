---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T02: Migrate ShodanAdapter to subclass BaseHTTPAdapter

Rewrite `app/enrichment/adapters/shodan.py` so that `ShodanAdapter` extends `BaseHTTPAdapter`. The migrated adapter defines only:

- Class attributes: `supported_types`, `name`, `requires_api_key` (unchanged)
- `_build_url(self, ioc)` — returns `f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"`
- `_make_pre_raise_hook(self, ioc)` — returns the existing 404→no_data closure
- `_parse_response(self, ioc, body)` — delegates to the existing module-level `_parse_response()` function

The following stay unchanged in the module:
- `SHODAN_INTERNETDB_BASE` constant
- `_MALICIOUS_TAGS` constant  
- `_parse_response()` module-level function (verdict logic)
- Module docstring (update to note subclassing)

The `__init__`, `is_configured`, and `lookup` methods are REMOVED — inherited from BaseHTTPAdapter.

Constructor signature stays `ShodanAdapter(allowed_hosts=[...])` — the base class accepts `allowed_hosts` as first positional arg and `api_key` defaults to `""`.

Verification: all 25 tests in `tests/test_shodan.py` pass with ZERO modifications. The `setup.py` constructor call works unchanged. `isinstance(ShodanAdapter(allowed_hosts=[]), Provider)` still passes.

## Inputs

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter to subclass (created in T01)`
- ``app/enrichment/adapters/shodan.py` — current ShodanAdapter to migrate`
- ``tests/test_shodan.py` — existing tests that must pass unchanged`
- ``app/enrichment/setup.py` — registration call that must work unchanged`

## Expected Output

- ``app/enrichment/adapters/shodan.py` — ShodanAdapter now subclasses BaseHTTPAdapter`

## Verification

python3 -m pytest tests/test_shodan.py -v && python3 -c "from app.enrichment.adapters.shodan import ShodanAdapter; from app.enrichment.provider import Provider; a = ShodanAdapter(allowed_hosts=['internetdb.shodan.io']); assert isinstance(a, Provider); assert a.is_configured(); print('OK')" && python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(['internetdb.shodan.io','api.abuseipdb.com','api.greynoise.io','hashlookup.circl.lu','ipinfo.io','mb-api.abuse.ch','otx.alienvault.com','api.virustotal.com','threatfox-api.abuse.ch','urlhaus-api.abuse.ch','crt.sh','api.threatminer.org','whois.iana.org'], ConfigStore(':memory:')); print(f'registry OK: {len(r.all())} providers')" && grep -c 'class ShodanAdapter(BaseHTTPAdapter)' app/enrichment/adapters/shodan.py | grep -q 1 && echo 'subclass confirmed'
