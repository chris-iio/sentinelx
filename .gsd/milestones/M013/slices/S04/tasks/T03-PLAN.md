---
estimated_steps: 24
estimated_files: 6
skills_used:
  - test
  - verify-before-complete
---

# T03: Run the final milestone-close rerun and fix any proof regressions on the verified state

Finish M013 with fresh evidence, not inherited claims. Run the focused browser lane plus the final audit command that captures `make verify-fast` and `make verify-deep`, and only make the smallest regression fixes needed to keep the audited final state green. This task is allowed to touch source or tests only when the rerun exposes a real regression from T01/T02.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tests/e2e/test_results_page.py` mocked-online results-page proof | Treat any DOM/state regression as a slice blocker because it threatens analyst-visible continuity | Use the existing deterministic mocked-online flow; do not swap in live-provider dependencies | If the browser output no longer matches the contract, fix code/tests or audit wording before claiming completion |
| `make verify-fast` / `make verify-deep` capture commands | Do not mark the slice complete until both commands pass on the same final state captured into the audit artifact | Keep captures on the audit runner's deterministic command surface rather than ad hoc shell notes | Failed captures must remain visible in the artifact/command output, not be hidden by a partial rerun |
| Final generated audit artifact | Regenerate it last so the capture table reflects the verified final repository state | Bound generation to the existing runner timeout/command-capture behavior | Stop if the artifact and the actual verification state disagree |

## Load Profile

- **Shared resources**: the repo-wide fast/deep verification lanes, the deterministic mocked-online browser harness, and the generated audit artifact.
- **Per-operation cost**: one focused browser pytest run plus one final baseline audit generation that shells out to `make verify-fast` and `make verify-deep`.
- **10x breakpoint**: letting final proof depend on stale earlier output, or chasing broad refactors instead of the smallest fix needed to restore the verified final state.

## Negative Tests

- **Malformed inputs**: missing detail links, missing loaded-slot markers, wrong owner/runtime attributes, or stale capture rows in the final audit.
- **Error paths**: Vitest/E2E/build/typecheck failures surfaced through the captured verify lanes.
- **Boundary conditions**: live and history paths still share the coordinator, the final audit captures both verification lanes, and the generated artifact reflects the exact final state used for slice closure.

## Steps

1. Run `pytest tests/e2e/test_results_page.py -q` after the focused code/test changes settle so the analyst-visible live seam is checked before the expensive full rerun.
2. Run the final audit command with `verify-fast` and `verify-deep` capture commands so `.gsd/milestones/M013/M013-AUDIT.md` becomes the durable record of the last verified state.
3. If the rerun exposes regressions, make the smallest source/test/audit fix needed and rerun until the generated artifact, focused E2E lane, and captured fast/deep proof all agree.

## Must-Haves

- [ ] Fresh mocked-online results-page proof passes on the post-S04 code state.
- [ ] The final audit artifact embeds fresh `verify-fast` and `verify-deep` captures from the same repository state.
- [ ] Any regression fixes stay narrowly scoped to restoring the promised live/history/frontend continuity.
- [ ] The slice finishes with durable evidence that satisfies R040 instead of relying on earlier slice output.

## Inputs

- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/enrichment.ts``
- ``app/static/src/ts/modules/history.ts``
- ``tests/e2e/test_results_page.py``
- ``tools/optimization_audit.py``
- ``.gsd/milestones/M013/M013-AUDIT.md``

## Expected Output

- ``.gsd/milestones/M013/M013-AUDIT.md``

## Verification

pytest tests/e2e/test_results_page.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md --capture-command 'verify-fast::make verify-fast' --capture-command 'verify-deep::make verify-deep'

## Observability Impact

- Signals added/changed: the final capture table in `.gsd/milestones/M013/M013-AUDIT.md` becomes the durable proof surface for `verify-fast` and `verify-deep` on the last shipped state.
- How a future agent inspects this: read the regenerated audit artifact and rerun `pytest tests/e2e/test_results_page.py -q` if analyst-visible DOM continuity is in doubt.
- Failure state exposed: final-state regressions surface as explicit capture failures, missing mocked-online DOM assertions, or mismatches between the artifact wording and the verified code.
