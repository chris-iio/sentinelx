# S04 UAT: Test DRY-up — shared adapter fixtures

## Preconditions

- Working directory: M004 worktree
- Python 3.10+, Node.js with TypeScript 5+
- All prior slices (S01–S03) complete and merged

---

## Test Case 1: Shared helpers module is functional

**Goal:** Verify `tests/helpers.py` is importable and factories produce valid objects.

1. Run: `python3 -c "from tests.helpers import make_mock_response; r = make_mock_response(200, {'ok': True}); assert r.status_code == 200; print('OK')"`
   - **Expected:** Prints "OK", exit 0.
2. Run: `python3 -c "from tests.helpers import make_mock_response; r = make_mock_response(500, None); r.raise_for_status()" 2>&1`
   - **Expected:** Raises `requests.exceptions.HTTPError` (500 Server Error).
3. Run: `python3 -c "from tests.helpers import make_ipv4_ioc, make_domain_ioc; i = make_ipv4_ioc(); d = make_domain_ioc(); print(i.type, d.type)"`
   - **Expected:** Prints `IOCType.IPV4 IOCType.DOMAIN` (or equivalent enum repr), exit 0.

---

## Test Case 2: All 10 adapter test files use shared helpers

**Goal:** No local mock-response factories remain; all import from shared module.

1. Run: `grep -rl "from tests.helpers import" tests/test_*.py | sort`
   - **Expected:** Exactly 10 files listed:
     ```
     tests/test_abuseipdb.py
     tests/test_greynoise.py
     tests/test_hashlookup.py
     tests/test_ip_api.py
     tests/test_malwarebazaar.py
     tests/test_otx.py
     tests/test_shodan.py
     tests/test_threatfox.py
     tests/test_urlhaus.py
     tests/test_vt_adapter.py
     ```
2. Run: `grep -l "def _make_mock_.*response" tests/test_*.py`
   - **Expected:** No output (exit 1 — no files contain local mock-response factories).
3. Run: `grep -rl "from tests.helpers import" tests/test_crtsh.py tests/test_threatminer.py tests/test_asn_cymru.py tests/test_dns_lookup.py 2>/dev/null`
   - **Expected:** No output — these 4 files were intentionally not migrated.

---

## Test Case 3: Full test suite passes

**Goal:** Zero regressions from mock-response migration.

1. Run: `python3 -m pytest tests/ -x -q`
   - **Expected:** ≥944 passed, 0 failures.
2. Run: `python3 -m pytest tests/test_vt_adapter.py tests/test_abuseipdb.py tests/test_otx.py -v --tb=short`
   - **Expected:** All tests pass — these are the highest-risk files (VT has mock complexity, AbuseIPDB has 429 pre-check, OTX has 24 call sites).

---

## Test Case 4: tsconfig incremental compilation (R024)

**Goal:** TypeScript incremental builds enabled.

1. Run: `grep '"incremental": true' tsconfig.json`
   - **Expected:** Line found in compilerOptions.
2. Run: `npx tsc --noEmit`
   - **Expected:** Exit 0 (clean).
3. Run: `ls tsconfig.tsbuildinfo 2>/dev/null && echo "exists" || echo "not yet"`
   - **Expected:** File may or may not exist (created on first `tsc` run with `noEmit`).

---

## Test Case 5: Tailwind email safelist (R024)

**Goal:** Email IOC type classes won't be purged by Tailwind.

1. Run: `grep "ioc-type-badge--email" tailwind.config.js`
   - **Expected:** Found in safelist array.
2. Run: `grep "filter-pill--email" tailwind.config.js`
   - **Expected:** Found in safelist array.

---

## Test Case 6: CSP header completeness (R025)

**Goal:** All 7 CSP directives present and returned in HTTP responses.

1. Run:
   ```bash
   python3 -c "
   from app import create_app
   app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
   with app.test_client() as c:
       resp = c.get('/')
       csp = resp.headers.get('Content-Security-Policy', '')
       for d in ['default-src', 'script-src', 'style-src', 'connect-src', 'img-src', 'font-src', 'object-src']:
           assert d in csp, f'Missing {d}'
       print('All 7 directives present')
       print(csp)
   "
   ```
   - **Expected:** Prints "All 7 directives present" and the full CSP string containing `object-src 'none'`.
2. Verify `object-src 'none'` specifically blocks plugin content (Flash, Java applets) — inspect the CSP string output includes exactly `object-src 'none'`.

---

## Test Case 7: SECRET_KEY startup warning (R025)

**Goal:** Warning fires when SECRET_KEY env var is unset.

1. Run (without SECRET_KEY set):
   ```bash
   python3 -c "
   import logging; logging.basicConfig(level=logging.WARNING)
   from app import create_app
   create_app({'TESTING': True})
   " 2>&1 | grep -i "SECRET_KEY"
   ```
   - **Expected:** Line containing "SECRET_KEY not set in environment" at WARNING level.
2. Run (with SECRET_KEY set):
   ```bash
   SECRET_KEY=test123 python3 -c "
   import logging; logging.basicConfig(level=logging.WARNING)
   from app import create_app
   create_app({'TESTING': True})
   " 2>&1 | grep -ic "SECRET_KEY"
   ```
   - **Expected:** Output is `0` — no warning emitted when SECRET_KEY is set.

---

## Test Case 8: Rate limiter documented exception

**Goal:** Rate limiter stays memory:// with documented justification.

1. Run: `grep "memory://" app/__init__.py`
   - **Expected:** Found with explanatory comment on the same or adjacent line.
2. Confirm D037 or D038 exists in `.gsd/DECISIONS.md` documenting this choice.

---

## Edge Cases

- **Empty body mock response:** `make_mock_response(204, None)` should produce a response with status 204 and no JSON body — verify: `python3 -c "from tests.helpers import make_mock_response; r = make_mock_response(204, None); assert r.status_code == 204; print('OK')"`
- **CSP doesn't block normal page rendering:** The full test suite includes E2E tests that would fail if CSP blocks legitimate assets. Test case 3 passing confirms this.
- **Incremental build doesn't cache stale errors:** If a `.tsbuildinfo` file from a previous broken state exists, `npx tsc --noEmit` still passes — TypeScript invalidates stale cache entries automatically.
