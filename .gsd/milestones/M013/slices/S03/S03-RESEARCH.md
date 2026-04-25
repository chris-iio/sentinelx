# S03 Research — Request-flow and persistence seam shipped fixes

## Slice / requirement focus

Primary requirements for this slice are **R008, R010, R018, and R019**: preserve analyst-visible polling/progress continuity while making the `/enrichment/status` path truly incremental end-to-end. **R022** is the supporting persistence guardrail: the WAL-backed cache/history stores should only change if S03 finds real contention evidence, not because they look old-fashioned. **R040** stays mandatory because S03 must refresh the audit artifact and carry fresh verification evidence after any shipped change. If helper-owned diagnostics or status serialization widen, **R009** also matters because the current settings diagnostics intentionally avoid leaking raw analyst input or result payloads.

Relevant durable context pulled from memory matches the baseline artifact: **MEM092** says the next high-confidence work is the request/status path before frontend or store rewrites, while **MEM075/MEM077** say cache/history WAL stores remain explicit keep-decisions unless concurrent-load evidence proves otherwise.

## Summary

This is **targeted research**. The codebase already has a clear request/status hot path and already has deliberate persistence design. The strongest S03 outcome is:

1. ship the cursor-native request/status fix,
2. preserve helper-owned diagnostics and terminal semantics,
3. refresh the audit so persistence stays an explicit measured keep-decision unless new evidence appears.

The key architectural surprise is that the current poll path pays **two full copies per request**:

- `app/routes/_helpers.py::_get_enrichment_status()` calls `orchestrator.get_status(job_id)`, and `app/enrichment/orchestrator.py::get_status()` copies the **entire** `results` list every time.
- The helper then also reads `orchestrator.cached_markers`, which copies the **entire** cached-marker dict every time, even though the route only serializes `results[since:]`.

That means the obvious S03 optimization seam is still the helper/orchestrator boundary, not the SQLite stores. By contrast, `app/cache/store.py` and `app/enrichment/history_store.py` are still simple singleton-WAL stores with focused unit coverage, persistent connections, and no new evidence of lock pain.

## Recommendation

Ship S03 by adding a **dedicated incremental read API on `EnrichmentOrchestrator`** and switching `_get_enrichment_status()` to use it. Do **not** rewrite `get_status()` itself.

Recommended shape:

- keep `get_status(job_id)` as the full-snapshot API for non-hot-path callers and existing tests,
- add a new method such as `get_status_since(job_id, since)` / `get_status_delta(job_id, since)` that snapshots, under one lock:
  - scalar status fields (`total`, `done`, `complete`, `status`, `terminal`, `terminal_reason`, `error`)
  - only the tail slice of results needed for the current poll
  - only the cached markers relevant to that slice (or pre-resolved cached timestamps)
  - the correct `next_since`

That approach keeps the current snapshot guarantee for full-history callers while removing the per-poll O(total-results) and O(total-cached-markers) copies from the hot status path.

`_run_enrichment_and_save()` should continue using the full `get_status()` snapshot. It runs once at job completion, needs the full result set for persistence, and is not the request-path bottleneck.

For persistence, follow the existing audit/memory guidance: **do not force a store rewrite just because this slice includes persistence in the title**. The SQLite work for S03 should be limited to refreshing/strengthening the keep-decision evidence unless a new concurrent-load capture shows real pressure.

Skill guidance that materially affects the implementation:

- From **`observability`**: **“LOG DECISIONS, NOT ACTIVITY.”** Applied here, prefer a bounded orchestrator read surface and explicit audit evidence over new per-poll debug logging.
- From **`verify-before-complete`**: **“EVIDENCE BEFORE CLAIMS, ALWAYS.”** S03 is not done until the audit is refreshed and fresh `make verify-fast` / `make verify-deep` output exists after the last code change.

## Implementation landscape

### Core request/status seam

- `app/routes/_helpers.py`
  - Main S03 boundary file.
  - Owns `_orchestrators`, helper-level `_terminal_jobs`, `_enrichment_pool`, history-save diagnostics, `_setup_orchestrator()`, `_run_enrichment_and_save()`, and `_get_enrichment_status()`.
  - `_get_enrichment_status()` currently does the wasteful work: full `get_status()` snapshot, full `cached_markers` snapshot, then `results[since:]` slicing and serialization.
  - This file also owns the bounded history-save diagnostics surfaced on `/settings`, so helper refactors must preserve that contract.

- `app/enrichment/orchestrator.py`
  - Best place to add the new incremental read API.
  - `get_status()` is intentionally a full snapshot and already has a specific test protecting that contract.
  - `cached_markers` is also lock-protected and currently copied wholesale.
  - Any S03 optimization should live here rather than complicating route modules with piecemeal lock choreography.

- `app/routes/enrichment.py` and `app/routes/api.py`
  - Thin route wrappers around `_get_enrichment_status()`.
  - Good boundary discipline already exists; keep them thin.
  - If S03 is implemented correctly, these files probably do not need meaningful logic changes.

### Frontend / contract consumers

- `app/static/src/ts/modules/enrichment.ts`
  - Poller only depends on stable top-level fields: `done`, `total`, `results`, `next_since`, `complete`, `terminal`, `terminal_reason`, `error`.
  - S03 should be backend-transparent from the frontend’s perspective.

- `app/static/src/ts/types/api.ts`
  - Documents the current `EnrichmentStatus` payload contract.
  - Ideally no type change is needed if S03 only optimizes how the backend assembles existing fields.

### Persistence seam

- `app/cache/store.py`
  - Shared singleton cache store created once in `app/__init__.py`.
  - Persistent SQLite connection, WAL mode, `busy_timeout`, single lock, simple queries, focused thread-safety tests.
  - No obvious low-regret optimization surfaced from code inspection alone.

- `app/enrichment/history_store.py`
  - Same general design as the cache store: persistent connection, WAL, single lock, simple save/list/load API.
  - Used on the post-enrichment durability path, not every poll.
  - Also not an obvious hot-path rewrite candidate from code inspection.

- `app/__init__.py`
  - Important constraint: both stores are app singletons by design, explicitly to avoid connection churn and repeated PRAGMA setup.
  - S03 should preserve that ownership unless there is strong contradictory evidence.

### Diagnostics / settings continuity

- `app/routes/settings.py`
  - Reads `get_history_save_diagnostics()` and renders the bounded aggregate diagnostics surface.
  - If helper internals change, this surface must stay bounded and free of raw analyst input/results.

- `tests/test_settings.py`
  - Explicitly proves the diagnostics surface shows aggregate counters/timestamps/outcome while **not** exposing raw input text or result rows.
  - Important supporting proof for R009 if helper diagnostics code moves.

### Audit / durable evidence

- `tools/optimization_audit.py`
  - Baseline artifact still describes the request/status seam as the active `do now` item.
  - S03 must update the internal measurement and the baseline finding text so the durable audit reflects the shipped request/status fix rather than stale “still broken” wording.
  - If persistence remains unchanged, keep the WAL store row as an explicit leave-alone decision and refresh its evidence rather than hand-waving it.

- `tests/test_optimization_audit.py`
  - Pins the current finding text and capture summaries.
  - Will need updates because the request/status section should change once S03 ships the cursor-native path.

## Key constraints / surprises

- **Two terminal-state layers exist and matter.**
  - Helper-level `_terminal_jobs` in `app/routes/_helpers.py` covers registry eviction / unknown helper state.
  - Orchestrator-level `_terminal_jobs` in `app/enrichment/orchestrator.py` covers per-orchestrator job eviction.
  - S03 should preserve the distinction between `unknown` and `evicted` instead of collapsing everything into a generic 404.

- **`get_status()`’s full-snapshot contract is load-bearing.**
  - `tests/test_orchestrator.py` explicitly proves callers cannot mutate the internal `results` list through `get_status()`.
  - Do not “optimize” this away for all callers. Add a new API for the hot path instead.

- **The helper currently copies both results and cache markers on every poll.**
  - The baseline artifact highlights the results copy, but the code inspection shows `cached_markers` is also a full-copy cost today.
  - A good S03 design retires both together.

- **`_run_enrichment_and_save()` is not the seam to optimize first.**
  - It calls `get_status()` once after enrichment finishes so it can persist the full result set.
  - Leave it on the full-snapshot path unless a later slice finds a real persistence bottleneck there.

- **Negative `since` is currently not normalized.**
  - `request.args.get("since", 0, type=int)` allows negative ints, and Python slicing would treat them as tail offsets.
  - If S03 decides to clamp/normalize negative values, do it intentionally with tests; otherwise preserve current behavior to avoid accidental contract changes while optimizing.

- **Persistence code is conservative by design.**
  - Both stores use one connection plus one lock. Reads are also serialized through that lock.
  - That may look like an optimization opportunity, but the current evidence and tests say it is an intentional simplicity/safety tradeoff, not obviously wasted work.

## Natural task seams for the planner

1. **Incremental orchestrator read API**
   - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`
   - Goal: add a lock-safe delta/since API that returns only the poll tail plus any slice-relevant cache metadata while preserving the existing full-snapshot `get_status()` contract.
   - Scope boundary: no provider/backoff/session changes; no store changes.

2. **Helper/route adoption + contract coverage**
   - Files: `app/routes/_helpers.py`, `tests/test_routes.py`, `tests/test_api.py`, possibly `tests/test_history_routes.py` / `tests/test_settings.py` if helper internals move
   - Goal: switch `/enrichment/status` and `/api/status` to the new incremental path without changing payload shape or terminal semantics.
   - Important missing test to add: prove cached results still carry `cached_at` through the incremental path rather than only proving generic result slicing.

3. **Audit refresh + persistence keep-decision update**
   - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`
   - Goal: update the durable artifact so the request/status finding reflects the shipped fix and the persistence row remains a measured keep-decision unless new evidence appears.
   - Best-case addition: an internal capture comparing old full-snapshot behavior against the new cursor-native read path, so the audit records the improvement concretely.

4. **Only-if-evidence-demands-it persistence follow-through**
   - Files: likely just `tools/optimization_audit.py` and focused store tests unless real code pain appears
   - Goal: strengthen the leave-alone decision with better concurrent-load capture, not a speculative SQLite redesign.
   - This is optional; do not force store code churn if the request/status fix is the only justified shipped change.

## What to prove first

Prove the hot-path seam before touching persistence:

1. The new orchestrator API can return only the tail slice needed for `since` polling.
2. That API preserves snapshot safety and cache-marker correctness under the orchestrator lock.
3. `/enrichment/status` and `/api/status` still return the same payload contract the frontend expects.
4. `unknown`, `evicted`, and `job_failed` semantics remain distinct and truthful.
5. If persistence stays unchanged, the audit still records an explicit keep-decision with current evidence instead of silently dropping the seam.

## Verification

### Fast inner-loop checks

- `pytest tests/test_orchestrator.py tests/test_routes.py tests/test_api.py -q`
- `pytest tests/test_history_routes.py tests/test_settings.py -q` if helper diagnostics/state ownership changes
- `pytest tests/test_optimization_audit.py -q` when the audit runner text/captures change
- `pytest tests/test_cache_store.py tests/test_history_store.py -q` to re-prove the persistence keep-decision with focused store coverage

### Slice-close proof

Per the audit contract and the `verify-before-complete` skill, S03 should finish with fresh output from:

1. `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`
2. `make verify-fast`
3. `make verify-deep`

`make verify-deep` still matters even if S03 is “backend-only” because it touches live polling/status flow, which is part of the mocked-online browser seam.

## Skill guidance / discovery

Installed skills that directly inform this slice:

- `observability` — use its bounded decision-signal rule; prefer durable status/audit evidence over noisy request logging.
- `verify-before-complete` — fresh verification after the last edit is mandatory before slice-close claims.
- `debug-like-expert` — useful fallback if the new incremental read API produces racey or contract-breaking behavior under tests.

Promising external skills discovered for core technologies in this slice (do not install automatically):

- Flask:
  - `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`
  - `npx skills add jezweb/claude-skills@flask`
- SQLite:
  - `npx skills add martinholovsky/claude-skills-generator@sqlite-database-expert`

Recommendation: the Flask skill is only worth pulling in if S03 unexpectedly widens into route/API contract work; the SQLite skill is only worth it if a new concurrent-load capture actually justifies store-level work.