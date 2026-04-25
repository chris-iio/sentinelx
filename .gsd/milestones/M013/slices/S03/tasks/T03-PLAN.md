---
estimated_steps: 24
estimated_files: 7
skills_used:
  - observability
  - test
  - verify-before-complete
---

# T03: Refresh audit evidence and persistence keep-decisions on the final code path

Update the durable optimization artifact so S03 records the shipped request/status fix and keeps WAL-backed cache/history persistence on explicit evidence-based footing unless new contention proof appears during execution. This task should prefer audit/test refresh over speculative store rewrites: only modify `app/cache/store.py` or `app/enrichment/history_store.py` if a focused measurement or failing test proves a real persistence problem.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` baseline runner | Fail loudly and keep the artifact generation path readable; stale request/status wording is a slice blocker | Bound captures to the existing deterministic internal benchmarks and verification lanes | Render an explicit failed capture summary rather than silently dropping the seam |
| WAL-backed stores and their focused tests | Preserve the existing keep-decision if no new evidence appears; do not churn storage code to satisfy the slice title | Keep persistence proof local and deterministic; do not wait on external services | Treat malformed metrics or unclear contention data as insufficient evidence for store rewrites |
| Final verification lanes (`make verify-fast`, `make verify-deep`) | Do not mark the slice done until the audit refresh and both lanes pass on the same final state | Use the existing deterministic mocked-online browser proof instead of adding live-provider dependencies | Any route/poller/browser regression is a blocker because it threatens R008/R040 continuity |

## Load Profile

- **Shared resources**: audit artifact generation, temp SQLite WAL stores used by the internal capture, and the repo verification lanes.
- **Per-operation cost**: one audit refresh, focused pytest suites for audit/store continuity, plus the standard fast/deep end-to-end proof commands.
- **10x breakpoint**: reopening persistence implementation without actual lock/contention evidence, or letting the audit artifact drift from the verified code state.

## Negative Tests

- **Malformed inputs**: missing capture rows, malformed benchmark summaries, or audit text that still claims the request/status seam is unshipped.
- **Error paths**: focused cache/history store tests failing under the refreshed audit stance, or audit regeneration failing after the request-path code lands.
- **Boundary conditions**: persistence seam remains unchanged, request/status seam ships, and the final artifact still names WAL persistence as a measured keep-decision rather than a silent omission.

## Steps

1. Update `tools/optimization_audit.py` and `tests/test_optimization_audit.py` so the request/status row reflects the shipped delta path and the persistence row still cites current temp-WAL evidence unless new data justifies reopening it.
2. Run or strengthen focused `tests/test_cache_store.py` and `tests/test_history_store.py` only as needed to keep the persistence keep-decision evidence explicit and current without speculative store churn.
3. Regenerate `.gsd/milestones/M013/M013-AUDIT.md`, then run the focused pytest lanes plus `make verify-fast` and `make verify-deep` so the durable artifact matches the final repository state.

## Must-Haves

- [ ] The audit artifact no longer describes `/enrichment/status` as an unshipped do-now idea; it records the actual shipped request/status fix and its continuity notes.
- [ ] WAL-backed cache/history persistence remains an explicit measured keep-decision unless execution uncovers stronger contradictory evidence.
- [ ] The final audit refresh, focused pytest lanes, `make verify-fast`, and `make verify-deep` all run against the same final state.
- [ ] No store rewrite is shipped without a concrete measurement or failing-test reason documented in code/tests and the audit.

## Inputs

- `tools/optimization_audit.py` — current baseline findings, request/status benchmark text, and persistence keep-decision captures
- `tests/test_optimization_audit.py` — artifact contract tests that still pin the pre-S03 wording
- `tests/test_cache_store.py` — focused WAL cache continuity proof for the persistence keep-decision
- `tests/test_history_store.py` — focused WAL history continuity proof for the persistence keep-decision
- `.gsd/milestones/M013/M013-AUDIT.md` — durable artifact that must be regenerated from the final code state
- `app/cache/store.py` — current persistent-connection WAL cache implementation that should stay unchanged absent evidence
- `app/enrichment/history_store.py` — current persistent-connection WAL history implementation that should stay unchanged absent evidence

## Expected Output

- `tools/optimization_audit.py` — refreshed request/status and persistence findings/captures
- `tests/test_optimization_audit.py` — assertions aligned with the shipped S03 artifact wording
- `.gsd/milestones/M013/M013-AUDIT.md` — regenerated audit artifact matching the final code state

## Verification

pytest tests/test_optimization_audit.py tests/test_cache_store.py tests/test_history_store.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md && make verify-fast && make verify-deep

## Observability Impact

- Signals added/changed: durable request/status and persistence ranking rows plus fresh verification evidence captured in the regenerated M013 audit artifact.
- How a future agent inspects this: rerun the audit runner, compare the request/status row, and use focused store/audit tests to confirm the keep-decision still has proof.
- Failure state exposed: stale audit claims, missing benchmark rows, or unjustified persistence churn become explicit mismatches between the artifact and the focused/full verification lanes.
