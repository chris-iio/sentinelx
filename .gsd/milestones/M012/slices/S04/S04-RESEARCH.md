# S04 Research — Persistence and helper-layer next-work decision

## Summary

S04 is a **targeted decision slice, not a presumed refactor slice**.

Current evidence still says the SQLite persistence layer is healthy:

- `app/cache/store.py` and `app/enrichment/history_store.py` both use one persistent SQLite connection, WAL mode, `synchronous=NORMAL`, `busy_timeout=5000`, memory temp store, and a time-column index.
- Prior M012 research already measured these seams as comfortably fast on synthetic local workloads.
- Fresh focused verification still passes on the persistence/history surface:
  - `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py -q` → **52 passed in 1.30s**
  - `python3 -m pytest tests/test_routes.py tests/test_api.py -q` → **49 passed in 0.51s**

The main decision seam is **not raw DB throughput**. It is the helper/runtime boundary in `app/routes/_helpers.py`, which currently owns:

- job registry lifetime (`_orchestrators`, `_terminal_jobs`)
- job submission (`_enrichment_pool`)
- status serialization / cursor slicing
- final history persistence via `_run_enrichment_and_save()`

That helper file is where future complexity could accumulate. But today the code remains small, tested, and already stabilized by S01/S02/S03. The strongest recommendation is therefore:

> **Leave the SQLite stores alone now unless new measurement proves contention or file-growth pain.**
> If S04 ships code at all, keep it helper-layer-local and observability/decision oriented rather than doing a storage rewrite.

## Requirements This Slice Owns / Supports

### Primary

- **R022** — preserve WAL-mode cache-store behavior unless evidence supports a better approach.
- **R040** — any keep/change decision here needs explicit proof, not structural assumptions.

### Supported / must not regress

- **R008** — history reload continuity depends on `HistoryStore.save_analysis()` persisting the full results payload and `/history/<id>` replaying the same UI shape.
- **R019** — `_get_enrichment_status()` in `app/routes/_helpers.py` still owns the `?since=` cursor contract; helper changes must not disturb it.
- **R009 / R010** — this slice should avoid unnecessary frontend/status-path churn now that S01/S02 already proved the live/history contract.

## Skill Notes

Two loaded skills matter to planning even if this slice stays small:

- **`verify-before-complete`** — do not claim a persistence/helper optimization unless fresh evidence exists in this slice. For S04 that likely means targeted pytest plus, if code changes touch runtime/results behavior, escalation to `make verify-fast` or `make verify-deep`.
- **`write-docs`** — the primary deliverable may legitimately be a durable ranked decision for future-you rather than code churn. If so, optimize the slice for a clear keep/change rationale with explicit proof.

No additional technology-specific skill discovery looks necessary here; the work is in established local Flask/SQLite/TypeScript patterns already used throughout the repo.

## Implementation Landscape

### `app/cache/store.py`

What exists:

- Single SQLite connection per `CacheStore` instance, created at app startup in `app/__init__.py`.
- Coarse `threading.Lock()` around **both** reads and writes.
- `get()` does TTL filtering in Python after fetching a row.
- `put()` performs `INSERT OR REPLACE` + immediate `commit()`.
- `get_all_for_ioc()` intentionally ignores TTL so IOC detail/history views can show all cached provider data.
- `purge_expired()` already exists for maintenance-style cleanup.

Planner-relevant implication:

- The store is intentionally conservative. A naive “optimization” such as removing the read lock is risky because one shared `sqlite3` connection is being used cross-thread (`check_same_thread=False`). The current lock is part of the thread-safety story, not obviously wasted overhead.
- If anyone wants more read concurrency later, that is a **different design** (per-thread/per-operation connections or a clearer connection model), not a one-line lock deletion.

### `app/enrichment/history_store.py`

What exists:

- Same healthy SQLite baseline as `CacheStore`.
- `save_analysis()` persists the full `input_text`, IOC list, full serialized results list, a computed `top_verdict`, and timestamp.
- `list_recent()` reads only summary columns and truncates input text to 120 chars.
- `load_analysis()` is the only full-row read path.

Planner-relevant implication:

- History is intentionally **full-fidelity persistence**, not a summary cache. This matches prior project memory: storing full results avoids re-enrichment on reload, preserves quota, and keeps `/history/<id>` instant.
- Do **not** propose slimming history rows or recomputing data on page load unless the slice first proves actual storage or latency pain.

### `app/routes/_helpers.py`

What exists:

- `_setup_orchestrator()` creates a fresh `EnrichmentOrchestrator`, registers it under a bounded ordered dict, enforces helper-level eviction tombstones, and submits background work to `_enrichment_pool`.
- `_run_enrichment_and_save()` waits for `orchestrator.enrich_all()`, then serializes full results and writes to `HistoryStore` using the same `job_id` as the history record id.
- History save failures are logged and swallowed.
- `_get_enrichment_status()` remains the shared API/HTML status contract owner for cursor slicing and terminal metadata.

Planner-relevant implication:

- The helper layer is the real seam if S04 wants a quick win.
- But the best candidate is **not** a broad route split; it is a very narrow improvement such as better decision-grade observability around history-save outcomes or a clearer helper responsibility boundary.
- Any change here must preserve S01’s additive terminal contract and S02/S03’s stable results-page ownership assumptions.

### `app/routes/history.py` and `app/routes/analysis.py`

What exists:

- `analysis.py` stays thin: validate text, run pipeline, optionally call `_setup_orchestrator()`, render `results.html`.
- `history.py` stays thin: `list_recent(limit=50)` for `/history`, `load_analysis()` + replay into the same `results.html` surface for `/history/<analysis_id>`.

Planner-relevant implication:

- There is no evidence that route decomposition is the next move. The important code already lives in helper/store layers.

### Test surface

Relevant files already exist and are healthy:

- `tests/test_cache_store.py`
- `tests/test_history_store.py`
- `tests/test_history_routes.py`
- `tests/test_routes.py`
- `tests/test_api.py`

These already pin:

- roundtrip persistence
- ordering / truncation / verdict computation
- concurrent writes
- history route replay contract
- helper/API status behavior

Planner-relevant implication:

- S04 can stay evidence-first without creating a large new harness. The slice already has a good regression surface.

## Natural Seams for Tasking

### Seam 1 — decision artifact first

Best first task: collect the persistence/helper verdict in a durable artifact before touching code.

Why first:

- The roadmap explicitly allows a “leave alone” outcome.
- Existing evidence already points toward “stores are healthy; helper seam is where future complexity lives.”
- This unlocks a low-churn close to the milestone even if no code change is justified.

### Seam 2 — helper-only quick win, only if evidence demands code

If the planner wants executable product work in S04, keep it inside `app/routes/_helpers.py` and adjacent tests.

Good candidates:

- make history-save success/failure more decision-visible for future debugging
- tighten helper-layer responsibility boundaries without changing route/template behavior
- add a small maintenance/inspection surface around cache/history behavior **only if** it stays local and does not alter the live analyst flow

Bad candidates for this slice:

- rewriting SQLite locking strategy
- changing history storage shape
- replacing full-result persistence with summaries
- reopening S01/S02 frontend ownership/polling seams

### Seam 3 — persistence should only move with fresh measurement

If a planner insists on persistence work, require one of these proofs first:

- measurable DB contention under realistic concurrent online analyses
- meaningful DB file growth / stale-cache accumulation problem
- request-path latency trace that points to store access rather than provider/network/runtime waits

Without one of those, persistence changes are likely optimization theater.

## Recommendation

### Recommended slice outcome

**Close S04 with an evidence-backed “leave storage alone now” decision and rank helper-layer observability/clarity above persistence refactors.**

Concretely:

1. **Do now / in S04:**
   - write the ranked next-work decision using the evidence already collected
   - explicitly record that `CacheStore` and `HistoryStore` remain keepers for now
   - if code is required, limit it to a helper-layer-only, low-regret improvement

2. **Do next:**
   - if future milestones need more certainty, measure helper/runtime behavior under multiple simultaneous online jobs before touching store internals
   - only revisit persistence after that measurement says DB work is material

3. **Later:**
   - consider a different SQLite concurrency model or maintenance strategy only if real load/file-size evidence appears

4. **Leave alone:**
   - WAL mode + persistent connections + current summary/full-load route split
   - full history result storage for `/history/<id>` replay

### Why this is the best recommendation

The current code already reflects intentional tradeoffs that fit the product:

- cache and history both prioritize simple, local, durable SQLite usage
- history intentionally stores full results to avoid re-enrichment and preserve analyst continuity
- route modules are already thin; the helper layer is the concentration point
- existing test coverage on these seams is strong relative to their size

The remaining risk is not “these stores are obviously too slow.” The remaining risk is that future changes might destabilize a healthy seam because the milestone felt pressure to ship a refactor anyway.

## Risks / Unknowns To Keep Explicit

- The coarse lock in `CacheStore`/`HistoryStore` may become a real limit later, but current evidence does not prove it is one now.
- `_run_enrichment_and_save()` still treats history-save failure as log-only; that is more an observability / trust-in-decision issue than a measured performance issue.
- Cache expiration cleanup is available (`purge_expired`) but not visibly scheduled from the app path shown here; this matters only if stale DB growth becomes a demonstrated operational problem.
- Because provider backoff/wall-clock latency dominates many real online runs, local SQLite micro-optimizations could easily disappear into noise unless measured at the end-to-end helper/runtime seam.

## Verification

Fresh focused verification run during this research:

- `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py -q` → **52 passed in 1.30s**
- `python3 -m pytest tests/test_routes.py tests/test_api.py -q` → **49 passed in 0.51s**

Use these as the minimal proof floor for any S04 code touching persistence/history/helper behavior.

Escalation guidance for the planner:

- **If S04 stays decision-only or helper/store-local:** the focused pytest commands above are the right default proof.
- **If S04 touches broader runtime/results behavior:** escalate to `make verify-fast`.
- **Only run `make verify-deep`** if the change reopens browser-visible results-page/live enrichment behavior already stabilized in S01-S03.
