# S04 Research — Verification, review, and refactor closure

## Summary

S04 owns the two still-active milestone requirements:

- **R065** — preserve existing SentinelX verification and app behavior
- **R069** — end M014 with an explicit review/refactor pass over the changed workflow seams

This slice is **closure work, not a new subsystem**. S01-S03 already shipped the three core seams:

- `tools/runtime_state_boundary.py` + `make verify-runtime-boundary`
- `tools/runtime_state_repair.py` + `make repair-runtime-state`
- `tools/dev_server.py` + `make dev-server-start|status|restart|stop` + `GET /api/health`

What is still missing is the **final composed proof** and the **explicit review/refactor pass** across those seams.

The important project-level constraint from loaded knowledge applies here: **do not trust task/slice summaries alone**. Re-read the code and rerun proof commands from scratch before closure. S02’s compact summary is especially not detailed enough to use as the implementation source of truth.

This is **targeted research**, not deep research. The technology is familiar; the risk is in cross-seam composition and drift.

## Recommendation

Plan S04 as **three narrow tasks** in this order:

1. **Review the shipped workflow seam as code, not as summaries**
   - Read the S01-S03 implementation files and focused tests together.
   - Use the `review` skill rule: full-file context first, real issues only, no style churn.
   - Produce a short list of actual maintainability/drift risks.

2. **Land only minimal refactors that retire real drift/complexity risk**
   - Do **not** force refactors just to satisfy R069.
   - R069 requires an explicit review/refactor pass; it does **not** require gratuitous code motion if review finds no justified change.
   - If no real issue is found, record that the review passed with no code refactor required.

3. **Re-prove the assembled workflow after the final edit**
   - Run focused workflow tests first.
   - Then run the operator surfaces (`make repair-runtime-state`, dev-server lifecycle exercise, `make verify-runtime-boundary`).
   - Finish with repo verification (`make verify`).

The `verify-before-complete` skill should govern the closeout: **fresh evidence after the last code change**.

## Implementation Landscape

### Workflow seam files

- `tools/runtime_state_boundary.py`
  - Authoritative classifier and audit CLI.
  - Owns the durable/transient/manual-review policy and issue codes.
  - Natural review focus: classification priority/conflict handling, audit discovery, git inspection helpers.

- `tools/runtime_state_repair.py`
  - Mutating companion that maps classifier findings to actions.
  - Natural review focus: action planning, quarantine behavior, exit semantics, fail-closed behavior.

- `tools/dev_server.py`
  - Repo-native lifecycle manager for `start/status/restart/stop`.
  - Natural review focus: health probe contract, status-file validation, restart/failure synthesis, CLI surface duplication/complexity.

- `app/routes/api.py`
  - Produces `GET /api/health` contract consumed by `tools/dev_server.py`.
  - Natural review focus: drift against the manager’s expected health payload.

- `Makefile`
  - Operator-facing surface for repair, boundary verification, dev-server lifecycle, and repo verification lanes.
  - Important constraint from S03: Make targets should stay **thin wrappers** over the checked-in Python tools.

- `README.md`
- `docs/runtime-state-boundary.md`
  - Operator/docs contract for the workflow seam.
  - S04 should keep them aligned with whatever review/refactor outcome lands.

### Focused proof surface already exists

Boundary / classifier:
- `tests/test_runtime_state_boundary.py`
- `tests/test_runtime_state_boundary_git.py`

Repair / cleanup:
- `tests/test_runtime_state_repair.py`
- `tests/test_runtime_state_repair_git.py`

Dev lifecycle / health contract:
- `tests/test_api.py`
- `tests/test_dev_server.py`
- `tests/test_dev_server_process.py`

Repo-wide continuity:
- `make verify-fast`
- `make verify-deep`
- `make verify`

### Real review targets / likely refactor candidates

These are the main seams worth evaluating first:

1. **Duplicated health contract constant**
   - `tools/dev_server.py` and `app/routes/api.py` each define the same `HEALTH_PAYLOAD`.
   - This is a real drift risk: S03 intentionally locked the probe to an exact secret-free payload, but the producer and consumer do not share one source of truth.
   - S04 should decide whether to centralize this constant or explicitly accept duplication and document why.

2. **`tools/dev_server.py` is the complexity hotspot**
   - Largest functions are currently here:
     - `command_start` (~117 lines)
     - `DevServerStatus.from_payload` (~107 lines)
     - `probe_health` (~90 lines)
     - `refresh_status` (~52 lines)
   - If any refactor happens in S04, this file is the likeliest place.
   - The safest style is extraction of pure helpers while keeping CLI behavior and Makefile wrappers unchanged.

3. **Boundary/repair semantics are intentionally classifier-owned**
   - S02’s memory and code both reinforce this: `tools/runtime_state_repair.py` must not grow its own path policy.
   - Any refactor here must preserve `runtime_state_boundary.py` as the single policy source.

4. **Blocker-code list is repeated at the repo surface**
   - The fail-on codes are repeated in `Makefile` and documentation.
   - This is lower risk than the health payload duplication, but still a drift seam worth reviewing.

### Natural task seams

#### Seam A — review / issue selection
Read together:
- `tools/runtime_state_boundary.py`
- `tools/runtime_state_repair.py`
- `tools/dev_server.py`
- `app/routes/api.py`
- `Makefile`
- `README.md`
- `docs/runtime-state-boundary.md`
- focused tests listed above

Deliverable:
- short explicit review notes with any real issues found
- decision whether a code refactor is warranted

#### Seam B — minimal refactor
Only if review finds a justified issue.

Likely-safe changes:
- extract shared health payload constant/helper
- extract pure helper(s) from `tools/dev_server.py`
- tighten duplicated output/rendering logic

Avoid:
- widening cleanup scope
- changing `.planning/**` handling
- adding a second operator surface beside the existing Make + Python tools
- mixing `.bg-shell/**` into SentinelX’s supported lifecycle contract

#### Seam C — integrated closure proof
This is where R065 closes.

The slice should end with one explicit proof pass that demonstrates:
- boundary verification still passes with only `.planning/**` manual-review backlog visible
- repair surface stays conservative on the live repo
- dev lifecycle still supports start → health → crash detection → restart → stop
- full repo verification still passes

## Constraints and watchouts

- **`.planning/**` remains manual-review by design.**
  - Do not “clean it up” in S04.
  - Success remains: no blocker-class findings, with manual-review backlog still surfaced.

- **Do not invent a second lifecycle path.**
  - Supported surface remains `make dev-server-*` backed by `tools/dev_server.py`.
  - `.bg-shell/**` remains harness-owned and out of scope.

- **Do not split policy across tools.**
  - `tools/runtime_state_boundary.py` stays authoritative for path classification.
  - Repair must keep mapping issue-code → action, not glob → action.

- **Keep Makefile wrappers thin.**
  - S03 established the pattern: Python tool is implementation source of truth; Make is convenience only.

- **Do not trust prior summaries as proof.**
  - Re-run verification after the last edit.

## Verification

### Fresh verification run during research

These commands were freshly re-run during research and passed on the current state:

- `make verify-runtime-boundary`
  - `tests/test_runtime_state_boundary.py` → `7 passed`
  - `tests/test_runtime_state_boundary_git.py` → `3 passed`
  - live audit → `237` `manual-review-path` findings only, no blocker-class failures

- `python3 -m pytest -q tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
  - `46 passed`

- `make verify-fast`
  - backend pytest: `1017 passed, 113 deselected`
  - Vitest: `81 passed`
  - `npx tsc --noEmit` passed
  - production build passed

- `make verify-deep`
  - E2E pytest: `113 passed`

### Recommended final proof order for the executor

After the last code change in S04, rerun in this order:

1. `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py`
2. `make repair-runtime-state`
3. `make verify-runtime-boundary`
4. Live dev lifecycle exercise on an ephemeral localhost port:
   - `python3 tools/dev_server.py start --host 127.0.0.1 --port <free-port> --format json`
   - fetch `http://127.0.0.1:<free-port>/api/health`
   - kill managed child
   - `python3 tools/dev_server.py status --format json` until `crashed`
   - `python3 tools/dev_server.py restart --format json`
   - `python3 tools/dev_server.py stop --format json`
5. `make verify`

If S04 changes docs only after code verification, rerun the commands affected by those edits before claiming completion.

## Skill discovery

Installed skills directly relevant to this slice:
- `review` — use for the explicit review/refactor pass
- `verify-before-complete` — use before final completion claims

Optional non-installed skills worth considering later if this repo keeps doing Flask/pytest-heavy closure work:
- `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`
- `npx skills add github/awesome-copilot@pytest-coverage`

No install is needed for S04.

## Planner handoff

If you want the thinnest correct plan, decompose S04 into:

1. **Review task** — inspect the S01-S03 seam files/tests, identify any real issue(s), and decide whether a refactor is warranted.
2. **Refactor task** — only if the review found a justified drift/complexity issue; keep changes minimal and seam-local.
3. **Closure proof task** — rerun focused workflow tests, rerun operator surfaces, rerun `make verify`, then write the slice summary/UAT with explicit evidence.

The most likely actual code change is a **small dev-server / health-contract drift reduction**, not a broad workflow rewrite.
