# S04 seam review

## Files inspected

Primary seam files:
- `tools/runtime_state_boundary.py`
- `tools/runtime_state_repair.py`
- `tools/dev_server.py`
- `app/routes/api.py`

Focused proof and contract files:
- `tests/test_runtime_state_boundary_git.py`
- `tests/test_runtime_state_repair_git.py`
- `tests/test_dev_server_process.py`
- `tests/test_dev_server.py`
- `tests/test_api.py`
- `Makefile`
- `README.md`
- `docs/runtime-state-boundary.md`
- `.gsd/DECISIONS.md` (`D067`, `D068`, `D069`)

## Seam invariants that must not change

1. **classifier-owned boundary policy**
   - `tools/runtime_state_boundary.py` stays the sole path-policy source.
   - `tools/runtime_state_repair.py`, `Makefile`, docs, and tests may consume classifier issue codes and behavior, but they must not grow a second policy table or parallel durable/transient classifier.

2. **classifier-owned repair actions**
   - `tools/runtime_state_repair.py` must stay a thin mutating companion to the classifier.
   - Supported automatic mutations remain limited to `tracked-transient` deindexing and `unignored-transient` quarantine.
   - `.planning/**` remains explicit `manual-review` / report-only behavior; no auto-cleanup, deindex, or quarantine should be added for those paths.

3. **thin Make wrappers**
   - `make repair-runtime-state` and `make verify-runtime-boundary` remain wrapper/verification surfaces over the checked-in tools.
   - `make dev-server-start|status|restart|stop` remain thin wrappers over `tools/dev_server.py`; T02 must not add a second server lifecycle entrypoint.

4. **local-only dev-server ownership**
   - `tools/dev_server.py` remains the single implementation source of truth for the supported SentinelX local server loop.
   - Managed state stays under `.gsd/runtime/dev-server/**`, remains transient, and stays separate from `.bg-shell/**` and `.planning/**`.
   - Host validation stays localhost-only and fail-closed.

5. **secret-free status/health output**
   - `GET /api/health` stays a fixed, secret-free contract.
   - `python3 tools/dev_server.py status --format json` continues to expose path-and-metadata only (`status`, `pid`, `restart_count`, `last_failure_reason`, probe summary, managed paths) without runtime log contents or provider keys.
   - The dev-server probe must continue to reject extra fields rather than silently tolerating secret-bearing payload drift.

## refactor-now

### Retire the duplicated health contract now

**Decision:** yes — retire the shared health contract seam in T02.

**Why this is the one justified refactor:**
- `app/routes/api.py` hardcodes the health payload producer contract.
- `tools/dev_server.py` separately hardcodes both `HEALTH_PATH` and `HEALTH_PAYLOAD` for its probe consumer contract.
- `tests/test_api.py`, `tests/test_dev_server.py`, and `tests/test_dev_server_process.py` all pin the same contract from different sides of the seam.
- This is real drift risk: changing the payload in one place but not the other would break local lifecycle health checks even though the boundary/repair subsystems are otherwise unchanged.

**T02 target shape:**
- Add `app/health_contract.py` as the single checked-in source for the local health contract.
- Move only the shared contract constants there (`HEALTH_PATH`, `HEALTH_PAYLOAD`).
- Update `app/routes/api.py` to produce that contract.
- Update `tools/dev_server.py` to consume that contract for `build_health_url()` and `probe_health()`.

**Constraints for T02:**
- Keep the refactor seam-local; do not widen into boundary policy, repair behavior, Make targets, README flow, or `.planning/**` handling.
- Preserve the exact JSON payload and exact path already pinned by tests.
- Preserve the current fail-closed probe behavior (`payload != HEALTH_PAYLOAD` stays malformed).
- Preserve direct CLI execution of `python3 tools/dev_server.py ...`; the shared-contract import must work for script execution and tests without introducing a second fallback copy of the constants.

## leave-alone

### Boundary classifier and repair seam
- `tools/runtime_state_boundary.py` already expresses the conservative three-class policy from `D067` and remains the correct authoritative seam.
- `tools/runtime_state_repair.py` already follows `D068`: it reuses classifier-owned findings and keeps `.planning/**` blocked/report-only.
- No refactor is justified here for T02 beyond continuing to consume existing issue codes.

### Dev-server lifecycle/state model
- `tools/dev_server.py` already follows `D069`: localhost-only ownership, managed runtime state under `.gsd/runtime/dev-server/**`, explicit statuses, restart counting, and secret-free failure summaries.
- The lifecycle/status state machine (`stopped|starting|running|stale|crashed`) is already explicit and covered by focused tests; T02 should not reopen it.

### Wrapper/docs/operator seam
- `Makefile` wrappers are already thin and should stay thin.
- `README.md` and `docs/runtime-state-boundary.md` already describe the supported loop and the transient/runtime boundary clearly enough for this slice.
- T02 should not broaden into docs churn unless a shared-contract import path forces a tiny wording correction.

### `.planning/**` handling
- The current manual-review seam is intentional and proven by both code and tests.
- There is no justification in this review for adding `.planning/**` ignore rules, cleanup automation, or migration logic in S04.

## Accepted no-change areas for T02

- No second path-policy table.
- No `.planning/**` auto-cleanup or automatic migration.
- No `.bg-shell` integration or alternate local-server workflow.
- No changes to repair action codes or quarantine layout.
- No change to health endpoint semantics beyond single-sourcing the existing contract.
- No new health/status fields, and no relaxation that would allow secret-bearing payloads to look healthy.
- No refactor of unrelated API routes, orchestrator polling, or full verification lanes.

## T02 handoff

If T02 does only one thing, it should be this:
1. single-source the health contract,
2. keep the exact existing payload/path,
3. preserve direct `tools/dev_server.py` execution,
4. leave boundary/repair/local-lifecycle ownership untouched.

Anything beyond that is scope creep relative to this review.
