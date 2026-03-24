# S04: Test DRY-up — shared adapter fixtures

**Goal:** Repetitive mock-response factories and IOC constructors extracted into a shared helper module; frontend config and CSP security gaps closed; all 944+ tests pass.
**Demo:** `tests/helpers.py` exists with shared `make_mock_response()` and IOC factories. 10 adapter test files import from it instead of defining local copies. `tsconfig.json` has `incremental: true`. Tailwind safelist includes email classes. CSP header covers all required directives. SECRET_KEY warning logged on startup when env var is unset.

## Must-Haves

- `tests/helpers.py` with `make_mock_response()` and IOC factory helpers (`make_ipv4_ioc`, `make_domain_ioc`, etc.)
- 10 adapter test files import `make_mock_response` from `tests.helpers` — no local `_make_mock_*_response` definitions remain
- IOC factory helpers adopted where files have 5+ identical inline `IOC(type=...)` constructions
- `tsconfig.json` includes `"incremental": true` (R024)
- `tailwind.config.js` safelist includes `ioc-type-badge--email`, `filter-pill--email`, `filter-pill--email` active variant (R024)
- CSP header includes `style-src 'self'`, `connect-src 'self'`, `img-src 'self'`, `font-src 'self'`, `object-src 'none'` (R025)
- Startup warning logged when `SECRET_KEY` is not set in environment (R025)
- All 944+ tests pass with 0 failures

## Verification

```bash
# Full test suite — must pass ≥944 with 0 failures
python3 -m pytest tests/ -x -q

# Confirm shared helpers are imported by 10 adapter test files
test $(grep -rl "from tests.helpers import" tests/test_*.py | wc -l) -eq 10

# Confirm no local _make_mock_*_response definitions remain in those files
! grep -l "def _make_mock_.*response" tests/test_*.py

# Confirm helpers.py has the shared factory
grep -q "def make_mock_response" tests/helpers.py

# R024: tsconfig incremental
grep -q '"incremental": true' tsconfig.json

# R024: tailwind email safelist
grep -q "ioc-type-badge--email" tailwind.config.js
grep -q "filter-pill--email" tailwind.config.js

# R025: CSP directives
grep -q "style-src" app/__init__.py
grep -q "connect-src" app/__init__.py
grep -q "object-src 'none'" app/__init__.py

# R025: SECRET_KEY warning
grep -q "SECRET_KEY" app/__init__.py
grep -q "warning\|WARNING\|warn" app/__init__.py

# TypeScript still clean
npx tsc --noEmit

# Diagnostic: confirm helpers module is importable and factories work
python3 -c "from tests.helpers import make_mock_response; r = make_mock_response(200, {'ok': True}); assert r.status_code == 200; print('helpers module OK')"

# Diagnostic: CSP header actually returned in response (failure-path check)
python3 -c "
from app import create_app
app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
with app.test_client() as c:
    resp = c.get('/')
    csp = resp.headers.get('Content-Security-Policy', '')
    assert 'object-src' in csp, f'CSP missing object-src: {csp}'
    assert 'style-src' in csp, f'CSP missing style-src: {csp}'
    print(f'CSP header OK: {csp[:80]}...')
"
```

## Tasks

- [x] **T01: Create tests/helpers.py and migrate 10 adapter test files** `est:45m`
  - Why: 10 adapter test files contain byte-for-byte identical mock-response factory functions (163 total call sites) and repetitive IOC construction. Extracting to a shared module cuts ~110 lines and establishes a single source of truth.
  - Files: `tests/helpers.py` (new), `tests/test_abuseipdb.py`, `tests/test_shodan.py`, `tests/test_otx.py`, `tests/test_greynoise.py`, `tests/test_ip_api.py`, `tests/test_hashlookup.py`, `tests/test_threatfox.py`, `tests/test_vt_adapter.py`, `tests/test_urlhaus.py`, `tests/test_malwarebazaar.py`
  - Do: Create `tests/helpers.py` with `make_mock_response(status_code, body)` — same body as existing `_make_mock_get_response`. Add IOC factory helpers: `make_ioc(ioc_type, value)`, `make_ipv4_ioc(value)`, `make_ipv6_ioc(value)`, `make_domain_ioc(value)`, `make_sha256_ioc(value)`, `make_md5_ioc(value)`, `make_url_ioc(value)`. In each of the 10 files: delete local `_make_mock_*_response` function definition, add `from tests.helpers import make_mock_response`, replace all calls. Adopt IOC factories in files with 5+ inline constructions. Do NOT touch crtsh, threatminer, asn_cymru, dns_lookup. Do NOT rename test classes or methods.
  - Verify: `python3 -m pytest tests/ -x -q` passes ≥944; `grep -rl "from tests.helpers import" tests/test_*.py | wc -l` returns 10; `! grep -l "def _make_mock_.*response" tests/test_*.py` returns no matches
  - Done when: All 944+ tests pass, 10 files import from helpers, no local mock-response factories remain in those 10 files

- [x] **T02: Frontend config fixes — tsconfig incremental + tailwind email safelist (R024)** `est:10m`
  - Why: R024 requires tsconfig incremental compilation and tailwind safelist entries for email IOC type classes that were added in M003 but never safelisted.
  - Files: `tsconfig.json`, `tailwind.config.js`
  - Do: Add `"incremental": true` to `tsconfig.json` compilerOptions. Add `"ioc-type-badge--email"`, `"filter-pill--email"` to tailwind.config.js safelist (near the other ioc-type-badge and filter-pill entries).
  - Verify: `grep -q '"incremental": true' tsconfig.json`; `grep -q "ioc-type-badge--email" tailwind.config.js`; `npx tsc --noEmit` exits 0
  - Done when: tsconfig has incremental, tailwind safelist includes email classes, typecheck passes

- [x] **T03: CSP header expansion + SECRET_KEY startup warning (R025)** `est:20m`
  - Why: R025 requires complete CSP coverage (style-src, connect-src, img-src, font-src, object-src) and a startup warning when SECRET_KEY is auto-generated. Current CSP only has default-src and script-src. Rate limiter storage backend left as memory:// — filesystem backend is not available in the limits library (only Redis/Memcached/MongoDB), and adding Redis would introduce infrastructure dependencies inappropriate for a local dev tool.
  - Files: `app/__init__.py`, `app/config.py`
  - Do: (1) Expand CSP header in `set_security_headers()` to: `"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; object-src 'none'"`. (2) In `create_app()`, after setting SECRET_KEY from config, add a warning log if `os.environ.get("SECRET_KEY")` is empty/None: `import logging; logger = logging.getLogger(__name__); if not os.environ.get("SECRET_KEY"): logger.warning("SECRET_KEY not set in environment — using auto-generated key. Sessions and CSRF tokens will not persist across restarts.")`. (3) Add `import os` at top of `__init__.py` if not present. (4) Rate limiter stays as `memory://` with an explanatory comment — record a decision documenting that filesystem storage is unavailable in the limits library.
  - Verify: `python3 -m pytest tests/ -x -q` passes ≥944; `grep -q "style-src" app/__init__.py`; `grep -q "object-src 'none'" app/__init__.py`; `grep -q "SECRET_KEY not set" app/__init__.py`
  - Done when: CSP header includes all R025 directives, SECRET_KEY warning is logged on startup, all tests pass

## Observability / Diagnostics

- **Test helpers module**: `tests/helpers.py` serves as the single source of truth for mock-response construction; any adapter test regression traces back to this file. `grep -c "from tests.helpers import" tests/test_*.py` shows adoption count.
- **Import-graph inspection**: `grep -rn "from tests.helpers import" tests/` shows which tests use shared helpers and which factories they import.
- **Failure visibility**: If `make_mock_response` drifts from what an adapter expects, pytest will report the adapter test file + line, making it easy to compare the mock factory output with the adapter's expected response shape.
- **CSP header inspection**: `curl -sI http://localhost:5000/ | grep -i content-security-policy` shows the live CSP header.
- **SECRET_KEY warning**: `flask run 2>&1 | grep -i "SECRET_KEY"` confirms the startup warning fires when the env var is unset.

## Files Likely Touched

- `tests/helpers.py` (new)
- `tests/test_abuseipdb.py`
- `tests/test_shodan.py`
- `tests/test_otx.py`
- `tests/test_greynoise.py`
- `tests/test_ip_api.py`
- `tests/test_hashlookup.py`
- `tests/test_threatfox.py`
- `tests/test_vt_adapter.py`
- `tests/test_urlhaus.py`
- `tests/test_malwarebazaar.py`
- `tsconfig.json`
- `tailwind.config.js`
- `app/__init__.py`
- `app/config.py`
