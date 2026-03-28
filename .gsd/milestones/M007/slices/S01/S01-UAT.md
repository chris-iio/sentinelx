# S01: safe_request() consolidation — UAT

**Milestone:** M007
**Written:** 2026-03-27T13:38:34.125Z

## UAT: safe_request() consolidation

### Preconditions
- Python 3.10+ with project dependencies installed
- All source files at post-S01 state

### Test 1: safe_request() exists with correct signature
**Steps:**
1. Run: `grep -c 'def safe_request' app/enrichment/http_safety.py`
2. Run: `python3 -c "from app.enrichment.http_safety import safe_request; import inspect; sig = inspect.signature(safe_request); print(list(sig.parameters.keys()))"`

**Expected:** Count is 1. Parameters include session, url, allowed_hosts, ioc, provider, method, data, json_payload, pre_raise_hook.

### Test 2: All 12 HTTP adapters use safe_request()
**Steps:**
1. Run: `for f in app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx,abuseipdb,greynoise,virustotal,malwarebazaar,threatfox,urlhaus}.py; do echo "$(basename $f): $(grep -c safe_request $f)"; done`

**Expected:** Every file shows count ≥ 1.

### Test 3: No adapter imports requests.exceptions
**Steps:**
1. Run: `grep -l 'requests.exceptions' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx,abuseipdb,greynoise,virustotal,malwarebazaar,threatfox,urlhaus}.py 2>/dev/null; echo "exit:$?"`

**Expected:** No files listed. Exit code 1 (no matches).

### Test 4: No adapter calls validate_endpoint or read_limited directly
**Steps:**
1. Run: `grep -l 'validate_endpoint\|read_limited' app/enrichment/adapters/{crtsh,threatminer,shodan,hashlookup,ip_api,otx,abuseipdb,greynoise,virustotal,malwarebazaar,threatfox,urlhaus}.py 2>/dev/null; echo "exit:$?"`

**Expected:** No files listed. Exit code 1 (no matches).

### Test 5: Redundant per-request headers removed
**Steps:**
1. Run: `grep -c 'headers={' app/enrichment/adapters/abuseipdb.py app/enrichment/adapters/greynoise.py`

**Expected:** Both return 0.

### Test 6: safe_request unit tests pass
**Steps:**
1. Run: `python3 -m pytest tests/test_http_safety.py -v`

**Expected:** 14 tests pass covering GET/POST success, SSRF rejection, all exception types (Timeout, HTTPError, SSLError, ConnectionError, generic), pre-raise hook short-circuit and pass-through, stream flag verification.

### Test 7: All adapter tests pass
**Steps:**
1. Run: `python3 -m pytest tests/test_crtsh.py tests/test_threatminer.py tests/test_shodan.py tests/test_hashlookup.py tests/test_ip_api.py tests/test_otx.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_vt_adapter.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py -v`

**Expected:** All adapter tests pass (no regressions from migration).

### Test 8: Full test suite passes
**Steps:**
1. Run: `python3 -m pytest -x -q`

**Expected:** 1057+ tests pass, 0 failures.

### Test 9: Exception chain ordering correctness
**Steps:**
1. Run: `python3 -c "import ast, inspect; from app.enrichment import http_safety; src = inspect.getsource(http_safety.safe_request); tree = ast.parse(src); handlers = [h.type for h in ast.walk(tree) if isinstance(h, ast.ExceptHandler) and h.type]; names = [h.attr if isinstance(h, ast.Attribute) else h.id for h in handlers]; ssl_idx = next(i for i, n in enumerate(names) if 'SSL' in n); conn_idx = next(i for i, n in enumerate(names) if n == 'ConnectionError'); assert ssl_idx < conn_idx, f'SSLError at {ssl_idx} must come before ConnectionError at {conn_idx}'"`

**Expected:** No assertion error — SSLError handler appears before ConnectionError handler.

### Test 10: Route tests work with refactored app attributes
**Steps:**
1. Run: `python3 -m pytest tests/test_routes.py tests/test_history_routes.py tests/test_ioc_detail_routes.py -v`

**Expected:** All 55 tests pass — mocks correctly target current_app attributes and _enrichment_pool.
