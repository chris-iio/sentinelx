# S01: BaseHTTPAdapter + proof migration — UAT

**Milestone:** M009
**Written:** 2026-03-29T16:32:19.658Z

## UAT: S01 — BaseHTTPAdapter + proof migration

### Preconditions
- Python 3.10+ environment with project dependencies installed
- Working directory: `/home/chris/projects/sentinelx`

### Test 1: BaseHTTPAdapter import and protocol conformance

**Steps:**
1. Run: `python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; print(type(BaseHTTPAdapter))"`
2. Run: `python3 -c "from app.enrichment.provider import Provider; from app.enrichment.adapters.base import BaseHTTPAdapter; from app.pipeline.models import IOCType; from app.enrichment.models import EnrichmentResult; import abc; assert issubclass(BaseHTTPAdapter, abc.ABC); print('is ABC')"`
3. Run: `python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; from app.pipeline.models import IOCType; from app.enrichment.models import EnrichmentResult; from app.enrichment.provider import Provider; 
class S(BaseHTTPAdapter):
    supported_types=frozenset({IOCType.IPV4}); name='t'; requires_api_key=False
    def _build_url(self,i): return 'http://x'
    def _parse_response(self,i,b): return EnrichmentResult(ioc=i,provider='t',verdict='clean',detection_count=0,total_engines=1,scan_date=None,raw_stats={})
assert isinstance(S(allowed_hosts=[]), Provider); print('protocol OK')"`

**Expected:** All print OK. BaseHTTPAdapter is an ABC. Minimal subclass satisfies Provider protocol via structural duck typing.

### Test 2: Abstract enforcement — cannot instantiate directly

**Steps:**
1. Run: `python3 -c "from app.enrichment.adapters.base import BaseHTTPAdapter; BaseHTTPAdapter(allowed_hosts=[])" 2>&1`

**Expected:** `TypeError` mentioning abstract methods `_build_url` and `_parse_response`.

### Test 3: BaseHTTPAdapter contract test suite

**Steps:**
1. Run: `python3 -m pytest tests/test_base_adapter.py -v`

**Expected:** 21 tests pass covering: protocol conformance (3), is_configured (4), type guard (2), lookup dispatch (2), auth headers (3), POST adapter (2), pre-raise hook (3), build_request_body (1), abstract enforcement (1).

### Test 4: ShodanAdapter subclass verification

**Steps:**
1. Run: `grep 'class ShodanAdapter' app/enrichment/adapters/shodan.py`
2. Run: `python3 -c "from app.enrichment.adapters.shodan import ShodanAdapter; print(ShodanAdapter.__bases__)"`
3. Verify ShodanAdapter does NOT define `__init__`, `is_configured`, or `lookup`: `grep -c 'def __init__\|def is_configured\|def lookup' app/enrichment/adapters/shodan.py`

**Expected:**
1. Output: `class ShodanAdapter(BaseHTTPAdapter):`
2. Output includes `BaseHTTPAdapter`
3. Count is 0 — these methods are inherited

### Test 5: All 25 Shodan tests pass unchanged

**Steps:**
1. Run: `python3 -m pytest tests/test_shodan.py -v`

**Expected:** 25/25 pass. No test file modifications were needed.

### Test 6: Registry integration — Shodan still works in full provider stack

**Steps:**
1. Run: `python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(['internetdb.shodan.io','api.abuseipdb.com','api.greynoise.io','hashlookup.circl.lu','ipinfo.io','mb-api.abuse.ch','otx.alienvault.com','api.virustotal.com','threatfox-api.abuse.ch','urlhaus-api.abuse.ch','crt.sh','api.threatminer.org','whois.iana.org'], ConfigStore(':memory:')); shodan = [p for p in r.all() if p.name == 'Shodan InternetDB']; assert len(shodan) == 1; assert shodan[0].is_configured(); print(f'registry OK: {len(r.all())} providers, Shodan configured')"`

**Expected:** `registry OK: 15 providers, Shodan configured`

### Test 7: Override points — POST adapter with auth headers (via base tests)

**Steps:**
1. Run: `python3 -m pytest tests/test_base_adapter.py::TestPostAdapter -v`
2. Run: `python3 -m pytest tests/test_base_adapter.py::TestAuthHeaders -v`

**Expected:** POST dispatch sends json_payload through safe_request. Auth header override injects headers into session.

### Edge Case: ShodanAdapter 404 handling preserved

**Steps:**
1. Run: `python3 -m pytest tests/test_shodan.py::TestLookupNotFound -v`

**Expected:** 404 → `EnrichmentResult(verdict="no_data")` via `_make_pre_raise_hook`, not an error.
