# SentinelX optimization audit workflow

M013 introduced the checked-in workflow for running and recording a full-stack optimization pass without turning the results into ad hoc prose. That history remains durable; the current completed milestone surface is M020, and the runner now accepts an explicit `--milestone-id` for milestone-local generation.

## Goals

- keep the workflow SentinelX-first while remaining reusable in another repo with light edits
- require **measurement when practical** and **explicit code-path reasoning** when direct measurement is awkward
- force every finding into one of four ranked outcomes:
  - `do now`
  - `do next`
  - `later`
  - `leave alone`
- preserve continuity guardrails and rerun expectations alongside each finding so later slices can ship changes without reconstructing the proof model

## Command surface

```bash
python3 tools/optimization_audit.py --help
make audit-m020-template
make audit-m020
```

The Make targets are the current M020 convenience wrappers. The direct CLI is the generic runner surface: pass `--milestone-id` and an explicit milestone-local output path.

### Direct CLI usage

```bash
python3 tools/optimization_audit.py \
  --milestone-id M020 \
  --mode template \
  --output .gsd/milestones/M020/M020-AUDIT-TEMPLATE.md

python3 tools/optimization_audit.py \
  --milestone-id M020 \
  --mode baseline \
  --output .gsd/milestones/M020/M020-AUDIT.md
```

`template` mode writes the reusable blank scaffold. `baseline` mode writes the working audit; `--milestone-id M020` selects the M020-specific aggressive-rewrite contract, ranked outcomes, seam notes, guardrail coverage, verification guidance, and lightweight local measurement captures. M013 remains the CLI default when no milestone ID is supplied.

### M013 history

M013 remains the workflow's origin and its artifacts remain under `.gsd/milestones/M013/`. The legacy `make audit-m013-template` and `make audit-m013` targets are still present for reproducing that milestone, but they are not the current rerun surface.

### Optional command captures

Use `--capture-command LABEL::COMMAND` to add measured command metadata to the artifact.

```bash
python3 tools/optimization_audit.py \
  --mode baseline \
  --output .gsd/milestones/M013/M013-AUDIT.md \
  --capture-command "verify-fast::make verify-fast" \
  --capture-command "smoke::python3 -c \"print('ok')\""
```

Each capture records:

- label
- exact command string
- exit code
- duration in milliseconds
- short output summary

If any captured command fails, the script still writes the artifact but exits non-zero so the caller can treat the run as incomplete.

## Artifact contract

The generated markdown includes:

1. the workflow contract
2. the repo-native command surface
3. verification-lane rerun guidance (`make verify-fast`, `make verify-deep`, `make verify`)
4. a verified rerun checklist that makes deterministic mocked-online browser proof explicit for live-stack changes
5. continuity guardrails for R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040
6. seam prompts for:
   - runtime/provider
   - request/status
   - persistence
   - frontend/render
7. a stable table schema under each ranked bucket
8. in `baseline` mode, populated ranked findings, per-seam notes, guardrail coverage, and internal temp-DB / status-snapshot / runtime-provider measurements

## Finding schema

Each finding row must include:

- **Finding** — one concrete optimization or keep-decision
- **Seam** — `runtime/provider`, `request/status`, `persistence`, or `frontend/render`
- **Evidence kind** — `measurement` or `code-path reasoning`
- **Evidence summary** — cite the timing, command capture, or exact path reasoning
- **Continuity guardrails** — requirement IDs that must remain protected
- **Rerun lanes** — one or more of `make verify-fast`, `make verify-deep`, `make verify`
- **Continuity notes** — what must remain true after the change, or why the seam should stay untouched

## Ranking vocabulary

### `do now`

High-confidence work with enough evidence to justify immediate shipping in the next slice.

### `do next`

Promising work that likely matters, but should follow after the current highest-confidence fixes land.

### `later`

Valid ideas that remain deferred because current evidence is weak, risk is higher than urgency, or the likely payoff is not yet proven.

### `leave alone`

Explicit keep-decisions for seams that are already intentionally shaped and do not justify churn.

## Recommended downstream usage

1. Refresh `.gsd/milestones/M020/M020-AUDIT.md` with `make audit-m020` or the equivalent `--milestone-id M020` baseline command so the completed milestone's shipped, rejected, deferred, and leave-alone outcomes remain reproducible.
2. Re-run `make verify-fast` for every shipped optimization and record the fresh evidence in the task summary or as an audit capture.
3. Re-run `make verify-deep` whenever the change touches live enrichment orchestration, polling/status behavior, shared result application, or analyst-visible DOM/state; deterministic mocked-online browser proof is part of the contract for those seams.
4. Compare the updated ranked rows, rerun lanes, and continuity notes in place instead of creating disconnected one-off notes.
5. Add command captures whenever a claim can be anchored to measured output.
6. Keep `leave alone` rows current. They are part of the audit proof, not filler.
7. For the runtime/provider seam specifically, use the synthetic `runtime-provider-diagnostics` capture to distinguish measured dispatch/retry behavior from explicit concurrency, backoff, and session keep-decisions.
