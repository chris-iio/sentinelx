---
id: S01
parent: M014
milestone: M014
provides:
  - An authoritative durable/transient/manual-review classifier for repo-local workflow state.
  - A supported boundary verifier that catches tracked/unignored transient blockers without hiding the legacy `.planning/**` backlog.
  - Executable Git regression proof for both tracked transient stash-pop conflicts and ignored/untracked transient checkout safety.
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - tools/runtime_state_boundary.py
  - tests/test_runtime_state_boundary.py
  - tests/test_runtime_state_boundary_git.py
  - .gitignore
  - Makefile
  - docs/runtime-state-boundary.md
  - README.md
key_decisions:
  - Keep `.planning/**` fail-closed as `manual-review` instead of auto-cleaning legacy planning state.
  - Treat milestone continue cursors as transient exceptions inside otherwise durable `.gsd/milestones/**` trees.
  - Make `make verify-runtime-boundary` fail only on blocker classes while still printing `manual-review-path` findings for downstream recovery/migration work.
patterns_established:
  - One checked-in classifier owns boundary decisions for ignore rules, audits, repair work, and later dev-loop tooling.
  - Repo-native workflow verification can stay green while still surfacing non-blocking legacy backlog by failing only on blocker issue codes.
  - Real temp-repo Git fixtures are the proof surface for stash/pop and checkout workflow regressions; mocks are not sufficient for this boundary seam.
observability_surfaces:
  - `python3 tools/runtime_state_boundary.py audit` with explicit issue codes: `tracked-transient`, `unignored-transient`, `manual-review-path`, `conflicting-rule-match`, `unknown-root`.
  - `make verify-runtime-boundary` as the supported operator/repo verifier.
  - Focused classifier and temp-repo Git regression suites under `tests/test_runtime_state_boundary.py` and `tests/test_runtime_state_boundary_git.py`.
drill_down_paths:
  - .gsd/milestones/M014/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M014/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-25T10:19:21.225Z
blocker_discovered: false
---

# S01: S01

**S01 established and verified the repo-local durable/transient boundary: SentinelX now has an authoritative runtime-state classifier, blocker-focused boundary verification, and temp-repo Git regression proof for the stash/pop conflict class.**

## What Happened

This slice turned the repo/runtime boundary from an implicit mix of ignore rules and operator folklore into an explicit checked-in contract. `tools/runtime_state_boundary.py` now classifies repo-local workflow paths as `durable`, `transient`, or `manual-review`, with durable milestone artifacts and canonical GSD ledgers preserved, transient `.gsd`/`.bg-shell` runtime surfaces fenced off, and legacy `.planning/**` deliberately left fail-closed for later migration work instead of being auto-cleaned. The repo-side wiring was aligned to that contract through `.gitignore`, index cleanup of known transient blockers, focused docs in `docs/runtime-state-boundary.md` and `README.md`, and a single supported verifier target in `Makefile`.

The slice also closed the proof gap around the original failure mode. `tests/test_runtime_state_boundary.py` pins representative classifications plus malformed/conflicting rule handling, and `tests/test_runtime_state_boundary_git.py` exercises real temp-repo Git flows showing that tracked transient `.gsd/audit/events.jsonl` is surfaced before stash-pop repair work, while ignored/untracked `.gsd/state-manifest.json` and `.gsd/event-log.jsonl` stay out of ordinary checkout flows. During closure, the verifier contract was tightened so `make verify-runtime-boundary` still prints the live `.planning/**` manual-review backlog for operators and downstream slices, but only fails on blocker classes (`tracked-transient`, `unignored-transient`, `conflicting-rule-match`, `unknown-root`). That preserves explicit visibility without re-breaking the supported proof lane. Together, the slice satisfies the M014/S01 goal: transient repo-local runtime state is behaviorally separated from durable planning artifacts, and the stash/conflict class is now either prevented by ignore/index policy or surfaced by an explicit repo-native audit command.

## Verification

Fresh slice-level verification passed on the final code: `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py` passed (10 tests); `make verify-runtime-boundary` passed with focused classifier + temp-repo Git proof and a live audit that reported only the intentional `manual-review-path` backlog under `.planning/**`; and `make verify-fast` passed end-to-end (`992 passed, 113 deselected` in pytest, `81 passed` in Vitest, successful `npx tsc --noEmit`, and a successful production build). I also confirmed the boundary observability surface works as designed by running `python3 tools/runtime_state_boundary.py audit --format text --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root`, which surfaced the `.planning/**` backlog while reporting zero blocker-class findings.

## Requirements Advanced

- R061 — Prevented or surfaced the stash/pop blocker class with classifier-backed ignore/index policy plus blocker-focused audit verification.
- R062 — Established the explicit repo boundary between durable planning artifacts and transient runtime state via a checked-in classifier, docs, and verifier.

## Requirements Validated

- R061 — `make verify-runtime-boundary` passed, and temp-repo Git fixtures proved tracked transient conflicts are surfaced while ignored transient files stay out of checkout workflows.
- R062 — Representative classification tests plus the final `tools/runtime_state_boundary.py`/`.gitignore`/`Makefile` contract proved durable `.gsd` artifacts, transient runtime files, and `.planning/**` manual-review paths are behaviorally separated.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

The closer adjusted the repo-native verifier contract so it fails only on blocker classes instead of all findings. This was necessary because the repo intentionally retains a large `.planning/**` manual-review backlog that must stay visible for later slices, but that backlog should no longer cause `make verify-runtime-boundary` itself to fail.

## Known Limitations

`.planning/**` still contains 237 manual-review legacy paths. They are intentionally surfaced in audit output and explicitly not auto-cleaned in this slice. S02 and later milestone work must preserve this conservative boundary unless they introduce a reviewed migration path.

## Follow-ups

S02 should build its repair/cleanup entrypoint on top of `tools/runtime_state_boundary.py` and the blocker-only verifier contract rather than inventing new path rules. S03 should ensure the supported local dev-process loop preserves the same durable/transient split and does not recreate tracked or unignored runtime blockers. S04 should re-prove the full assembled workflow, including the remaining manual-review backlog assumptions.

## Files Created/Modified

- `tools/runtime_state_boundary.py` — Added the authoritative boundary classifier/audit CLI and tightened the audit exit contract to fail only on blocker issue codes.
- `tests/test_runtime_state_boundary.py` — Pinned representative classifications, malformed/conflicting rule behavior, and selective fail-on-codes audit behavior.
- `tests/test_runtime_state_boundary_git.py` — Added temp-repo Git regression fixtures for tracked stash-pop blockers and ignored/untracked transient checkout safety.
- `.gitignore` — Aligned ignored repo-local runtime surfaces with the classifier-owned transient set.
- `Makefile` — Exposed `make verify-runtime-boundary` as the supported boundary verifier using blocker-class exit semantics.
- `docs/runtime-state-boundary.md` — Documented the class table, non-goal for `.planning/**` cleanup, and the blocker-focused verifier contract.
- `README.md` — Advertised the supported runtime-boundary verification lane and its intended use.
