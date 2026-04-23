# SentinelX optimization audit workflow

M013 adds a checked-in workflow for running and recording a full-stack optimization pass without turning the results into ad hoc prose.

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
make audit-m013-template
make audit-m013
```

### Direct CLI usage

```bash
python3 tools/optimization_audit.py \
  --mode template \
  --output .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md

python3 tools/optimization_audit.py \
  --mode baseline \
  --output .gsd/milestones/M013/M013-AUDIT.md
```

`template` mode writes the reusable blank scaffold.
`baseline` mode writes the current M013 baseline findings, seam notes, guardrail coverage, and lightweight local measurement captures.

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
4. continuity guardrails for R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040
5. seam prompts for:
   - runtime/provider
   - request/status
   - persistence
   - frontend/render
6. a stable table schema under each ranked bucket
7. in `baseline` mode, populated ranked findings, per-seam notes, guardrail coverage, and internal temp-DB / status-snapshot measurements

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

- Update the ranked tables in place instead of creating disconnected one-off notes.
- Add command captures whenever a claim can be anchored to measured output.
- If a later slice changes live enrichment orchestration, polling/status behavior, or results-page DOM/state, include `make verify-deep` in that finding’s rerun lanes.
- Keep `leave alone` rows current. They are part of the audit proof, not filler.
