# S01: Product-loop baseline and stale-plan cleanup

**Goal:** Reconcile M016 away from stale EmailRep execution and establish a concrete product-loop baseline before UI/runtime implementation.
**Demo:** The milestone docs, slice plan, and active state all describe SentinelX as a minimal local-first IOC evidence workbench; the current browser loop has specific audit targets and an initial runtime baseline target.

## Must-Haves

- M016 research and roadmap explicitly supersede EmailRep as the active implementation direction.
- S01 task plans point at product-loop audit and runtime baseline work, not provider integration.
- The current `/` → `/analyze` → results → history flow is audited for UI friction and product focus.
- At least one deterministic Offline paste-to-results timing path is identified and measured before speed claims.
- No code-level provider expansion is introduced in this slice.

## Proof Level

- This slice proves: documentation/state reconciliation + product-loop audit + baseline measurement.

## Integration Closure

The earlier email-provider launch plan is superseded by M016's product-hardening direction. Email provider coverage can be planned later as a separate provider milestone if the minimal product loop proves it is still a priority.

## Verification

- Documentation consistency check: grep M016 active docs/state/slice plans for stale provider-expansion execution titles.
- Runtime baseline command/artifact from T03.
- Browser or route-level audit notes from T02.

## Tasks

- [x] **T01: Replace stale EmailRep plan with minimal-product research and roadmap** `est:45m`
  Why: Execution must match the user's product question before implementation continues.
  - Files: `.gsd/milestones/M016/M016-RESEARCH.md`, `.gsd/milestones/M016/M016-ROADMAP.md`, `.gsd/STATE.md`, `.gsd/milestones/M016/slices/S01/*`
  - Verify: grep active M016 docs/state/slice plans for stale provider-expansion execution titles.

- [ ] **T02: Audit the current browser loop on desktop/mobile** `est:1h`
  Why: Identify concrete friction in the actual paste/extract/review/resume workflow before redesigning.
  - Files: `app/templates/index.html`, `app/templates/results.html`, result/filter partials, browser audit notes/artifact
  - Verify: audit notes include desktop and mobile observations tied to specific files/selectors.

- [ ] **T03: Capture Offline paste-to-results runtime baseline** `est:1h`
  Why: M016 speed work needs evidence before optimization claims.
  - Files: route/browser timing artifact or documented command output
  - Verify: baseline timing exists for Offline analysis route or browser submit path.

## Files Likely Touched

- `.gsd/milestones/M016/M016-RESEARCH.md`
- `.gsd/milestones/M016/M016-ROADMAP.md`
- `.gsd/STATE.md`
- `.gsd/milestones/M016/slices/S01/S01-PLAN.md`
- `.gsd/milestones/M016/slices/S01/tasks/T01-PLAN.md`
- `.gsd/milestones/M016/slices/S01/tasks/T01-SUMMARY.md`
- `.gsd/milestones/M016/slices/S01/tasks/T02-PLAN.md`
- `.gsd/milestones/M016/slices/S01/tasks/T03-PLAN.md`
