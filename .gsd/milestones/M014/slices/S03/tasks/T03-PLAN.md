---
estimated_steps: 4
estimated_files: 4
skills_used:
  - write-docs
  - observability
  - verify-before-complete
---

# T03: Expose the supported Makefile workflow and continuity proof

Make the lifecycle manager the supported operator path and prove it composes with the existing boundary and fast verification lanes. This task closes the slice by turning the direct CLI into the documented repo-native workflow contributors are supposed to use.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `Makefile` wrapper targets | Stop and fix the wrapper names/flags instead of leaving multiple unsupported startup paths in the repo | N/A | Treat wrapper drift from `tools/dev_server.py` as a blocker, not doc debt |
| Contributor docs in `README.md` / `docs/runtime-state-boundary.md` | Keep one canonical flow; if docs and code disagree, update them together before closing the slice | N/A | Remove ambiguous or harness-specific guidance rather than layering alternatives |
| Existing repo verification lanes | If `make verify-runtime-boundary` or `make verify-fast` regress, repair the code/docs before claiming the supported loop is shippable | Let the repo-native commands own the timing; no background supervisors | Treat unexpected failures as slice blockers because they undermine `R065` support |

## Load Profile

- **Shared resources**: repo-native command surface, build/test lanes, and the ignored `.gsd/runtime/dev-server/**` subtree.
- **Per-operation cost**: thin Make wrappers plus the existing verification commands.
- **10x breakpoint**: wrapper/doc drift that sends contributors back to ad hoc `python run.py` habits.

## Negative Tests

- **Malformed inputs**: missing Make targets, stale docs, and unsupported references to `.bg-shell/**` or manual runtime-file cleanup.
- **Error paths**: wrapper targets that bypass lifecycle state, docs that imply PID files are enough, and verification lanes that fail after wiring.
- **Boundary conditions**: `make dev-server-status` when nothing is running, clean repo/no-op runtime boundary audit, and routine `make verify-fast` continuity after the new workflow lands.

## Steps

1. Add repo-native Make targets `dev-server-start`, `dev-server-status`, `dev-server-restart`, and `dev-server-stop` that wrap `tools/dev_server.py` and keep the CLI as the single implementation source of truth.
2. Update `README.md` with the supported local dev loop, the crash-recovery/status path, and the rule that `.gsd/runtime/dev-server/**` is manager-owned transient state rather than checked-in workflow data.
3. Update `docs/runtime-state-boundary.md` so the boundary documentation explicitly includes the dev-server runtime subtree and keeps `.bg-shell/**` and `.planning/**` guidance aligned with S01/S02.
4. Re-run the focused dev-loop tests plus `make verify-runtime-boundary` and `make verify-fast` so this slice advances `R064` without regressing the broader repo proof lane that S04 will depend on.

## Must-Haves

- [ ] The documented operator path is `make dev-server-start|status|restart|stop`, not ad hoc `python run.py` archaeology.
- [ ] Docs explain where lifecycle state lives and why it remains transient/ignored.
- [ ] The new workflow keeps the runtime-boundary verifier green and preserves the default `make verify-fast` continuity lane.
- [ ] Wrapper names, docs, and CLI flags stay in sync so contributors have one obvious local-server path.

## Inputs

- ``tools/dev_server.py``
- ``Makefile``
- ``README.md``
- ``docs/runtime-state-boundary.md``
- ``tests/test_api.py``
- ``tests/test_dev_server_process.py``

## Expected Output

- ``Makefile``
- ``README.md``
- ``docs/runtime-state-boundary.md``
- ``tools/dev_server.py``

## Verification

`grep -n "^dev-server-start:\|^dev-server-status:\|^dev-server-restart:\|^dev-server-stop:" Makefile`
`python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
`make verify-runtime-boundary`
`make verify-fast`

## Observability Impact

- Signals added/changed: repo-native `dev-server-*` commands become the supported inspection surface layered over the manager's status JSON and health probe.
- How a future agent inspects this: `make dev-server-status`, `python3 tools/dev_server.py status --format json`, `make verify-runtime-boundary`, and `make verify-fast`.
- Failure state exposed: wrapper failures, boundary regressions, and fast-lane continuity failures are now part of the documented workflow instead of tribal knowledge.
