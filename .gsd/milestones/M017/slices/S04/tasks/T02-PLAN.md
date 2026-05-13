---
estimated_steps: 14
estimated_files: 5
skills_used: []
---

# T02: Implement or reject the narrow frontend render optimization

Why: S04 must either ship the remaining high-confidence optimization tied to the analyst results path or explicitly reject it with evidence. The preferred implementation target is reducing unnecessary flush-wide dashboard recount/reorder work after S03's backend polling optimization.

Skills used: `frontend-design` for preserving UI behavior, `react-best-practices`-style render minimization for plain TypeScript, `verify-before-complete`.

Do:
1. Use the T01 tests to identify whether the current result application path still performs avoidable dashboard recounts or severity reorders on provider-only/no-op deltas.
2. If avoidable work exists, implement the smallest shared-path optimization in `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/cards.ts`, or adjacent modules. Prefer cached severity/count/order signatures or dirty flags scoped to the affected IOC/card over broad rewrites.
3. Preserve live and history parity: the same shared result application behavior must work for polling updates and history/detail replay.
4. Preserve analyst affordances: filtering/sorting, verdict dashboard counts, copy/export buttons, provider slots, detail links, progress visibility, and terminal/error display.
5. Preserve security posture: keep text-safe DOM construction, CSRF/CSP assumptions, redaction boundaries, and no raw secret/token exposure.
6. If the tests show no justified code optimization remains, do not force a cleanup change; instead prepare the rejection evidence for T03 while keeping T01 regression tests as guardrails.

Threat surface (Q3): DOM update code handles untrusted IOC/provider strings and browser actions; avoid `innerHTML` expansion and preserve existing safety conventions.
Requirement impact (Q4): directly re-verifies R086, R087, R088 for the secondary optimization decision.
Failure modes (Q5): stale dashboard counts, incorrect sort/filter state, lost copy/export/detail links, divergence between live and history rendering, XSS regression, or optimization theater with no path proof.
Load profile (Q6): repeated incremental polling updates and history replay for multi-IOC result sets; optimize algorithmic/DOM work by code path, not microbenchmarks.
Negative tests (Q7): no-op/provider-only deltas skip global work; severity/order-affecting deltas still update counts/order; unsafe strings remain escaped as text.

## Inputs

- ``app/static/src/ts/modules/result-application.test.ts``
- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/cards.ts``
- ``app/static/src/ts/modules/enrichment.ts``
- ``app/static/src/ts/modules/row-factory.ts``
- ``tests/e2e/test_results_page.py``
- ``tests/e2e/test_emailrep_online.py``

## Expected Output

- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/cards.ts``
- ``app/static/src/ts/modules/enrichment.ts``
- ``app/static/src/ts/modules/row-factory.ts``
- ``app/static/src/ts/modules/result-application.test.ts``

## Verification

npm test -- --run && python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py

## Observability Impact

Keeps browser-visible state as the primary inspection surface: dashboard counts, sorted result cards, provider slots, progress/error text, history/detail links, copy/export controls, and e2e browser assertions.
