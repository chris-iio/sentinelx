---
id: S03
parent: M013
milestone: M013
provides:
  - A verified orchestrator-owned incremental polling path for `/enrichment/status` and `/api/status` that preserves cursor and terminal semantics while avoiding per-poll full-list copies.
  - A refreshed M013 audit artifact that records request/status as shipped work and WAL-backed persistence as an explicit measured keep-decision.
  - Fresh fast/deep regression proof that backend request/status changes did not regress history reload, cache continuity, helper diagnostics, or analyst-visible polling behavior.
requires:
  - slice: S01
    provides: Reusable M013 audit workflow, ranked artifact format, and rerun contract reused to publish the shipped request/status result and the persistence keep-decision.
affects:
  - S04
key_files:
  - app/enrichment/orchestrator.py
  - app/routes/_helpers.py
  - tools/optimization_audit.py
  - tests/test_orchestrator.py
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_optimization_audit.py
  - tests/test_cache_store.py
  - tests/test_history_store.py
  - .gsd/milestones/M013/M013-AUDIT.md
key_decisions:
  - Kept `EnrichmentOrchestrator.get_status()` as the full-snapshot/history contract while using `get_incremental_status()` for the polling hot path.
  - Kept `_get_enrichment_status()` on the incremental accessor while leaving `_run_enrichment_and_save()` on the full-snapshot path so history persistence never has to reconstruct state from deltas.
  - Recorded the request/status path as shipped in the audit and kept WAL-backed cache/history persistence as an explicit measured keep-decision, strengthening proof with deterministic PRAGMA assertions instead of speculative store rewrites.
patterns_established:
  - Split full-history and live-polling reads into separate orchestrator contracts: full snapshots for persistence, incremental tails for hot-path polling.
  - Keep helper-owned terminal tombstones and bounded diagnostics separate from the incremental status payload so contract truthfulness is preserved even when the poll path gets cheaper.
  - Treat measured keep-decisions as durable optimization outcomes and pin them with focused tests and audit wording, not just prose in task notes.
observability_surfaces:
  - Incremental status responses expose the health signal for live polling through `done`, `total`, `complete`, `terminal`, `terminal_reason`, `next_since`, and tail-only `cached_at` markers.
  - `/settings` continues to be the bounded helper-owned aggregate diagnostics surface for history-save behavior; no raw analyst or provider payloads were widened.
  - `.gsd/milestones/M013/M013-AUDIT.md` now acts as the durable inspection surface for the shipped request/status seam and the persistence keep-decision.
  - Focused route/orchestrator/audit/store pytest suites plus `make verify-fast` and `make verify-deep` are the failure signals for this seam.
drill_down_paths:
  - .gsd/milestones/M013/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M013/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M013/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-25T06:41:28.580Z
blocker_discovered: false
---

# S03: S03

**Shipped the cursor-native request/status polling path end-to-end, refreshed the M013 audit to record it as landed work, and re-proved WAL-backed persistence as an explicit keep-decision without regressing analyst-visible status/history behavior.**

## What Happened

S03 closed the Flask/helper ↔ SQLite seam by treating live polling and full-history persistence as two different contracts and keeping both truthful. The shipped backend path now relies on the orchestrator-owned incremental snapshot for `/enrichment/status/<job_id>` and `/api/status/<job_id>`, so pollers read scalar status fields plus only the requested `results[since:]` tail and aligned `cached_at` markers instead of copying the full retained results list on every request. At the same time, `EnrichmentOrchestrator.get_status()` remains the mutation-safe full snapshot used by history persistence and existing full-state callers, and `_run_enrichment_and_save()` stays on that full-snapshot path.

That split preserves the analyst-visible contract while removing the specific hot-path waste S03 set out to fix. Helper-owned terminal tombstones and aggregate history-save diagnostics remain bounded and truthful; `unknown`, helper-level `evicted`, and orchestrator `job_failed` semantics still stay distinct; `next_since`, `complete`, `status`, `terminal`, `terminal_reason`, `error`, and per-row `cached_at` behavior all remain stable from the frontend/API point of view. The TypeScript API contract did not need widening because the shipped route payload shape stayed compatible.

S03 also turned the audit artifact into a truthful record of what is now shipped versus what remains deferred. `.gsd/milestones/M013/M013-AUDIT.md` no longer frames request/status as an unshipped do-now idea; it now records the orchestrator-owned incremental snapshot path as landed work and keeps the WAL-backed cache/history seam as an explicit measured keep-decision. Instead of churning `app/cache/store.py` or `app/enrichment/history_store.py`, the slice strengthened proof with deterministic SQLite PRAGMA assertions showing WAL mode and `busy_timeout` remain enabled on live connections.

For downstream readers, the important pattern is now explicit: use the incremental snapshot for live polling, keep full snapshots for history persistence, and treat measured keep-decisions as first-class outcomes. S04 can therefore focus on the frontend/render seam without reopening backend request/status ambiguity, while any future persistence change must first bring real contention evidence rather than aesthetic concern about SQLite or per-operation commits.

## Verification

Fresh slice-close verification was run after the final repository state used for completion:

- `pytest tests/test_orchestrator.py tests/test_routes.py tests/test_api.py -q` ✅ passed with `94 passed in 0.73s`, proving the orchestrator incremental snapshot contract, helper/API cursor semantics, cached-marker serialization, terminal tombstones, negative-`since` compatibility, and API/HTML parity together.
- `pytest tests/test_optimization_audit.py tests/test_cache_store.py tests/test_history_store.py -q` ✅ passed with `46 passed in 1.32s`, proving the refreshed audit wording plus explicit WAL/`busy_timeout` persistence evidence.
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` ✅ exited `0` and regenerated the durable artifact on the same final state. The run emitted the expected synthetic capture log `Rate limit (429) from RateLimitBeta for 198.51.100.11 — backoff attempt 1, sleeping 15.0s`, which is part of the deterministic audit scenario rather than a slice failure.
- `make verify-fast` ✅ passed on the same state: `982 passed, 113 deselected in 3.41s`, `78` Vitest tests passed, `npx tsc --noEmit` passed, and the production build completed with `app/static/dist/main.js 29.5kb`.
- `make verify-deep` ✅ passed with `113 passed in 36.49s`, preserving the mocked-online browser proof for live enrichment, history continuity, and analyst-visible polling behavior.

Operational readiness for this slice is explicit. The health signals are the incremental status payload fields (`done`, `total`, `complete`, `terminal`, `terminal_reason`, `next_since`), bounded helper history-save diagnostics, and the request/status + persistence rows in `.gsd/milestones/M013/M013-AUDIT.md`. The failure signals are route/API regressions in the focused pytest suites, missing `cached_at` markers on cached delta rows, malformed/absent audit wording, or any fast/deep verification failure. The recovery path is to rerun the focused pytest lanes, regenerate `.gsd/milestones/M013/M013-AUDIT.md`, and then rerun `make verify-fast` plus `make verify-deep` before accepting any further change to the request/status or persistence seam. Monitoring gaps remain the same as before: persistence evidence is deterministic and local rather than production-load telemetry, so future store changes still require fresh contention measurement first.

## Requirements Advanced

- R008 — Preserved analyst-visible enrichment polling continuity while moving the backend status hot path to tail-only incremental snapshots.
- R010 — Reduced request-path work by avoiding full retained-list copies on every status poll while keeping existing polling semantics intact.
- R018 — Re-proved snapshot correctness, cached-marker lock alignment, and the separation between live incremental reads and full mutation-safe snapshots.
- R019 — Kept `/enrichment/status/<job_id>?since=<index>` and `/api/status/<job_id>?since=<index>` on the cursor-native incremental path with stable `next_since` semantics.
- R022 — Kept WAL-backed cache/history stores on explicit measured keep-decision footing and strengthened that decision with deterministic PRAGMA coverage for WAL mode and `busy_timeout`.

## Requirements Validated

- R040 — Fresh slice-close proof passed on the final state: the two focused pytest lanes, audit regeneration, `make verify-fast`, and `make verify-deep` all exited successfully.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

The request/status split and helper-route adoption were already present in the repository when slice close began, so the closeout work focused on integrated proof, artifact refresh, and persistence evidence hardening rather than landing a brand-new route/orchestrator patch during this final pass.

## Known Limitations

The persistence keep-decision is still based on deterministic local temp-DB captures and focused store tests rather than sustained production-like contention telemetry. If future slices observe real writer contention or long-tail latency in the field, they should measure that workload directly before changing WAL mode, connection lifetime, or commit behavior.

## Follow-ups

S04 should treat backend request/status behavior as settled and focus on the frontend/render seam plus the final milestone rerun. Any future attempt to rewrite cache/history persistence should start with new contention evidence, not code-style discomfort with SQLite or per-operation commits.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — Owns the split between full-snapshot status reads and the incremental polling snapshot used by live status routes.
- `app/routes/_helpers.py` — Consumes the incremental status accessor for live polling while preserving helper-owned terminal tombstones and bounded diagnostics.
- `app/routes/api.py` — Keeps the API status route as a thin wrapper over the shared helper path and its preserved contract.
- `app/routes/enrichment.py` — Keeps the HTML polling route aligned with the shared helper and incremental cursor semantics.
- `app/static/src/ts/types/api.ts` — Continues to match the preserved status payload shape, including cursor fields and optional per-row `cached_at` markers.
- `tools/optimization_audit.py` — Refreshes the audit artifact so request/status is recorded as shipped and persistence remains an explicit measured keep-decision.
- `tests/test_orchestrator.py` — Pins tail-only incremental snapshot behavior, full-snapshot safety, marker alignment, and terminal/negative-`since` edge cases.
- `tests/test_routes.py` — Pins shared helper route cursor semantics, cached-marker serialization, and terminal payload truthfulness.
- `tests/test_api.py` — Pins `/api/status` parity with the shared helper contract.
- `tests/test_optimization_audit.py` — Pins the updated shipped-path audit wording and guards against regression to pre-S03 request/status language.
- `tests/test_cache_store.py` — Adds explicit WAL/`busy_timeout` persistence proof for the cache store connection.
- `tests/test_history_store.py` — Adds explicit WAL/`busy_timeout` persistence proof for the history store connection.
- `.gsd/milestones/M013/M013-AUDIT.md` — Regenerated durable audit artifact reflecting the shipped request/status path and persistence keep-decision.
