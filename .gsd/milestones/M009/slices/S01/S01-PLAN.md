# S01: BaseHTTPAdapter + proof migration

**Goal:** BaseHTTPAdapter exists in base.py with full template-method skeleton. Shodan subclasses it. All 25 Shodan tests pass unchanged. The migration recipe is proven for S02.
**Demo:** After this: After this: BaseHTTPAdapter exists in base.py. Shodan (simplest HTTP adapter) subclasses it. All 25 Shodan tests pass unchanged. The migration recipe is proven.

## Tasks
- [x] **T01: Created BaseHTTPAdapter in base.py with template-method lookup, abstract _build_url/_parse_response, and 21 passing contract tests covering protocol conformance, auth, POST, and hooks** — Create `app/enrichment/adapters/base.py` with an abstract `BaseHTTPAdapter` class that absorbs the shared adapter skeleton. The class provides:

- `__init__(self, allowed_hosts, *, api_key="")` — creates `self._session`, stores `self._allowed_hosts`, stores `self._api_key`, calls `self._session.headers.update(self._auth_headers())`
- `is_configured()` — returns `bool(self._api_key)` if `self.requires_api_key` else `True`
- `lookup(ioc)` — template method: type guard → `_build_url(ioc)` → `_make_pre_raise_hook(ioc)` → `safe_request()` → isinstance check → `_parse_response(ioc, body)`
- Abstract methods: `_build_url(ioc) -> str`, `_parse_response(ioc, body: dict) -> EnrichmentResult`
- Override points with defaults: `_auth_headers() -> dict` (returns `{}`), `_make_pre_raise_hook(ioc) -> callable|None` (returns `None`), `_http_method: str = "GET"` class var, `_build_request_body(ioc) -> tuple[dict|None, dict|None]` (returns `(None, None)`)

Must NOT inherit from Provider protocol — structural duck typing is the contract. Must NOT import any adapter-specific module.

Also create `tests/test_base_adapter.py` with:
1. A minimal stub subclass (defines `name`, `supported_types`, `requires_api_key`, `_build_url`, `_parse_response`)
2. Provider protocol conformance: `isinstance(stub, Provider)` passes
3. `is_configured()` logic: True for zero-auth, True for api_key adapters with key, False without key
4. `lookup()` rejects unsupported IOC types
5. `lookup()` dispatches to safe_request with correct URL and returns parsed result
6. `_auth_headers()` default returns empty dict; override sets session headers
7. POST adapter variant: `_http_method="POST"` + `_build_request_body()` passes data/json to safe_request
  - Estimate: 45m
  - Files: app/enrichment/adapters/base.py, tests/test_base_adapter.py
  - Verify: python3 -m pytest tests/test_base_adapter.py -v && python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; print('import OK')" && python3 -c "from app.enrichment.provider import Provider; from app.enrichment.adapters.base import BaseHTTPAdapter; from app.pipeline.models import IOCType; from app.enrichment.models import EnrichmentResult; class Stub(BaseHTTPAdapter): supported_types=frozenset({IOCType.IPV4}); name='test'; requires_api_key=False; _build_url=lambda s,i:'http://x'; _parse_response=lambda s,i,b: EnrichmentResult(ioc=i,provider='test',verdict='clean',detection_count=0,total_engines=1,scan_date=None,raw_stats={}); assert isinstance(Stub(allowed_hosts=[]), Provider); print('protocol OK')"
- [x] **T02: ShodanAdapter now subclasses BaseHTTPAdapter with only _build_url, _parse_response, and _make_pre_raise_hook — all 25 tests pass unchanged** — Rewrite `app/enrichment/adapters/shodan.py` so that `ShodanAdapter` extends `BaseHTTPAdapter`. The migrated adapter defines only:

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
  - Estimate: 20m
  - Files: app/enrichment/adapters/shodan.py
  - Verify: python3 -m pytest tests/test_shodan.py -v && python3 -c "from app.enrichment.adapters.shodan import ShodanAdapter; from app.enrichment.provider import Provider; a = ShodanAdapter(allowed_hosts=['internetdb.shodan.io']); assert isinstance(a, Provider); assert a.is_configured(); print('OK')" && python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(['internetdb.shodan.io','api.abuseipdb.com','api.greynoise.io','hashlookup.circl.lu','ipinfo.io','mb-api.abuse.ch','otx.alienvault.com','api.virustotal.com','threatfox-api.abuse.ch','urlhaus-api.abuse.ch','crt.sh','api.threatminer.org','whois.iana.org'], ConfigStore(':memory:')); print(f'registry OK: {len(r.all())} providers')" && grep -c 'class ShodanAdapter(BaseHTTPAdapter)' app/enrichment/adapters/shodan.py | grep -q 1 && echo 'subclass confirmed'
