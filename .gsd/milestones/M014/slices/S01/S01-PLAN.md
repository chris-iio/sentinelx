# S01: Runtime state boundary hardening

**Goal:** Codify and enforce a conservative repo boundary between durable planning artifacts and transient runtime state so ordinary Git workflows stop tripping over tracked `.gsd`/adjacent runtime files, while ambiguous legacy planning trees are surfaced explicitly instead of being auto-cleaned.
**Demo:** After this: transient `.gsd` and adjacent repo-local runtime files are behaviorally separated from durable planning artifacts, and the stash/pop blocker class is either prevented by default or surfaced by explicit repo checks.

## Must-Haves

- ## Demo
- After this: transient `.gsd` and adjacent repo-local runtime files are behaviorally separated from durable planning artifacts, and the stash/pop blocker class is either prevented by default or surfaced by an explicit repo-native audit command.
- ## Must-Haves
- Ship one checked-in boundary classifier plus documentation that classifies representative `.gsd`, `.planning`, and `.bg-shell` paths as `durable`, `transient`, or `manual-review`/legacy.
- Expand repo ignore rules and remove unequivocally transient tracked files from the Git index without deleting working-tree contents; durable milestone ledgers and canonical `.gsd` docs remain tracked.
- Add temp-repo pytest coverage for both tracked-transient and untracked-transient stash/pop blocker classes so later slices inherit a real Git proof surface rather than path-string guesses.
- Expose one repo-native verification command in `Makefile` that runs the boundary audit and focused tests for S02/S03 reuse.
- ## Threat Surface
- **Abuse**: boundary tooling could silently classify durable planning docs as disposable or miss tracked transient blockers; automatic actions must stay scoped to an explicit transient allowlist and leave legacy/manual-review zones non-destructive.
- **Data exposure**: runtime logs/manifests may contain local machine state and workflow history; the boundary tooling must prevent those files from becoming durable tracked artifacts by accident.
- **Input trust**: file paths and Git command output are untrusted strings; the classifier/audit path must avoid shell interpolation hazards and reason over paths, not file contents.
- ## Requirement Impact
- **Requirements touched**: R061 and R062 directly; R063 and R065 as downstream guardrails.
- **Re-verify**: representative `git check-ignore` expectations, the repo audit command, the stash/pop regression fixture, and `make verify-fast` after `.gitignore` / `Makefile` / test changes land.
- **Decisions revisited**: D063 and D066 stay binding; S02 must consume this classifier/audit seam instead of inventing its own cleanup scope.
- ## Verification
- `pytest tests/test_runtime_state_boundary.py -q`
- `pytest tests/test_runtime_state_boundary_git.py -q`
- `python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues`
- `git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json`
- `make verify-fast`

## Proof Level

- This slice proves: - This slice proves: contract + integration proof at the repo/Git boundary.
- Real runtime required: yes — the proof must exercise real Git ignore/index behavior in temp repos and against the working tree.
- Human/UAT required: no.

## Integration Closure

- Upstream surfaces consumed: `.gitignore`, `Makefile`, Git index/ignore behavior, representative `.gsd/**` runtime files, `.planning/**` legacy planning files, `.bg-shell/**`, and the existing Python CLI/test pattern established by `tools/optimization_audit.py` plus `tests/test_optimization_audit.py`.
- New wiring introduced in this slice: `tools/runtime_state_boundary.py` becomes the authoritative classifier/audit seam; `Makefile` exposes the repo-native boundary verification command; `.gitignore` and index cleanup align the working tree with the classifier.
- What remains before the milestone is truly usable end-to-end: S02 still has to build the safe repair entrypoint on top of this seam, and S03 still has to make the supported dev-process loop preserve the same boundary.

## Verification

- Runtime signals: the audit command reports tracked-transient blockers, unignored transient files, and legacy/manual-review paths separately.
- Inspection surfaces: `python3 tools/runtime_state_boundary.py audit`, focused pytest files, `git check-ignore -v`, and `git status --short --ignored .gsd .planning .bg-shell`.
- Failure visibility: boundary regressions should surface as explicit issue codes / non-zero exits instead of surprise stash/pop conflicts.
- Redaction constraints: diagnostics should report path metadata and classification only; never print secret file contents.

## Tasks

- [x] **T01: Codify the durable/transient repo boundary in a checked-in classifier** `est:0.5d`
  Build the authoritative policy seam first so later ignore, deindex, cleanup, and dev-loop work all consume the same boundary contract instead of re-deriving it from ad hoc glob patterns.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Existing repo policy inputs in `.gitignore` plus representative `.gsd` / `.planning` / `.bg-shell` paths | Fail closed toward `manual-review` for ambiguous paths; never auto-promote a path into `transient` without an explicit rule | N/A | Treat unknown or conflicting patterns as `manual-review` and surface them in the audit output |
| New CLI contract in `tools/runtime_state_boundary.py` | Return a readable non-zero exit with issue details so later slices and CI can stop on policy drift | Keep execution local and bounded; no network or background work | Reject invalid path arguments and unsupported subcommands with clear usage text |
| Focused pytest contract in `tests/test_runtime_state_boundary.py` | Treat failing representative classifications as a blocker because every downstream slice depends on the policy being stable | N/A | Make mismatched class names and issue codes explicit in assertion messages |

## Load Profile

- **Shared resources**: the repo path-policy table and Git-facing audit logic that later slices will call repeatedly.
- **Per-operation cost**: one pure path classification plus lightweight Git state inspection per audited file; no file-content parsing or recursive shell pipelines in the hot path.
- **10x breakpoint**: policy drift or O(n²) path scans over repo-local runtime files; the task fails if the classifier becomes ambiguous or too coupled to specific filenames to scale across `.gsd` runtime surfaces.

## Negative Tests

- **Malformed inputs**: relative vs absolute paths, unknown roots, empty strings, and paths that intentionally straddle `.gsd`, `.planning`, and `.bg-shell` boundaries.
- **Error paths**: conflicting rule matches, unsupported commands, and representative legacy files that must resolve to `manual-review` instead of `transient`.
- **Boundary conditions**: durable milestone docs, canonical `.gsd` ledgers, tracked runtime streams like `.gsd/audit/events.jsonl`, transient manifests like `.gsd/state-manifest.json`, and adjacent legacy files like `.planning/STATE.md` / `.planning/HANDOFF.json`.

## Steps

1. Add `tools/runtime_state_boundary.py` with an explicit path-policy table and machine-readable classes for `durable`, `transient`, and `manual-review`/legacy.
2. Implement an `audit` subcommand that reports tracked-transient blockers, unignored transient files, and manual-review findings without mutating the repo.
3. Add focused pytest coverage for representative tracked paths so durable milestone docs stay durable, runtime streams stay transient, and `.planning` cursor files stay out of automatic cleanup.
4. Write a short checked-in document describing the supported classes, the non-goal for blanket `.planning/**` cleanup, and the expected handoff to S02/S03.

## Must-Haves

- [ ] The repo has one authoritative checked-in classifier for runtime-boundary decisions.
- [ ] Representative `.gsd`, `.planning`, and `.bg-shell` paths resolve to stable classes with focused regression tests.
- [ ] The audit command surfaces tracked-transient blockers and ambiguous/manual-review paths without changing repo state.
- [ ] The documentation explains why ambiguous legacy paths fail closed instead of being auto-cleaned.

## Verification

- `pytest tests/test_runtime_state_boundary.py -q`
- `python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json`

## Observability Impact

- Signals added/changed: stable class labels plus explicit audit issue codes for tracked-transient, unignored-transient, and manual-review findings.
- How a future agent inspects this: run the classifier/audit CLI directly and read `tests/test_runtime_state_boundary.py` for pinned examples.
- Failure state exposed: boundary regressions localize to a specific path class or audit issue instead of a later Git conflict.
  - Files: `.gitignore`, `.gsd/notifications.jsonl`, `.gsd/audit/events.jsonl`, `.planning/STATE.md`, `.planning/HANDOFF.json`, `.bg-shell/manifest.json`, `tools/optimization_audit.py`, `tests/test_optimization_audit.py`
  - Verify: pytest tests/test_runtime_state_boundary.py -q && python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json

- [x] **T02: Align `.gitignore`, tracked runtime files, and the repo-native boundary command** `est:0.75d`
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
  - Files: `tools/runtime_state_boundary.py`, `.gitignore`, `Makefile`, `README.md`, `docs/runtime-state-boundary.md`, `.gsd/audit/events.jsonl`, `.gsd/notifications.jsonl`, `.bg-shell/manifest.json`
  - Verify: python3 tools/runtime_state_boundary.py audit --format text --fail-on-issues && git check-ignore -v .gsd/state-manifest.json .gsd/event-log.jsonl .bg-shell/manifest.json && test -z "$(git ls-files .gsd/audit/events.jsonl .gsd/notifications.jsonl .bg-shell/manifest.json)"

- [x] **T03: Prove the stash/pop blocker class with temp-repo Git regression fixtures** `est:0.5d`
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
  - Files: `tools/runtime_state_boundary.py`, `Makefile`, `tests/test_runtime_state_boundary.py`, `docs/runtime-state-boundary.md`
  - Verify: pytest tests/test_runtime_state_boundary_git.py -q && make verify-runtime-boundary && make verify-fast

## Files Likely Touched

- .gitignore
- .gsd/notifications.jsonl
- .gsd/audit/events.jsonl
- .planning/STATE.md
- .planning/HANDOFF.json
- .bg-shell/manifest.json
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- tools/runtime_state_boundary.py
- Makefile
- README.md
- docs/runtime-state-boundary.md
- tests/test_runtime_state_boundary.py
