# M013 Optimization Audit — SentinelX

- Mode: `baseline`
- Generated at: `2026-04-24 02:29:27 UTC`
- Repo root: `/home/chris/projects/sentinelx`
- Output path: `.gsd/milestones/M013/M013-AUDIT.md`

## Workflow contract

- A finding must be backed by **measurement when practical**. If direct measurement is awkward or too invasive, the finding must cite **explicit code-path reasoning** instead of taste-based cleanup language.
- Every finding must land in exactly one ranked bucket: `do now`, `do next`, `later`, or `leave alone`.
- Every finding must call out the continuity guardrails it could endanger and the verification lanes that must be rerun before claiming the optimization is safe.
- `leave alone` is a valid outcome when current architecture is already intentional and the evidence does not justify churn.

## Command surface

| Entry point | Command | Purpose |
| --- | --- | --- |
| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |
| Template scaffold | `python3 tools/optimization_audit.py --mode template --output .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md` | Create a reusable milestone-local ranked artifact template. |
| Working baseline artifact | `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` | Create/update the current audit document used by later optimization slices. |
| Convenience targets | `make audit-m013-template` / `make audit-m013` | Repo-native wrappers around the same workflow for contributors. |

## Verification lanes

| Lane | Command | Use when |
| --- | --- | --- |
| verify-fast | `make verify-fast` | Default rerun lane for backend/frontend logic, build/test plumbing, and any finding that does not change mocked-online browser behavior. |
| verify-deep | `make verify-deep` | Required whenever a change touches live enrichment orchestration, polling/status flow, results-page DOM/state, or mocked-online browser seams. |
| verify | `make verify` | Full pre-handoff lane when downstream slices need the unambiguous repo-wide proof command. |

## Verified rerun checklist

| Step | Proof surface | Command | Required when | Expected durable evidence |
| --- | --- | --- | --- | --- |
| 1 | Workflow runner + ranked artifact refresh | `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` | Every optimization slice before handoff. | Updated M013 audit artifact with current ranked buckets, seam notes, and continuity guardrails. |
| 2 | Fast local regression lane | `make verify-fast` | Every shipped optimization, including keep-decisions that changed code or build/test plumbing. | Fresh command capture or task summary evidence proving unit/integration/frontend/build checks stayed green. |
| 3 | Deterministic mocked-online browser proof | `make verify-deep` | Any change touching live enrichment orchestration, polling/status flow, shared result application, or analyst-visible DOM/state. | Fresh command capture or task summary evidence proving the mocked-online browser seam still passes end-to-end. |
| 4 | Final comparison + continuity note refresh | compare the updated ranked row(s), rerun lanes, and continuity notes in `.gsd/milestones/M013/M013-AUDIT.md` | Every optimization slice after verification completes. | The artifact records whether the change shipped, moved buckets, stayed deferred, or remained an explicit leave-alone decision. |

## Continuity guardrails

| Requirement | Continuity guardrail |
| --- | --- |
| R008 | Preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity. |
| R009 | Preserve CSP, CSRF, SSRF allowlist, host validation, and DOM-safety constraints. |
| R010 | Preserve or improve polling/render efficiency. |
| R014 | Preserve per-provider concurrency behavior unless evidence proves a better approach. |
| R015 | Preserve 429 backoff behavior unless evidence proves a better approach. |
| R018 | Preserve semaphore/backoff and snapshot correctness unless evidence proves otherwise. |
| R019 | Preserve cursor-based polling efficiency unless evidence proves otherwise. |
| R020 | Preserve persistent HTTP session behavior where still justified. |
| R022 | Preserve WAL-mode cache/history store behavior unless evidence supports change. |
| R040 | Keep strong verification continuity while refactoring and optimizing. |

## Measurement captures

| Capture | Command | Exit | Duration (ms) | Summary |
| --- | --- | ---: | ---: | --- |
| runtime-provider-diagnostics | `internal benchmark: EnrichmentOrchestrator synthetic runtime/provider diagnostics` | 0 | 70 | provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e; dispatch=4; attempts=5; cache-hit ratio 1/5 (20%); retries=1 (429=1); errors=1; latency total=2.25s max=1.00s. |
| status-snapshot-scaling | `internal benchmark: EnrichmentOrchestrator.get_status() snapshot scaling` | 0 | 1 | 400 `get_status()` calls: 200 results 0.29ms vs 5000 results 1.43ms (4.9x slower), confirming the current per-poll full-list snapshot cost before `since` slicing. |
| cache-store-tempdb | `internal benchmark: CacheStore temp WAL put/get loop` | 0 | 17 | Temp WAL cache DB: 250 puts in 3.14ms, 250 TTL reads in 1.08ms, 250 hits, 250 retained rows. |
| history-store-tempdb | `internal benchmark: HistoryStore temp WAL save/list/load loop` | 0 | 20 | Temp WAL history DB: 180 saves in 2.98ms, list_recent(20) in 0.04ms, single load in 0.02ms, latest total_count=1, recent rows=20. |

## Seam checklist

### runtime/provider

- Continuity focus: Orchestrator concurrency, cache interaction, retry/backoff behavior, and provider dispatch cost.
- Audit prompt 1: What work is measured here, and what hot-path reasoning is still required?
- Audit prompt 2: Which guardrails and rerun lanes must stay attached if we change this seam?

### request/status

- Continuity focus: Flask route/helper status flow, next_since continuity, and history-save diagnostics.
- Audit prompt 1: What request-path work is actually hot versus only structurally central?
- Audit prompt 2: If a finding changes analyst-visible status behavior, which proof lane catches it?

### persistence

- Continuity focus: SQLite WAL cache/history store access, locking, query shape, and post-enrichment durability.
- Audit prompt 1: Is there measured contention, or should this seam remain a leave-alone decision?
- Audit prompt 2: What evidence would justify revisiting long-lived WAL-backed connections?

### frontend/render

- Continuity focus: Polling cadence, shared live/history result application, and DOM/render churn.
- Audit prompt 1: What analyst-visible work is actually happening per poll or per render flush?
- Audit prompt 2: Does the finding preserve live/history parity and deterministic mocked-online proof?

## Ranked finding schema

Use the same table shape in every bucket. Required fields per row:

- **Finding** — one concrete optimization or keep-decision.
- **Seam** — `runtime/provider`, `request/status`, `persistence`, or `frontend/render`.
- **Evidence kind** — `measurement` or `code-path reasoning`.
- **Evidence summary** — cite the measurement, command capture, or the exact path reasoning that justifies the rank.
- **Continuity guardrails** — list the requirement IDs that must remain protected.
- **Rerun lanes** — at minimum one of `make verify-fast`, `make verify-deep`, or `make verify`.
- **Continuity notes** — state what behavior must remain true after the future change ships, or why the seam should stay untouched.

## Baseline stance

- Highest-confidence near-term work: make the status path truly incremental so the backend no longer snapshots every retained result on each poll.
- The runtime/provider seam now has a deterministic local capture; if it changes at all, the only justified ship target is a narrow cache-hit-heavy dispatch reduction ahead of the worker/semaphore path.
- Highest-confidence explicit keep-decision: leave the WAL-backed cache/history stores and the provider backoff/session contract alone until measured contention or provider pain shows up.
- Frontend work remains important, but it should follow the status-path fix because the shared coordinator has a broader proof burden and depends on the same poll contract.

## Ranked findings

### do now

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Make `/enrichment/status` cursor-native end-to-end by avoiding full results-list snapshots before slicing `since`. | request/status | measurement + code-path reasoning | Internal capture `status-snapshot-scaling` shows `get_status()` cost rises with total retained results. `app/routes/_helpers.py::_get_enrichment_status()` currently calls `orchestrator.get_status()` first, and `app/enrichment/orchestrator.py::get_status()` clones the entire `results` list before the helper slices `results[since:]`, so every poll still pays an O(total-results) copy even when the frontend only needs the delta. | R008, R010, R018, R019, R040 | `make verify-fast`, `make verify-deep` | Preserve `next_since`, terminal failure semantics, progress/warning banners, and analyst-visible completion while shifting backend polling to a truly incremental read path. |

### do next

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Cache IOC card/slot handles inside the shared result-application coordinator before chasing deeper render changes. | frontend/render | code-path reasoning | `app/static/src/ts/modules/result-application.ts` performs `findCardForIoc()` and `.querySelector('.enrichment-slot')` per incoming result, then `updateDashboardCounts()` scans every `.ioc-card` and `sortCardsBySeverity()` reorders the whole grid after each flush. The shared coordinator is the correct seam because both live polling and history replay depend on it. | R008, R009, R010, R019, R040 | `make verify-fast`, `make verify-deep` | Must preserve live/history parity, textContent-only DOM construction, expand toggles, export/copy/detail-link wiring, and deterministic mocked-online browser proof. |
| If the runtime/provider seam changes at all, limit it to a cache-hit-heavy dispatch reduction before touching semaphores. | runtime/provider | measurement + code-path reasoning | Internal capture `runtime-provider-diagnostics` reports provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e; dispatch=4, attempts=5, cache-hit ratio 1/5 (20%), retries=1 (429=1), and latency total=2.25s max=1.00s. The capture proves the new diagnostics surface can quantify provider mix and retry cost locally, so the only justified ship target is skipping known-cache work before the worker/semaphore path rather than reopening concurrency policy. | R014, R015, R018, R020, R040 | `make verify-fast`, `make verify-deep` | Preserve per-provider caps, cache-hit markers, retry/backoff semantics, and adapter-owned session reuse; any shipped change must stay narrower than a thread-pool or session-policy rewrite. |

### later

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |

### leave alone

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Keep WAL-backed cache/history stores and persistent connections unchanged until contention evidence appears. | persistence | measurement + code-path reasoning | Internal temp-DB captures show low-latency cache puts/gets and history saves/loads on the current code, while `app/cache/store.py` and `app/enrichment/history_store.py` already enable WAL, `busy_timeout`, persistent connections, and simple indexed queries. No lock-pressure or write-amplification evidence justified churn in this baseline pass. | R022, R040 | `make verify-fast` | If a later slice sees real writer contention, measure concurrent load first; do not trade away WAL or persistent-connection simplicity speculatively. |
| Keep per-provider backoff/session semantics as explicit measured keep-decisions. | runtime/provider | measurement + code-path reasoning | The same `runtime-provider-diagnostics` capture surfaces retry/rate-limit cost and provider error tallies without widening analyst-visible status, and `tests/test_orchestrator.py` still proves semaphores exclude backoff sleep, cached markers stay locked, and diagnostics snapshots stay stable. That combination makes measurement the additive change while keeping adapter-owned sessions and backoff rules on explicit keep-decision footing until a later slice shows real provider pain. | R014, R015, R018, R020, R040 | `make verify-fast`, `make verify-deep` | Future work should consume the measured diagnostics surface first and only revisit the contract if live evidence shows meaningful provider pain beyond cache-hit-heavy dispatch overhead. |

## Per-seam baseline notes

### runtime/provider

- Boundary: `app/enrichment/orchestrator.py` plus `tests/test_orchestrator.py`.
- Current shape: Dispatch fans out IOC/adaptor pairs through a thread pool, but rate-limited providers are gated by per-provider semaphores and 429 backoff sleeps happen outside the semaphore. Cache hits short-circuit lookup work inside `_single_attempt()`, and tests already prove concurrency, retry, and snapshot invariants.
- Continuity watch: R014, R015, R018, R020, R040 stay attached to any change here.
- Baseline call: Use the new `runtime-provider-diagnostics` capture to decide whether a cache-hit-heavy dispatch reduction is worth shipping; do not rewrite concurrency policy, backoff scope, or session ownership on aesthetics.

### request/status

- Boundary: `app/routes/_helpers.py`, `app/routes/analysis.py`, and helper/status regression coverage.
- Current shape: The helper owns a bounded module-level orchestrator registry, a shared enrichment thread pool, terminal tombstones, and history-save diagnostics. The frontend's `since` cursor contract is preserved, but the helper still asks the orchestrator for a full status snapshot before slicing incremental results.
- Continuity watch: R008, R010, R018, R019, R040 are the key guardrails.
- Baseline call: This is the highest-confidence near-term optimization seam because it sits on every poll request and already has a clear correctness contract to preserve.

### persistence

- Boundary: `app/cache/store.py`, `app/enrichment/history_store.py`, and their focused unit suites.
- Current shape: Both stores use persistent SQLite connections, WAL mode, `busy_timeout`, and simple indexed access patterns. Writes commit per operation, which is conservative but currently uncomplicated and well-covered by tests.
- Continuity watch: R022 and R040 must remain explicit.
- Baseline call: Keep the current store design until a later slice captures real contention, lock waits, or write-amplification evidence under concurrent load.

### frontend/render

- Boundary: `app/static/src/ts/modules/enrichment.ts`, `result-application.ts`, `row-factory.ts`, and mocked-online browser proof.
- Current shape: The live polling loop runs every 750ms, batches DOM flushes with a 100ms timer, and routes both live and history application through one coordinator. The same shared path still performs repeated card/slot lookups, full dashboard recounts, and grid reorders after flushes.
- Continuity watch: R008, R009, R010, R019, R040 remain coupled to any render optimization.
- Baseline call: Optimize this seam only after the request/status cursor cost lands, because the shared coordinator makes render work worth improving but the current proof burden is high.

## Continuity guardrail coverage

| Requirement | Primary seam(s) in this baseline | Covered by | Continuity notes |
| --- | --- | --- | --- |
| R008 | request/status + frontend/render | Do-now cursor work plus do-next coordinator caching | Keep polling continuity, export/copy/detail-link behavior, and progress visibility intact. |
| R009 | frontend/render | Do-next coordinator/render work | Preserve textContent-only DOM construction, CSP/CSRF assumptions, and host-validation-adjacent safety expectations. |
| R010 | request/status + frontend/render | Do-now cursor work plus do-next render work | Any shipped optimization must reduce or at least not worsen polling/render churn. |
| R014 | runtime/provider | Measured runtime/provider ship target plus explicit keep-decision | Per-provider concurrency remains part of the contract unless a narrow cache-hit optimization proves safe. |
| R015 | runtime/provider | Measured runtime/provider ship target plus explicit keep-decision | 429 backoff stays protected; future changes must prove they do not regress quota safety. |
| R018 | runtime/provider + request/status | Do-now cursor work plus measured runtime/provider evidence | Snapshot correctness, semaphore scope, and cached-marker locking remain non-negotiable. |
| R019 | request/status + frontend/render | Do-now cursor work plus do-next coordinator caching | Keep `since`/`next_since` incremental polling semantics end-to-end. |
| R020 | runtime/provider | Measured runtime/provider ship target plus explicit keep-decision | Persistent adapter-owned sessions stay justified until measured evidence argues otherwise. |
| R022 | persistence | Leave-alone WAL store decision | WAL and persistent connection behavior stay explicit keep-decisions pending contention evidence. |
| R040 | all seams | Every ranked finding | Each future slice must rerun the listed proof lanes before claiming an optimization is safe. |

## Audit notes

- This baseline intentionally makes keep-decisions explicit; `leave alone` rows are part of the evidence set, not filler.
- Re-run this command after each optimization slice so later artifacts can compare the ranked buckets instead of restating assumptions.
- Add explicit `--capture-command` entries when a downstream slice can attach fresh end-to-end timings or verification output to one of these rows.
