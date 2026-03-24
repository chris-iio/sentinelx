---
id: M004
title: "Refactor & Optimize"
status: complete
outcome: partial_success
started_at: 2026-03-21
completed_at: 2026-03-24
total_slices: 4
slices_completed: 4
test_count_start: 924
test_count_end: 944
requirement_outcomes:
  - id: R018
    from_status: active
    to_status: validated
    proof: "S01 fixed 3 concurrency bugs (semaphore-during-sleep, get_status snapshot, _cached_markers locking). 3 new unit tests prove each independently. 944 tests pass."
  - id: R019
    from_status: active
    to_status: validated
    proof: "S02/T01: ?since= cursor on /enrichment/status/<job_id>. Frontend since counter replaces rendered dedup map. 4 new unit tests. grep 'rendered' enrichment.ts → 0."
  - id: R020
    from_status: active
    to_status: validated
    proof: "S02/T02: All 12 adapters use self._session = requests.Session(). 7 auth headers moved to session-level. grep requests.get/post in adapters → 0 code hits."
  - id: R021
    from_status: active
    to_status: validated
    proof: "S02/T03: ip_api.py rewritten for ipinfo.io HTTPS. IPINFO_BASE = https://ipinfo.io. ip-api.com removed from ALLOWED_API_HOSTS. 50/50 tests pass."
  - id: R022
    from_status: active
    to_status: validated
    proof: "S02/T04: CacheStore PRAGMA journal_mode=WAL + persistent self._conn. purge_expired(ttl_seconds) method. 34/34 cache+config tests pass."
  - id: R023
    from_status: active
    to_status: validated
    proof: "S03: All 5 O(N²) patterns fixed — querySelector attr selector, batched dashboard+sort, debounced filter (100ms), SEVERITY_MAP, nodeIndexMap. 105 E2E + 839 unit pass."
  - id: R024
    from_status: active
    to_status: validated
    proof: "S04/T02: tsconfig.json incremental:true. tailwind safelist includes email badge+filter classes. tsc --noEmit clean."
  - id: R025
    from_status: active
    to_status: validated
    proof: "S04/T03: CSP expanded to 7 directives. SECRET_KEY startup warning. Rate limiter kept as memory:// (no filesystem backend in limits library — D037/D038)."
---

# M004: Refactor & Optimize — Milestone Summary

## Outcome

**Partial success.** M004 delivered significant IO and concurrency improvements, but three success criteria from the original roadmap were not met due to scope changes during execution:

1. **`safe_request()` consolidation** — Descoped from S01 by the planner. Adapters still import `validate_endpoint`, `read_limited`, `TIMEOUT` individually and contain inline HTTP boilerplate. The ~40% LOC reduction target was not achieved.
2. **Registry caching** — `analyze()` still calls `build_registry()` per request. The S02 plan was re-scoped to focus on the polling cursor, persistent sessions, ipinfo.io migration, and WAL caching instead of registry caching in `create_app()`.
3. **Routes decomposition** — The routes file gained a `_serialize_result()` helper and `?since=` cursor logic, but `analyze()` was not decomposed into smaller helpers as planned.

Everything that **was** delivered is fully tested and verified.

## What Was Delivered

### S01: Backend Concurrency & Error Correctness
Four concurrency bugs in `orchestrator.py` fixed:
- Semaphore released before backoff sleep (extracted `_single_attempt()`)
- `get_status()` returns `list()` snapshot, not live reference
- `_cached_markers` reads/writes protected by `_lock`
- Non-429 retry waits 1s before retry attempt

All 12 requests-based adapters received explicit `SSLError` → `"SSL/TLS error"` and `ConnectionError` → `"Connection failed"` exception handlers, ordered correctly (SSLError before ConnectionError, since SSLError is a subclass).

### S02: IO Performance & Polling Protocol
- **Polling cursor:** `GET /enrichment/status/<job_id>?since=N` returns only `results[since:]` + `next_since`. Frontend replaced the O(N²) `rendered` dedup map with a server-driven `since` counter. Total polling work is now O(N).
- **Persistent sessions:** All 12 HTTP adapters use `self._session = requests.Session()`. 7 API-key adapters moved auth headers to session-level (`self._session.headers.update()`).
- **ipinfo.io migration:** ip_api.py rewritten for `https://ipinfo.io/{ip}/json`. HTTP cleartext eliminated. Private IPs handled via 404 (not JSON status field). `ALLOWED_API_HOSTS`: ipinfo.io replaces ip-api.com.
- **CacheStore:** WAL journal mode, persistent connection, `purge_expired(ttl_seconds)` method.
- **ConfigStore:** In-memory `_cached_cfg` parser cache with write-through invalidation.

### S03: Frontend Tightening — TypeScript + CSS Audit
- Dead code removed: `computeConsensus()`, `consensusBadgeClass()` deleted from verdict-compute.ts. `getOrCreateSummaryRow` un-exported. 6 dead CSS rules (~40 lines) pruned.
- Five O(N²) performance patterns fixed per R023: querySelector attribute selector, batched dashboard/sort calls, debounced search filter (100ms), `SEVERITY_MAP` pre-built Map, `nodeIndexMap` pre-built Map.
- TypeScript strict-mode clean. Bundle: 26.2kb.

### S04: Test DRY-up & Build Config
- `tests/helpers.py` with `make_mock_response()` — 153 call sites migrated across 10 adapter test files.
- `tsconfig.json` incremental compilation enabled.
- `tailwind.config.js` email IOC class safelist added.
- CSP header expanded to 7 directives. SECRET_KEY startup warning.

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 924+ tests pass with zero regressions | ✅ MET | 944 pass (839 unit + 105 E2E) |
| No adapter contains inline validate_endpoint/read_limited — all use safe_request() | ❌ NOT MET | safe_request() does not exist; adapters still use validate_endpoint/read_limited/TIMEOUT |
| Each HTTP adapter reduced by ~40% LOC | ❌ NOT MET | Descoped with safe_request(); LOC unchanged |
| Per-provider requests.Session injected and used for connection pooling | ✅ MET | All 12 adapters: self._session = requests.Session(); 0 bare requests.get/post |
| analyze() reads current_app.registry, not build_registry() per request | ❌ NOT MET | analyze() still calls build_registry() per request |
| TypeScript strict mode clean, dead code removed | ✅ MET | npx tsc --noEmit → 0 errors; 2 dead functions + 6 dead CSS rules removed |
| CSS dead rules pruned, E2E tests confirm no visual regressions | ✅ MET | 0 dead rules remain; 105 E2E tests pass |
| Adapter test files use shared fixtures | ✅ MET | tests/helpers.py make_mock_response() used by 10 test files |

**5 of 8 success criteria fully met. 3 not met (safe_request consolidation, registry caching, adapter LOC reduction).**

## Definition of Done Verification

| Criterion | Status |
|-----------|--------|
| All 924+ tests pass with zero regressions | ✅ 944 pass |
| 12 HTTP adapters use safe_request() with per-provider Session | ❌ safe_request() does not exist; Sessions ✅ |
| analyze() reads cached registry from current_app.registry | ❌ Still calls build_registry() per request |
| Routes file is decomposed — no 90-line monolithic functions | ⚠️ Partial — analyze() is ~70 lines, not decomposed into helpers |
| TypeScript strict-mode clean, no dead exports, no dead code | ✅ |
| CSS audited — dead rules removed, E2E tests confirm no visual regressions | ✅ |
| Adapter test files use shared fixtures where repetition was extracted | ✅ |
| Success criteria re-checked against running app | ⚠️ 5/8 met |

## Requirement Outcomes

| Requirement | Transition | Proof |
|-------------|-----------|-------|
| R018 | active → validated | 3 concurrency bugs fixed with dedicated unit tests |
| R019 | active → validated | ?since= cursor; frontend since counter; 4 unit tests; 0 rendered refs |
| R020 | active → validated | 12/12 adapters use self._session; 0 bare requests hits |
| R021 | active → validated | ipinfo.io HTTPS; ip-api.com removed; 50/50 tests pass |
| R022 | active → validated | WAL mode; persistent conn; purge_expired(); 34/34 tests |
| R023 | active → validated | 5/5 O(N²) patterns fixed; grep + E2E verified |
| R024 | active → validated | incremental: true; email safelist; tsc clean |
| R025 | active → validated | 7-directive CSP; SECRET_KEY warning; memory:// exception documented |

All 8 covered requirements (R018–R025) validated. No regressions on previously validated requirements.

## What Was Not Delivered (Future Work)

These items were in the original roadmap but descoped during execution:

1. **`safe_request()` helper function** — Would consolidate `validate_endpoint()` + `read_limited()` + `TIMEOUT` + exception handling into a single shared helper called by all 12 adapters. Would reduce each adapter by ~40% LOC. Not a correctness issue — the inline patterns work correctly.

2. **Registry caching in `create_app()`** — `current_app.registry` would avoid `build_registry()` per request. `settings_post()` would rebuild on key change. Not a correctness issue — the per-request build takes <1ms with the new ConfigStore caching.

3. **Routes decomposition** — `analyze()` could be split into `_extract_iocs()`, `_launch_enrichment()`, `_build_template_context()` helpers. Not a correctness issue — the function is readable at ~70 lines.

## Test Baseline

- **Unit tests:** 839 (up from 828 at M003 close; +11 new tests across S01–S04)
- **E2E tests:** 105 (unchanged from M003)
- **Total:** 944
- **TypeScript:** strict-mode clean, 0 errors
- **Bundle:** 26.2kb (down from 26.8kb at M003 close)

## Key Decisions Made

- **D032:** ipinfo.io free tier replaces ip-api.com for HTTPS GeoIP
- **D036:** Auth headers moved to session-level in __init__
- **D037:** ipinfo.io 404 = private IP (not error)
- **D038:** Rate limiter kept as memory:// (no filesystem backend in `limits` library)

## Patterns Established

- **Per-attempt semaphore:** acquire → _single_attempt() → release in try/finally; sleep outside semaphore
- **Adapter test mock:** `adapter._session = MagicMock()` (no with-patch context manager)
- **Header assertions:** `dict(adapter._session.headers)` (session-level, not call-level)
- **E2E debounce awareness:** POM methods wait ≥ debounce duration after fill()
- **O(1) lookups:** `Map` preferred over `indexOf`/`find` for repeated lookups in TS

## What's Fragile

- ipinfo.io free tier rate limits undocumented (50k/month stated, not enforced via headers). No 429 handler.
- WAL mode silently falls back to DELETE on NFS. No warning logged.
- `test_semaphore_released_during_backoff_sleep` uses threading.Event coordination — timing-sensitive with timeout=5 guards.
- SSLError handler ordering (before ConnectionError) is a hard correctness constraint — alphabetizing exception handlers would break this silently.

## Files Changed (56 non-.gsd files)

**Backend (28 files):** orchestrator.py, 12 adapter files, ip_api.py rewrite, routes.py, __init__.py, cache/store.py, config_store.py, config.py, pipeline/classifier.py, pipeline/models.py

**Frontend (10 files):** enrichment.ts, filter.ts, graph.ts, row-factory.ts, verdict-compute.ts, ioc.ts, api.ts, input.css, dist/main.js, dist/style.css

**Tests (16 files):** 12 adapter test files, test_orchestrator.py, test_routes.py, test_cache_store.py, helpers.py, e2e/conftest.py, e2e/pages/results_page.py

**Config (2 files):** tsconfig.json, tailwind.config.js
