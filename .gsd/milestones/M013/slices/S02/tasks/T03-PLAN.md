---
estimated_steps: 3
estimated_files: 7
skills_used:
  - observability
  - verify-before-complete
  - debug-like-expert
---

# T03: Ship the measured runtime fix or codify the keep-decision and rerun proof

**Slice:** S02 — Runtime/provider seam shipped fixes
**Milestone:** M013

## Description

Use the T02 measurements to decide whether this slice should ship a narrow runtime/provider code change or refresh the audit with an explicit keep-decision. The only acceptable code-path optimization is a cache-hit-heavy dispatch reduction that avoids scheduling needless work before the thread-pool/semaphore path while preserving cached-marker output, retry/backoff behavior, provider concurrency, and adapter-owned session reuse. If the measurements do not show a meaningful win, do not reopen concurrency/session policy; instead refresh the audit so the leave-alone stance is explicit and durable.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| T02 runtime/provider evidence | Default to the audit-only keep-decision path; do not invent an optimization without evidence | Keep proof bounded to the repo verification lanes | Treat incomplete evidence as a blocker for code churn, not as permission to guess |
| Orchestrator hot path in `app/enrichment/orchestrator.py` | Preserve cached markers, retries, and semaphore semantics or revert to audit-only outcome | Existing provider timeout/backoff behavior must stay unchanged | Reject any optimization that depends on raw provider payload shape |
| Full verification lanes (`make verify-fast`, `make verify-deep`) | Do not mark the slice done until both lanes are green after the final audit refresh | Use the existing deterministic mocked-online proof instead of live-provider retries | Treat browser/status regressions as slice blockers because they threaten R008/R040 continuity |

## Load Profile

- **Shared resources**: orchestrator thread pool, shared cache store, provider semaphores, and the full regression/browser verification lanes.
- **Per-operation cost**: one final measured runtime/provider pass, focused unit regressions, and the standard slice-close verification commands.
- **10x breakpoint**: an over-broad optimization that changes global concurrency/session behavior; keep the implementation narrow or stay with the explicit keep-decision.

## Negative Tests

- **Malformed inputs**: mixed cache-hit/miss batches, unsupported IOC/provider pairs, and adapters returning malformed errors.
- **Error paths**: 429 retries after an initial miss, non-429 single-retry behavior, and audit refresh after a no-optimization keep decision.
- **Boundary conditions**: all-cache-hit runs, zero-auth providers mixed with key-required providers, and concurrent status snapshots while work completes.

## Steps

1. Read the T02 capture results and decide explicitly whether the slice will ship a narrow cache-hit/dispatch reduction or preserve the current runtime seam as a measured keep-decision.
2. If the evidence justifies a code change, implement only the measured hot-path reduction in `app/enrichment/orchestrator.py` and extend `tests/test_orchestrator.py` / `tests/test_optimization_audit.py` to pin the new behavior; otherwise update the audit text so the keep-decision is explicit and traceable.
3. Refresh `.gsd/milestones/M013/M013-AUDIT.md`, then run the full slice-close proof so the artifact and verification evidence match the final code path.

## Must-Haves

- [ ] The final state is either a measured runtime/provider code improvement or an explicit audited keep-decision; there is no speculative middle ground.
- [ ] Provider concurrency, 429 backoff, cached-marker correctness, snapshot safety, and adapter-owned session reuse remain preserved.
- [ ] The final audit refresh, `make verify-fast`, and `make verify-deep` all run against the same final code state.

## Verification

- `pytest tests/test_orchestrator.py tests/test_http_safety.py tests/test_base_adapter.py tests/test_optimization_audit.py -q`
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`
- `make verify-fast`
- `make verify-deep`

## Observability Impact

- Signals added/changed: the final runtime/provider evidence row and, if warranted, any new hot-path counters that distinguish cache-hit short-circuiting from provider dispatch work.
- How a future agent inspects this: compare the refreshed audit artifact with the focused orchestrator/audit tests and rerun lanes.
- Failure state exposed: unjustified optimization churn, verification regressions, or stale audit text become explicit mismatches between the artifact and the final proof commands.

## Inputs

- `app/enrichment/orchestrator.py` — runtime/provider hot path that may change only if the evidence justifies it
- `tests/test_orchestrator.py` — guardrail tests for concurrency, retries, cache markers, and snapshots
- `tools/optimization_audit.py` — runtime/provider capture and ranked-finding text refreshed at slice close
- `tests/test_optimization_audit.py` — artifact contract coverage for the runtime/provider row
- `.gsd/milestones/M013/M013-AUDIT.md` — durable artifact refreshed to match the final code path

## Expected Output

- `app/enrichment/orchestrator.py` — measured runtime/provider change or preserved hot path with explicit keep-decision support
- `tests/test_orchestrator.py` — final guardrail coverage for the chosen path
- `tools/optimization_audit.py` — final runtime/provider capture and ranked-finding wording
- `tests/test_optimization_audit.py` — tests aligned with the final runtime/provider artifact contract
- `.gsd/milestones/M013/M013-AUDIT.md` — final audit refresh matching the verified code state
