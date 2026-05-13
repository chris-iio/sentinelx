---
estimated_steps: 8
estimated_files: 2
skills_used: []
---

# T03: Prove the audit workflow and S03 handoff are mechanically usable

Why: S02 closes only when the refreshed workflow and generated artifact are executable, structurally valid, and usable by downstream S03 without reinterpreting project identity. Executor skills: test, verify-before-complete.

Do:
1. Run the focused audit workflow tests after T01/T02.
2. Regenerate the M017 audit artifact once more from the checked runner to prove the artifact is not hand-maintained.
3. Run structural assertions that the artifact includes ranked buckets, project-map grounding, R085/R087 or equivalent evidence-standard language, concrete seam paths, and an S03 selected target/proof handoff.
4. If any assertion fails, fix the runner or artifact generation path rather than weakening the proof.
5. Record command outputs in the task summary at completion time.

Failure Modes (Q5): If pytest passes but generated artifact structure fails, treat the runner contract as incomplete and add/adjust tests. If the artifact says S03 should implement a target but does not name proof lanes, treat it as blocked. Load Profile (Q6): Focused pytest and local generation only; no browser/runtime load. Negative Tests (Q7): Verification includes negative placeholder grep and required-section assertions.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `Makefile`
- `.gsd/milestones/M017/M017-AUDIT.md`

## Expected Output

- `.gsd/milestones/M017/M017-AUDIT.md`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py && python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md && python3 - <<'PY'
from pathlib import Path
p = Path('.gsd/milestones/M017/M017-AUDIT.md')
text = p.read_text(encoding='utf-8')
required = ['docs/project-map.md', '### do now', '### do next', '### later', '### leave alone', 'S03', 'app/enrichment', 'app/routes', 'app/pipeline']
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f'missing required audit markers: {missing}')
if any(token in text for token in ['TBD', 'TODO', '_Fill during']):
    raise SystemExit('unresolved placeholder present')
print('PASS M017 audit workflow')
PY

## Observability Impact

Fresh verification output proves future agents can reproduce the audit state from the CLI and trust the artifact as generated, not hand-edited.
