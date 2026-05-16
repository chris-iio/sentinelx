---
estimated_steps: 4
estimated_files: 1
skills_used: []
---

# T01: Measure large-result render pressure at the severity-change gate

Expected executor skills: react-best-practices, tdd, verify-before-complete.

Why: S04 needs evidence for a browser-visible optimization target before either shipping a frontend rewrite or rejecting/defering it. The risky candidate is DOM virtualization/result-render churn; the first increment must make the current cost model executable instead of relying on taste.

Do: Add or tighten a focused Vitest in `app/static/src/ts/modules/result-application.test.ts` that builds a large results fixture (around 240 cards is enough to stress the code path without making tests slow), applies an initial clean result, then applies a same-severity second provider result and a later malicious severity change. Spy on dashboard recount/sort helpers and relevant `.ioc-card` `querySelectorAll` calls so the test proves: same-severity updates do not trigger whole-grid scans/recounts/sorts, while an actual severity change performs only the expected dashboard/sort work. Keep fixtures free of secrets and do not read `.gsd`, `.planning`, `.audits`, or `.git` paths from tests.

Done when: the focused test fails if the severity-change gate regresses, documents enough work-count evidence to decide whether virtualization is warranted, and passes with the current implementation.

## Inputs

- `app/static/src/ts/modules/result-application.test.ts`
- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/cards.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/shared-rendering.ts`
- `app/static/src/ts/types/api.ts`

## Expected Output

- `app/static/src/ts/modules/result-application.test.ts`

## Verification

npx vitest run app/static/src/ts/modules/result-application.test.ts

## Observability Impact

Adds an executable frontend work-count inspection surface for future agents: Vitest failures will localize regression to dashboard recounts, sort calls, or whole-grid scans during live/history result application.
