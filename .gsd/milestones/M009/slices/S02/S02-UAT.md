# S02: Migrate remaining 11 HTTP adapters — UAT

**Milestone:** M009
**Written:** 2026-03-29T17:58:39.631Z

## UAT: S02 — Migrate remaining 11 HTTP adapters

### Preconditions
- Python 3.10+ with all dependencies installed
- Working directory: `/home/chris/projects/sentinelx`
- S01 complete (BaseHTTPAdapter + Shodan migration proven)

### Test 1: All adapter tests pass
```bash
python3 -m pytest tests/test_abuseipdb.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py tests/test_crtsh.py tests/test_vt_adapter.py tests/test_threatminer.py tests/test_shodan.py -v
```
**Expected:** 396 tests pass, 0 failures.

### Test 2: Full test suite passes
```bash
python3 -m pytest tests/ -x -q
```
**Expected:** 983+ tests pass, 0 failures (e2e may be skipped if Playwright not installed).

### Test 3: Structural — 12 HTTP adapters subclass BaseHTTPAdapter
```bash
grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | grep -v base.py | wc -l
```
**Expected:** 12

### Test 4: Structural — 3 non-HTTP adapters remain standalone
```bash
grep -c 'BaseHTTPAdapter' app/enrichment/adapters/dns_lookup.py app/enrichment/adapters/asn_cymru.py app/enrichment/adapters/whois_lookup.py
```
**Expected:** All three show `:0`

### Test 5: Registry instantiates all 15 providers
```bash
python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(['127.0.0.1'], ConfigStore(':memory:')); print(len(r.all())); [print(f'  {p.name}') for p in r.all()]"
```
**Expected:** 15 providers listed by name

### Test 6: Simple adapters have no boilerplate
```bash
grep -n 'def __init__\|def is_configured\|def lookup' app/enrichment/adapters/abuseipdb.py app/enrichment/adapters/greynoise.py app/enrichment/adapters/hashlookup.py app/enrichment/adapters/ip_api.py app/enrichment/adapters/otx.py app/enrichment/adapters/shodan.py
```
**Expected:** No output (exit code 1) — none of the 6 simple adapters define these methods.

### Test 7: POST adapters have correct method
```bash
grep '_http_method.*POST' app/enrichment/adapters/malwarebazaar.py app/enrichment/adapters/threatfox.py app/enrichment/adapters/urlhaus.py
```
**Expected:** Each file shows `_http_method = "POST"`

### Test 8: Complex adapters override lookup()
```bash
grep -c 'def lookup' app/enrichment/adapters/crtsh.py app/enrichment/adapters/virustotal.py app/enrichment/adapters/threatminer.py
```
**Expected:** Each shows `:1`

### Edge Cases
- VT `supported_types` is `frozenset` not `set`: `python3 -c "from app.enrichment.adapters.virustotal import VTAdapter; a = VTAdapter(allowed_hosts=['example.com']); assert isinstance(a.supported_types, frozenset); print('frozenset OK')"`
- E2E conftest guard works when Playwright is missing: `python3 -c "import sys; sys.modules.pop('playwright', None); sys.modules.pop('playwright.sync_api', None)"` then run `python3 -m pytest tests/ -x -q` — e2e tests should be skipped, not error.
