# S02: IO Performance & Polling Protocol — Research

**Date:** 2026-03-21
**Depth:** Targeted

## Summary

S02 covers five independent backend/frontend changes unified by the theme "reduce wasted IO": (1) `?since=` polling cursor in routes.py + enrichment.ts, (2) persistent `requests.Session` on all 12 requests-based adapters, (3) ip-api.com → ipinfo.io HTTPS migration, (4) SQLite WAL mode + persistent connection + `purge_expired()`, and (5) config file read caching. All five are well-understood patterns with clear implementation paths. The only risk item is the polling cursor wire protocol change, which touches both Python and TypeScript and must be E2E-verified.

The work divides cleanly into five independent tasks plus a test update task. The polling cursor (routes.py ↔ enrichment.ts) is the riskiest piece because it changes the API contract between backend and frontend — an off-by-one in cursor tracking produces skipped or duplicated results. The other four are mechanical transformations with grep-verifiable outcomes.

## Recommendation

Build the polling cursor first (routes.py + enrichment.ts + api.ts) because it's the only cross-boundary change and the only one needing E2E verification. The other four changes are independent of each other and can be done in any order. The adapter session reuse is the most mechanical (12 files, same pattern). The ip-api → ipinfo.io migration is the most impactful to tests (49 tests in test_ip_api.py, all mock `requests.get` — must change to mock `self._session.get`).

## Implementation Landscape

### Key Files

**Polling cursor:**
- `app/routes.py` — `enrichment_status()` at line 334: currently returns full `status["results"]` list. Must accept `?since=<int>` query param, return `results[since:]`, and include `next_since` in response.
- `app/static/src/ts/modules/enrichment.ts` — polling loop at line 530: currently uses `rendered: Record<string, boolean>` dedup map. Must track a `since` counter, send `?since=N` on each fetch, remove `rendered` map, and use `data.next_since` to update counter.
- `app/static/src/ts/types/api.ts` — `EnrichmentStatus` interface at line 104: must add `next_since: number` field.
- `tests/test_routes.py` — existing enrichment_status tests (lines 375-500): must be updated for `?since=` param and `next_since` response field.
- `tests/e2e/conftest.py` — `MOCK_ENRICHMENT_RESPONSE_8888` and `setup_enrichment_route_mock()`: must include `next_since` field in mock responses. The E2E tests use Playwright route mocking (`page.route("**/enrichment/status/**")`), so the mock must return `next_since` or the frontend cursor will break.

**Persistent sessions (12 adapters):**
- `app/enrichment/adapters/abuseipdb.py` — uses `requests.get()` at line 143. Must change to `self._session.get()` with `self._session = requests.Session()` in `__init__`.
- `app/enrichment/adapters/crtsh.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/greynoise.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/hashlookup.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/ip_api.py` — uses `requests.get()`. Will be rewritten for ipinfo.io, session added as part of rewrite.
- `app/enrichment/adapters/malwarebazaar.py` — uses `requests.post()`. Must change to `self._session.post()`.
- `app/enrichment/adapters/otx.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/shodan.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/threatminer.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/urlhaus.py` — uses `requests.get()`. Same pattern.
- `app/enrichment/adapters/virustotal.py` — already creates `session = requests.Session()` *inside* `lookup()` (line 208). Must move to `self._session` in `__init__`.
- `app/enrichment/adapters/threatfox.py` — already creates `session = requests.Session()` *inside* `lookup()` (line 176). Must move to `self._session` in `__init__`.
- NOT touched: `asn_cymru.py` (uses `dns.resolver`, not requests), `dns_lookup.py` (uses `dns.resolver`, not requests).

**Test files affected by session change:**
- All 12 adapter test files. Current mock patterns:
  - 10 adapters use `with patch("requests.get", return_value=mock_resp)` or `with patch("requests.post", ...)` — these must change to patch the session object on the adapter instance, e.g. `adapter._session.get = MagicMock(return_value=mock_resp)` or `with patch.object(adapter._session, "get", return_value=mock_resp)`.
  - VT tests (`test_vt_adapter.py`) already mock `requests.Session` class — must change to mock `self._session.get` on the adapter instance.
  - ThreatFox tests (`test_threatfox.py`) — same as VT, already mock `requests.Session`.

**ip-api → ipinfo.io HTTPS migration:**
- `app/enrichment/adapters/ip_api.py` — complete rewrite of URL, response parsing, and docstrings. Decision D032 specifies ipinfo.io free tier: `https://ipinfo.io/{ip}/json`. Response format differs: ipinfo.io returns `{ ip, city, region, country, loc, org, postal, timezone }` where `org` is like `"AS15169 Google LLC"`. The adapter must map this to the same `raw_stats` shape (country_code, city, as_info, asname, reverse, geo, flags). **Note:** ipinfo.io does not provide proxy/hosting/mobile flags or reverse DNS. The `flags` field will be empty `[]` and `reverse` will be `""`. This is a known scope reduction accepted by D032.
- `app/config.py` — `ALLOWED_API_HOSTS` list: must add `"ipinfo.io"` and remove `"ip-api.com"`.
- `app/enrichment/setup.py` — line 153: `IPApiAdapter(allowed_hosts=allowed_hosts)` — no change needed if the class name stays `IPApiAdapter` (or rename to `IPInfoAdapter`; either works).
- `tests/test_ip_api.py` — 49 tests. Many assert specific response fields (`reverse`, `flags`, geo format). Tests asserting `http://` URL must change to `https://`. Tests asserting `ip-api.com` in ALLOWED_API_HOSTS must change to `ipinfo.io`. Tests for flags/reverse must be updated for the reduced feature set. Mock response fixtures must match ipinfo.io format.

**SQLite WAL + persistent connection + purge_expired:**
- `app/cache/store.py` — `CacheStore.__init__` (line 44): currently creates a connection, runs CREATE TABLE, then closes it immediately. Every method calls `self._connect()` for a new connection. Must: (a) keep `self._conn` as a persistent connection, (b) set `PRAGMA journal_mode=WAL` after opening, (c) add `purge_expired(ttl_seconds)` method that deletes rows where `cached_at` is older than TTL.
- `tests/test_cache_store.py` — 16 tests. Must add tests for `purge_expired()`. Existing tests use `tmp_path` fixtures so WAL mode won't leak between tests.

**Config read caching:**
- `app/enrichment/config_store.py` — `_read_config()` (line 33): reads and parses the INI file on every call. Must cache the parsed `ConfigParser` object with write-through invalidation (clear cache on `_save_config()`). Simple pattern: `self._cached_cfg: ConfigParser | None = None` in `__init__`, return cached on read, set to `None` in `_save_config()`.
- `tests/test_config_store.py` — existing tests cover read-after-write round-trips. Caching is transparent — no new tests needed unless we want to verify disk reads are reduced (optional).

### Build Order

1. **T01: Polling cursor** (routes.py + enrichment.ts + api.ts + test_routes.py updates + E2E conftest mock update) — riskiest piece, cross-boundary change, must be E2E-verified. Do this first so any wire protocol bugs surface early.
2. **T02: Persistent sessions on all 12 adapters** — mechanical but high file count. Changes all adapter `__init__` + `lookup()` methods + all 12 test files' mock patterns. Independent of T01.
3. **T03: ip-api → ipinfo.io HTTPS migration** — depends on T02 (adapter already has `self._session`). Rewrites ip_api.py adapter, updates config.py ALLOWED_API_HOSTS, rewrites test_ip_api.py fixtures and assertions.
4. **T04: SQLite WAL + persistent connection + purge_expired** — fully independent. Changes store.py + adds purge tests.
5. **T05: Config read caching** — fully independent. Changes config_store.py only.

T02 and T03 should be ordered sequentially (T02 first) since T03's ipinfo.io rewrite needs the session already in place. T04 and T05 are fully independent of everything else.

### Verification Approach

**Polling cursor (T01):**
- `python3 -m pytest tests/test_routes.py -v -k enrichment_status` — all existing + new cursor tests pass
- Grep: `grep -c 'since' app/routes.py` ≥ 3 (param read, slice, next_since)
- Grep: `grep -c 'since' app/static/src/ts/modules/enrichment.ts` ≥ 3
- Grep: `grep -c 'rendered' app/static/src/ts/modules/enrichment.ts` = 0 (dedup map removed)
- `grep 'next_since' app/static/src/ts/types/api.ts` — field exists
- E2E mock responses include `next_since` — E2E suite still passes

**Persistent sessions (T02):**
- `grep -rl 'self._session' app/enrichment/adapters/` — must return exactly 12 files (not 14 — excludes asn_cymru.py and dns_lookup.py)
- `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/` — must return 0 hits (all calls go through `self._session`)
- `grep -c 'requests.Session()' app/enrichment/adapters/*.py` — each of the 12 files has exactly 1 occurrence (in `__init__`), 0 in `lookup()`
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — all 831+ unit tests pass

**ip-api → ipinfo.io (T03):**
- `grep 'http://' app/enrichment/adapters/ip_api.py` — 0 hits (no cleartext HTTP)
- `grep 'ipinfo.io' app/enrichment/adapters/ip_api.py` — ≥ 1 hit
- `grep 'ipinfo.io' app/config.py` — present in ALLOWED_API_HOSTS
- `grep 'ip-api.com' app/config.py` — 0 hits (removed from allowlist)
- `python3 -m pytest tests/test_ip_api.py -v` — all tests pass with new fixtures

**SQLite WAL + purge (T04):**
- `grep 'journal_mode' app/cache/store.py` — WAL pragma present
- `grep 'purge_expired' app/cache/store.py` — method exists
- `grep 'self._conn' app/cache/store.py` — persistent connection used
- `python3 -m pytest tests/test_cache_store.py -v` — existing + new purge tests pass

**Config caching (T05):**
- `grep '_cached_cfg' app/enrichment/config_store.py` — cache variable present
- `python3 -m pytest tests/test_config_store.py -v` — all tests pass

**Full suite gate:**
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — ≥ 936 tests pass (S01 baseline: 936 = 831 unit + 105 E2E, but unit-only was 831 in S01 verification... checking: S01 summary says 936 total. The 831 count I just verified is the post-S01 unit-only count.)

## Constraints

- **Thread safety of `requests.Session`**: `Session.get()` and `Session.post()` are thread-safe for concurrent read-only use (no header mutation between calls). This is satisfied because: (a) adapters with API keys set headers once in `__init__` via `self._session.headers.update(...)` and never mutate after, (b) adapters without API keys don't set custom headers. The orchestrator calls `adapter.lookup()` from multiple threads, but each call only reads session state — no writes.
- **VT and ThreatFox already create ephemeral `requests.Session()` inside `lookup()`**: These two adapters set per-session headers (`x-apikey`, `Auth-Key`). Moving the session to `__init__` means headers are set once — this is correct because the API key doesn't change between calls.
- **E2E mock format**: The E2E conftest `MOCK_ENRICHMENT_RESPONSE_8888` and `setup_enrichment_route_mock()` must include `next_since` in the response body. The frontend will read `data.next_since` — if it's undefined, the cursor won't advance and results will re-render. The mock already returns `complete: true` on first poll, so `next_since` just needs to equal `len(results)`.
- **`?since=` backward compatibility**: Per D033, the cursor resets on page reload. If `since` param is absent, the route returns all results (backward-compatible default). This means existing tests that don't pass `?since=` continue to work without modification (they'll just get the full list as before).
- **ipinfo.io reduced feature set**: ipinfo.io free tier does not provide `proxy`, `hosting`, `mobile` boolean flags or `reverse` DNS. The adapter's `raw_stats` will still include these keys but with default values (`reverse: ""`, `proxy: False`, `hosting: False`, `mobile: False`, `flags: []`). The frontend context line rendering already handles empty/missing fields gracefully.

## Common Pitfalls

- **Off-by-one in `?since=` cursor** — If the server returns `next_since = len(results)` and the client sends `?since=<next_since>`, then `results[since:]` correctly returns only new items. If `next_since` were `len(results) - 1`, the last result would be re-sent. The server must return `next_since = len(status["results"])` (not `done` or `total` — those count all dispatched tasks including pending ones, while `results` only contains completed ones).

- **Frontend cursor initialization** — The `since` counter must start at `0`, not `undefined` or `null`. If the first poll sends `?since=undefined`, the server's `request.args.get("since", 0, type=int)` will correctly default to 0, but it's cleaner to initialize explicitly.

- **Test mock patch targets change with session refactor** — Adapters currently using `requests.get()` are mocked with `patch("requests.get", ...)`. After switching to `self._session.get()`, the mock target must change. Two viable patterns: (a) `adapter._session = MagicMock()` then `adapter._session.get.return_value = mock_resp`, or (b) `with patch.object(adapter._session, "get", return_value=mock_resp)`. Pattern (a) is simpler and avoids needing to know the session's internal state.

- **ipinfo.io `org` field format** — ipinfo.io returns `org` as `"AS15169 Google LLC"` (ASN number + org name in one string). The existing `_parse_response` splits `as` field on first space to extract ASN number and ISP name separately. The same split logic works on ipinfo.io's `org` field. But ipinfo.io uses `country` (2-letter code) not `countryCode`, and `city` (same name). The field mapping must be correct.

- **WAL mode persistence in test fixtures** — WAL mode persists in the SQLite database file. Since tests use `tmp_path`-based fixtures (`CacheStore(db_path=tmp_path / "cache.db")`), each test gets a fresh DB file. WAL mode won't leak between tests.

## Open Risks

- **ipinfo.io rate limit (50k/month)** — For a local dev tool this is generous, but there's no explicit rate-limit handling for ipinfo.io yet. The existing 429 error handling in the adapter will catch it if ipinfo.io returns 429, but this should be verified. The free tier may return 429 or a different error format — the adapter should handle both gracefully.
- **ipinfo.io response format changes** — The adapter will parse specific field names (`country`, `city`, `org`). If ipinfo.io changes their API, the adapter breaks silently (returns empty data, not errors). This is the same risk as ip-api.com and is acceptable for a local tool.
