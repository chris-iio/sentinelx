---
estimated_steps: 5
estimated_files: 7
skills_used:
  - firecrawl-search
---

# T01: Replace stale EmailRep plan with minimal-product research and roadmap

Why: The user questioned what the tool should be and whether we should research a better direction. M016 must point at product-loop hardening before code execution continues.

Do:
1. Research comparable IOC investigation/enrichment workflows enough to validate the product direction.
2. Audit the local M016 context for conflicts between minimal-product direction and EmailRep execution plans.
3. Rewrite `M016-RESEARCH.md` around SentinelX as a local-first IOC evidence workbench.
4. Rewrite `M016-ROADMAP.md` into vertical slices for product-loop baseline, minimal intake, scannable results, and runtime/integration hardening.
5. Update active state and S01 task plans so the next action is browser/product audit, not `EmailRepAdapter` implementation.

Done when: Active M016 docs/state/slice plans agree that EmailRep is superseded and M016 execution starts with product-loop audit plus runtime baseline.

## Inputs

- User direction in the current session.
- `.gsd/milestones/M016/M016-CONTEXT.md`
- Current M016 research/roadmap/slice plans.
- Local templates/routes for the existing product loop.
- Web research artifacts under `.firecrawl/`.

## Expected Output

- Updated `.gsd/milestones/M016/M016-RESEARCH.md`
- Updated `.gsd/milestones/M016/M016-ROADMAP.md`
- Updated `.gsd/STATE.md`
- Updated S01 plan/task files.

## Verification

```bash
python3 - <<'PY'
import pathlib, re
paths = [pathlib.Path('.gsd/STATE.md'), *pathlib.Path('.gsd/milestones/M016').glob('*.md'), *pathlib.Path('.gsd/milestones/M016/slices/S01').rglob('*.md')]
patterns = [
    re.compile(r'^# S01: ' + r'EmailRep launch-readiness'),
    re.compile(r'^# T02: ' + r'Implement EmailRepAdapter'),
    re.compile(r'Active ' + r'Milestone.*' + r'Email ' + r'Reputation'),
    re.compile(r'Next ' + r'Action.*' + r'EmailRep' + r'Adapter'),
]
for path in paths:
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if any(pattern.search(line) for pattern in patterns):
            print(f'{path}:{lineno}:{line}')
PY
```

Expected: no output.

## Observability Impact

No runtime code changes. This task improves process observability by making the active plan reflect the actual product decision.
