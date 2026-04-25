# M014: Local workflow hardening and recovery loop

**Vision:** Harden SentinelX’s local operator loop so transient runtime-state stops polluting git workflows, repo-native repair/recovery becomes explicit and safe, and the supported local dev-process path handles crashes cleanly — then close with an explicit review/refactor pass.

## Success Criteria

- Ordinary local git workflows are no longer blocked by transient runtime-state in the observed stash/conflict class.
- Durable planning artifacts and transient machine/session state are behaviorally separated at the repo boundary.
- One supported repair/recovery entrypoint exists for local runtime-state cleanup and git-workflow repair.
- One supported local dev-process path exists, including cheap crash recovery for the local SentinelX server.
- Final proof shows the assembled workflow survives the triggering failure classes and preserves existing SentinelX verification.

## Slices

- [x] **S01: S01** `risk:High — if the durable/runtime boundary stays fuzzy, every later repair or dev-process change risks either breaking git workflows again or touching durable planning artifacts unsafely.` `depends:[]`
  > After this: After this: transient `.gsd` and adjacent repo-local runtime files are behaviorally separated from durable planning artifacts, and the stash/pop blocker class is either prevented by default or surfaced by explicit repo checks.

- [x] **S02: S02** `risk:High — cleanup logic is easy to get wrong, and an unsafe repair command would be more damaging than the current manual friction.` `depends:[]`
  > After this: After this: there is one supported repo-native recovery entrypoint that detects and repairs transient-state/git-workflow issues without silently touching durable milestone artifacts.

- [ ] **S03: S03** `risk:Medium — local process management is narrower than the boundary/cleanup work, but hidden assumptions in current ad hoc startup habits could still invalidate downstream closure if not retired here.` `depends:[]`
  > After this: After this: SentinelX has one supported local dev-process path, and a crashed local server can be detected and restarted through the supported workflow instead of manual archaeology.

- [ ] **S04: Verification, review, and refactor closure** `risk:Medium — the individual pieces may work in isolation but still compose badly; the final review/refactor pass is also easy to skip unless it is first-class scope.` `depends:[S01,S02,S03]`
  > After this: After this: the assembled workflow is re-proved against the original stash/conflict and crash-recovery classes, existing SentinelX verification still passes, and the changed seams get an explicit code review/refactor pass.

## Boundary Map

### S01 → S02

Produces:
- A concrete durable-vs-transient path policy for repo-local `.gsd` and adjacent workflow state
- Ignore/classification rules that identify stash/pop blocker candidates without touching durable milestone artifacts
- A reproducible fixture or verifier for the triggering stash/pop conflict class

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- The supported definition of which local state is runtime-owned versus durable
- The repo-local contract the dev-process loop must preserve when starting, stopping, or restarting services

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- One supported repo-native repair/recovery entrypoint
- Deterministic cleanup/report behavior for transient runtime-state and git-workflow blockers
- Integration proof that the supported repair path resolves the observed stash/pop blocker class conservatively

Consumes from S01:
- Durable/transient path policy and stash/conflict fixture

### S03 → S04

Produces:
- One supported local dev-process path with explicit restart behavior
- Detectable crash/restart flow for the local SentinelX server
- Process-state conventions that work with, not against, the repair surface

Consumes from S01:
- Durable/transient path policy and repo-local state boundary
