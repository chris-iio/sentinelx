# Code Audit Report: SentinelX

**Date:** 2026-05-13  
**Scope:** repository-wide read-only audit of Flask backend, enrichment adapters/orchestrator, SQLite stores, diagnostics/settings/history routes, TypeScript frontend modules, CSS, and tooling.

## Executive Summary

- **0 critical**, **6 high**, **8 medium**, **6 low** issues/non-ideal patterns identified.
- The highest-impact fixes are:
  1. Isolate or thread-localize HTTP adapter `requests.Session` usage to remove concurrent shared mutable state.
  2. Add an explicit authorization/local-admin boundary around sensitive history, diagnostics, status, and settings routes.
  3. Bound expensive pre-extraction text processing and long-term history retention.

The generated workflow artifact is in `.gsd/quick/1-audit-all-the-code/CODE-AUDIT.md` and includes measured captures for `npm audit --omit=dev --json` and `make verify-fast`.

## Prioritized Findings

### High

1. **Shared `requests.Session` across concurrent enrichment worker threads**
   - Evidence: `app/enrichment/adapters/base.py`, `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`.
   - Risk: flaky connection-pool/cookie/header state under concurrent provider lookups.
   - Fix: use per-lookup sessions, thread-local sessions, or adapter factories that avoid shared mutable session state.

2. **Sensitive history and diagnostics routes lack an authorization boundary**
   - Evidence: `app/routes/history.py`, `app/routes/diagnostics.py`, `app/diagnostics/sources.py`, `app/enrichment/history_store.py`.
   - Risk: any reachable caller can browse recent analyses or export diagnostic bundles containing analyst input snippets.
   - Fix: enforce loopback-only/local-admin token or real auth; omit raw input from diagnostics by default.

3. **Settings mutations are unauthenticated beyond CSRF**
   - Evidence: `app/routes/settings.py`.
   - Risk: a directly reachable caller can replace provider keys, clear cache, or change TTL after fetching a CSRF token.
   - Fix: use the same admin guard as other sensitive routes and add bounded audit logging without secret values.

4. **Nested enrichment thread pools can create large request bursts**
   - Evidence: outer `_enrichment_pool` in `app/routes/_helpers.py` plus per-job `ThreadPoolExecutor` in `app/enrichment/orchestrator.py`.
   - Risk: up to roughly outer jobs × inner workers provider calls, stressing CPU, local storage, and provider quotas.
   - Fix: use a shared bounded lookup executor or lower per-job worker counts when multiple jobs are accepted.

5. **Large submissions can force several full-text IOC scans before online limits apply**
   - Evidence: `app/config.py`, `app/routes/analysis.py`, `app/pipeline/extractor.py`.
   - Risk: CPU-heavy extraction on up to 5 MB of text even when few/no IOCs exist.
   - Fix: add an analysis text/candidate limit before extraction and optional early-stop behavior.

6. **Config writes are not atomic and can lose concurrent updates**
   - Evidence: `app/enrichment/config_store.py`.
   - Risk: concurrent settings requests can overwrite each other; crashes during truncate/write can leave partial config.
   - Fix: in-process lock, temp-file write, fsync, and `os.replace`; consider file lock for multi-process use.

### Medium

1. **History storage grows indefinitely and stores raw input/results**
   - Evidence: `app/enrichment/history_store.py`.
   - Fix: add max rows/max age retention and store bounded previews unless full replay is explicitly required.

2. **Incremental status accepts negative cursors**
   - Evidence: `app/routes/_helpers.py`, `app/enrichment/orchestrator.py`.
   - Fix: reject or clamp `since < 0` at route and orchestrator boundaries.

3. **Browser `/analyze` accepts arbitrary mode values while API rejects them**
   - Evidence: `app/routes/analysis.py`, `app/routes/api.py`.
   - Fix: share the API mode validation contract with the browser route.

4. **Cached-result marker keys omit IOC type**
   - Evidence: `app/enrichment/orchestrator.py`, `app/routes/_helpers.py`; cache store keys include type.
   - Fix: include IOC type in marker keys or carry `cached_at` directly on serialized result state.

5. **Unexpected provider exceptions are returned as raw client-visible text**
   - Evidence: `app/enrichment/http_safety.py`, `app/routes/_helpers.py` serialization.
   - Fix: log exception class/details server-side but return a generic provider error to clients.

6. **Card severity sorting re-appends every card on each debounced flush**
   - Evidence: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/cards.ts`.
   - Fix: sort only when severity changed, batch with a `DocumentFragment`, or use CSS `order`.

7. **Filtering repeatedly queries and mutates all cards/buttons on each filter change**
   - Evidence: `app/static/src/ts/modules/filter.ts`.
   - Fix: cache stable node lists or refresh on a dirty flag; toggle a class instead of inline display.

8. **Security-sensitive frontend rendering helpers lack direct tests**
   - Evidence: `app/static/src/ts/modules/shared-rendering.ts`, `app/static/src/ts/modules/graph.ts`, current test mocks.
   - Fix: add Vitest coverage for URL encoding, idempotency, malformed data attributes, and text-node rendering.

### Low

1. **Outbound HTTP guard does not centrally enforce HTTPS**
   - Evidence: `app/enrichment/http_safety.py`; current adapters use HTTPS constants.
   - Fix: reject non-HTTPS schemes and userinfo in `validate_endpoint()`.

2. **`crt.sh` query URL is manually interpolated**
   - Evidence: `app/enrichment/adapters/crtsh.py`.
   - Fix: use `urllib.parse.urlencode` for query construction.

3. **CSS uses `transition: all` and unbounded stagger delays**
   - Evidence: `app/static/src/input.css`.
   - Fix: transition explicit properties and cap stagger delay.

4. **Sticky `backdrop-filter` may be costly on lower-end GPUs**
   - Evidence: `app/static/src/input.css`.
   - Fix: provide lower-cost fallback or disable under reduced-motion/data modes.

5. **`tools/dev_server.py` suppresses cleanup failure after startup timeout**
   - Evidence: `tools/dev_server.py`.
   - Fix: include cleanup failure in persisted status and user-facing remediation output.

6. **Provider-count tests are brittle**
   - Evidence: `tests/test_registry_setup.py`, `tests/e2e/test_settings.py`.
   - Fix: derive expectations from the central provider metadata contract and keep only one intentional provider-count contract test.

## Verification Performed

- Generated `.gsd/quick/1-audit-all-the-code/CODE-AUDIT.md` with `tools/optimization_audit.py --mode baseline`.
- Captured `npm audit --omit=dev --json`: exit 0, no production npm vulnerabilities reported.
- Captured `make verify-fast`: exit 0.
- Subagent read-only audits completed for performance/code quality, security, and reviewer perspectives.

## Recommended Fix Order

1. Add route-level auth/local-admin guard for history, diagnostics, settings, and status surfaces.
2. Fix adapter session isolation and nested provider concurrency limits together.
3. Add input extraction limits and history retention.
4. Harden status cursor validation, mode validation, HTTPS validation, and generic exception text.
5. Optimize frontend flush/filter DOM churn and CSS transitions.
6. Add missing direct frontend security tests and reduce provider-contract test brittleness.
