---
estimated_steps: 11
estimated_files: 3
skills_used: []
---

# T03: Encode the S04 secondary optimization outcome in the audit generator

Why: M017 requires optimization decisions to be durable and evidence-backed. S04 must update the generated audit source so future agents see whether the frontend/render follow-up shipped or was rejected, and why.

Skills used: `write-docs` for durable audit language, `verify-before-complete`.

Do:
1. Update `tools/optimization_audit.py` so the M017 audit no longer describes browser rendering churn as an unresolved S04 target after T02.
2. If T02 shipped a change, describe the exact code path and proof: focused frontend tests plus mocked-online browser checks. If T02 rejected the change, record the explicit reason and evidence without implying work shipped.
3. Extend `tests/test_optimization_audit.py` to reject stale S04 target-only language and require the current S04 outcome language.
4. Regenerate `.gsd/milestones/M017/M017-AUDIT.md` with the canonical audit command.
5. Keep generated audit wording aligned with D078-D080 and R086-R088; do not hand-edit the audit artifact without generator support.

Requirement impact (Q4): validates R085-R088 evidence continuity and supports S05 final assembly.
Failure modes (Q5): stale audit text, hand-patched artifact that cannot regenerate, or claim of shipped optimization without proof.
Negative tests (Q7): audit test must fail if stale phrases such as unresolved do-next S04 target remain after the outcome is known.

## Inputs

- ``tools/optimization_audit.py``
- ``tests/test_optimization_audit.py``
- ``app/static/src/ts/modules/result-application.test.ts``
- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/cards.ts``

## Expected Output

- ``tools/optimization_audit.py``
- ``tests/test_optimization_audit.py``
- ``.gsd/milestones/M017/M017-AUDIT.md``

## Verification

python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md && python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Makes S04 evidence inspectable through the generated M017 audit artifact and focused audit regression tests.
