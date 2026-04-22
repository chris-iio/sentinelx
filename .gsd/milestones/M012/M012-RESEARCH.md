# M012 Research — Optimization Audit & Next-Work Decision

## Executive Summary

SentinelX is already in the "tight seams, not broken architecture" phase.

The codebase is comparatively small in app code (~11.1k LOC across Python/TS/HTML/CSS), heavily tested (~15.0k LOC of Python tests plus 66 Vitest tests), and several of the historically obvious optimization targets have already been retired. The app factory, provider registry, adapter base class, cursor-based polling, and WAL-backed stores are all evidence-backed keepers unless live profiling disproves them.

The next milestone should **not** start with a broad refactor. It should start by proving where current cost actually lives across the live stack:

1. **runtime latency / failure visibility at the enrichment boundary**
2. **frontend live/history rendering seam and DOM work duplication**
3. **test-loop cost, especially Playwright-heavy proof paths**
4. **only then** persistence or route refactors if measurements show they matter

The biggest surprise from this pass is that the codebase's likely near-term pain is less raw compute than **incomplete failure visibility and duplicated coordination seams**. Those weaken future decision quality and can hide real performance issues.

## Key Measurements Collected

- `python3 -m pytest -q --durations=15` → **1041 passed in 44.92s**
  - Slowest tests are dominated by Playwright E2E cases (~1.4s–2.3s each)
  - A real backoff log surfaced during full-suite execution:
    - `Rate limit (429) from ThreatMiner ... sleeping 31.3s`
- `python3 -m pytest tests/test_orchestrator.py -q` → **27 passed in 0.11s**
- `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py -q` → **38 passed in 0.93s**
- `npx vitest run` → **66 passed in 1.28s** wall time
- `npx tsc --noEmit` → **0.40s**
- `make build` → **1.60s**
  - Tailwind build ~532ms
  - esbuild bundle ~9ms
  - output JS bundle: **28.7 KB** (`app/static/dist/main.js`)
- Synthetic local microbenchmarks on temp DBs:
  - `CacheStore.put()` 1000 writes → **0.054s**
  - `CacheStore.get()` 1000 reads → **0.004s**
  - threaded cache 10x200 put+get → **0.349s** (~11.5k ops/s)
  - threaded history 10x50 save → **0.091s** (~5.5k writes/s)
- Offline pipeline spot-check:
  - `run_pipeline()` on ~151 chars → **0.89ms avg**
  - ~1.5k chars → **9.67ms avg**
  - ~7.5k chars → **101.98ms avg**
  - ~15.1k chars → **343.44ms avg**
  - ~30.2k chars → **1200.73ms avg**

## Codebase Shape That Matters

### Backend / Runtime

- `app/__init__.py`
  - clean app-factory pattern
  - singleton `CacheStore`, `HistoryStore`, cached provider registry
  - security setup is centralized and should be preserved
- `app/enrichment/setup.py`
  - single registration point for all 15 providers
  - good architectural boundary; do not fragment this
- `app/enrichment/adapters/base.py`
  - strong consolidation point for HTTP-backed providers
  - persistent `requests.Session` per adapter instance remains a good optimization
- `app/enrichment/orchestrator.py`
  - still the most important backend seam
  - per-provider semaphores + retry/backoff + cache interaction + job status all converge here
- `app/routes/_helpers.py`
  - central runtime bridge between Flask routes and orchestrator lifecycle
  - also where several future-proofing concerns now live (job registry, save-to-history, status serialization)

### Persistence

- `app/cache/store.py`
- `app/enrichment/history_store.py`

Both stores use the same healthy pattern:
- persistent SQLite connection
- WAL mode
- `synchronous=NORMAL`
- busy timeout
- temp store in memory
- explicit index on time column

Given both the code shape and synthetic measurements, persistence is **not yet proven** as the next optimization target.

### Frontend

- `app/static/src/ts/modules/enrichment.ts` is the live polling/render coordinator
- `app/static/src/ts/modules/history.ts` replays stored results into the same UI shape, but by partially duplicating the live rendering pipeline
- `app/static/src/ts/modules/row-factory.ts` is a major but sensible DOM construction hub

Frontend architecture is modular and already partially de-duplicated, but the **live-vs-history split is still carrying duplicate rendering logic**.

### Tests / Tooling

- Python coverage is very deep
- TS unit coverage exists but is narrow (2 Vitest files / 66 tests)
- E2E tests are the dominant cost center of the proof loop
- Build/typecheck loops are already fast enough that they are not the current bottleneck

## Findings by Subsystem

### 1) Orchestrator / Runtime: highest-value next investigation target

**Why this should be proven first**

`app/enrichment/orchestrator.py` and `app/routes/_helpers.py` define the system's real runtime behavior under load, retries, cache hits, and job lifecycle. If the next milestone wants evidence-backed optimization, this is the seam where proof quality matters most.

**What is already strong**

- per-provider semaphores preserve `R014`
- backoff sleep happens outside semaphore scope, preserving `R018`
- cursor polling contract exists end-to-end (`R019`)
- persistent sessions remain in adapter instances (`R020`)
- job/result snapshots are copied before exposure, reducing race hazards

**Important constraints**

- `_helpers.py` uses a shared `_enrichment_pool` capped at 4 jobs globally
- each job creates a fresh `EnrichmentOrchestrator`, but provider adapters are shared from the app registry
- orchestrator state is memory-resident and bounded by `_MAX_ORCHESTRATORS = 200`

**Known failure modes that should shape slice ordering**

1. **Silent polling failure path**
   - frontend polling in `app/static/src/ts/modules/enrichment.ts` swallows fetch failures in `.catch(function () {})`
   - if `/enrichment/status/<job_id>` starts returning non-OK or 404, the UI keeps polling without surfacing a terminal state
2. **Job eviction visibility gap**
   - `_get_enrichment_status()` returns 404 when a job is missing
   - `_orchestrators` is LRU-bounded; evicted jobs are indistinguishable from unknown IDs to the frontend
3. **History-save failure is only logged**
   - `_run_enrichment_and_save()` logs history persistence failures but does not surface them
4. **Backoff can dominate wall-clock completion**
   - `_BACKOFF_BASE = 15`, multiplier 2, max retries 2
   - a single repeatedly-rate-limited provider can add ~15s then ~30s sleeps for that IOC/provider pair
   - semaphore release prevents global starvation, which is good, but user-facing completion latency can still become very long

**Assessment**

This is the best candidate for the first deep optimization slice, but it should begin as **measurement + failure-mode audit**, not immediate refactor.

### 2) Persistence: currently a likely leave-alone unless live contention is proven

**Evidence**

- both SQLite stores use the right baseline pragmas and persistent connections
- local microbenchmarks were comfortably fast
- code is simple and consistent

**Potential concerns worth measuring before touching**

- `CacheStore.get()` also takes the global lock, so read concurrency is serialized
- `CacheStore.put()` commits every successful result write
- `HistoryStore.save_analysis()` writes the fully serialized result set in one final transaction after enrichment

**Assessment**

These are reasonable tradeoffs today. The stores should be treated as **measurement targets, not presumed problems**. A roadmap slice that rewrites storage before runtime evidence lands would likely be churn.

### 3) Frontend enrichment/render flow: second-best target after runtime proof

**What is already strong**

- cursor-based polling avoids client-side O(N²) re-fetching
- result handling is modularized
- debounced summary/detail sorting is already in place
- bundle size is modest

**Important seam**

The results UI exists in two coordination modes:
- live polling (`enrichment.ts`)
- history replay (`history.ts`)

`history.ts` mirrors much of the same routing/rendering logic as `enrichment.ts`:
- slot lookup
- context-provider split
- verdict entry accumulation
- detail-row routing
- summary/card verdict finalization

This is not a cosmetic issue; it is a future optimization seam. When rendering logic changes, there are now two places to keep behavior aligned.

**Likely value**

A slice that extracts a shared "result application" engine for both live and history modes would improve:
- future change velocity
- testability
- confidence that performance or UI fixes apply to both paths

**Assessment**

Good near-term target, especially after runtime/failure-state instrumentation clarifies whether UI coordination or network wait is the bigger real cost.

### 4) Routes / API wiring: healthy overall, but the helper layer is the real seam

`app/routes/analysis.py` and `app/routes/api.py` are thin and mostly healthy. The interesting complexity lives in `app/routes/_helpers.py`, which effectively acts as an in-process runtime coordinator.

That means route-level optimization should probably be framed as:
- helper/runtime lifecycle work
- status contract hardening
- failure-state explicitness

…not as broad Flask route decomposition. The broad decomposition work already happened.

### 5) Test / build / proof loop: real value area for future-building

**Evidence**

- typecheck/build/Vitest are already cheap
- full pytest is not catastrophic, but **44.92s** is long enough to matter for iterative work
- the slowest tests are mostly Playwright
- a real backoff log surfaced during the suite, which suggests at least one path can still incur non-mocked retry cost during proof

**Assessment**

There is likely a meaningful next-work slice around:
- making the full verification loop more predictable
- ensuring no accidental real backoff sleeps leak into test runs
- possibly rebalancing proof so expensive browser checks stay targeted

This is a strong candidate because it directly supports the user's stated goal: "best build ourselves to keep building."

## What Should Be Proven First

1. **Where live online-mode latency actually comes from**
   - provider wait/backoff vs cache vs route serialization vs frontend render
2. **Whether failure visibility is strong enough to trust future measurements**
   - especially 404/eviction/non-OK polling paths and history-save failures
3. **Whether the next real drag on development is runtime cost or proof-loop cost**
   - current evidence suggests proof-loop cost is already one of the most tangible developer-facing bottlenecks

## Existing Patterns to Reuse

Keep and reuse these patterns rather than replacing them:

- Flask app factory + singleton stores (`app/__init__.py`)
- single provider registration boundary (`app/enrichment/setup.py`)
- `BaseHTTPAdapter` template-method consolidation (`app/enrichment/adapters/base.py`)
- WAL-backed persistent SQLite stores (`app/cache/store.py`, `app/enrichment/history_store.py`)
- cursor-based polling contract (`app/routes/_helpers.py` + `app/static/src/ts/modules/enrichment.ts`)
- TS row-factory / shared-rendering split as the frontend's current modularization foundation

## Boundary Contracts That Matter

### Backend ↔ Frontend polling contract

- route returns `{ total, done, complete, results, next_since }`
- client assumes incremental append semantics using `since`
- client currently does **not** distinguish transient failure from terminal failure

This is a critical contract and should be hardened before deeper optimization claims.

### Orchestrator ↔ persistence contract

- cache writes happen per successful result
- history write happens only after whole-job completion
- a history-write failure does not invalidate enrichment completion today

This is a valid but important contract; roadmap slices should preserve it unless changing it deliberately.

### Registry / adapter contract

- provider instances are created once and reused
- adapter sessions are persistent
- `supported_types` and `is_configured()` remain the source of dispatch truth

This contract is clean and should be preserved.

## Requirements Analysis

### Table-stakes continuity requirements

These look like hard continuity constraints for any optimization work in this milestone:
- `R008` enrichment UI workflow continuity
- `R009` security posture continuity
- `R010` polling/render efficiency continuity
- `R014` per-provider concurrency
- `R015` 429 backoff behavior
- `R018` semaphore/backoff/snapshot correctness
- `R019` cursor-based polling
- `R020` persistent HTTP sessions
- `R022` WAL-mode cache behavior unless disproven
- `R040` existing test coverage remains a safety net

### Missing but likely valuable candidate requirements

These should be considered as **candidate requirements**, not silently adopted:

1. **Failure visibility requirement (candidate)**
   - If enrichment status polling enters a terminal error state (unknown job, evicted job, repeated non-OK responses), the UI/API should surface a clear analyst-visible state instead of silent retry forever.
   - Why: right now this is a meaningful operability and optimization-trust gap.

2. **Verification-budget requirement (candidate)**
   - The default local proof loop for touched areas should stay under an agreed budget, or be decomposed into fast and slow lanes.
   - Why: current build/typecheck loops are fast, but full-suite cost is meaningful and directly affects future work velocity.

3. **Measurement-before-storage-change requirement (candidate)**
   - Persistence rewrites should require evidence of live contention or write-amplification, not just theoretical concern.
   - Why: current storage evidence does not justify preemptive churn.

### What should remain advisory, not requirement-level

- unifying live/history rendering paths
- changing cache commit granularity
- altering backoff parameters
- route/helper refactors for elegance alone

These are good candidate actions only if a slice proves concrete value.

## Slice Boundaries Suggested for the Roadmap Planner

### Slice A — Runtime Baseline & Failure-Visibility Audit

Goal:
- instrument or benchmark the enrichment path end-to-end
- explicitly audit polling/error/eviction/history-save failure states
- decide whether runtime optimization or failure-surface hardening is the first shipped outcome

Why first:
- all later optimization claims depend on trustworthy runtime evidence

### Slice B — Frontend Result-Application Consolidation

Goal:
- extract shared live/history result-application logic
- preserve current UI behavior while shrinking duplicated coordination logic

Why second:
- clear seam, bounded blast radius, directly improves future change velocity

### Slice C — Verification Loop Optimization

Goal:
- trim or rebalance slow proof paths
- ensure no accidental real sleeps/network-like waits leak into full-suite runs
- define a fast-path verification contract for future milestones

Why near-term:
- immediately improves future building, even if app runtime is already near diminishing returns

### Slice D — Persistence/Route Hotpath Follow-up (only if Slice A proves it)

Goal:
- address any measured cache/history contention or serialization costs
- otherwise explicitly leave storage alone

Why later:
- current evidence does not justify leading with this

## Risks / Unknowns

- The biggest real bottleneck may simply be upstream provider latency/backoff, not local code inefficiency.
- If so, the best next work may be better analyst-facing failure/progress states and better developer proof loops, not deeper backend churn.
- The polling contract currently hides too much failure detail, which can produce misleading user experience and misleading optimization conclusions.
- The pipeline cost rises noticeably with large repeated text; if analysts regularly paste very large blobs, extraction latency may deserve targeted measurement later.

## Skill Discovery

### Already-installed skills directly relevant here

- `code-optimizer` — useful for deeper anti-pattern/performance sweeps
- `debug-like-expert` — useful if runtime/failure-mode investigation turns ambiguous
- `observability` — directly relevant if the milestone decides failure visibility is part of optimization
- `test` / `verify-before-complete` — relevant for proof-loop work

### Promising not-yet-installed skills

No install recommended automatically, but these looked relevant from `npx skills find`:

- Flask
  - `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`
  - `npx skills add jezweb/claude-skills@flask`
- SQLite
  - `npx skills add martinholovsky/claude-skills-generator@sqlite-database-expert`
- TypeScript
  - `npx skills add sickn33/antigravity-awesome-skills@typescript-expert`

Of those, the most directly useful for this milestone appear to be the **Flask** and **SQLite** options; TypeScript is less urgent because the existing frontend code is already relatively small and structured.

## Recommended Next-Work Decision Surface

### Do now

- prove runtime cost and failure visibility in the live enrichment path
- verify whether full-suite proof cost is the bigger practical drag than app runtime

### Do next

- consolidate frontend live/history result application if runtime baseline says architecture is mostly sound
- tighten failure-state UX/API semantics around polling/job lifecycle

### Later

- persistence tuning only if measured contention appears
- deeper extraction/pipeline optimization only if large-input use is common and measured as user-visible

### Leave alone unless disproven

- app factory / singleton store pattern
- provider registry boundary
- BaseHTTPAdapter consolidation
- WAL-mode SQLite approach
- esbuild/tailwind/tsc build pipeline

## Bottom Line

The codebase does **not** currently read like a candidate for a rewrite-oriented optimization milestone. It reads like a mature codebase where the next value comes from proving the live runtime seam, hardening failure visibility, and reducing the coordination/test friction that future work will keep paying.

That means the roadmap should start with **evidence capture and seam hardening**, not speculative cleanup.
