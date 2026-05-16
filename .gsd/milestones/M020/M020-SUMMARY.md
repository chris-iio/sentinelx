---
id: M020
title: "Audit-Led Aggressive Refactor and Deep Optimization"
status: complete
completed_at: 2026-05-16T09:33:34.406Z
key_decisions:
  - Generated audit source in `tools/optimization_audit.py` is the canonical source for M020 optimization outcomes.
  - Route IOC helper centralization was treated as shipped because shared ownership already exists in `app/routes/_helpers.py` and focused tests prove the seam.
  - Route-level helper imports were preserved as compatibility/test seams instead of being removed for cosmetic cleanup.
  - Diagnostics policy centralization was treated as a shipped keep-decision because downstream modules already consume `DIAGNOSTIC_SANITIZATION_POLICY`-derived caps.
  - Frontend virtualization, major storage redesign, broad UI/product redesign, and new provider integrations were deferred as explicit non-claims.
key_files:
  - tools/optimization_audit.py
  - tests/test_optimization_audit.py
  - .gsd/milestones/M020/M020-AUDIT.md
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/api.py
  - app/routes/history.py
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_history_routes.py
  - app/diagnostics/policy.py
  - app/diagnostics/assembler.py
  - app/diagnostics/redaction.py
  - app/diagnostics/sources.py
  - tests/test_diagnostic_export_assembler.py
  - tests/test_diagnostic_redaction.py
  - tests/test_diagnostic_export_sources.py
  - app/static/src/ts/modules/result-application.test.ts
  - .gsd/milestones/M020/M020-LEARNINGS.md
  - .gsd/PROJECT.md
lessons_learned:
  - Code-path reasoning plus focused regressions can be stronger than artificial measurement when the optimization target is an already-existing centralization seam.
  - Compatibility imports and helper aliases may be real public/test seams; cleanup should be reverted when regression evidence shows downstream reliance.
  - Deferred-scope requirements need explicit non-claim language and tests so validation can prove both what shipped and what intentionally did not ship.
  - Browser-visible rewrites should be deferred when focused gate/work-count evidence shows current behavior is safe and the rewrite would risk analyst affordances.
---

# M020: Audit-Led Aggressive Refactor and Deep Optimization

**M020 generated an audit-led optimization record, shipped or preserved high-confidence route and diagnostics refactor outcomes, explicitly deferred risky broad rewrites, and proved the analyst IOC loop with fresh final verification.**

## What Happened

M020 broadened SentinelX optimization work from ad hoc prose into a source-generated audit and proof loop. S01 established `.gsd/milestones/M020/M020-AUDIT.md` as generated output from `tools/optimization_audit.py`, with ranked do-now, do-next, later, and leave-alone candidates plus proof requirements. S02 consumed the top route/API/history IOC helper target and closed it as a shipped centralization outcome: shared grouping and payload construction already live in `app/routes/_helpers.py`, route-level compatibility seams were preserved, focused route/API/history tests proved behavior, and the generated audit recorded the code-path reasoning. S03 closed the second cross-module target as a shipped diagnostics policy keep-decision, proving that assembler, source, and redaction caps derive from `app/diagnostics/policy.py` and locking diagnostics failure-state and redaction regressions. S04 resolved the browser-visible virtualization candidate as a measured deferment because focused large-result severity-change gate proof and deep browser verification showed the existing seam was safer than an unproven rewrite. S05 assembled closeout evidence across focused backend, diagnostics, audit, frontend, and final `make verify` lanes. S06 remediated deferred-scope coverage by making the generated audit explicitly document R101-R103 as non-claims, preserving S02-S04 handoff contracts, and rerunning final verification. A fresh closeout `make verify` was run in this completion turn and passed with the E2E lane reporting 126 passed tests.

## Success Criteria Results

- [x] Generated audit artifact exists and is source-generated: S01, S05, and S06 regenerated `.gsd/milestones/M020/M020-AUDIT.md` from `tools/optimization_audit.py` through `make audit-m020`, with `tests/test_optimization_audit.py` protecting the contract.
- [x] Audit ranks do-now, do-next, later, and leave-alone outcomes: validation and S01 evidence confirm all buckets and proof requirements are present.
- [x] Shipped refactors or rejections tie back to audit targets: S02 route IOC helper centralization, S03 diagnostics policy centralization, S04 virtualization deferment, and S06 deferred-scope non-claims are all generated audit outcomes.
- [x] Each shipped change has measurement or code-path reasoning: S02 and S03 use code-path reasoning plus focused regressions; S04 uses measured large-result/severity-gate proof plus frontend/deep verification.
- [x] Focused regressions protect changed seams: route/API/history, diagnostics assembler/redaction/sources, result-application Vitest, and audit tests all passed in slice evidence.
- [x] Analyst-visible workflows remain intact: validation maps intake, extraction, enrichment response paths, results, history/detail, diagnostics, filtering, copy, and export to focused tests and final all-up verification.
- [x] Risky optimizations are documented as keep/defer decisions: virtualization, storage redesign, broad UI/product redesign, and new provider integrations are explicit generated-audit non-claims/deferments.
- [x] Final verification proves end-to-end operation: S05 and S06 passed `make verify`; fresh completion verification `make verify` also exited 0 with 126 E2E tests passing.

## Definition of Done Results

- All roadmap slices are checked complete: `gsd_milestone_status` reported S01-S06 complete with 18/18 tasks done.
- Slice summaries exist and provide cross-slice evidence: S01-S06 summaries record shipped/deferred outcomes, verification lanes, deviations, limitations, and handoff contracts.
- Integration branch/code-change guard passed: although HEAD matched `main` at closeout, milestone commit evidence with `GSD-Task: Sxx/Tyy` trailers shows non-`.gsd` implementation/test files changed, including `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, route/API/history tests, diagnostics tests, Makefile, and frontend result-application tests.
- Integrated verification passed: fresh `make verify` via `gsd_exec` exited 0 in 72.535s and ended with `126 passed` in `tests/e2e`.
- Project state and learnings were refreshed before milestone completion: `.gsd/PROJECT.md` was updated, `.gsd/milestones/M020/M020-LEARNINGS.md` was written, and durable memories were captured for M020 decisions, lessons, and patterns.

## Requirement Outcomes

- R094: Validated by source-generated M020 audit creation through `make audit-m020` and audit contract tests.
- R095: Validated by generated audit bucket taxonomy and proof requirements for do-now, do-next, later, and leave-alone outcomes.
- R096: Validated by S02/S03 code-path reasoning plus focused regressions and S04 measured virtualization deferment.
- R097: Validated by focused route/API/history, diagnostics, frontend result-application, and final `make verify` evidence covering the analyst loop.
- R098: Validated by strict verification lanes: focused seam tests, `make verify-fast` for backend implementation slices, `make verify-deep` for browser-visible proof, and final `make verify`.
- R099: Validated by diagnostics source status/error/omitted/truncated metadata, redaction tests, and route/API/history failure-path proof.
- R100: Covered by generated audit closeout tests and regenerated audit language documenting what changed, what was left alone, and why.
- R101: Remains deferred with validation-backed non-claim evidence; no storage redesign shipped.
- R102: Remains deferred with validation-backed non-claim evidence; no broad UI/product redesign shipped.
- R103: Remains deferred with validation-backed non-claim evidence; no new provider integration shipped.
- R106: Covered by the generator/test-protected audit source-of-truth pattern; M020 closeout did not rely on hand-edited audit prose.

## Deviations

Several high-ranked refactor targets were already correctly implemented, so M020 delivered stronger regression coverage, generated audit documentation, and explicit keep/defer decisions rather than unnecessary production churn. The validation artifact was present and passing but lacked freshness/coverage confidence, so this closeout reran fresh final `make verify` before completion.

## Follow-ups

Future milestones may revisit frontend virtualization only with measured evidence that the severity-change gate is insufficient and with proof preserving filtering, sorting, copy/export, detail links, expansion state, and DOM-safe rendering. Major storage redesign, broad UI/product redesign, and new provider integrations remain deferred until new evidence justifies separate scoped milestones.
