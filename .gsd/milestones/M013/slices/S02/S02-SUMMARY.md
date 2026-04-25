---
id: S02
parent: M013
milestone: M013
provides:
  - A verified job-scoped runtime/provider diagnostics surface on the orchestrator that downstream slices can inspect without widening the analyst-visible status contract.
  - A refreshed audit artifact that records the runtime/provider dispatch path and backoff/session behavior as explicit measured keep-decisions.
  - Fresh fast and deep proof that preserves per-provider caps, 429 backoff, cache-marker correctness, snapshot safety, and adapter-owned session reuse on the final slice state.
requires:
  - slice: S01
    provides: Reusable M013 audit workflow, ranked artifact format, and rerun contract that S02 reused to publish runtime/provider evidence and keep-decisions.
affects:
  - S03
  - S04
key_files:
  - app/enrichment/orchestrator.py
  - tools/optimization_audit.py
  - tests/test_orchestrator.py
  - tests/test_optimization_audit.py
  - .gsd/milestones/M013/M013-AUDIT.md
  - tests/test_http_safety.py
  - tests/test_base_adapter.py
key_decisions:
  - Kept runtime/provider diagnostics job-local on `EnrichmentOrchestrator` and exposed them through `get_diagnostics()` instead of widening `get_status()` or storing mutable counters on shared adapters.
  - Treated `.gsd/milestones/M013/M013-AUDIT.md` as generated output and refreshed it from `tools/optimization_audit.py` rather than hand-editing runtime/provider findings.
  - Made the runtime/provider dispatch path an explicit measured keep-decision because the deterministic capture’s `1/5 (20%)` cache-hit ratio did not justify a new pre-dispatch fast path ahead of the worker/semaphore boundary.
patterns_established:
  - Keep runtime/provider observability aggregate and job-local: bounded counters/timers on the orchestrator are safe to snapshot; mutable metrics on shared adapters are not.
  - Use the audit artifact as the durable decision surface for optimization work, including explicit `leave alone` rows when evidence does not justify code churn.
  - Gate runtime optimizations on measured workload shape, not aesthetic dislike of current dispatch flow.
observability_surfaces:
  - `EnrichmentOrchestrator.get_diagnostics()` is the bounded health surface for provider mix, cache-hit ratio, retries, latency, and provider/error counts without exposing raw provider payloads.
  - The `runtime-provider-diagnostics` row in `.gsd/milestones/M013/M013-AUDIT.md` is the durable slice-level inspection surface for the measured keep-decision.
  - Focused orchestrator/audit tests act as the failure signal for missing diagnostics keys, malformed summaries, or drift in the keep-decision wording and capture contract.
drill_down_paths:
  - .gsd/milestones/M013/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-24T02:56:05.769Z
blocker_discovered: false
---

# S02: S02

**Verified the runtime/provider seam, refreshed M013’s audit with bounded orchestrator diagnostics, and codified a measured keep-decision instead of shipping speculative dispatch-path churn.**

## What Happened

S02 closed the runtime/provider seam by confirming that the planned bounded diagnostics and audit capture were already present locally, then refreshing the durable evidence around them instead of inventing a change for its own sake. Across T01 and T02, the slice verified that `EnrichmentOrchestrator` owns job-scoped runtime/provider diagnostics under the existing lock, keeps shared adapters stateless with respect to metrics, exposes snapshot-safe inspection through `get_diagnostics()`, and feeds a deterministic `runtime-provider-diagnostics` capture into `tools/optimization_audit.py` without widening the analyst-visible status contract.

T03 then used that evidence to make the slice’s explicit ship/keep decision. The refreshed runtime capture reported provider mix `CacheAlpha:2d/0e, RateLimitBeta:2d/1e`, `dispatch=4`, `attempts=5`, `cache-hit ratio 1/5 (20%)`, `retries=1 (429=1)`, `errors=1`, and `latency total=2.25s max=1.00s`. Because cache hits were not dominant and the orchestrator already short-circuits them inside `_single_attempt()`, the slice did not add a new pre-dispatch cache short-circuit ahead of the worker/semaphore boundary. Instead, `.gsd/milestones/M013/M013-AUDIT.md` now records the runtime/provider dispatch path, plus the existing backoff/session contract, as explicit measured `leave alone` decisions.

This makes the runtime/provider seam more trustworthy for downstream work. The durable audit now tells future slices what the health signal is, what failure looks like, and what to do next: use the bounded diagnostics surface and refresh the audit before changing concurrency, backoff, session reuse, or cache-dispatch behavior; if diagnostics go missing or drift, the focused orchestrator/audit tests and audit capture fail loudly; if a future slice wants to revisit this seam, it should first produce a more cache-hit-heavy or provider-pain-heavy capture. The highest-confidence next work therefore remains S03’s request/status optimization, while S04 can still treat frontend coordinator caching as the next deferred ship target.

## Verification

Fresh slice-close verification was run after the final repository state used for completion:

- `pytest tests/test_orchestrator.py tests/test_http_safety.py tests/test_base_adapter.py tests/test_optimization_audit.py -q` ✅ passed with `74 passed in 0.57s`, proving the orchestrator diagnostics contract, HTTP/session safety, backoff invariants, and audit wording stayed green together.
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` ✅ regenerated the durable audit artifact from the same final code state. The refreshed `runtime-provider-diagnostics` capture reports provider mix `CacheAlpha:2d/0e, RateLimitBeta:2d/1e`, `dispatch=4`, `attempts=5`, `cache-hit ratio 1/5 (20%)`, `retries=1 (429=1)`, `errors=1`, and `latency total=2.25s max=1.00s`.
- `make verify-fast` ✅ passed end-to-end: `965 passed, 113 deselected in 3.71s`, `78` Vitest tests passed, `npx tsc --noEmit` passed, and the production build completed with `app/static/dist/main.js 29.5kb`.
- `make verify-deep` ✅ passed with `113 passed in 38.28s`, preserving the mocked-online browser proof for live enrichment orchestration and analyst-visible continuity.

Operational readiness for this slice is bounded and explicit: the health signal is `EnrichmentOrchestrator.get_diagnostics()` plus the audit artifact’s runtime/provider capture row; the failure signal is missing/malformed diagnostics data or any regression in the focused orchestrator/audit suites; the recovery path is to refresh `.gsd/milestones/M013/M013-AUDIT.md` and rerun the same focused pytest + `make verify-fast` + `make verify-deep` lanes before accepting any further runtime/provider change.

## Requirements Advanced

- R014 — The refreshed runtime/provider audit now records per-provider concurrency as an explicit measured keep-decision, so later slices must preserve provider caps unless a stronger capture justifies change.
- R015 — S02 preserved 429 backoff behavior as a measured keep-decision and re-proved it through focused orchestrator coverage plus full fast/deep verification.
- R018 — The slice kept semaphore/backoff scope, snapshot safety, and locked cache-marker behavior attached to the runtime/provider seam and the audit’s continuity notes.
- R020 — Persistent adapter-owned session reuse remained protected as part of the explicit runtime/provider keep-decision rather than being reopened without evidence.

## Requirements Validated

- R040 — Fresh slice-close proof passed on the final state: `pytest tests/test_orchestrator.py tests/test_http_safety.py tests/test_base_adapter.py tests/test_optimization_audit.py -q`, `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`, `make verify-fast`, and `make verify-deep` all exited successfully.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

The planned source work was largely already present on the local branch before slice close. Instead of adding redundant orchestrator changes, S02 spent its closing pass verifying the existing diagnostics/capture implementation, refreshing the durable audit artifact, and converting the runtime/provider dispatch idea into an explicit measured keep-decision.

## Known Limitations

The runtime/provider evidence is intentionally synthetic and local. S02 does not add sustained live-provider profiling or a production-like cache-hit-heavy workload, so future runtime/provider changes remain measurement-gated until a stronger capture justifies reopening the seam.

## Follow-ups

S03 should start from the audit’s `do now` request/status row and remove the per-poll full results snapshot before `since` slicing. Any future runtime/provider optimization should consume the existing diagnostics surface first and only revisit pre-dispatch cache short-circuiting if a new capture shows cache hits dominating enough to outweigh the regression surface.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — Provides the job-scoped runtime/provider diagnostics surface whose bounded counters and snapshot-safe accessor were re-verified during slice close.
- `tools/optimization_audit.py` — Generates the deterministic runtime/provider capture and the explicit measured keep-decision wording used in the refreshed audit artifact.
- `tests/test_orchestrator.py` — Pins cache-hit accounting, retry/backoff counters, latency aggregation, malformed-state coercion, and snapshot-stability invariants for the runtime seam.
- `tests/test_optimization_audit.py` — Pins the runtime/provider capture summary and the keep-decision wording so later slices cannot drift the audit contract silently.
- `.gsd/milestones/M013/M013-AUDIT.md` — Durable ranked artifact refreshed at slice close with the current runtime/provider measurement capture and explicit leave-alone decisions.
- `tests/test_http_safety.py` — Re-verified adapter HTTP safety invariants as part of the slice-close regression lane.
- `tests/test_base_adapter.py` — Re-verified base adapter/session contract continuity as part of the slice-close regression lane.
