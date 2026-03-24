---
id: T02
parent: S02
milestone: M004
provides:
  - All 12 enrichment adapters use persistent requests.Session (self._session) created in __init__; zero bare requests.get/post calls remain
  - All 12 test files updated to mock adapter._session instead of requests.get/requests.post/requests.Session
key_files:
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/urlhaus.py
  - app/enrichment/adapters/virustotal.py
  - tests/test_abuseipdb.py
  - tests/test_crtsh.py
  - tests/test_greynoise.py
  - tests/test_hashlookup.py
  - tests/test_ip_api.py
  - tests/test_malwarebazaar.py
  - tests/test_otx.py
  - tests/test_shodan.py
  - tests/test_threatfox.py
  - tests/test_threatminer.py
  - tests/test_urlhaus.py
  - tests/test_vt_adapter.py
key_decisions:
  - API-key adapters (abuseipdb, greynoise, otx, malwarebazaar, urlhaus, threatfox, virustotal) move auth headers to self._session.headers.update() in __init__ — per-call headers removed
  - Header-checking tests rewritten to inspect adapter._session.headers directly (no network call needed) instead of asserting call_kwargs["headers"]
  - SSRF tests that create a specific Adapter(allowed_hosts=[]) must NOT have adapter overwritten by transform injection — fixed by detecting specific-adapter-followed-by-_make_adapter() pattern
patterns_established:
  - Test mock pattern is now adapter._session = MagicMock(); adapter._session.get.return_value = mock_resp (no with patch context manager)
  - ThreatMiner._call() uses self._session.get() so all 3 lookup methods (IP/domain/hash) share the same persistent session
observability_surfaces:
  - "Connection errors now surface as ConnectionError via the existing SSLError → ConnectionError handler chain (unchanged from S01)"
  - "Session reuse is transparent — no new metrics; TCP handshake savings visible in network traces"
duration: ~60m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Add persistent requests.Session to all 12 adapters and update test mocks

**Added `self._session = requests.Session()` to all 12 enrichment adapter `__init__` methods, moved per-call auth headers to session-level, and updated all 12 test files to mock `adapter._session` instead of `requests.get`/`requests.post`/`requests.Session`.**

## What Happened

All 12 adapters were updated from bare `requests.get()`/`requests.post()` calls to using a persistent `self._session` created in `__init__`. For adapters with API keys (abuseipdb, greynoise, otx, malwarebazaar, urlhaus, threatfox, virustotal), auth headers were moved from per-call `headers={}` arguments to `self._session.headers.update({})` in `__init__`.

**VT and ThreatFox** had ephemeral `session = requests.Session()` inside `lookup()` — removed and replaced with `self._session` from `__init__`.

**ThreatMiner** uses a private `_call()` helper — the `requests.get()` call in `_call()` was updated to `self._session.get()`.

All 12 test files were transformed from the old `with patch("requests.get", ...)` context manager pattern to directly setting `adapter._session = MagicMock()` followed by `adapter._session.get.return_value = mock_resp`.

**Edge cases fixed during execution:**
1. Several adapter files (abuseipdb, crtsh, greynoise, hashlookup, ip_api, shodan) had been restored from git HEAD mid-task (after the Read tool returned corrupted display with trailing garbage), requiring the `self._session` changes to be re-applied.
2. SSRF tests that create `SpecificAdapter(allowed_hosts=[])` were having `adapter` overwritten by the transform's injected `adapter = _make_adapter()` — detected via pattern scan and fixed.
3. Header-checking tests (`test_auth_header_uses_capital_key`, `test_auth_header_uses_lowercase_key`, etc.) were testing that headers were passed per-call; these were rewritten to check `dict(adapter._session.headers)` directly.
4. VT's `mock_session` variable references (from the old Session-class-mock pattern) needed to be updated to `adapter._session` after the transform.
5. ThreatMiner had one untransformed `with patch("requests.get", return_value=mock_resp) as mock_get:` in the 429-domain test — fixed manually.

## Verification

```
grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py  → 0 code hits
grep -rl 'self._session' app/enrichment/adapters/*.py | wc -l          → 12
grep -rn 'session = requests\.Session()' app/enrichment/adapters/*.py  → 0 (all are self._session)
python3 -m pytest tests/ --ignore=tests/e2e -x -q                      → 835 passed
```

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py \| grep -v comment` | 1 (no matches) | ✅ pass | <1s |
| 2 | `grep -rl 'self._session' app/enrichment/adapters/*.py \| wc -l` | 0 | ✅ pass (count=12) | <1s |
| 3 | `grep -rn '^\s*session = requests\.Session()' app/enrichment/adapters/*.py` | 1 (no matches) | ✅ pass | <1s |
| 4 | `python3 -m pytest tests/ --ignore=tests/e2e -x -q` | 0 | ✅ pass (835 tests) | 8.99s |

## Diagnostics

Session reuse is transparent at runtime — no new metrics added. The persistence means:
- TCP connection to each provider API is established once per adapter instance (per enrichment job), not per `lookup()` call
- `adapter._session` is inspectable at runtime for debugging (e.g., `adapter._session.headers` shows configured auth headers)
- Connection failures still surface through the existing `SSLError → ConnectionError` handler chain from S01

## Deviations

1. **`abuseipdb.py` already had `self._session`** in HEAD when the task started (S01 partially landed this). Restore from git mid-task was needed when the Read tool's display artifact (trailing garbage in output) confused the diff — the actual file was clean.
2. **Header-checking tests** originally verified headers were passed per-call (via `call_kwargs["headers"]`). Since headers are now session-level, these tests were rewritten to check `dict(adapter._session.headers)` — semantically equivalent but more accurate.
3. **SSRF test transform bug**: the automated Python transform injected `adapter = _make_adapter()` after SSRF tests that already created a specific adapter with `allowed_hosts=[]`. Detected by pattern scan and fixed in all 11 affected test files.

## Known Issues

None. 835 tests pass (same baseline as after T01 — T03/T04 will add the remaining tests to reach ≥936).

## Files Created/Modified

- `app/enrichment/adapters/abuseipdb.py` — Session headers (Key, Accept) moved to `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/crtsh.py` — `self._session = requests.Session()` in `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/greynoise.py` — Session header ('key') moved to `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/hashlookup.py` — `self._session` in `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/ip_api.py` — `self._session` in `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/malwarebazaar.py` — Removed per-call `requests.post()` with headers; uses `self._session.post()` via session headers
- `app/enrichment/adapters/otx.py` — Session headers (X-OTX-API-KEY, Accept) in `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/shodan.py` — `self._session` in `__init__`; `self._session.get()` in `lookup()`
- `app/enrichment/adapters/threatfox.py` — Already had `self._session` from a prior partial; confirmed correct
- `app/enrichment/adapters/threatminer.py` — `self._session` in `__init__`; `self._session.get()` in `_call()`
- `app/enrichment/adapters/urlhaus.py` — Session headers (Auth-Key, Accept) in `__init__`; `self._session.post()` in `lookup()`
- `app/enrichment/adapters/virustotal.py` — Removed ephemeral `session = requests.Session()` from `lookup()`; `self._session` in `__init__`; `self._session.get()` in `lookup()`
- `tests/test_abuseipdb.py` — Mocks `adapter._session.get`; header tests check `dict(adapter._session.headers)`
- `tests/test_crtsh.py` — Mocks `adapter._session.get`; multi-patch `with` blocks refactored
- `tests/test_greynoise.py` — Mocks `adapter._session.get`; lowercase 'key' header test updated
- `tests/test_hashlookup.py` — Mocks `adapter._session.get`
- `tests/test_ip_api.py` — Mocks `adapter._session.get`
- `tests/test_malwarebazaar.py` — Mocks `adapter._session.post`
- `tests/test_otx.py` — Mocks `adapter._session.get`; X-OTX-API-KEY header test updated
- `tests/test_shodan.py` — Mocks `adapter._session.get`
- `tests/test_threatfox.py` — Mocks `adapter._session.post` directly (removed Session-class mock)
- `tests/test_threatminer.py` — Mocks `adapter._session.get`; 429-domain test fixed manually
- `tests/test_urlhaus.py` — Mocks `adapter._session.post`; Auth-Key header test updated
- `tests/test_vt_adapter.py` — Mocks `adapter._session.get` directly (removed Session-class mock); `mock_session` refs updated
