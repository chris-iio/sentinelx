---
estimated_steps: 8
estimated_files: 8
skills_used:
  - best-practices
  - test
  - verify-before-complete
---

# T02: Align `.gitignore`, tracked runtime files, and the repo-native boundary command

Apply the new policy to the actual repository so R061 and R062 become true in repo behavior, not just in a classifier. This task is where the slice stops being diagnostic-only and actually prevents the known blocker class for unequivocally transient paths.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| T01 classifier/audit contract in `tools/runtime_state_boundary.py` | Stop and fix the policy seam before changing ignore/index state; do not fork the rules inside `.gitignore` or `Makefile` | N/A | Treat unexpected classifications as blockers, not as permission to widen cleanup scope |
| Git index state for tracked runtime files like `.gsd/audit/events.jsonl` and `.bg-shell/manifest.json` | Preserve working-tree contents while removing only explicit transient paths from the index | Git commands stay local and bounded; no long-running operations expected | Fail loudly if a target path is no longer present or resolves to a non-transient class |
| Supported command surface in `Makefile` and repo docs | Keep one obvious verifier entrypoint for later slices; do not require shell archaeology to re-run the boundary checks | N/A | If docs/commands drift, surface that through the focused verification instead of leaving hidden assumptions |

## Load Profile

- **Shared resources**: Git ignore rules, the working index, and the repo-native verification entrypoint that later slices and contributors will rely on.
- **Per-operation cost**: a handful of ignore/index updates plus one focused repo audit command; no recursive deletion or blanket `.planning/**` rewrites.
- **10x breakpoint**: accidental widening of the transient set or a verifier that relies on brittle filename-by-filename checks instead of the classifier's path classes.

## Negative Tests

- **Malformed inputs**: transient candidates that are already ignored, transient candidates that are still tracked, and legacy/manual-review `.planning` files that must not be auto-deindexed.
- **Error paths**: deindex commands that would delete working-tree contents, `.gitignore` rules that shadow durable milestone docs, and a `Makefile` target that passes while tracked-transient blockers still exist.
- **Boundary conditions**: durable `.gsd/milestones/**` files remain tracked, canonical `.gsd` ledgers remain tracked, and runtime surfaces like `.gsd/state-manifest.json`, `.gsd/event-log.jsonl`, `.gsd/audit/events.jsonl`, `.gsd/notifications.jsonl`, and `.bg-shell/manifest.json` move into the supported transient class.

## Steps

1. Expand `.gitignore` for the classifier-approved transient `.gsd` / `.bg-shell` surfaces that are currently unignored or only partially fenced.
2. Remove already tracked transient paths from the Git index without deleting local files, leaving durable milestone artifacts and canonical ledgers untouched.
3. Add a repo-native `Makefile` target that runs the boundary audit and focused pytest coverage in one supported command.
4. Update the checked-in boundary doc (and README if needed) so later slices know which surfaces are transient, which remain durable, and which adjacent legacy files are manual-review only.

## Must-Haves

- [ ] `.gitignore` and the classifier agree on the transient surfaces S01 owns.
- [ ] Known tracked-transient blockers are removed from the index while their working-tree files remain available for local runtime use.
- [ ] Durable milestone artifacts and canonical `.gsd` ledgers remain tracked.
- [ ] The repo exposes one supported boundary verification command for humans and later slices.

## Verification

- `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues`
- `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json`
- `test -z "$(git ls-files .gsd/audit/events.jsonl .gsd/notifications.jsonl .bg-shell/manifest.json)"`

## Observability Impact

- Signals added/changed: the supported verifier now reports exactly which transient paths are still tracked or unignored.
- How a future agent inspects this: run the `Makefile` target and compare its audit output with `git status --short --ignored .gsd .planning .bg-shell`.
- Failure state exposed: repo-boundary regressions show up as named tracked-transient or unignored-transient findings before a stash/pop conflict occurs.

## Inputs

- ``tools/runtime_state_boundary.py``
- ``tests/test_runtime_state_boundary.py``
- ``.gitignore``
- ``Makefile``
- ``.gsd/audit/events.jsonl``
- ``.gsd/notifications.jsonl``
- ``.bg-shell/manifest.json``
- ``.planning/STATE.md``

## Expected Output

- ``.gitignore``
- ``Makefile``
- ``README.md``
- ``docs/runtime-state-boundary.md``
- ``.gsd/audit/events.jsonl``
- ``.gsd/notifications.jsonl``
- ``.bg-shell/manifest.json``

## Verification

python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues && git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json && test -z "$(git ls-files .gsd/audit/events.jsonl .gsd/notifications.jsonl .bg-shell/manifest.json)"

## Observability Impact

- Signals added/changed: supported verifier output for tracked-transient blockers and unignored transient paths.
- How a future agent inspects this: `make verify-runtime-boundary`, `python3 tools/runtime_state_boundary.py audit --format text`, and `git status --short --ignored .gsd .planning .bg-shell`.
- Failure state exposed: index drift becomes visible immediately instead of surfacing only during stash/pop.
