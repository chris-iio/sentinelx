# Audit: understand the performance, bottlenecks and do a deep security analysis

**Date:** March 17, 2026
**Goal:** understand the performance, bottlenecks and do a deep security analysis
**Codebase:** sentinelx — /home/chris/projects/sentinelx

---

## Strengths

### Security — strong baseline

The codebase has one of the best security postures I've seen in a project of this scale. It's clearly been built by someone who thinks about attack surfaces:

- **SSRF prevention (SEC-16):** Every HTTP adapter calls `validate_endpoint()` against a hostname allowlist *before* any network request. The allowlist is centralized in `app/config.py` (12 hosts). DNS-based adapters correctly skip this — they note that HTTP safety controls don't apply to port 53.

- **HTTP safety controls (SEC-04/05/06):** All 12 HTTP adapters consistently use `timeout=(5,30)`, `allow_redirects=False`, `stream=True` with a 1MB byte cap via `read_limited()`. These are centralized in `app/enrichment/http_safety.py` — no duplication, no drift.

- **XSS prevention (SEC-08):** Jinja2 autoescaping is on by default. A security test (`test_no_safe_filter_in_templates`) enforces zero `|safe` usage across all templates. The TypeScript frontend uses `createElement`/`textContent`/`createTextNode` exclusively — no `innerHTML` anywhere. The `tojson` filter in `ioc_detail.html` auto-escapes `<>` to unicode escapes — verified.

- **CSRF (SEC-10):** Flask-WTF `CSRFProtect` is initialized globally. Every POST form includes `csrf_token()`. There's a regression test (`test_csrf_token_required`) that verifies rejection without a token.

- **Input size cap (SEC-12):** `MAX_CONTENT_LENGTH = 512KB` is enforced at the Flask level before route handlers run. Custom 413 error page.

- **No dangerous primitives (SEC-13):** Zero `eval`, `exec`, `subprocess`, `os.system`, `pickle`, `yaml.load` calls confirmed via grep. Comment in `__init__.py` documents this as an invariant.

- **API key storage (SEC-17):** Config file written with `os.open(..., 0o600)` — owner-only permissions. Parent dir created with `0o700`. Keys stored outside the repo tree at `~/.sentinelx/config.ini`.

- **Debug hardcoded off (SEC-15):** `app.debug = False` is set *after* `config_override` — even test overrides can't accidentally enable it.

- **Rate limiting (SEC-21):** Flask-Limiter with in-memory storage. Per-route limits: 10/min on `/analyze`, 120/min on polling, 60/min on index. Custom 429 handler.

- **Security regression tests:** `test_security_audit.py` encodes three structural security invariants as automated tests (CSP blocks inline scripts, no `|safe`, no IOC value in outbound URLs). These survive refactoring.

- **Immutable data models:** `IOC`, `EnrichmentResult`, and `EnrichmentError` are all `frozen=True` dataclasses — prevents mutation bugs across thread boundaries.

### Architecture — clean separation

- **Pipeline isolation:** `app/pipeline/` has zero Flask imports. Pure functions, no side effects, no network calls. Offline mode genuinely makes no outbound requests (verified by `test_offline_mode_makes_no_http_calls`).

- **Provider protocol:** `Provider` is a `@runtime_checkable` Protocol — structural typing, no forced inheritance. Clean adapter pattern across 14 providers.

- **Single registration point:** `app/enrichment/setup.py` is the only place adapters are imported and registered. Adding a new provider requires one file + one `register()` call.

- **Thread safety:** Orchestrator uses `Lock` for all job dict mutations. Adapters create fresh `requests.Session` or `requests.get` per lookup — no shared session state. Cache uses `threading.Lock` on writes.

### Test coverage

- 4,868 lines of application code, 12,841 lines of tests (~2.6x ratio). Strong.
- Unit tests for every adapter, pipeline stage, cache, config store, orchestrator, and routes.
- E2E tests with Playwright page objects covering 7 user flows.
- Security-specific regression tests.

---

## Gaps

### Security gaps

**S1. TRUSTED_HOSTS enforcement is missing (SEC-11 claimed but not implemented)**
`app/config.py` sets `TRUSTED_HOSTS = ["localhost", "127.0.0.1"]` and `__init__.py` stores it in `app.config`. But there is no `@app.before_request` hook that actually validates the `Host` header against this list. The test `test_invalid_host_returns_400` passes only because it sets `SERVER_NAME='localhost'` on the test fixture — Flask's built-in `SERVER_NAME` check rejects mismatched hosts. In production (`run.py`), `SERVER_NAME` is never set, so any `Host` header is accepted. This opens the door to Host header injection attacks (cache poisoning, password reset poisoning).
*File:* `app/__init__.py` — needs a `@app.before_request` hook.

**S2. No `SESSION_COOKIE_HTTPONLY` or `SESSION_COOKIE_SECURE` configuration**
`SESSION_COOKIE_SAMESITE = "Lax"` is set (SEC-19), but `SESSION_COOKIE_HTTPONLY` (defaults to `True` in Flask, so this is actually fine) and `SESSION_COOKIE_SECURE` (defaults to `False`) are not explicitly configured. Since this is a localhost-only app, the `Secure` flag would break things — but this should be documented as a conscious decision, not left as an implicit default.

**S3. IOC values interpolated directly into URL path segments without encoding**
Multiple adapters construct URLs by interpolating `ioc.value` directly into path segments:
- `app/enrichment/adapters/shodan.py:105`: `f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"`
- `app/enrichment/adapters/greynoise.py:112`: `f"{GREYNOISE_BASE}/{ioc.value}"`
- `app/enrichment/adapters/otx.py:122`: `f"{OTX_BASE}/{otx_type}/{ioc.value}/general"`
- `app/enrichment/adapters/hashlookup.py:110`: `f"{HASHLOOKUP_BASE}/lookup/{hash_path}/{ioc.value}"`
- `app/enrichment/adapters/crtsh.py:101`: `f"{CRTSH_BASE}/?q={ioc.value}&output=json"` (query param, not path)
- `app/enrichment/adapters/abuseipdb.py:119`: `f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"` (query param)

While `validate_endpoint()` blocks SSRF to unauthorized hosts, the IOC values are not URL-encoded. A crafted IOC value containing `?`, `#`, `/../`, or newline characters could manipulate the URL structure before it reaches the validated host. The `test_no_ioc_value_in_outbound_url` test catches some patterns but misses path-segment injection. The classifier regex does pre-validate format (IPs via `ipaddress`, hashes via hex regex, domains via hostname regex), which mitigates this significantly for most types. However, URLs (`IOCType.URL`) pass through with minimal transformation and could contain path traversal sequences.

**S4. ip-api.com adapter uses plain HTTP**
`app/enrichment/adapters/ip_api.py:45`: `IP_API_BASE = "http://ip-api.com/json"` — the free tier only supports HTTP. This means IP context data (including the analyst's queried IP values) is sent in plaintext. Documented in the file but worth flagging: an on-path attacker can see what IPs the analyst is investigating. Consider upgrading to the paid tier (HTTPS) or documenting this as an accepted risk.

**S5. `ioc_detail` route accepts arbitrary `ioc_value` via `<path:>` converter with no validation**
`app/routes.py:289`: `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")` — the `ioc_type` is validated against `IOCType`, but `ioc_value` is passed directly to `cache.get_all_for_ioc()` and rendered in the template. While Jinja2 autoescaping prevents XSS, the raw value is used as a SQLite query parameter (safe due to parameterized queries) and rendered in `<code>` elements. A user can craft URLs with arbitrary strings. The risk is low but the route should validate that `ioc_value` matches expected IOC format patterns.

**S6. No `Strict-Transport-Security` (HSTS) header**
While this is a localhost-only app today, if it's ever exposed over HTTPS (e.g., behind a reverse proxy), there's no HSTS header. The `set_security_headers` after_request hook could include it conditionally.

**S7. `SECRET_KEY` auto-generation creates a new key on every restart**
`app/config.py:22`: `SECRET_KEY = os.environ.get("SECRET_KEY", "") or secrets.token_hex(32)` — if the env var isn't set, every server restart invalidates all existing sessions and CSRF tokens. For a localhost dev tool this is acceptable, but it means the `.env.example` guidance (`# auto-generated if not set`) downplays the impact. Users who restart the server mid-analysis lose their flash messages and any session state.

### Performance gaps

**P1. New SQLite connection opened per cache operation — no connection pooling**
`app/cache/store.py:52-53`: `_connect()` creates a fresh `sqlite3.connect()` on every `get()`, `put()`, and `get_all_for_ioc()` call. Under online mode, with 14 providers × N IOCs, this means hundreds of connection open/close cycles per analysis. SQLite handles this reasonably, but a connection-per-thread pool (or even a single cached connection per CacheStore instance) would reduce overhead. The `check_same_thread=False` flag is set, which is correct for multi-threaded use but means concurrent writes serialize on SQLite's file lock.

**P2. No limit on IOC count extracted from input**
The extraction pipeline (`run_pipeline()`) will happily extract and return thousands of IOCs from a 512KB paste. In online mode, each IOC is dispatched to every matching adapter (up to 14 providers per IOC). Submitting 100 IOCs creates up to 1,400 outbound API requests from a single form submission. With `max_workers=4`, this will run for a very long time and likely hit rate limits across multiple providers. There is no cap on the number of IOCs processed or enriched.

**P3. `ThreadPoolExecutor` max_workers=4 is a global bottleneck for multi-provider enrichment**
The orchestrator uses 4 worker threads regardless of how many adapters are configured (now 14). With 14 providers and 10 IOCs, that's 140 dispatch pairs sharing 4 threads. Most of the zero-auth providers (Shodan, ip-api, Hashlookup, crt.sh, ThreatMiner, Cymru ASN, DNS) have much higher rate limits than VT's 4/min. A single slow or timing-out adapter (30s read timeout) blocks a thread for 30 seconds, stalling 3/4 of the worker pool. Consider separating rate-limited providers from high-throughput ones, or using a higher worker count with per-provider rate limiting.

**P4. No connection reuse across lookups to the same provider**
Each adapter creates a fresh `requests.Session` or bare `requests.get()` per lookup call. For N IOCs × 1 provider, this means N separate TCP connections (handshake + TLS negotiation) to the same host. Using a shared `requests.Session` per provider (with thread-local or per-adapter-instance scoping) would enable HTTP keep-alive and connection reuse. The current approach is safe (no shared state) but pays a significant latency penalty.

**P5. Frontend polling interval is fixed at 750ms regardless of job size**
`app/static/src/ts/modules/enrichment.ts`: `setInterval(..., 750)` polls `/enrichment/status/<job_id>` at a fixed interval. For a job with 3 IOCs, this is fine. For 100 IOCs × 14 providers = 1,400 results, the polling endpoint returns the *entire* results array on every call (the orchestrator's `get_status` returns all results, and dedup happens client-side). As results accumulate, each 750ms poll transfers increasingly large JSON payloads. Consider: (a) returning only new results since last poll (cursor-based), (b) adaptive polling interval, or (c) SSE/WebSocket for push-based delivery.

**P6. `_orchestrators` dict grows unbounded within the 200-slot LRU window**
`app/routes.py:36-38`: The `_orchestrators` OrderedDict is capped at 200 entries, but each entry holds the full `EnrichmentOrchestrator` with all results in memory. For a large job (100 IOCs × 14 providers), each orchestrator could hold 1,400 result objects. 200 orchestrators × 1,400 results = significant memory if the app sees sustained traffic. The completed orchestrators are never cleaned up until LRU-evicted.

**P7. `iocextract` and `iocsearcher` regex-based extraction has no timeout**
The extraction pipeline runs synchronously in the Flask request thread. Complex or adversarial input (e.g., deeply nested brackets, long repetitive sequences) could cause regex backtracking in the third-party `iocextract` library. The 512KB input cap limits the blast radius, but there's no per-extraction timeout. A worst-case regex backtrack could block the request thread for seconds.

**P8. No database indexing beyond the primary key composite**
The `enrichment_cache` table has `PRIMARY KEY (ioc_value, ioc_type, provider)`. The `get_all_for_ioc` query filters on `(ioc_value, ioc_type)` — a prefix of the PK, so it's indexed. But there's no index to support cleanup of expired entries (no `cached_at` index), and no `VACUUM` or `PRAGMA optimize` is ever run. Over time, the cache database could grow unbounded if the analyst never manually clears it.

---

## Next Steps

### Critical (security)

1. **Implement TRUSTED_HOSTS enforcement** — Add a `@app.before_request` hook in `app/__init__.py` that validates `request.host` against `app.config["TRUSTED_HOSTS"]` and returns `abort(400)` for mismatches. Fix the test to not rely on `SERVER_NAME` for this behavior.

2. **URL-encode IOC values in adapter URL construction** — Use `urllib.parse.quote(ioc.value, safe='')` when interpolating IOC values into URL path segments. Add to the security test suite: a test that crafts an IOC value with path-traversal characters and verifies it's encoded.

3. **Document ip-api.com HTTP risk** — Add a `SEC-XX` comment documenting the plaintext HTTP risk. Consider adding a user-facing warning in the settings page. Evaluate paid tier cost vs. acceptable risk for localhost-only use.

### High (performance)

4. **Add IOC count cap for online mode** — Cap enriched IOC count at a configurable limit (e.g., 50). Beyond the cap, show only offline extraction results with a message suggesting smaller batches. This prevents runaway API requests and rate limit cascades.

5. **Increase `max_workers` and add per-provider rate limiting** — Raise the thread pool to 8-12 workers. Implement per-provider rate limiters (e.g., `threading.Semaphore` per adapter class) instead of relying on the global worker count to throttle VT's 4/min limit.

6. **Implement cursor-based polling** — Modify `/enrichment/status/<job_id>` to accept a `?since=N` parameter and return only results after index N. Reduces payload size from O(total) to O(delta) per poll.

7. **Add SQLite connection caching** — Use a thread-local connection or a simple connection pool in `CacheStore` instead of opening a new connection per operation.

### Medium (hardening)

8. **Add `SESSION_COOKIE_SECURE` and HSTS documentation** — Document as a conscious decision in `app/config.py` that `SESSION_COOKIE_SECURE = False` is required for localhost HTTP. Add conditional HSTS header for non-localhost deployments.

9. **Add cache expiry/vacuum** — Implement periodic cleanup of expired cache entries. Add a `PRAGMA optimize` call on startup. Consider an automatic purge of entries older than 30 days.

10. **Add extraction timeout** — Wrap `extract_iocs()` in a `signal.alarm` or `concurrent.futures.ThreadPoolExecutor` with a 5-second timeout to protect against regex backtracking on adversarial input.

11. **Enable connection reuse in adapters** — For adapters that make multiple requests to the same host (per-IOC), accept a shared `requests.Session` with keep-alive. Thread safety can be maintained with a session-per-thread pattern.

12. **Add SECRET_KEY persistence guidance** — Update `.env.example` to strongly recommend setting `SECRET_KEY` for any non-ephemeral use. Consider auto-persisting the generated key to `~/.sentinelx/config.ini` on first run.

---

*Generated by /audit — read-only recce, no code was modified.*
