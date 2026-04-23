<p align="center">
  <img src="app/static/images/screenshot.png" alt="SentinelX" width="600">
</p>

## Verification lanes

SentinelX exposes three repo-native verification commands so contributors can choose the right proof loop without guessing:

- `make verify-fast` is the default lane for routine changes. It runs non-E2E backend tests, Vitest, TypeScript typecheck, and the production asset build without starting the slower browser suite.
- `make verify-deep` runs the browser-heavy pytest E2E lane in `tests/e2e`. Use it when a change touches live enrichment orchestration, mocked online flows, results-page DOM/state, or any behavior that could accidentally trigger real background enrichment work.
- `make verify` runs both lanes in order for full confidence before handoff or merge.

### Which lane should I run?

- Stop at `make verify-fast` when your change is limited to non-browser backend/frontend logic, documentation, or build/test plumbing that does not affect the mocked online/browser path.
- Escalate to `make verify-deep` (or just run `make verify`) whenever you change live enrichment behavior, browser flows, result rendering, polling/status handling, or deterministic mocked E2E coverage.
- If you need the unambiguous full repo proof command, run `make verify`.

## Optimization audit workflow

M013 adds a checked-in SentinelX-first audit runner so later optimization work can produce durable, ranked findings instead of ad hoc notes.

- `python3 tools/optimization_audit.py --help` shows the available modes and options.
- `make audit-m013-template` writes the milestone-local scaffold at `.gsd/milestones/M013/M013-AUDIT-TEMPLATE.md`.
- `make audit-m013` writes the working audit artifact at `.gsd/milestones/M013/M013-AUDIT.md`.
- Every finding must be backed by measurement when practical; otherwise it must cite explicit code-path reasoning.
- Every finding must land in one of `do now`, `do next`, `later`, or `leave alone`.

See `docs/optimization-audit.md` for the full artifact contract, ranking vocabulary, and command-capture format.

