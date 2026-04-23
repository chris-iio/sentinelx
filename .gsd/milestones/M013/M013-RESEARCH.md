# M013 Research — SentinelX optimization-audit milestone

## Executive summary

M013 should start by proving the audit loop itself, not by picking a subsystem and immediately rewriting it. SentinelX already has strong optimization history and a fairly deliberate architecture, so the biggest risk is **optimization theater**: spending time churning seams that are already intentionally shaped, especially around concurrency, WAL-backed persistence, and live/history rendering parity.

The codebase already contains the right structural seams for a full-stack optimization pass:

- `app/enrichment/orchestrator.py` is the central runtime seam for concurrency, caching, retry/backoff, and in-memory job status.
- `app/routes/_helpers.py` is the request/status bridge that turns orchestrator state into poller-visible JSON and owns helper-level history-save diagnostics.
- `app/cache/store.py` and `app/enrichment/history_store.py` are persistent SQLite WAL stores with explicit busy-timeout/cache pragmas and single long-lived connections.
- `app/static/src/ts/modules/enrichment.ts`, `result-application.ts`, `history.ts`, and `main.ts` already separate live polling, shared result application, history replay, and surface ownership.
- The verification floor is unusually strong for this kind of work: `make verify-fast`, `make verify-deep`, deterministic mocked-online E2E fixtures, and targeted concurrency/backoff tests already exist.

That means the first slice should create a **repeatable measurement + ranking workflow** and run one baseline pass across these seams. The planner should treat workflow assets and measured findings as the backbone of the milestone, with code fixes following only where the evidence is strong.

## Existing architecture that matters

### 1. Runtime/provider seam is already centralized and intentionally shaped

`app/enrichment/orchestrator.py` is the most important optimization seam in the repo.

What is already there:

- Per-provider semaphore limiting for key-required providers.
- Uncapped zero-auth providers by design.
- 429-aware backoff with jitter.
- Retry behavior separated from semaphore holding so sleeping threads do not monopolize provider slots.
- Cache lookup + store inside the same orchestrated attempt path.
- LRU-like in-memory job retention plus terminal tombstones for evicted jobs.
- A bounded `max_workers` thread pool per enrichment job.

This is not “messy code waiting for cleanup”; it is a consciously tuned subsystem with a lot of correctness encoded in it. The test suite around it is large and specific (`tests/test_orchestrator.py` alone is ~875 lines and covers concurrency caps, backoff growth, semaphore release during backoff, cache behavior, job failure, and eviction semantics).

**Implication for planning:** orchestrator work is high-value but high-regression-risk. The first runtime slice should measure and rank behavior before attempting structural simplification. Low-regret wins here are more likely to be measurement, visibility, and narrow hot-path reductions than architecture replacement.

### 2. Request/status flow is split between route entrypoints and a shared state helper

`app/routes/analysis.py` and `app/routes/api.py` are intentionally thin. The real coupling lives in `app/routes/_helpers.py`, which currently owns:

- orchestrator registry lifecycle
- bounded helper-level job eviction
- terminal payload normalization
- `next_since` cursor continuity
- history-save attempt/outcome diagnostics
- background submission via a shared `_enrichment_pool`

This helper is substantial (~355 lines) and is a real optimization/reasoning seam because it sits between Flask request flow, async job launch, persistence, and frontend polling expectations.

Two things matter here:

1. There are **two levels of bounded state retention**: helper-level orchestrator registry and orchestrator-level job state.
2. Polling semantics are now part of a stable contract: terminal 404s still carry structured payloads, and `next_since` continuity is explicit.

**Implication for planning:** request-flow work should focus on hot-path reasoning, state ownership clarity, and failure visibility. It should not casually merge or flatten these mechanisms without proof.

### 3. SQLite persistence is deliberate, not accidental

Both `app/cache/store.py` and `app/enrichment/history_store.py` use the same pattern:

- one persistent SQLite connection
- `check_same_thread=False`
- `threading.Lock` around writes / DB operations
- `PRAGMA journal_mode=WAL`
- `PRAGMA synchronous=NORMAL`
- `PRAGMA busy_timeout=5000`
- page cache and temp-store tuning

This exactly matches the M012 keep-decision described in project context: the repo already decided not to rewrite this until measurement proves contention or write-path pain.

The stores also serve different latency/value roles:

- `CacheStore` is on the enrichment hot path.
- `HistoryStore` is post-enrichment durability and reload support.

**Implication for planning:** persistence should be its own slice or sub-slice, but the likely first deliverable is a measurement/reporting pass, not a store redesign. The milestone should assume “leave alone” is a valid outcome for both stores unless measured contention appears.

### 4. Frontend live/history parity is already modularized

The frontend is not one giant results script anymore.

Current structure:

- `app/static/src/ts/modules/enrichment.ts` owns polling interval, terminal-state handling, warnings, and debounced live flushes.
- `app/static/src/ts/modules/result-application.ts` owns shared stateful result application into cards/slots.
- `app/static/src/ts/modules/history.ts` replays stored results through the same rendering path.
- `app/static/src/ts/main.ts` resolves the results-surface owner and ensures only the right runtime initializes.
- `app/static/src/ts/modules/row-factory.ts` is now the largest UI rendering seam (~568 lines), concentrating DOM construction and provider-specific display shaping.

Important live-stack contracts already exist:

- `data-results-owner` / owner resolution controls whether the page is live, history, or static.
- `next_since` is the transport contract for incremental polls.
- terminal `unknown` / `evicted` / `job_failed` states have explicit analyst-visible handling.

The frontend unit coverage around this is significant (~57 tests across the main live/history modules), and E2E coverage is large (~113 tests across browser flows).

**Implication for planning:** frontend optimization should target measured DOM/render churn, batching behavior, and provider-row application cost. It should reuse the shared application seam rather than reopening the live/history split.

### 5. Verification is already a first-class subsystem

This repo is unusually ready for an optimization milestone because the proof lanes already exist:

- `make verify-fast` = non-E2E pytest + Vitest + TypeScript + production build
- `make verify-deep` = browser E2E
- `make verify` = full combined lane
- `tests/e2e/conftest.py` provides deterministic mocked-online job IDs and route mocking so browser tests can verify live results UX without firing real background enrichment

This means M013 does **not** need to invent a proof culture from scratch. It should build on this by adding a measurement/reporting workflow alongside the existing verification lanes.

## What should be proven first

The first proof should be:

1. **Can we run a whole-repo optimization pass repeatably?**
2. **Can we collect ranked findings with evidence rather than taste?**
3. **Can we separate “ship now” from “leave alone” without weakening behavior/security?**

Concretely, the first slice should establish:

- the audit checklist / workflow
- baseline commands and where outputs live
- what counts as measurement vs code-path reasoning
- a ranked findings format (`do now`, `do next`, `later`, `leave alone`)
- the exact full-stack proof surfaces to revisit after any shipped fix

Without that, every later slice risks becoming ad hoc cleanup.

## Existing patterns to reuse, not replace

### Reuse these patterns

- `BaseHTTPAdapter` + `safe_request()` as the canonical HTTP provider path. Thirteen adapters inherit the base HTTP pattern; only three are non-HTTP lookup styles. This is a strength.
- `ProviderRegistry` + `build_registry()` as the single provider registration/config surface.
- shared route helper logic in `app/routes/_helpers.py` for poll/status/history behavior.
- WAL-backed persistent store pattern in both SQLite stores.
- live/history shared render path via `result-application.ts`.
- deterministic mocked-online E2E seam in `tests/e2e/conftest.py`.
- `make verify-fast` / `verify-deep` split as the default proof vocabulary.

### Avoid premature rewrites of

- the orchestrator concurrency model
- WAL persistence design
- the live/history render split
- provider adapter inheritance shape
- the current verification lane structure

Those are all places where the codebase shows prior judgment and proof, not obvious neglect.

## Boundary contracts that matter

These should shape slice boundaries and review criteria.

### Provider/runtime contract

- Provider selection comes from `registry.configured()` and `supported_types`.
- Keyed providers get semaphore caps; zero-auth providers do not.
- HTTP adapters route through `safe_request()` with SSRF allowlist, timeout, no redirects, streaming, and body-size cap.
- 429 semantics are intentionally special-cased.

### Polling/status contract

- `results`, `done`, `total`, `complete`, and `next_since` must stay truthful.
- Terminal failures are structured and analyst-visible.
- `unknown` and `evicted` are not interchangeable.

### Persistence contract

- Cache/history are durable SQLite WAL stores, not ephemeral request-local state.
- History save failures are visible via diagnostics but should not break enrichment completion.
- Any optimization must preserve history reload correctness and cache continuity.

### Frontend ownership contract

- A results page has one runtime owner: `live`, `history`, or `static`.
- History pages must replay results, not poll.
- Live pages must stop polling cleanly on terminal conditions.

These are not implementation details anymore; they are continuity constraints.

## Risks and failure modes that should shape slice ordering

1. **False-positive optimization work**
   - Because the codebase has already been optimized repeatedly, the next mistakes are likely to come from chasing tidy-looking refactors instead of measured pain.

2. **Breaking seam behavior while “simplifying”**
   - The orchestrator and route helper layers encode concurrency, retry, eviction, and terminal-state semantics. Simplification without proof is risky.

3. **Reopening live/history divergence**
   - The frontend now has a deliberate shared application seam. UI work should preserve parity instead of reintroducing separate logic.

4. **Touching SQLite because it looks old-school, not because it is slow**
   - Current WAL + long-lived connection choices are intentional and should only move with evidence.

5. **Weakening deterministic proof loops**
   - The mocked-online browser seam is part of what makes this repo auditable. Optimizing away that determinism would make future work worse.

## Natural slice boundaries for the roadmap planner

### Slice 1 — Workflow + baseline audit pass

Goal: create the reusable M013 optimization workflow, baseline measurements, and the ranked findings artifact format.

Why first:

- everything downstream depends on the proof model
- it prevents premature subsystem rewrites
- it produces the ranked backlog that later slices can retire

Likely outputs:

- audit checklist / commands
- measurement capture/report template
- first ranked findings document
- explicit list of “leave alone” seams

### Slice 2 — Runtime/provider seam audit and shipped low-regret fixes

Goal: examine `orchestrator.py`, provider dispatch, retry/backoff behavior, cache interaction, and request overhead.

Why second:

- central runtime seam
- likely highest leverage if there is hidden waste
- already very well tested, so narrow fixes are ship-friendly once evidence exists

### Slice 3 — Persistence + request-flow seam audit and shipped low-regret fixes

Goal: evaluate `CacheStore`, `HistoryStore`, and `app/routes/_helpers.py` for contention, hot-path overhead, or awkward state ownership.

Why third:

- directly covers SQLite + Flask request flow from milestone acceptance
- needs baseline and likely targeted instrumentation first
- may end in a keep decision, which is still valuable

### Slice 4 — Frontend polling/render coordination audit and shipped low-regret fixes

Goal: measure and improve analyst-visible polling/render cost while preserving live/history parity.

Why after backend/persistence baseline:

- frontend work depends on knowing whether transport churn or DOM churn is the actual bottleneck
- shared render path is already in place, so this slice can stay narrow and evidence-driven

### Slice 5 — Full-pass closeout and final proof

Goal: rerun the audit workflow end-to-end, validate shipped fixes, publish the ranked outcomes, and record what remains deferred.

Why separate:

- milestone completion requires one full proven pass, not just per-slice local success
- this slice can close the loop on “workflow plus shipped fixes” as a coherent deliverable

## Requirements audit

### Table-stakes continuity requirements

From the milestone context, these look non-negotiable for M013 work:

- `R008` — preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity
- `R009` — preserve CSP/CSRF/SSRF/host validation/DOM safety
- `R010` — preserve or improve polling/render efficiency
- `R014` — preserve per-provider concurrency behavior unless evidence proves better
- `R015` — preserve 429 backoff unless evidence proves better
- `R018` — preserve semaphore/backoff/snapshot correctness unless evidence proves otherwise
- `R019` — preserve cursor-based polling efficiency unless evidence proves otherwise
- `R020` — preserve persistent HTTP session behavior where justified
- `R022` — preserve WAL-mode cache/history behavior unless evidence supports change
- `R040` — keep strong verification continuity while refactoring and optimizing

These are the guardrails that keep the milestone honest.

### Candidate requirements worth considering

These should remain advisory unless the planner wants to formalize them.

1. **Measured-finding evidence requirement**
   - Candidate requirement: any shipped optimization change must cite either before/after measurement or explicit code-path reasoning when direct measurement is impractical.
   - Why: the milestone’s main failure mode is unproven cleanup disguised as optimization.

2. **Deterministic verification continuity for live-stack changes**
   - Candidate requirement: changes touching polling/render/live results must preserve deterministic mocked-online browser proof.
   - Why: this is already a crucial launchability/proof asset, but it is not framed explicitly in the requirement list excerpt.

3. **Ranked audit artifact requirement**
   - Candidate requirement: the workflow must emit a durable ranked artifact with `do now / do next / later / leave alone` buckets.
   - Why: this is central to the milestone outcome and easy to validate.

### Things that are clearly out of scope

- new infrastructure for distributed metrics/logging
- broad cross-repo packaging/productization
- speculative persistence rewrites
- redesigning extraction/classification pipeline without evidence that it is part of the current waste
- style-only refactors done under the optimization banner

## Skill discovery

No already-installed project skill directly targets the core stack combination here (Flask + SQLite + Playwright-based browser proof) closely enough to change the plan.

Promising external skills discovered:

- **Flask** — `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`
  - Highest install count among the Flask-specific results and directly relevant to request-flow review.
- **SQLite** — `npx skills add martinholovsky/claude-skills-generator@sqlite-database-expert`
  - Strongest install signal among SQLite-specific options; relevant if the persistence slice uncovers real query/locking work.
- **Playwright** — `npx skills add currents-dev/playwright-best-practices-skill@playwright-best-practices`
  - Very high install count and directly relevant to preserving/improving deterministic browser proof.

These are promising, but none are necessary to start M013.

## Recommended planning stance

The planner should bias M013 toward:

- **baseline first**
- **narrow shipped fixes second**
- **explicit keep decisions as a valid outcome**
- **full-stack verification at the end**

The main strategic insight is that SentinelX does **not** look under-architected. It looks like a codebase where the next useful work is careful ranking, careful proof, and only then carefully chosen fixes.

That should shape the roadmap: do not decompose M013 into generic subsystem cleanup. Decompose it into a reusable audit workflow plus evidence-backed retirement of the highest-confidence findings.
