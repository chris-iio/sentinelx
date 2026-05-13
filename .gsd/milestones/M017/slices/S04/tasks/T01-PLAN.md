---
estimated_steps: 13
estimated_files: 5
skills_used: []
---

# T01: Lock browser result rendering churn contract with focused frontend tests

Why: S04's secondary target is the do-next frontend/render opportunity named by the M017 audit: flush-wide verdict dashboard recounts and severity reorders during polling/history replay. Before changing code, create or extend focused Vitest coverage that exposes the desired contract and protects analyst-visible behavior.

Skills used: `tdd`, `react-best-practices`-style frontend performance discipline (plain TS codebase), `verify-before-complete`.

Do:
1. Inspect the existing frontend test layout under `app/static/src/ts` and extend the closest result-application/card/enrichment test file; if no suitable file exists, add `app/static/src/ts/modules/result-application.test.ts`.
2. Add tests around the real shared result application path, not a detached helper. Cover at minimum: provider-only result deltas that do not change verdict/severity/order state, deltas that do change severity/order state, history replay parity, and preservation of copy/export/detail-link DOM affordances.
3. Add assertions that make unnecessary flush-wide work observable in tests without adding production-only diagnostics. Prefer spies around existing dashboard/order update helpers or a test-only DOM fixture/counter over broad timing assertions.
4. Keep security behavior locked: rendered IOC/provider strings must continue to use safe text insertion (`textContent`/equivalent), not unsafe HTML injection.
5. Do not read from `.gsd/`, `.planning/`, `.audits/`, or other gitignored paths in tests.

Threat surface (Q3): untrusted IOC/provider text reaches browser DOM; tests must protect text-safe rendering and avoid adding HTML injection surfaces.
Requirement impact (Q4): supports R086, R087, R088 by defining proof for the frontend/render follow-up.
Failure modes (Q5): false-positive tests that exercise only mocks, brittle DOM selectors, or timing-based performance assertions.
Load profile (Q6): local analyst-scale result batches plus repeated polling/history deltas; no production load test required.
Negative tests (Q7): unchanged severity/provider-only delta must not trigger unnecessary global recount/reorder; malicious-looking IOC/provider text must not render as HTML.

## Inputs

- ``app/static/src/ts/modules/result-application.ts``
- ``app/static/src/ts/modules/cards.ts``
- ``app/static/src/ts/modules/enrichment.ts``
- ``app/static/src/ts/modules/row-factory.ts``
- ``package.json``
- ``vitest.config.ts``

## Expected Output

- ``app/static/src/ts/modules/result-application.test.ts``

## Verification

npm test -- --run

## Observability Impact

Creates focused test observability for frontend render churn without exposing new runtime diagnostics or sensitive IOC/provider data.
