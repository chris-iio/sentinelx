---
estimated_steps: 2
estimated_files: 4
skills_used: []
---

# T01: Create the reusable audit runner and ranked artifact format

Add a checked-in command surface for the M013 pass — likely a Make target plus a small helper script or equivalent documented entrypoint — that runs the agreed baseline lanes, captures timing/measurement metadata, and writes milestone-local outputs in a consistent format. Encode the core milestone rule directly into the workflow: a finding must be backed by measurement when practical, otherwise by explicit code-path reasoning, and every output must land in one of `do now`, `do next`, `later`, or `leave alone`.

Keep the workflow SentinelX-first but lightly reusable: the command surface should assume this repo’s current verify lanes and directory layout, while keeping the ranking/report format portable enough for future light-edit reuse.

## Inputs

- `M013 context and research findings`
- `Existing verification lanes in Makefile`
- `Current project layout for docs and milestone artifacts`

## Expected Output

- `Checked-in audit runner/entrypoint for local M013 passes`
- `Stable ranked artifact schema or template with `do now` / `do next` / `later` / `leave alone` buckets`
- `Documented rule for measurement-backed findings vs code-path reasoning`

## Verification

python3 tools/optimization_audit.py --help

## Observability Impact

Creates the durable command and artifact surface every later slice will use as its before/after comparison point.
