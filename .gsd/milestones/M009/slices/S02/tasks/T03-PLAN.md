---
estimated_steps: 39
estimated_files: 3
skills_used: []
---

# T03: Migrate VirusTotal + ThreatMiner and run full-suite verification

Migrate the 2 complex adapters that require full `lookup()` overrides, then run the complete test suite and structural verification checks.

VirusTotal uses `ENDPOINT_MAP[ioc.type]` lambdas for URL construction (including base64 URL encoding for URL IOCs) and a complex pre-raise hook (404→no_data, 429→rate limit, 401/403→auth error). VT overrides `lookup()` entirely.

ThreatMiner has a multi-call `lookup()` with 3 sub-methods (`_lookup_ip`, `_lookup_domain`, `_lookup_hash`). Domain lookups make 2 sequential API calls and merge results. Cannot use the base class template-method `lookup()`. Overrides `lookup()` entirely, inheriting only `__init__`/`is_configured`.

## Steps

1. Migrate `app/enrichment/adapters/virustotal.py`:
   - Subclass BaseHTTPAdapter
   - Remove `__init__` and `is_configured`
   - Keep `lookup()` as an override — VT's endpoint-map + hook logic doesn't fit the base template
   - Convert `supported_types` from plain `set` to `frozenset` (pitfall from roadmap)
   - `_auth_headers()` returns `{"x-apikey": self._api_key, "Accept": "application/json"}`
   - `_build_url` and `_parse_response` implemented but `lookup()` doesn't call them via super — it has its own dispatch. They satisfy the abstract requirement.
   - Actually — `_build_url` can raise NotImplementedError since VT uses ENDPOINT_MAP lambdas directly. Better: implement `_build_url` to use the ENDPOINT_MAP so the abstract is satisfied meaningfully, even if `lookup()` calls it directly.
   - Run: `python3 -m pytest tests/test_vt_adapter.py -v`
2. Migrate `app/enrichment/adapters/threatminer.py`:
   - Subclass BaseHTTPAdapter
   - Remove `__init__` and `is_configured`
   - Keep entire `lookup()` override and all sub-methods (`_lookup_ip`, `_lookup_domain`, `_lookup_hash`, `_call`)
   - `_build_url` and `_parse_response` must be implemented (abstract) — can be simple stubs that raise NotImplementedError with comment explaining lookup() is overridden, OR implement `_build_url` to return a base URL and `_parse_response` as a no-op. Since ThreatMiner uses multiple calls, stubs are more honest.
   - Run: `python3 -m pytest tests/test_threatminer.py -v`
3. Run full test suite: `python3 -m pytest tests/ -x -q`
4. Run structural verification:
   - `grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | wc -l` → 12
   - `grep -c 'BaseHTTPAdapter' app/enrichment/adapters/dns_lookup.py app/enrichment/adapters/asn_cymru.py app/enrichment/adapters/whois_lookup.py` → all 0
   - `python3 -c "from app.enrichment.setup import build_registry; ..."` → 15 providers

## Must-Haves

- [ ] VT and ThreatMiner subclass BaseHTTPAdapter
- [ ] VT `supported_types` is frozenset, not plain set
- [ ] VT and ThreatMiner override `lookup()` entirely — multi-call / endpoint-map logic preserved
- [ ] All 86 tests (17 VT + 69 ThreatMiner) pass unchanged
- [ ] Full test suite passes (`python3 -m pytest tests/ -x -q`)
- [ ] 12 adapter files contain `BaseHTTPAdapter` subclass
- [ ] 3 non-HTTP adapters do NOT contain `BaseHTTPAdapter`
- [ ] Registry instantiates all 15 providers

## Pitfalls

- VT `supported_types` is currently a plain `set` — must convert to `frozenset` for BaseHTTPAdapter type annotation
- VT and ThreatMiner still need `_build_url` and `_parse_response` defined (they're abstract in base) even though `lookup()` is overridden. For VT, `_build_url` can use ENDPOINT_MAP meaningfully. For ThreatMiner, stubs are appropriate.
- ThreatMiner `_parse_response` signature in the module-level function takes `(ioc, body)` — same as the abstract method, no bridge needed IF it's used. But ThreatMiner's lookup doesn't call it via the template — the sub-methods have their own parsing.
- VT test file is `tests/test_vt_adapter.py` (not `test_virustotal.py`)
- ThreatMiner test file is `tests/test_threatminer.py`

## Inputs

- ``app/enrichment/adapters/base.py` — BaseHTTPAdapter abstract base class`
- ``app/enrichment/adapters/shodan.py` — reference migration pattern`
- ``app/enrichment/adapters/virustotal.py` — adapter to migrate`
- ``app/enrichment/adapters/threatminer.py` — adapter to migrate`
- ``app/enrichment/adapters/abuseipdb.py` — already migrated by T01 (confirms pattern)`
- ``app/enrichment/adapters/crtsh.py` — already migrated by T02 (lookup override reference)`

## Expected Output

- ``app/enrichment/adapters/virustotal.py` — migrated to BaseHTTPAdapter subclass`
- ``app/enrichment/adapters/threatminer.py` — migrated to BaseHTTPAdapter subclass`

## Verification

python3 -m pytest tests/test_vt_adapter.py tests/test_threatminer.py -v && python3 -m pytest tests/ -x -q && test $(grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | wc -l) -eq 12 && python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(ConfigStore(':memory:')); assert len(r.all()) == 15, f'Expected 15, got {len(r.all())}'; print('15 providers OK')"
