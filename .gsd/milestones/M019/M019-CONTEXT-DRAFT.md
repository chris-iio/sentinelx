# M019 Context Draft — Broad Refactor and Optimization

## Vision
Refactor and optimize the SentinelX codebase broadly. The user said "everything is allowed" and confirmed the goal is to go through everything.

## Reflection Confirmed
- This is primarily refactoring/migration plus performance optimization work.
- The effort is likely one substantial milestone with roughly 4–6 vertical slices, unless the audit reveals enough large architectural work to split into follow-up milestones.
- The milestone should avoid optimization theater by tying changes to evidence, measurement, or explicit code-path reasoning.

## Scope Confirmed

### In Scope
- Whole-codebase refactor and optimization across backend, frontend, routes, enrichment, adapters, pipeline, stores, templates/CSS, tests, build tooling, docs, and repo automation.
- User-visible behavior and UI changes are allowed if they make SentinelX clearer, faster, or more maintainable.
- Prior validated optimization work can be revisited if fresh evidence shows a better direction.
- Dependency/package upgrades are allowed.

### Out of Scope / Guardrails
- No subsystem is categorically off-limits.
- Guardrail: changes must preserve or intentionally improve the analyst IOC triage loop, not accidentally regress it.
- Guardrail: optimization claims need evidence: measurement where practical, or explicit code-path reasoning plus regression proof.

## Architecture Confirmed
- No dedicated audit-only first slice. M019 should not spend its first slice only producing an artifact before changing code.
- Work begins directly with whole-codebase refactor/optimization execution. Each slice can inspect and rank locally, but must ship real improvements.
- Cross-seam rewrites are allowed. A slice may touch route + orchestrator + frontend contract together when that is the cleanest improvement.
- Dependency/package upgrades are allowed as part of the optimization pass.
- Evidence still matters: each shipped change should carry measurement where practical or explicit code-path reasoning plus regression proof.

## Existing Codebase Evidence
- Python/Flask backend with TypeScript frontend and Tailwind-built CSS.
- Existing modules: app/enrichment, app/routes, app/pipeline, app/cache, app/diagnostics, app/static/src/ts.
- Prior optimization and clarity milestones validated cursor polling, WAL cache basics, shared rendering seams, diagnostic export, intake redesign, and M017 audit/proof artifacts.
- Existing verification lanes include make verify-fast and make verify-deep.

## Open Error Handling Questions
- Whether aggressive refactors should fail closed when uncertain or preserve fail-open surfaces like intake/history where prior requirements require continuity.
- How to handle partial optimization failures: rollback slice vs keep improvements with documented limitations.
