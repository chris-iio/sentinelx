# S03: S03 — UAT

**Milestone:** M013
**Written:** 2026-04-25T06:41:28.581Z

# S03 UAT — request/status hot path and persistence continuity

## Preconditions

- SentinelX dependencies are installed and the app can run locally from this repository.
- Use a local dev/test environment with deterministic provider behavior (the same environment used by `make verify-fast` / `make verify-deep` is acceptable).
- Start with an empty browser session or a clean API client so polling can be observed from the first response.

## Test Case 1 — Live status polling returns only the requested tail

1. Submit an analysis through the UI or `POST /api/analyze` with multiple IOCs so enrichment produces more than one result row.
   - **Expected:** A `job_id` is returned and the analysis begins normally.
2. Request `GET /enrichment/status/<job_id>` with no `since` parameter.
   - **Expected:** The payload includes `results`, `next_since`, `done`, `total`, `complete`, `status`, `terminal`, `terminal_reason`, and `error` fields.
3. Record the returned `next_since` value, then poll `GET /enrichment/status/<job_id>?since=<next_since>` while the job is still running.
   - **Expected:** The response contains only newly produced rows after the prior cursor, not a replay of earlier rows.
   - **Expected:** `next_since` advances to the retained result length, and `done` / `total` / `complete` continue to reflect true job progress.
4. Poll again after the job completes using the most recent `next_since`.
   - **Expected:** `results` is empty (or contains only rows created since the last cursor), `complete` is `true`, and no earlier rows are resent.

## Test Case 2 — API parity and cached markers remain intact

1. Repeat or reuse a completed analysis so at least one provider result is served from cache.
   - **Expected:** The analysis completes successfully.
2. Poll `GET /api/status/<job_id>?since=0` and inspect the returned `results` rows.
   - **Expected:** Cached rows include `cached_at`; non-cached rows do not invent a marker.
3. Poll `GET /enrichment/status/<job_id>?since=0` for the same job.
   - **Expected:** The HTML route payload and API route payload expose the same top-level contract (`results`, `next_since`, `complete`, `status`, `terminal`, `terminal_reason`, `error`) and the same `cached_at` behavior for matching rows.
4. Poll both endpoints again with `since=<len(results from first poll)>`.
   - **Expected:** Both routes return an empty tail or only newly arrived rows, proving API/HTML parity on cursor semantics.

## Test Case 3 — Edge and terminal semantics stay truthful

1. Request `GET /enrichment/status/<unknown_job_id>` and `GET /api/status/<unknown_job_id>` with a clearly nonexistent id.
   - **Expected:** Both surfaces preserve the existing terminal/404 behavior for unknown work instead of returning a misleading success payload.
2. Poll a real job with `?since=-5`.
   - **Expected:** Current negative-`since` compatibility is preserved; the request does not crash and continues to return the same contract shape.
3. Poll a real job with `?since=<large number beyond retained length>`.
   - **Expected:** The response returns an empty `results` tail and a stable `next_since` rather than replaying the full history.
4. Force or simulate a failed enrichment job using the existing test/dev mechanism.
   - **Expected:** `terminal`, `terminal_reason`, and `error` remain truthful, and helper-owned `unknown` / `evicted` / `job_failed` semantics are still distinct.

## Test Case 4 — History reload and helper diagnostics remain bounded

1. Complete an analysis and allow it to be saved to history.
   - **Expected:** The analysis is listed in recent history and reloads successfully.
2. Open the saved analysis from the history UI.
   - **Expected:** The stored result set renders correctly and matches the completed enrichment state; no live polling contract changes are required for history replay.
3. Visit `/settings` (or the existing diagnostics surface used in local verification).
   - **Expected:** History-save diagnostics remain aggregate-only and bounded; no raw analyst input, full provider payloads, or widened helper diagnostics are exposed.

## Test Case 5 — Audit artifact reflects the shipped S03 outcome

1. Run `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`.
   - **Expected:** The command exits successfully; an expected synthetic 429/backoff log line may appear during capture.
2. Open `.gsd/milestones/M013/M013-AUDIT.md`.
   - **Expected:** The request/status seam is recorded as shipped on the orchestrator-owned incremental snapshot path, not as an unshipped do-now item.
   - **Expected:** The persistence seam explicitly remains a WAL-backed keep-decision unless stronger contention evidence appears.
3. Run `make verify-fast` and `make verify-deep`.
   - **Expected:** Both pass on the same final state, proving the shipped request/status change preserved live polling, history continuity, and the broader analyst-visible contract.

