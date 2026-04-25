# M014: Local workflow hardening and recovery loop

**Gathered:** 2026-04-25
**Status:** Ready for planning

## Project Description

M014 is repo/operator hardening work for SentinelX. It is not a new analyst-facing product feature. The milestone exists because transient local runtime-state is still able to interfere with normal git workflows, and local process recovery still depends too much on noticing failures and cleaning up by hand. The concrete trigger was a `git stash pop` failure caused by `.gsd` runtime-state files colliding with local repo state, followed by a separate crashed local Flask process surfacing as a background-process alert.

The goal is to make the local loop safer and more legible: durable planning artifacts should have a sharper behavioral boundary from machine/session state, there should be one supported repo-native repair surface for cleanup and recovery, and there should be one supported local dev-process path with cheap crash recovery. The milestone ends with an explicit code review/refactor pass over the changed workflow seams.

## Why This Milestone

SentinelX’s product-facing work is in a strong state after M013, but the local operator loop is still fragile in ways that slow or block future work. If transient `.gsd` state can still wedge stash/pop or leave the repo in an ambiguous state, and if crashed local processes still require manual archaeology, then the cost of every later milestone stays higher than it should be.

This milestone solves that now because the product surface is stable enough to support workflow hardening, and because the failure modes are already concrete rather than hypothetical. The repo already tries to distinguish durable `.gsd` artifacts from runtime noise; M014 exists to finish that seam instead of leaving it half-true.

## User-Visible Outcome

### When this milestone is complete, the user can:

- run ordinary local git workflows without transient `.gsd` runtime-state unexpectedly blocking them in the failure class we already observed
- recover from wedged local runtime-state or a crashed local server through one supported repo-native recovery path instead of manual cleanup and guesswork

### Entry point / environment

- Entry point: local repo workflow (`git stash`, local repair command, supported dev entrypoint, Makefile-driven verification)
- Environment: local dev shell with repo-local `.gsd` state and local SentinelX server process
- Live dependencies involved: git, repo-local `.gsd` runtime state, local Flask process, background shell/process metadata

## Completion Class

- Contract complete means: the repo clearly distinguishes durable planning artifacts from transient runtime/session state, and the supported repair/dev entrypoints exist with deterministic behavior
- Integration complete means: the repair path, git-facing state boundary, and supported local dev-process loop work together on the same local repo state rather than as isolated scripts
- Operational complete means: a crashed supported local server can be detected and restarted cheaply, and transient runtime-state cleanup does not silently damage durable milestone artifacts

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- the stash/pop blocker class that triggered this milestone is either prevented by default or recoverable through the supported repair path
- a crashed local SentinelX server can be brought back through the supported local dev-process path without manual archaeology
- existing SentinelX verification still passes after the workflow hardening and final review/refactor pass

## Scope

### In Scope

- hardening the repo-local boundary between durable planning artifacts and transient runtime/session state
- fixing the observed stash/pop blocker class and adjacent repo workflow debris, not just the two exact files from the triggering failure
- adding one supported repo-native repair surface for cleanup and recovery
- adding or standardizing one supported local dev-process ownership/restart path
- ending the milestone with explicit code review/refactor across the changed workflow seams

### Out of Scope / Non-Goals

- adding a new analyst-facing SentinelX feature
- depending on immediate upstream GSD engine changes outside this repository
- preserving today’s local workflow unchanged for its own sake if the current behavior is part of the problem

## Architectural Decisions

### Durable vs transient state boundary

**Decision:** Keep durable planning artifacts in-repo, but treat transient machine/session state as runtime-only with a sharper repo-local boundary.

**Rationale:** The repo already partially distinguishes durable `.gsd` artifacts from runtime noise, but the seam is incomplete. That partial boundary is what allowed transient state to interfere with stash/pop while other runtime areas were already ignored.

**Evidence source:** Current `.gitignore`, live `git stash pop` failure, and the actual `.gsd/` tree showing ignored runtime directories alongside still-visible transient files.

**Alternatives Considered:**
- Leave the existing layout alone and document cleanup better — rejected because the failure mode stays live.
- Move all `.gsd` state out of the repo immediately — rejected for now because M014 should solve the problem at the repo boundary first, without assuming upstream engine changes.

### Repo-native repair surface

**Decision:** Add one supported repo-native repair/recovery entrypoint instead of relying on manual git and process cleanup.

**Rationale:** Recovery is currently implicit and scattered across git output, runtime files, and background-process alerts. One explicit repair surface makes cleanup rules visible, testable, and safer.

**Evidence source:** Triggering stash/pop conflict, separate crashed `sentinelx-flask` process alert, and the current absence of a single obvious recovery command in the repo surface.

**Alternatives Considered:**
- Pure documentation/manual recovery — rejected because it does not reduce workflow friction.
- Immediate startup-time self-healing — deferred until cleanup rules are explicit and proven safe.

### Supported local dev-process loop

**Decision:** Standardize one supported local dev-process path with explicit ownership and cheap restart behavior.

**Rationale:** Runtime-state cleanup and local process recovery are related operator problems. A safer cleanup path without a supported local process loop still leaves contributors in ad hoc restart territory.

**Evidence source:** Current crash alert behavior and the lack of a single repo-blessed local dev-process ownership model.

**Alternatives Considered:**
- Keep ad hoc process starts and only improve cleanup — rejected because lifecycle behavior remains inconsistent.
- Introduce a heavier external supervisor/orchestrator — rejected for now unless repo-local hardening proves insufficient.

### Repo-boundary-first constraint

**Decision:** Solve M014 at the SentinelX repo boundary first rather than assuming upstream GSD engine changes outside this repository.

**Rationale:** Repo-local hardening is directly shippable here and keeps the milestone tractable. Upstream engine changes may still be worthwhile later, but they are not required to retire the current failure modes.

**Evidence source:** Discussion constraint and the fact that the triggering failures are observable from repo-local state and process behavior.

**Alternatives Considered:**
- Make upstream engine redesign a prerequisite — rejected because it would block practical local improvements we can ship now.

## Error Handling Strategy

Keep the cleanup path conservative. Transient runtime-state that is clearly machine-owned can be ignored, pruned, or quarantined through the supported repair flow. Anything ambiguous should be surfaced before deletion rather than silently removed. Durable milestone/context/summary artifacts are never auto-cleaned.

Git-facing workflow failures should be detected before they recur where practical, and the supported repair path should prefer non-destructive cleanup first. Process failures should be loud and cheap to recover from: the supported local dev entrypoint should make restart obvious, stale process metadata should not block a clean restart, and crash state should be summarized in a small explicit report rather than left scattered across logs. If a condition is unsafe to auto-fix, the tool should stop and say why.

## Risks and Unknowns

- The durable/runtime boundary may be messier than it first appears — if more transient files are treated as source-like today, boundary hardening could need broader repo changes than the triggering failure suggests.
- Cleanup classification may have gray areas — deleting or ignoring the wrong `.gsd` files would be worse than leaving some noise in place.
- The supported local dev-process path may expose hidden assumptions in current ad hoc startup/restart behavior.

## Existing Codebase / Prior Art

- `.gitignore` — already contains a partial `.gsd` runtime-ignore model; M014 should extend or sharpen it instead of inventing a second policy language
- `README.md` — documents the current verification and audit command surface that M014 must preserve while hardening the local workflow around it
- `.gsd/` runtime tree — shows the current mixed state of durable milestone artifacts and transient runtime/session files
- `Makefile` — likely home for the supported repo-native repair or supported local dev-process entrypoints if they belong in the normal repo surface

## Relevant Requirements

- R061 — prevent runtime-state from blocking normal Git workflows
- R062 — establish the durable/transient repo boundary
- R063 — add the supported repair/recovery entrypoint
- R064 — add the supported local dev-process path with cheap crash recovery
- R065 — preserve existing SentinelX verification and app behavior
- R069 — end with explicit review/refactor closure

## Technical Constraints

- Do not silently delete durable milestone/context/summary artifacts
- Do not assume immediate upstream GSD engine changes outside this repository
- Preserve the existing SentinelX verification contract (`verify-fast`, `verify-deep`, `verify`) on the final milestone state

## Integration Points

- Git — stash/pop and related local repo operations must stop colliding with transient runtime-state in the observed failure class
- `.gsd` runtime and milestone artifacts — the milestone hardens the boundary between durable planning records and machine/session state
- Makefile / repo-native commands — likely surface for supported repair and dev entrypoints
- Local Flask/dev process — crash detection and supported restart behavior must be part of the final assembled workflow

## Testing Requirements

Use layered proof. Contract tests should classify runtime vs durable paths and verify conservative cleanup behavior around ambiguous files. Integration/shell tests should reproduce the stash-blocking class with fixture state and prove the supported repair path resolves it. Process/integration proof should simulate a dead local server state and prove the supported dev-process path restores a usable local loop. Final milestone proof must rerun existing SentinelX verification to show the workflow hardening did not regress the product.

## Acceptance Criteria

- The specific stash/pop blocker class that triggered M014 is prevented by default or recoverable through one repo-native repair entrypoint
- Transient `.gsd` runtime files and durable planning artifacts are separated by real repo behavior, not just comments or docs
- There is one supported local dev-process path, and a crashed local server is detectable and restartable through that path
- The recovery path stays conservative around durable milestone/context/summary artifacts
- The changed workflow seams receive an explicit review/refactor pass after integration proof
- Existing SentinelX verification still passes on the final state

## Open Questions

- Which exact repo-native command surface is most natural for the supported repair and supported dev entrypoints (`make`, script wrapper, or both)?
- Whether repo-local quarantine is a better default than deletion for some classes of transient runtime debris
