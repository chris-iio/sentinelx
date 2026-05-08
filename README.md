<p align="center">
  <img src="app/static/images/screenshot.png" alt="SentinelX" width="600">
</p>

## Launch/readiness artifacts

- `docs/code-analysis-launch-deck.html` summarizes the code audit, market research, launch positioning, and verification evidence as an HTML slide deck.
- `docs/launch-checklist.md` defines the release artifact boundary, clean install smoke path, required pre-launch proof, positioning, and roadmap candidates.

## Supported local dev-server workflow

Use the repo-native manager commands as the one supported local server path:

- `make dev-server-start` launches the manager-owned child and waits for the fixed `GET /api/health` contract to report healthy.
- `make dev-server-status` is the routine inspection surface. It reports the current manager state, recorded PID/log path, restart count, last failure timestamp/reason, and live probe result without dumping runtime log contents.
- `make dev-server-restart` is the supported crash-recovery path after a stale/crashed child or any time you need a cheap clean restart.
- `make dev-server-stop` stops the manager-owned child without asking contributors to hunt for PID files or background supervisors.
- `python3 tools/dev_server.py status --format json` remains the machine-readable inspection surface; the Make targets are thin wrappers over that checked-in CLI so the repo has one implementation source of truth.

The manager owns `.gsd/runtime/dev-server/**` as transient repo-local state. Treat that subtree as path-and-metadata only: inspect it through the commands above, do not check it in, and do not manually edit or clean up `status.json`, PID metadata, or managed log paths as part of the normal workflow. If the runtime boundary looks suspect, re-run `make verify-runtime-boundary` instead of improvising a second server path.

## Verification lanes

SentinelX exposes three repo-native verification commands so contributors can choose the right proof loop without guessing:

- `make verify-fast` is the default lane for routine changes. It runs non-E2E backend tests, Vitest, TypeScript typecheck, and the production asset build without starting the slower browser suite.
- `make verify-deep` runs the browser-heavy pytest E2E lane in `tests/e2e`. Use it when a change touches live enrichment orchestration, mocked online flows, results-page DOM/state, or any behavior that could accidentally trigger real background enrichment work.
- `make verify` runs both lanes in order for full confidence before handoff or merge.

### Which lane should I run?

- Stop at `make verify-fast` when your change is limited to non-browser backend/frontend logic, documentation, or build/test plumbing that does not affect the mocked online/browser path.
- Escalate to `make verify-deep` (or just run `make verify`) whenever you change live enrichment behavior, browser flows, result rendering, polling/status handling, or deterministic mocked E2E coverage.
- If you need the unambiguous full repo proof command, run `make verify`.

## Runtime-state boundary

SentinelX now exposes both a repo-native verifier and a repo-native repair loop for the durable-versus-transient workflow split:

- `make repair-runtime-state` is the one supported recovery entrypoint. It runs `tools/runtime_state_repair.py` in apply mode, deindexes `tracked-transient` findings, quarantines `unignored-transient` files into `.gsd/runtime/repair-quarantine/<timestamp>/...`, and then re-runs the inspection-only boundary audit so lingering blocker classes remain visible.
- `make verify-runtime-boundary` runs the focused classifier pytest coverage, the temp-repo Git regression fixtures, and then the live repo audit with `--fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root`.
- Transient runtime surfaces such as `.gsd/state-manifest.json`, `.gsd/event-log.jsonl`, `.gsd/notifications.jsonl`, `.gsd/audit/**`, `.gsd/runtime/**`, `.gsd/runtime/dev-server/**`, `.gsd/exec/**`, `.gsd/graphs/**`, `.gsd/safety/**`, and `.bg-shell/**` are repo-local state and should stay ignored/untracked.
- Durable milestone artifacts and canonical ledgers under `.gsd/milestones/**`, `.gsd/CODEBASE.md`, `.gsd/DECISIONS.md`, `.gsd/PROJECT.md`, and `.gsd/REQUIREMENTS.md` remain checked in.
- Legacy `.planning/**` paths are surfaced as `manual-review` findings on purpose; repair reports them explicitly but will not auto-clean, move, or deindex them.

See `docs/runtime-state-boundary.md` for the full class table, repair action table, and non-goals.

## Optimization audit workflow

M013 adds a checked-in SentinelX-first audit runner so later optimization work can produce durable, ranked findings instead of ad hoc notes.

- `python3 tools/optimization_audit.py --help` shows the available modes and options.
- `make audit-m013-template` writes the milestone-local scaffold at `.gsd/milestones/M013/M013-AUDIT-TEMPLATE.md`.
- `make audit-m013` writes the working audit artifact at `.gsd/milestones/M013/M013-AUDIT.md`.
- Every finding must be backed by measurement when practical; otherwise it must cite explicit code-path reasoning.
- Every finding must land in one of `do now`, `do next`, `later`, or `leave alone`.

See `docs/optimization-audit.md` for the full artifact contract, ranking vocabulary, and command-capture format.

