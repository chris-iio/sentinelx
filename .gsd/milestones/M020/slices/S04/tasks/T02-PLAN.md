---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: Record the S04 optimization decision in the generated audit source

Expected executor skills: write-docs, verify-before-complete.

Why: M020 requires every shipped or rejected optimization decision to be durable in the generated audit, not hand-edited only in `.gsd`. After T01, the evidence should either justify preserving the severity-change gate and deferring virtualization, or justify a narrowly scoped implementation change.

Do: Inspect `app/static/src/ts/modules/result-application.ts` against the T01 measurement. If the current severity-change gate already satisfies the proof, do not churn production code; record the S04 outcome as a measured rejection/deferment of virtualization in `tools/optimization_audit.py` and lock that generated language in `tests/test_optimization_audit.py`. If the measurement exposes a justified small optimization, make the minimal production change and still update the audit source/tests with the shipped outcome. Regenerate `.gsd/milestones/M020/M020-AUDIT.md` through `make audit-m020`; do not hand-edit the generated artifact. Preserve failure visibility, DOM safety, filtering, sorting, copy/export, detail links, expansion state, and live/history parity in the outcome language.

Done when: the audit generator and tests produce an M020 audit row that names the S04 frontend/render outcome, cites the focused Vitest evidence, includes `make verify-deep` as the browser-visible proof lane, and explains what was left alone or changed.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- `Makefile`

## Expected Output

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M020/M020-AUDIT.md`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Keeps the generated audit as the durable inspection surface for S04: future agents can see the measured browser-visible outcome, rerun lane, and redaction/failure-visibility guardrails without rediscovering the frontend evidence.
