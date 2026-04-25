---
estimated_steps: 24
estimated_files: 3
skills_used:
  - test
  - verify-before-complete
---

# T02: Refresh the audit runner and pinned wording for the shipped frontend/render fix

Update the generated-audit source of truth so M013 stops describing frontend coordinator caching as queued work and instead truthfully records what S04 ships now versus what still remains deferred. Keep the artifact generated from `tools/optimization_audit.py`; do not hand-edit `.gsd/milestones/M013/M013-AUDIT.md`.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` baseline constants and rendered prose | Fail loudly in tests if the wording still claims the frontend fix is unshipped or silently drops the seam | Keep the runner deterministic and local; do not add long-running external captures here | Render explicit failure/capture summaries rather than ambiguous or placeholder wording |
| `tests/test_optimization_audit.py` pinned expectations | Update assertions in lockstep with the new truthful bucket/wording so later slices cannot drift the audit contract silently | N/A | Treat stale assertions as a blocker, not as a reason to weaken coverage |
| Generated audit artifact `.gsd/milestones/M013/M013-AUDIT.md` | Regenerate from the runner on the same code state instead of hand-editing markdown | Bound generation to the existing deterministic workflow | If the regenerated artifact disagrees with the tests or runner constants, stop and fix the source of truth |

## Load Profile

- **Shared resources**: the audit runner constants, generated markdown artifact, and focused audit tests.
- **Per-operation cost**: one local markdown regeneration plus focused pytest coverage.
- **10x breakpoint**: wording drift between runner, tests, and generated artifact that makes the final milestone rerun untrustworthy.

## Negative Tests

- **Malformed inputs**: missing or stale frontend/render row text, placeholder bucket content, or capture rows that omit the frontend seam entirely.
- **Error paths**: a regenerated artifact that still claims coordinator caching is `do next`, or tests that no longer reflect the shipped/deferred split.
- **Boundary conditions**: the request/status and persistence rows keep their current shipped/leave-alone stance while only the frontend/render wording changes to match S04 reality.

## Steps

1. Update the frontend/render finding, seam note, and any baseline-stance prose in `tools/optimization_audit.py` so the audit describes the coordinator-local cache as shipped and leaves any broader render work explicitly deferred.
2. Update `tests/test_optimization_audit.py` to pin the new wording and guard against regression back to the pre-S04 `do next` language.
3. Regenerate `.gsd/milestones/M013/M013-AUDIT.md` from the runner and confirm the artifact matches the new truthful wording before starting the expensive final proof.

## Must-Haves

- [ ] The frontend/render row no longer describes stable-handle caching as queued work.
- [ ] Any remaining render follow-up stays explicit in the ranked audit instead of disappearing.
- [ ] Runner, tests, and generated artifact all agree on the shipped frontend/render stance.
- [ ] The audit remains generated output sourced from `tools/optimization_audit.py`.

## Inputs

- ``tools/optimization_audit.py``
- ``tests/test_optimization_audit.py``
- ``.gsd/milestones/M013/M013-AUDIT.md``

## Expected Output

- ``tools/optimization_audit.py``
- ``tests/test_optimization_audit.py``
- ``.gsd/milestones/M013/M013-AUDIT.md``

## Verification

pytest tests/test_optimization_audit.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md
