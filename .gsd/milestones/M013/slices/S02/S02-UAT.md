# S02: S02 — UAT

**Milestone:** M013
**Written:** 2026-04-24T02:56:05.769Z

# S02 UAT — Runtime/provider seam shipped fixes

## Preconditions

1. Work from the repo root with Python and Node dependencies installed.
2. No live provider credentials are required; this slice’s runtime/provider proof is deterministic and local.
3. Ensure `make`, `python3`, `pytest`, and the browser dependencies used by `make verify-deep` are available.
4. Start from the current M013 worktree so `.gsd/milestones/M013/M013-AUDIT.md` can be regenerated.

## Test Case 1 — Regenerate the runtime/provider audit capture

1. Run `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`.
   - Expected: The command exits successfully and rewrites `.gsd/milestones/M013/M013-AUDIT.md`.
2. Open `.gsd/milestones/M013/M013-AUDIT.md`.
   - Expected: The `Measurement captures` table contains a `runtime-provider-diagnostics` row.
   - Expected: That row reports provider mix `CacheAlpha:2d/0e, RateLimitBeta:2d/1e`, `dispatch=4`, `attempts=5`, `cache-hit ratio 1/5 (20%)`, `retries=1 (429=1)`, and bounded latency totals.

## Test Case 2 — Confirm the slice codified a measured keep-decision instead of speculative churn

1. In `.gsd/milestones/M013/M013-AUDIT.md`, navigate to the `leave alone` bucket.
   - Expected: One row says `Keep the runtime/provider dispatch path unchanged until diagnostics show a materially cache-hit-heavy workload.`
   - Expected: The evidence summary explains that the orchestrator already short-circuits cache hits inside `_single_attempt()` and that the measured `1/5 (20%)` cache-hit ratio does not justify a new pre-dispatch fast path.
2. Stay in the same bucket.
   - Expected: A separate row keeps per-provider backoff/session semantics as explicit measured keep-decisions.
   - Expected: The continuity notes preserve per-provider caps, cache-hit markers, retry/backoff behavior, and adapter-owned session reuse.

## Test Case 3 — Prove the bounded diagnostics surface and guardrails still hold

1. Run `pytest tests/test_orchestrator.py -q`.
   - Expected: The command passes.
   - Expected: The suite covers cache-hit/miss accounting, retry and 429 counters, latency aggregation, malformed-state coercion, semaphore/backoff invariants, and snapshot-safe diagnostics access.
2. Run `pytest tests/test_optimization_audit.py -q`.
   - Expected: The command passes.
   - Expected: The suite pins the runtime/provider capture wording and fails if the explicit keep-decision or failure-handling contract drifts.

## Test Case 4 — Re-run the slice close proof lanes against the same final state

1. Run `pytest tests/test_orchestrator.py tests/test_http_safety.py tests/test_base_adapter.py tests/test_optimization_audit.py -q`.
   - Expected: The combined command passes.
2. Run `make verify-fast`.
   - Expected: Backend pytest, Vitest, TypeScript typecheck, and production build all pass.
3. Run `make verify-deep`.
   - Expected: The deterministic mocked-online browser suite passes, preserving analyst-visible live enrichment continuity.

## Edge Cases

- All-cache-hit workloads must still report bounded diagnostics and preserve cache-hit markers without exposing raw provider payloads in status responses.
- Repeated 429 behavior must remain observable in diagnostics (`rate_limit_retries`) while semaphore slots are not held during backoff sleep.
- Blank or malformed provider names must be normalized into bounded diagnostics buckets (for example `unknown`) rather than crashing the capture or widening the contract.
- If a future runtime/provider slice wants to revisit pre-dispatch short-circuiting, it must first produce a materially more cache-hit-heavy capture than the current `1/5 (20%)` profile.
