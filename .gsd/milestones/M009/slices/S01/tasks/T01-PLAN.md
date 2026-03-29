---
estimated_steps: 15
estimated_files: 2
skills_used: []
---

# T01: Create BaseHTTPAdapter abstract base class with contract tests

Create `app/enrichment/adapters/base.py` with an abstract `BaseHTTPAdapter` class that absorbs the shared adapter skeleton. The class provides:

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

## Inputs

- ``app/enrichment/http_safety.py` — safe_request() function the base class delegates to`
- ``app/enrichment/provider.py` — Provider protocol the base class must satisfy`
- ``app/enrichment/models.py` — EnrichmentResult and EnrichmentError types`
- ``app/pipeline/models.py` — IOC and IOCType types`
- ``tests/helpers.py` — make_mock_response, IOC factories, mock_adapter_session`

## Expected Output

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter abstract base class`
- ``tests/test_base_adapter.py` — contract tests for the base class`

## Verification

python3 -m pytest tests/test_base_adapter.py -v && python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; print('import OK')" && python3 -c "from app.enrichment.provider import Provider; from app.enrichment.adapters.base import BaseHTTPAdapter; from app.pipeline.models import IOCType; from app.enrichment.models import EnrichmentResult; class Stub(BaseHTTPAdapter): supported_types=frozenset({IOCType.IPV4}); name='test'; requires_api_key=False; _build_url=lambda s,i:'http://x'; _parse_response=lambda s,i,b: EnrichmentResult(ioc=i,provider='test',verdict='clean',detection_count=0,total_engines=1,scan_date=None,raw_stats={}); assert isinstance(Stub(allowed_hosts=[]), Provider); print('protocol OK')"
