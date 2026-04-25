# M014/S02 — Research

**Date:** 2026-04-25

## Summary

This is **targeted research** for **R063** (supported local recovery entrypoint), consuming the validated S01 boundary work from **R061/R062**. The important current-state finding is that the live repo is already clean of blocker-class boundary failures: `python3 tools/runtime_state_boundary.py audit --format text --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root` now reports **237 `manual-review-path` findings only**, all under `.planning/**`. That means S02 is no longer an emergency deindex slice for this repo; it is a **productization slice** that must turn the classifier/audit seam into one safe, repeatable repair command that is a no-op on today’s clean boundary and only mutates paths the classifier already marks as transient.

The safest architecture is to **keep `tools/runtime_state_boundary.py` inspection-only** and add a separate mutating repair CLI that imports its helpers. S01’s boundary tool currently promises that it never mutates the working tree, and the repo/docs/tests are already built around that purity. S02 should preserve that contract, then layer a repair surface on top: `tracked-transient` findings are safe to auto-fix with `git rm --cached -- <path>` because the working-tree file remains; `manual-review-path`, `conflicting-rule-match`, and `unknown-root` findings must remain report-only; and any transient file that exists but is not ignored should be handled conservatively via **quarantine into an already-ignored transient area**, not blanket deletion.

A second important constraint surfaced during research: the repo already contains **real transient runtime trees** (`.gsd/runtime/**`, `.gsd/activity/**`, `.bg-shell/**`) and a **registered `.gsd/worktrees/M005` worktree**. S02 should therefore avoid broad cleanup primitives like `rm -rf .gsd/*` or blind `git worktree prune` calls. The repair surface needs **per-finding actions**, not directory-level scrubbing. This also lines up with the recent safety notification stream, which flagged a recursive delete attempt as destructive during the failed S02 research run.

## Recommendation

Ship **one supported repo-native entrypoint** as a Make target wrapping a new repair CLI:

- Human-facing entrypoint: `make repair-runtime-state` (name can vary, but keep it singular and explicit)
- Implementation: `python3 tools/runtime_state_repair.py`
- Boundary dependency: import and reuse `tools/runtime_state_boundary.py` helpers (`audit_paths`, issue codes, path normalization) instead of re-deriving glob rules

Recommended repair behavior:

1. Run the boundary audit first.
2. For `tracked-transient` findings:
   - fix with `git rm --cached -- <path>`
   - keep the working-tree file in place
   - report which paths were deindexed
3. For `unignored-transient` findings:
   - move the live file into a timestamped quarantine under an **already transient/ignored subtree** such as `.gsd/runtime/repair-quarantine/<timestamp>/...`
   - do **not** auto-edit `.gitignore` at runtime
   - report that recurrence means policy drift must be fixed in code
4. For `manual-review-path`, `conflicting-rule-match`, and `unknown-root` findings:
   - never mutate
   - print them as explicit blockers / follow-up items
5. Exit cleanly when there is nothing actionable so the command is safe to run on every local repo before or after a rough git workflow.

Why this shape:

- It preserves S01’s core rule: **one checked-in classifier owns the boundary**.
- It keeps `audit` pure and composable for S04 verification.
- It avoids silently touching durable milestone artifacts or the mixed `.planning/**` legacy tree.
- It gives S03 a stable recovery seam to compose with later process ownership/restart work, without prematurely pulling server lifecycle into S02.

## Implementation Landscape

### Key Files

- `tools/runtime_state_boundary.py` — authoritative durable/transient/manual-review classifier plus Git-aware audit helpers. Reuse this module; do not fork its rule table into a second script.
- `tests/test_runtime_state_boundary.py` — focused examples of path classification, fail-on-codes behavior, and Git inspection semantics. Use as the pattern for repair-tool unit coverage.
- `tests/test_runtime_state_boundary_git.py` — already has the temp-repo stash/pop fixture and the ignored/untracked checkout-safety fixture. These are the exact proof surfaces S02 should extend after adding repair behavior.
- `Makefile` — current repo-native workflow surface. Add the supported repair target here next to `verify-runtime-boundary`.
- `README.md` — currently documents only the verifier. Needs the supported repair command and a short “what it will / will not touch” contract.
- `docs/runtime-state-boundary.md` — boundary contract doc. Extend it with the repair entrypoint, action table, and the explicit non-goal for `.planning/**` mutation.
- `run.py` — confirms that app startup is still manual `python run.py`; useful mainly as a boundary note that server restart remains S03 scope, not S02 scope.
- `.bg-shell/manifest.json` — currently ignored/transient and empty; good reminder that process-state cleanup belongs to the same boundary, but process restart semantics should stay out of S02.
- `.gsd/worktrees/M005` — a live registered worktree inside a transient subtree. This is why S02 must not implement blanket `.gsd/worktrees/**` deletion.

### Natural seams

1. **Repair engine**
   - New file: `tools/runtime_state_repair.py`
   - Responsibilities: consume audit findings, map issue codes to actions, perform conservative mutations, print a readable summary

2. **Repair proof**
   - New tests likely split into:
     - `tests/test_runtime_state_repair.py` for action-selection/idempotency/reporting
     - `tests/test_runtime_state_repair_git.py` for temp-repo mutation proof
   - Reuse the same temp-repo Git setup helpers/patterns as `tests/test_runtime_state_boundary_git.py`

3. **Repo-native surface + docs**
   - `Makefile`, `README.md`, `docs/runtime-state-boundary.md`
   - Keep this wiring thin; the behavioral complexity should stay in the repair CLI and its tests

### Build Order

1. **Add the repair module without mutation first.**
   Start by loading the boundary audit and translating findings into explicit planned actions / blocked actions. This gives the planner a stable action table before any filesystem or Git mutation exists.

2. **Implement `tracked-transient` repair first.**
   This is the clearest safe auto-fix and directly addresses the original stash/pop blocker class. Use the existing temp-repo tracked-transient fixture and prove the path is no longer in `git ls-files` after repair.

3. **Add quarantine for `unignored-transient` findings.**
   Only after tracked-transient is proven. The quarantine path should live under an already transient/ignored subtree so S02 does not need another ignore-policy change.

4. **Wire the Make target and docs last.**
   Once the CLI behavior and tests are stable, expose the single supported command and document its safety boundaries.

### Verification Approach

Use fresh temp-repo proof plus one live-repo no-op check:

- **Tracked transient repair fixture**
  - Seed tracked `.gsd/audit/events.jsonl`
  - Run the repair CLI
  - Assert the path is no longer tracked
  - Assert `python3 tools/runtime_state_boundary.py audit --fail-on-codes tracked-transient ...` is clean
  - Optionally re-run the stash/pop reproduction to prove the blocker class is retired by the repair path

- **Unignored transient quarantine fixture**
  - Seed an unignored transient like `.gsd/state-manifest.json`
  - Run the repair CLI
  - Assert the original path is gone
  - Assert a quarantined copy exists under `.gsd/runtime/repair-quarantine/...`
  - Assert the audit no longer reports `unignored-transient`

- **Manual-review safety fixture**
  - Seed `.planning/STATE.md`
  - Run the repair CLI
  - Assert the file is untouched
  - Assert the command reports the path but does not mutate it

- **Live repo no-op proof**
  - Run the supported repair command on the current repo
  - Expect “no actionable transient repairs” (or equivalent)
  - Confirm the command does not touch `.planning/**` and does not create blocker findings
  - Re-run `make verify-runtime-boundary`

## Constraints

- `git check-ignore` alone is insufficient; S01 proved tracked files must be checked with `git ls-files` too. The repair tool must use the full audit result, not ignore checks alone.
- `tools/runtime_state_boundary.py` should stay inspection-only. Its current docs/tests assume that contract.
- Do **not** auto-clean `.planning/**`. The live repo still has 237 manual-review findings there, and that backlog is intentional.
- Do **not** treat all of `.gsd/**` as disposable. Durable exceptions include `.gsd/milestones/**`, canonical ledgers, and `.gsd/reports/**`.
- Avoid blanket recursive deletion. Recent notify/safety output already flagged that pattern as destructive during a failed S02 attempt.

## Common Pitfalls

- **Overloading S02 with process restart work.** Repairing runtime-state and restart semantics are related, but `run.py` is still the only app entrypoint and the milestone explicitly assigns cheap crash recovery to S03.
- **Mutating the live repo as the main proof surface.** The current repo is already blocker-clean; the real proof must come from temp repos that recreate the failure classes.
- **Pruning worktrees blindly.** `.gsd/worktrees/M005` is currently registered in `git worktree list --porcelain`; broad worktree cleanup would be unsafe.
- **Writing quarantine output into durable artifact trees.** Keep quarantine in an already transient/ignored subtree so S02 does not create new tracked evidence by accident.

## Relevant skill guidance

- **`debug-like-expert`**: use evidence-first repair logic. The repair tool should act only on explicit boundary issue codes, not on guessed filename patterns.
- **`verify-before-complete`**: do not claim the repair surface works until a fresh temp-repo repair run and a fresh live-repo no-op run both happen in the same closing message.

## Skills Discovered

- No directly relevant installed skill exists for repo-local runtime repair.
- Promising optional external skill if the user wants one later: `akillness/oh-my-skills@git-workflow` (`npx skills add akillness/oh-my-skills@git-workflow`). It is relevant to Git workflow heuristics, but S02 can proceed without it because the core boundary/repair logic is repo-specific and already defined locally.
