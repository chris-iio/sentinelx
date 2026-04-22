---
estimated_steps: 4
estimated_files: 2
skills_used:
  - test
  - verify-before-complete
---

# T01: Codify fast and deep verification lanes in the repo-native command surface

**Slice:** S03 — Fast default proof loop and deterministic expensive lane
**Milestone:** M012

## Description

Add explicit Make targets for the fast/default lane and the deeper browser lane, then document when each lane is required so optimization work has unambiguous proof expectations tied to existing commands rather than ad-hoc tribal knowledge. Keep the command surface boring and repo-native: reuse the current pytest marker split, Vitest, TypeScript typecheck, and build commands rather than inventing a new test harness.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `Makefile` targets and recursive `make` calls | Fail fast and keep each lane target small enough that the failing subcommand is obvious | Do not add retries or sleeps; contributors should rerun the named lane directly | N/A |
| `python3 -m pytest`, `npx vitest run`, `npx tsc --noEmit`, `make build` | Keep target definitions as thin wrappers around the real commands so failures stay attributable | Preserve current command boundaries so a slow/failing subcommand is visible in output | N/A |
| `README.md` contributor guidance | Keep docs literal and command-exact; if docs drift from Makefile names, the task is incomplete | N/A | Avoid vague lane labels; use the final target names exactly |

## Load Profile

- **Shared resources**: contributor and CI wall-clock time, local Node/Python toolchain startup, and frontend build artifacts.
- **Per-operation cost**: one non-E2E pytest run, one Vitest run, one TypeScript typecheck, and one build for the fast lane; one E2E pytest run for the deep lane.
- **10x breakpoint**: if the default lane accidentally includes E2E/browser work, routine feedback jumps from seconds to tens of seconds and the slice goal fails.

## Negative Tests

- **Malformed inputs**: missing or misspelled lane names in docs, and Make targets that recurse incorrectly or omit one of the required fast-lane commands.
- **Error paths**: one fast-lane subcommand fails and the target should stop immediately instead of hiding the failure behind later commands.
- **Boundary conditions**: contributors run `make verify-fast` only, `make verify-deep` only, or `make verify` for full confidence and each path should map cleanly to the documented contract.

## Steps

1. Update `Makefile` with named `verify-fast`, `verify-deep`, and `verify` targets that compose the real repo commands without inventing a new wrapper stack.
2. Keep `verify-fast` limited to `python3 -m pytest -q -m 'not e2e'`, `npx vitest run`, `npx tsc --noEmit`, and `make build`, and make `verify` compose the fast and deep lanes explicitly.
3. Expand `README.md` with a concise verification section that says what each lane proves and when live-enrichment/results-surface work must run the deeper browser lane.
4. Run the fast lane through the new target so the documented/default command surface is verified immediately.

## Must-Haves

- [ ] `Makefile` exposes `verify-fast`, `verify-deep`, and `verify` as the canonical proof-lane commands.
- [ ] `verify-fast` stays on the sub-10-second-style default path by excluding E2E pytest.
- [ ] `README.md` states when contributors may stop at the fast lane and when they must escalate to the deep/browser lane.
- [ ] The documented commands match the actual Make targets exactly.

## Verification

- `make verify-fast`
- `rg -n "verify-fast|verify-deep|verify" Makefile README.md`

## Inputs

- `Makefile` — current repo-native build/typecheck surface that should become the verification entrypoint.
- `README.md` — current contributor-facing root doc that needs the proof-lane contract.
- `pyproject.toml` — existing `e2e` marker split for pytest.
- `package.json` — confirms there is no richer npm script surface to preserve.
- `vitest.config.ts` — confirms the current frontend unit-test command surface.

## Expected Output

- `Makefile` — named fast/deep/full verification targets that wrap the existing commands.
- `README.md` — contributor guidance for which verification lane to run and why.
