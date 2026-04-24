---
estimated_steps: 3
estimated_files: 4
skills_used:
  - observability
  - verify-before-complete
---

# T02: Capture runtime/provider evidence in the audit workflow

**Slice:** S02 — Runtime/provider seam shipped fixes
**Milestone:** M013

## Description

Extend the audit workflow so S02 can capture deterministic runtime/provider evidence from the orchestrator and carry it into the durable ranked artifact. Keep the measurement synthetic/local and based only on tracked code paths — no live provider keys, no `.gsd` fixtures, and no dependency on hidden temp-state beyond task-local temporary files.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` measurement harness | Fail the capture loudly and preserve the rest of the artifact generation path | Bound runtime with the existing command timeout path | Surface a readable capture failure summary instead of crashing markdown generation |
| Orchestrator diagnostics from T01 | Fall back to an explicit audit capture failure until the diagnostics contract is fixed | Keep captures local and deterministic; do not block on real providers | Validate expected keys and summarize missing fields as a failed capture |
| Audit rendering/tests | Keep template and baseline modes readable even when the new runtime/provider capture fails | N/A | Escape summary text and keep markdown tables structurally valid |

## Load Profile

- **Shared resources**: local thread pool/orchestrator state during the synthetic capture, temp cache or in-memory fixtures, and markdown artifact generation.
- **Per-operation cost**: one deterministic local enrichment measurement plus updated baseline/template rendering and unit assertions.
- **10x breakpoint**: flaky timing assertions or heavy synthetic workloads; keep the capture shape deterministic and assert on counters/structure rather than brittle absolute timings.

## Negative Tests

- **Malformed inputs**: missing diagnostics keys, empty adapter lists, and capture helpers returning incomplete summaries.
- **Error paths**: capture helper exception, failed output write, and summary text containing markdown table delimiters.
- **Boundary conditions**: all-cache-hit run, mixed success/retry run, and baseline mode with no external `--capture-command` arguments.

## Steps

1. Add a deterministic runtime/provider measurement helper to `tools/optimization_audit.py` that exercises the orchestrator with synthetic adapters/cache state and records provider mix, cache-hit ratio, retry/rate-limit cost, and latency summary fields from T01.
2. Update the baseline/runtime-provider audit text so the S02 row can cite the new capture and clearly distinguish a measured ship target from an explicit keep-decision.
3. Extend `tests/test_optimization_audit.py` to pin the new capture label/summary and keep the artifact format stable.

## Must-Haves

- [ ] The audit runner emits a deterministic runtime/provider capture without real provider credentials or network calls.
- [ ] `.gsd/milestones/M013/M013-AUDIT.md` can carry provider-mix/cache-hit/retry evidence in the same durable vocabulary S01 established.
- [ ] Audit tests pin the new capture so later slices can refresh the artifact without drifting the runtime/provider evidence shape.

## Verification

- `pytest tests/test_optimization_audit.py -q`
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`

## Observability Impact

- Signals added/changed: durable runtime/provider measurement rows in the audit artifact, sourced from orchestrator diagnostics rather than ad hoc prose.
- How a future agent inspects this: rerun `python3 tools/optimization_audit.py --mode baseline --output …` and compare the runtime/provider capture row and ranked finding text.
- Failure state exposed: missing diagnostics keys or malformed summaries become audit-test failures or explicit capture-failure rows in the artifact.

## Inputs

- `tools/optimization_audit.py` — current audit runner and baseline/runtime-provider findings
- `tests/test_optimization_audit.py` — current audit artifact contract tests
- `app/enrichment/orchestrator.py` — T01 diagnostics surface consumed by the measurement helper
- `.gsd/milestones/M013/M013-AUDIT.md` — durable artifact that must carry the new runtime/provider evidence

## Expected Output

- `tools/optimization_audit.py` — deterministic runtime/provider capture and refreshed audit text
- `tests/test_optimization_audit.py` — coverage pinning the new capture row/summary
- `.gsd/milestones/M013/M013-AUDIT.md` — refreshed artifact with runtime/provider evidence
