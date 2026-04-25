---
estimated_steps: 7
estimated_files: 8
skills_used:
  - debug-like-expert
  - test
  - verify-before-complete
---

# T01: Codify the durable/transient repo boundary in a checked-in classifier

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

## Inputs

- ``.gitignore``
- ``.gsd/notifications.jsonl``
- ``.gsd/audit/events.jsonl``
- ``.planning/STATE.md``
- ``.planning/HANDOFF.json``
- ``.bg-shell/manifest.json``
- ``tools/optimization_audit.py``
- ``tests/test_optimization_audit.py``

## Expected Output

- ``tools/runtime_state_boundary.py``
- ``tests/test_runtime_state_boundary.py``
- ``docs/runtime-state-boundary.md``

## Verification

pytest tests/test_runtime_state_boundary.py -q && python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json

## Observability Impact

- Signals added/changed: stable class labels and audit issue codes for tracked-transient, unignored-transient, and manual-review findings.
- How a future agent inspects this: `python3 tools/runtime_state_boundary.py audit --format text` and `pytest tests/test_runtime_state_boundary.py -q`.
- Failure state exposed: classifier drift shows up as explicit audit findings instead of latent Git surprises.
