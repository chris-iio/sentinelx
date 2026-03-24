---
id: S02
parent: M004
milestone: M004
provides:
  - "?since= cursor protocol on /enrichment/status/<job_id> — returns results[since:] and next_since field (O(N) total polling vs previous O(N²))"
  - All 12 enrichment adapters use persistent self._session (requests.Session) — zero bare requests.get/post in adapter code
  - "ip_api.py rewritten for ipinfo.io HTTPS (was HTTP ip-api.com) — 404-based private IP handling, org→ASN+ISP split, always-empty flags"
  - "CacheStore: WAL journal mode + persistent self._conn + purge_expired(ttl_seconds) method"
  - "ConfigStore: _cached_cfg in-memory parser cache with write-through invalidation on _save_config()"
  - 7 API-key adapters have auth headers at session level (self._session.headers.update in __init__)
requires:
  - S01 complete (adapters use safe_request; http_safety.py exists)
affects:
  - enrichment.ts polling protocol (cursor replaces dedup map)
  - api.ts EnrichmentStatus type (new next_since field)
  - All 12 adapter test files (mock pattern is now adapter._session = MagicMock())
  - E2E conftest (next_since in mock response)
  - config.py ALLOWED_API_HOSTS (ipinfo.io replaces ip-api.com)
key_files:
  - app/routes.py
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/types/api.ts
  - app/enrichment/adapters/*.py (all 12)
  - app/enrichment/adapters/ip_api.py
  - app/config.py
  - app/cache/store.py
  - app/enrichment/config_store.py
  - tests/test_routes.py
  - tests/test_ip_api.py
  - tests/test_cache_store.py
  - tests/test_config_store.py
  - tests/e2e/conftest.py
key_decisions:
  - "D032: ipinfo.io free tier replaces ip-api.com for HTTPS GeoIP"
  - "D036: Auth headers moved to self._session.headers.update() in __init__ — per-call headers removed"
  - "D037: ipinfo.io 404 = private IP (not error) — checked before raise_for_status()"
  - "next_since = len(serialized_results) — total count, not since+len(slice)"
patterns_established:
  - "Adapter test mock pattern: adapter._session = MagicMock(); adapter._session.get.return_value = mock_resp (no with-patch context manager)"
  - "Header-checking tests inspect dict(adapter._session.headers) directly instead of call_kwargs['headers']"
  - "ipinfo.io 404 for private IPs: check status_code == 404 before raise_for_status(), return no_data with empty raw_stats"
  - "CacheStore write methods: with self._lock → self._conn.execute() → self._conn.commit() (no context-manager on conn)"
  - "ConfigStore cache: set _cached_cfg = cfg in _read_config(), set _cached_cfg = None in _save_config()"
observability_surfaces:
  - "GET /enrichment/status/<job_id>?since=0 returns full results + next_since (curl / browser devtools)"
  - "next_since increment visible on each poll tick — off-by-one produces skipped/duplicate results"
  - "adapter._session.headers shows configured auth headers at runtime"
  - "CacheStore.stats() unchanged; purge_expired() return value reports rows deleted"
  - "SELECT COUNT(*) FROM enrichment_cache WHERE cached_at < datetime('now', '-24 hours') — entries eligible for purge"
drill_down_paths:
  - tasks/T01-SUMMARY.md (cursor protocol)
  - tasks/T02-SUMMARY.md (persistent sessions)
  - tasks/T03-SUMMARY.md (ipinfo.io migration)
  - tasks/T04-SUMMARY.md (WAL + config caching)
duration: ~2.5h total across 4 tasks
verification_result: passed (15/15 slice checks + 839 unit tests)
completed_at: 2026-03-24
---

# S02: IO Performance & Polling Protocol

**Eliminated wasted IO across the enrichment pipeline: polling sends only deltas via `?since=` cursor, all 12 adapters reuse TCP connections via persistent `requests.Session`, GeoIP uses HTTPS (ipinfo.io), SQLite is WAL-backed with persistent connections, and config reads are cached.**

## What Happened

### T01: Polling cursor (`?since=`)
`enrichment_status()` in routes.py now accepts `?since=<int>` query parameter, returns `results[since:]` and `next_since: len(results)`. Frontend enrichment.ts replaced the client-side `rendered: Record<string, boolean>` dedup map with a server-driven `since` counter — each poll tick sends `?since=${since}` and updates `since = data.next_since`. The `EnrichmentStatus` TypeScript type gained a `next_since: number` field. 4 new cursor unit tests added; E2E conftest mock updated with `next_since`. This changes O(N²) total work per enrichment job to O(N).

### T02: Persistent `requests.Session` on all 12 adapters
Every adapter now creates `self._session = requests.Session()` in `__init__`. The 7 API-key adapters (abuseipdb, greynoise, otx, malwarebazaar, urlhaus, threatfox, virustotal) moved auth headers from per-call `headers={}` to `self._session.headers.update({})`. VT and ThreatFox previously had ephemeral per-call sessions — replaced. ThreatMiner's `_call()` helper updated. All 12 test files transformed from `with patch("requests.get")` to `adapter._session = MagicMock()` pattern. Header-checking tests now inspect `dict(adapter._session.headers)` directly.

### T03: ipinfo.io HTTPS migration
ip_api.py fully rewritten: `IPINFO_BASE = "https://ipinfo.io"`, URL `f"{IPINFO_BASE}/{ip}/json"`, new `_parse_response()` mapping ipinfo.io fields (`country`→`country_code`, `org`→ASN+ISP via first-space split, `hostname`→`reverse`). Private IP handling changed from HTTP 200 + `status="fail"` to HTTP 404 check before `raise_for_status()`. Flags/proxy/hosting/mobile hardcoded to empty (not available on ipinfo.io free tier). `ALLOWED_API_HOSTS` in config.py: `ipinfo.io` replaces `ip-api.com`. 50 tests fully rewritten with ipinfo.io fixtures.

### T04: SQLite WAL + purge + config caching
CacheStore uses a persistent `self._conn` with WAL journal mode — one connection for the store's lifetime. `purge_expired(ttl_seconds)` deletes entries older than TTL and returns row count. ConfigStore caches parsed `ConfigParser` in `_cached_cfg`, invalidated on `_save_config()`. Stale "requests.get/post" references in 7 adapter docstrings were also cleaned up (required for slice grep verification to pass).

## Verification (15/15 checks passed)

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest test_routes.py -k enrichment_status` | 6/6 passed ✅ |
| 2 | `grep -rn 'requests\.get\|requests\.post' adapters/*.py` | 0 hits ✅ |
| 3 | `grep -rl 'self._session' adapters/*.py \| wc -l` | 12 ✅ |
| 4 | `grep 'http://' ip_api.py` | 0 hits ✅ |
| 5 | `grep 'ipinfo.io' ip_api.py` | present ✅ |
| 6 | `grep 'ipinfo.io' config.py` | present ✅ |
| 7 | `! grep 'ip-api.com' config.py` | absent ✅ |
| 8 | `pytest test_ip_api.py` | 50/50 passed ✅ |
| 9 | `grep 'journal_mode' store.py` | WAL pragma present ✅ |
| 10 | `grep 'purge_expired' store.py` | method exists ✅ |
| 11 | `pytest test_cache_store.py test_config_store.py` | 34/34 passed ✅ |
| 12 | `grep -c 'rendered' enrichment.ts` | 0 ✅ |
| 13 | `grep 'next_since' api.ts` | field exists ✅ |
| 14 | `pytest tests/ --ignore=tests/e2e -x -q` | 839 passed ✅ |
| 15 | All adapter docstrings updated (no stale refs) | 0 grep hits ✅ |

## Deviations from Plan

1. **Test count 836→839 (not 936).** The plan's ≥936 target included E2E tests; the verification command `--ignore=tests/e2e` counts only unit tests. With E2E included, the full suite is 944 (per T04 verification).
2. **ip_api test count 50 instead of 49.** One test added (`test_config_does_not_allow_ip_api_com`) for negative coverage. None deleted.
3. **`IPINFO_BASE` constant** renamed from `IP_API_BASE` for clarity — internal only.
4. **T04 discovered stale docstrings** from T02 that needed cleanup before slice grep verification could pass — not planned but required.

## Known Issues

None. All verification checks pass.

## Files Created/Modified

**Routes & Frontend (T01):** `app/routes.py`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/types/api.ts`, `tests/test_routes.py`, `tests/e2e/conftest.py`

**Adapters — persistent session (T02):** All 12 adapter files in `app/enrichment/adapters/`, all 12 test files (`tests/test_*.py`)

**ipinfo.io migration (T03):** `app/enrichment/adapters/ip_api.py`, `app/config.py`, `tests/test_ip_api.py`

**WAL + config cache (T04):** `app/cache/store.py`, `tests/test_cache_store.py`, `app/enrichment/config_store.py`

**Docstring cleanup (T04 bonus):** 7 adapter files (abuseipdb, crtsh, greynoise, hashlookup, malwarebazaar, shodan, threatminer, urlhaus)

## Forward Intelligence

### What the next slice should know
- **Adapter test mock pattern has changed.** All 12 test files now use `adapter._session = MagicMock()` instead of `with patch("requests.get")`. S04 (test DRY-up) must use this pattern for shared fixtures.
- **Header tests check `dict(adapter._session.headers)`** — not call-level kwargs. S04 shared helpers should follow this pattern.
- **`next_since` is in the E2E mock response.** Any E2E test touching enrichment polling must include it.
- **ipinfo.io fields differ from ip-api.com.** `org` contains "AS15169 Google LLC" format; `hostname` replaces `reverse`; no flags/proxy/hosting/mobile. Tests asserting GeoIP fields must use ipinfo.io shape.
- **CacheStore.purge_expired() exists** but is not yet called by any background task or route handler. A future slice could wire a periodic purge.
- **839 unit tests passing** (944 including E2E). The baseline has grown from 835 (post-T01) through 836 (post-T03, +1 new test) to 839 (post-T04, +3 purge tests).

### What's fragile
- ipinfo.io free tier has no rate limit documentation — 50k req/month is stated but not enforced via HTTP headers. No 429 handling exists yet (adapter doesn't have backoff for ipinfo.io specifically).
- WAL mode silently falls back to DELETE mode on NFS filesystems — no warning logged.
- `check_same_thread=False` on the CacheStore connection assumes the Lock properly gates all writes.

### Authoritative diagnostics
- `curl localhost:5000/enrichment/status/<job_id>?since=0` — inspect cursor protocol
- `sqlite3 ~/.sentinelx/cache.db "PRAGMA journal_mode;"` — should print "wal"
- `adapter._session.headers` — inspect session-level auth headers at runtime
