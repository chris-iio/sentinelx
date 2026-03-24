# S02: IO Performance & Polling Protocol

**Goal:** Eliminate wasted IO across the enrichment pipeline — polling sends only deltas, adapters reuse TCP connections, GeoIP uses HTTPS, SQLite is WAL-backed with persistent connections, config reads are cached.
**Demo:** `?since=` cursor returns only new results per poll tick (E2E verified); `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/` returns 0 hits; ip-api.py uses `https://ipinfo.io`; `CacheStore` opens one connection with WAL mode and has `purge_expired()`; `ConfigStore._read_config()` returns cached parser.

## Must-Haves

- `enrichment_status()` in routes.py accepts `?since=<int>`, returns `results[since:]` and `next_since` field
- Frontend enrichment.ts polling loop sends `?since=N`, removes `rendered` dedup map, uses `data.next_since`
- `EnrichmentStatus` type in api.ts includes `next_since: number`
- All 12 requests-based adapters create `self._session = requests.Session()` in `__init__` and use `self._session.get()`/`.post()` for all HTTP calls
- No bare `requests.get()` or ephemeral `requests.Session()` in any adapter file
- All 12 adapter test files updated to mock `adapter._session.get`/`.post` instead of `requests.get`/`requests.post`
- ip-api adapter rewritten to use `https://ipinfo.io/{ip}/json` with HTTPS; `IP_API_BASE` uses `https://`
- `ALLOWED_API_HOSTS` in config.py updated: `ipinfo.io` added, `ip-api.com` removed
- `CacheStore.__init__` enables WAL mode, keeps persistent `self._conn`, all methods use `self._conn`
- `CacheStore.purge_expired(ttl_seconds)` method exists and deletes expired entries
- `ConfigStore._read_config()` caches parsed `ConfigParser`; `_save_config()` invalidates cache
- E2E conftest mock includes `next_since` in response body
- All unit tests pass (≥936); E2E mock responses compatible

## Proof Level

- This slice proves: contract + integration (API contract change between backend ↔ frontend, verified by unit tests and E2E mock compatibility)
- Real runtime required: no (all verification via pytest + grep)
- Human/UAT required: no

## Verification

- `python3 -m pytest tests/test_routes.py -v -k enrichment_status` — all cursor tests pass including new `?since=` tests
- `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py` — returns 0 hits (all calls through `self._session`)
- `grep -rl 'self._session' app/enrichment/adapters/*.py | wc -l` — returns 12
- `grep 'http://' app/enrichment/adapters/ip_api.py` — returns 0 hits
- `grep 'ipinfo.io' app/enrichment/adapters/ip_api.py` — returns ≥1 hit
- `grep 'ipinfo.io' app/config.py` — present
- `! grep 'ip-api.com' app/config.py` — removed
- `python3 -m pytest tests/test_ip_api.py -v` — all tests pass with ipinfo.io fixtures
- `grep 'journal_mode' app/cache/store.py` — WAL pragma present
- `grep 'purge_expired' app/cache/store.py` — method exists
- `python3 -m pytest tests/test_cache_store.py -v` — existing + new purge tests pass
- `grep '_cached_cfg' app/enrichment/config_store.py` — cache variable present
- `python3 -m pytest tests/test_config_store.py -v` — all tests pass
- `grep -c 'rendered' app/static/src/ts/modules/enrichment.ts` — returns 0 (dedup map removed)
- `grep 'next_since' app/static/src/ts/types/api.ts` — field exists
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — ≥936 tests pass

## Observability / Diagnostics

- Runtime signals: `enrichment_status()` now returns `next_since` in JSON — inspectable via browser dev tools or curl
- Inspection surfaces: `GET /enrichment/status/<job_id>?since=0` returns all results (backward-compatible); `CacheStore.stats()` unchanged
- Failure visibility: off-by-one in cursor → duplicate or skipped results visible in E2E test assertions; adapter connection reuse failure → `ConnectionError`/`SSLError` handlers from S01 surface the error
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `app/enrichment/orchestrator.py` (S01's restructured `_single_attempt()` and `get_status()` snapshot)
- New wiring introduced in this slice: `?since=` query param on `/enrichment/status/<job_id>` → `enrichment.ts` cursor counter; `self._session` on all adapters (consumed by orchestrator's `_single_attempt()` which calls `adapter.lookup()`)
- What remains before the milestone is truly usable end-to-end: S03 (frontend rendering/dead code), S04 (build config + security + integration gate)

## Tasks

- [x] **T01: Implement ?since= polling cursor in routes.py, enrichment.ts, and api.ts** `est:45m`
  - Why: The polling endpoint currently re-serializes and re-transmits the full results list on every 750ms tick. This is the only cross-boundary change in S02 (Python ↔ TypeScript) and the riskiest piece — an off-by-one in cursor tracking produces skipped or duplicated results. Covers R019.
  - Files: `app/routes.py`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/types/api.ts`, `tests/test_routes.py`, `tests/e2e/conftest.py`
  - Do: (1) Add `?since=` param to `enrichment_status()` in routes.py — `since = request.args.get("since", 0, type=int)`, slice `results[since:]`, add `next_since: len(status["results"])` to response JSON. (2) Add `next_since: number` to `EnrichmentStatus` in api.ts. (3) In enrichment.ts, replace `rendered: Record<string, boolean>` dedup map with `let since = 0` counter, add `?since=${since}` to fetch URL, use all returned results (no dedup check), update `since = data.next_since` after processing. (4) Add unit tests for `?since=` in test_routes.py. (5) Add `next_since` to E2E conftest mock response.
  - Verify: `python3 -m pytest tests/test_routes.py -v -k enrichment_status` passes; `grep -c 'rendered' app/static/src/ts/modules/enrichment.ts` returns 0; `grep 'next_since' app/static/src/ts/types/api.ts` shows field
  - Done when: routes.py returns `next_since` and slices by `since`; enrichment.ts uses cursor; `rendered` map removed; all existing + new tests pass

- [x] **T02: Add persistent requests.Session to all 12 adapters and update test mocks** `est:45m`
  - Why: Each adapter currently creates a new TCP+TLS connection on every `lookup()` call. Moving to a persistent session eliminates 50–150ms of handshake overhead per call. This also prepares ip_api.py for the T03 HTTPS migration. Covers R020.
  - Files: `app/enrichment/adapters/abuseipdb.py`, `app/enrichment/adapters/crtsh.py`, `app/enrichment/adapters/greynoise.py`, `app/enrichment/adapters/hashlookup.py`, `app/enrichment/adapters/ip_api.py`, `app/enrichment/adapters/malwarebazaar.py`, `app/enrichment/adapters/otx.py`, `app/enrichment/adapters/shodan.py`, `app/enrichment/adapters/threatfox.py`, `app/enrichment/adapters/threatminer.py`, `app/enrichment/adapters/urlhaus.py`, `app/enrichment/adapters/virustotal.py`, `tests/test_abuseipdb.py`, `tests/test_crtsh.py`, `tests/test_greynoise.py`, `tests/test_hashlookup.py`, `tests/test_ip_api.py`, `tests/test_malwarebazaar.py`, `tests/test_otx.py`, `tests/test_shodan.py`, `tests/test_threatfox.py`, `tests/test_threatminer.py`, `tests/test_urlhaus.py`, `tests/test_vt_adapter.py`
  - Do: For each of the 12 adapters: (1) Add `self._session = requests.Session()` in `__init__`. (2) For adapters with API key headers (abuseipdb, greynoise, malwarebazaar, otx, virustotal, threatfox), move header setup to `self._session.headers.update(...)` in `__init__`. (3) Replace `requests.get(...)` / `requests.post(...)` with `self._session.get(...)` / `self._session.post(...)` in `lookup()`. (4) Update docstring thread-safety note. For each test file: replace `with patch("requests.get", return_value=mock_resp)` with `adapter._session = MagicMock(); adapter._session.get.return_value = mock_resp` (or `.post` for malwarebazaar/urlhaus). VT and ThreatFox tests already mock `requests.Session` — change to directly mock `adapter._session.get`/`.post`.
  - Verify: `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py` returns 0 hits; `grep -rl 'self._session' app/enrichment/adapters/*.py | wc -l` returns 12; `python3 -m pytest tests/ --ignore=tests/e2e -x -q` passes ≥936
  - Done when: All 12 adapters use `self._session` for HTTP calls; no bare `requests.get()`/`requests.post()` in adapter files; all unit tests pass with updated mocks

- [x] **T03: Migrate ip-api adapter from HTTP ip-api.com to HTTPS ipinfo.io** `est:40m`
  - Why: ip-api.com free tier uses cleartext HTTP, leaking IOC lookups to network observers. Decision D032 selected ipinfo.io free tier as the HTTPS replacement. Depends on T02 (session already in place). Covers R021.
  - Files: `app/enrichment/adapters/ip_api.py`, `app/config.py`, `tests/test_ip_api.py`
  - Do: (1) Rewrite `ip_api.py`: change `IP_API_BASE` to `https://ipinfo.io`; update URL construction to `https://ipinfo.io/{ip}/json`; rewrite `_parse_response()` to map ipinfo.io fields (`country`→`country_code`, `city`→`city`, `org`→split into ASN+ISP, `loc`→geo coords); set `reverse=""`, `flags=[]` (ipinfo.io doesn't provide these); keep verdict as `no_data`. (2) In `app/config.py` `ALLOWED_API_HOSTS`: add `"ipinfo.io"`, remove `"ip-api.com"`. (3) Rewrite `tests/test_ip_api.py` mock fixtures to match ipinfo.io response format; update URL assertions from `http://ip-api.com` to `https://ipinfo.io`; update field assertions for reduced feature set (empty `reverse`, empty `flags`); ensure all 49 test functions pass or are adapted.
  - Verify: `grep 'http://' app/enrichment/adapters/ip_api.py` returns 0 hits; `grep 'ipinfo.io' app/enrichment/adapters/ip_api.py` returns ≥1; `grep 'ipinfo.io' app/config.py` present; `! grep 'ip-api.com' app/config.py`; `python3 -m pytest tests/test_ip_api.py -v` all pass
  - Done when: ip_api.py uses HTTPS ipinfo.io endpoint; ALLOWED_API_HOSTS updated; all 49 tests pass with ipinfo.io fixtures

- [x] **T04: SQLite WAL + persistent connection + purge_expired, and config read caching** `est:30m`
  - Why: CacheStore creates a new connection per operation (200+ open/close per batch) and lacks WAL mode. ConfigStore re-parses the INI file on every read. Both are mechanical optimizations with isolated scope. Covers R022.
  - Files: `app/cache/store.py`, `tests/test_cache_store.py`, `app/enrichment/config_store.py`, `tests/test_config_store.py`
  - Do: (1) CacheStore: replace per-method `self._connect()` with a persistent `self._conn` created in `__init__`; add `self._conn.execute("PRAGMA journal_mode=WAL")` after opening; update all methods to use `self._conn` instead of `with self._connect() as conn`; add `purge_expired(ttl_seconds: int)` method that deletes rows where `cached_at` is older than TTL; keep `self._lock` for write operations. (2) Add tests for `purge_expired()` in test_cache_store.py — test that expired entries are deleted, non-expired are kept, and empty DB doesn't error. (3) ConfigStore: add `self._cached_cfg: configparser.ConfigParser | None = None` in `__init__`; in `_read_config()`, return `self._cached_cfg` if not None, otherwise read+cache+return; in `_save_config()`, set `self._cached_cfg = None` to invalidate. (4) Verify existing config_store tests still pass (caching is transparent).
  - Verify: `grep 'journal_mode' app/cache/store.py` shows WAL; `grep 'purge_expired' app/cache/store.py` method exists; `grep 'self._conn' app/cache/store.py` shows persistent connection; `grep '_cached_cfg' app/enrichment/config_store.py` present; `python3 -m pytest tests/test_cache_store.py tests/test_config_store.py -v` all pass
  - Done when: CacheStore uses WAL + persistent connection + has `purge_expired()`; ConfigStore caches parsed config with write-through invalidation; all existing + new tests pass

## Files Likely Touched

- `app/routes.py`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/types/api.ts`
- `tests/test_routes.py`
- `tests/e2e/conftest.py`
- `app/enrichment/adapters/abuseipdb.py`
- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/greynoise.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/otx.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/virustotal.py`
- `app/config.py`
- `app/cache/store.py`
- `app/enrichment/config_store.py`
- `tests/test_ip_api.py`
- `tests/test_abuseipdb.py`
- `tests/test_crtsh.py`
- `tests/test_greynoise.py`
- `tests/test_hashlookup.py`
- `tests/test_malwarebazaar.py`
- `tests/test_otx.py`
- `tests/test_shodan.py`
- `tests/test_threatfox.py`
- `tests/test_threatminer.py`
- `tests/test_urlhaus.py`
- `tests/test_vt_adapter.py`
- `tests/test_cache_store.py`
- `tests/test_config_store.py`
