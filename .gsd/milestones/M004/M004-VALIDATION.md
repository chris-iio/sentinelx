---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M004

## Success Criteria Checklist

- [x] **All 924+ tests pass with zero regressions after every slice** — evidence: S01 ended at 944 tests passing; S02 at 839 unit + 105 E2E = 944; S03 at 944; S04 at 944. Every slice summary confirms full suite green.
- [ ] **No HTTP adapter contains inline `validate_endpoint`/`read_limited`/`requests.get`/`requests.post` — all use `safe_request()`** — gap: `safe_request()` was **never implemented**. S01 was re-scoped to focus on concurrency/error handling and deferred `safe_request()` extraction. All 12 adapters still import and use `validate_endpoint`, `read_limited`, and `TIMEOUT` from `http_safety.py` directly. However, the sub-goal of eliminating bare `requests.get()`/`requests.post()` IS met — all adapters use `self._session.get()`/`self._session.post()`.
- [ ] **Each HTTP adapter reduced by ~40% LOC** — gap: Without `safe_request()` consolidation, the ~40% LOC reduction did not occur. Adapters still contain inline HTTP boilerplate (validate_endpoint, read_limited, timeout, exception handling). Total adapter LOC is 3086 across 14 files.
- [x] **Per-provider `requests.Session` injected and used for connection pooling** — evidence: `grep -rl 'self._session' adapters/*.py` returns 12. All 12 requests-based adapters create `self._session = requests.Session()` in `__init__`. 7 API-key adapters have auth headers at session level. No bare `requests.get()`/`requests.post()` remain.
- [ ] **`analyze()` reads `current_app.registry`, not `build_registry()` per request** — gap: `analyze()` (L129 of routes.py) still calls `build_registry(allowed_hosts=allowed_hosts, config_store=config_store)` on every request. No `current_app.registry` caching was implemented. S02 focused on polling cursor, persistent sessions, ipinfo.io migration, and WAL/config caching — registry caching was not addressed.
- [x] **TypeScript strict mode clean, dead code removed** — evidence: `npx tsc --noEmit` exits 0 with no errors. S03 removed `computeConsensus()`, `consensusBadgeClass()` (dead exports). S03 un-exported `getOrCreateSummaryRow`. Grep confirms zero hits for removed symbols.
- [x] **CSS dead rules pruned, E2E tests confirm no visual regressions** — evidence: S03 deleted `.alert-success`, `.alert-warning`, and `.consensus-badge` family (~40 lines). 105 E2E tests pass. Grep confirms zero hits for deleted CSS classes.
- [x] **Adapter test files use shared fixtures, repetitive patterns extracted** — evidence: S04 created `tests/helpers.py` with `make_mock_response()`. 10 adapter test files import from shared module. 153 call sites migrated. All 944 tests pass.

**Result: 5/8 criteria met, 3 gaps identified.**

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | All 12 HTTP adapters use `safe_request()` with per-provider Session. Each adapter ~40% shorter. 924+ tests pass. | Concurrency bugs fixed (semaphore, get_status snapshot, cached_markers locking). SSLError/ConnectionError handlers added to all 12 adapters. Session pooling confirmed (pre-existing). **`safe_request()` not implemented.** No LOC reduction. 944 tests pass. | **partial** |
| S02 | `analyze()` reads cached registry. Routes file shorter and decomposed. Settings POST rebuilds registry. All tests pass. | `?since=` cursor protocol implemented. Persistent sessions confirmed. ipinfo.io migration complete. WAL + config caching done. **Registry caching not implemented** — `analyze()` still calls `build_registry()` per request. Routes not decomposed (analyze is 85 lines). 944 tests pass. | **partial** |
| S03 | Dead code removed from TS. Dead CSS pruned. TypeScript strict-mode clean. E2E pass. | Fully delivered as claimed. Dead code removed, CSS pruned, 5 O(N²) fixes (R023), strict-mode clean, 944 tests pass. | **pass** |
| S04 | Shared test helpers extract repetitive patterns. Tests still pass. Test files shorter. | Fully delivered as claimed. `tests/helpers.py` created, 10 files migrated, 153 call sites. Also delivered R024 (tsconfig, tailwind) and R025 (CSP, SECRET_KEY warning). 944 tests pass. | **pass** |

## Cross-Slice Integration

### Boundary Map vs. Actual

| Boundary | Expected | Actual | Status |
|----------|----------|--------|--------|
| S01 → S02: `http_safety.py` with `safe_request()` | S02 consumes `safe_request()` | `safe_request()` does not exist. S02 proceeded without it — adapted by using `self._session` directly. | **mismatch (non-blocking)** |
| S01 → S04: Mock pattern shift to `patch("requests.request")` | S04 uses new mock pattern | S04 uses `adapter._session = MagicMock()` pattern (S02's contribution), not `patch("requests.request")`. This is a better pattern than planned. | **evolved (acceptable)** |
| S02 → terminal: `current_app.registry` cached | analyze() uses cached registry | `analyze()` still calls `build_registry()` per request. | **not delivered** |

### Assessment

The boundary map anticipated `safe_request()` flowing from S01 to S02, but S01 was re-scoped. S02 adapted by working directly with `self._session`. The mock pattern also evolved to `adapter._session = MagicMock()` which is cleaner than the originally planned `patch("requests.request")`. These are acceptable deviations.

The missing registry caching (`current_app.registry`) is a gap — `analyze()` still builds a fresh registry per request.

## Requirement Coverage

| Req | Description | Covered By | Status |
|-----|-------------|------------|--------|
| R018 | Orchestrator concurrency fixes | S01 | ✅ validated |
| R019 | Polling cursor protocol | S02/T01 | ✅ validated |
| R020 | Persistent Session on all adapters | S02/T02 | ✅ validated |
| R021 | HTTPS GeoIP (ipinfo.io) | S02/T03 | ✅ validated |
| R022 | CacheStore WAL + purge_expired | S02/T04 | ⚠️ **delivered but status still "active"** — needs validation update |
| R023 | Five O(N²) frontend fixes | S03/T02 | ✅ validated |
| R024 | tsconfig incremental + tailwind safelist | S04/T02 | ✅ validated |
| R025 | CSP + SECRET_KEY warning + rate limiter | S04/T03 | ✅ validated |

**R022 gap:** The work is complete (WAL mode confirmed at L51 of store.py, `purge_expired()` at L155), but the requirement status was never updated from "active" to "validated". This is an administrative gap, not a delivery gap.

## Verdict Rationale

**Verdict: needs-attention** (not needs-remediation)

Three success criteria were not met:
1. **`safe_request()` consolidation** — S01 was deliberately re-scoped by the planner to prioritize concurrency correctness. The underlying goal of eliminating bare `requests.get()`/`requests.post()` IS met. The remaining `validate_endpoint`/`read_limited`/`TIMEOUT` pattern is functional and safe — it's a DRY opportunity, not a correctness issue.
2. **~40% LOC reduction** — Directly dependent on `safe_request()`. Without the consolidation, adapters retain their current structure. Not a regression — code is correct, just not consolidated.
3. **Registry caching** — `analyze()` still calls `build_registry()` per request. This is a performance optimization that was planned but not delivered. The impact is moderate (one registry build per analyze request, not per enrichment result).

These are **deferred optimizations, not regressions or correctness issues.** The milestone delivered substantial value:
- 4 concurrency bugs fixed with tests
- Polling changed from O(N²) to O(N)
- All adapters use persistent sessions
- HTTPS-only GeoIP
- SQLite WAL + persistent connection
- Config caching
- Dead code removed (TS + CSS)
- 5 frontend O(N²) patterns fixed
- Test DRY-up across 10 files
- CSP hardening + startup warnings
- TypeScript strict-mode clean

All 944 tests pass. No regressions. The undelivered items are clean-up work that can be captured in a future milestone.

**This does not warrant remediation slices** — the gaps are optimizations that were consciously descoped during execution, the codebase is in a better state than before M004, and all active requirements with delivered work are validated.

## Administrative Action Required

- **R022** should be updated from "active" to "validated" — the work (WAL mode + purge_expired) is confirmed delivered by S02/T04.
- The three undelivered success criteria (`safe_request()` consolidation, ~40% LOC reduction, registry caching) should be noted as deferred to a future milestone if desired.

## Remediation Plan

None required. Gaps are deferred optimizations, not blocking issues.
