---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: Generate the M017 ranked optimization audit artifact

Why: S03 needs a concrete, current, ranked audit artifact that names the chosen do-now target and proof requirements. Executor skills: write-docs, verify-before-complete.

Do:
1. Regenerate the milestone-local artifact with `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md` or the Makefile target added in T01.
2. Ground the findings in `docs/project-map.md` seam priorities: enrichment fan-out/status snapshot cost, frontend result/render churn, SQLite cache/history access shape, IOC pipeline duplicate handling, and provider registration/config diagnostics clarity.
3. Rank all current findings into `do now`, `do next`, `later`, and `leave alone`; every row must include evidence kind, evidence summary, continuity guardrails, rerun lanes, and continuity notes.
4. Include an explicit S03 handoff section naming the selected do-now optimization target and the proof expected from implementation. If no code change is justified, the artifact must say so explicitly and cite why.
5. Avoid secrets and avoid analyst-sensitive IOC data; any examples should be synthetic.

Failure Modes (Q5): If runner generation fails, do not hand-edit around it; fix T01 runner/test contract first. If available evidence does not justify a do-now code change, record an explicit no-code-justified outcome rather than inventing an optimization. Load Profile (Q6): Artifact generation is local and deterministic except optional captures; no runtime load is introduced. Negative Tests (Q7): Structural checks should reject missing ranked buckets, missing project-map grounding, and unresolved placeholders.

## Inputs

- `tools/optimization_audit.py`
- `Makefile`
- `docs/project-map.md`
- `.gsd/PROJECT.md`

## Expected Output

- `.gsd/milestones/M017/M017-AUDIT.md`

## Verification

python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md && test -s .gsd/milestones/M017/M017-AUDIT.md && grep -q "docs/project-map.md" .gsd/milestones/M017/M017-AUDIT.md && grep -q "### do now" .gsd/milestones/M017/M017-AUDIT.md && grep -q "### do next" .gsd/milestones/M017/M017-AUDIT.md && grep -q "### later" .gsd/milestones/M017/M017-AUDIT.md && grep -q "### leave alone" .gsd/milestones/M017/M017-AUDIT.md && grep -qi "S03" .gsd/milestones/M017/M017-AUDIT.md && ! grep -Eq "TBD|TODO|_Fill during" .gsd/milestones/M017/M017-AUDIT.md

## Observability Impact

Creates the durable inspection surface future agents will use to see current ranked optimization decisions, evidence class, and downstream proof lanes.
