---
estimated_steps: 6
estimated_files: 4
skills_used:
  - debug-like-expert
  - test
  - verify-before-complete
---

# T03: Prove the stash/pop blocker class with temp-repo Git regression fixtures

Close the slice with real Git behavior. The point of S01 is not that the rules look plausible; it is that tracked transient state no longer wedges ordinary workflows without either being prevented or being surfaced by an explicit repo check.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Real Git CLI behavior in temp repos | Fail the task if the fixture no longer reproduces the blocker or if the hardened path fails to detect/prevent it; do not replace Git with mocks | Keep fixtures small and local so they finish quickly in pytest | Capture stderr/stdout from failed Git commands so the regression points to stash/pop behavior, not an opaque assertion |
| Boundary verifier from T01/T02 | Use the same classifier/audit command the repo ships; the proof is invalid if the fixture invents a separate rule set | N/A | Treat mismatches between fixture expectations and verifier output as blockers |
| Existing fast verification lane | Re-run `make verify-fast` after the focused Git fixtures so the slice proves it did not regress unrelated SentinelX checks while hardening the repo boundary | N/A | If the broader lane fails, stop and repair before claiming the slice is complete |

## Load Profile

- **Shared resources**: temp Git repos, the boundary audit command, and the repo's focused Python verification lane.
- **Per-operation cost**: initialize a small temp repo, create a tracked-transient conflict, create an untracked-transient collision, and run the supported verifier.
- **10x breakpoint**: overfitting the proof to one exact filename instead of the broader tracked/untracked transient classes the classifier owns.

## Negative Tests

- **Malformed inputs**: missing `.gitignore`, stale classifier rules, and temp repos where transient paths sit outside the expected boundary roots.
- **Error paths**: stash/apply or checkout failures caused by tracked transient files, plus untracked transient collisions that should be ignored or surfaced cleanly after hardening.
- **Boundary conditions**: both the representative tracked `.gsd/audit/events.jsonl` class and the untracked `.gsd/state-manifest.json` / `.gsd/event-log.jsonl` class are covered, while durable milestone files remain outside the transient fixture.

## Steps

1. Add temp-repo pytest fixtures that reproduce the observed stash/pop blocker class with a tracked transient file and a second case with untracked transient collisions.
2. Prove the hardened boundary either prevents the conflict through ignore/index state or surfaces it through the shipped audit command before `stash pop`/checkout is attempted.
3. Wire the focused fixture suite into the repo-native boundary verifier target and re-run `make verify-fast` on the same final state.

## Must-Haves

- [ ] The repo has an executable regression test for the tracked-transient stash/pop blocker class.
- [ ] The repo has a second executable regression test for untracked transient collisions.
- [ ] The supported boundary verifier is part of the proof path, not just the unit tests.
- [ ] `make verify-fast` still passes after the repo-boundary hardening lands.

## Verification

- `pytest tests/test_runtime_state_boundary_git.py -q`
- `make verify-runtime-boundary`
- `make verify-fast`

## Inputs

- ``tools/runtime_state_boundary.py``
- ``tests/test_runtime_state_boundary.py``
- ``.gitignore``
- ``Makefile``
- ``docs/runtime-state-boundary.md``

## Expected Output

- ``tests/test_runtime_state_boundary_git.py``
- ``Makefile``
- ``docs/runtime-state-boundary.md``

## Verification

pytest tests/test_runtime_state_boundary_git.py -q && make verify-runtime-boundary && make verify-fast
