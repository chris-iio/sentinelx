---
id: M012
title: "Optimization Audit & Next-Work Decision"
status: complete
completed_at: 2026-04-23T03:00:03.721Z
key_decisions:
  - D050 — Run M012 in risk-first order, starting with live enrichment failure visibility before considering deeper optimization work.
  - D051 — Treat storage/helper rewrites as measurement-gated follow-through rather than default cleanup.
  - D053 — Centralize shared live/history stateful rendering in `app/static/src/ts/modules/result-application.ts` and enforce exclusive runtime ownership on `.page-results`.
  - D054 — Keep repo-native `make verify-fast` / `make verify-deep` proof lanes and make mocked-online browser tests deterministic at the fixture boundary.
  - D055 — Ship additive helper diagnostics plus a ranked keep/change assessment instead of speculative persistence rewrites.
  - D056 — Preserve WAL-backed stores, full-results history replay, and cursor polling semantics unless future diagnostics or measurements prove real pain.
key_files:
  - app/routes/_helpers.py
  - app/enrichment/orchestrator.py
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/main.ts
  - app/static/src/ts/modules/shared-rendering.ts
  - app/routes/settings.py
  - app/templates/settings.html
  - Makefile
  - README.md
  - tests/e2e/conftest.py
  - tests/test_history_routes.py
  - tests/test_settings.py
  - .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md
  - .gsd/milestones/M012/M012-VALIDATION.md
lessons_learned:
  - The highest-value optimization work in SentinelX was not a deep storage rewrite; it was making the live analyst-visible seam truthful first, then using that seam to ground later decisions.
  - Shared UI-path refactors stay safe when the stateful coordination seam is extracted explicitly and protected by parity/non-polling tests, rather than by informal duplication.
  - A cheap, explicit verification floor (`make verify-fast`) plus a deterministic browser escalation lane produces better optimization decisions than ad-hoc test selection.
  - Persistence and helper seams should be instrumented before they are redesigned; bounded diagnostics on an existing inspection surface can retire uncertainty without destabilizing continuity-critical paths.
---

# M012: Optimization Audit & Next-Work Decision

**M012 turned the optimization audit into shipped live-status, shared-rendering, verification-lane, and helper-diagnostics improvements, then closed with a validated ranked next-work decision future work can trust.**

## What Happened

M012 started by hardening the highest-risk live seam instead of chasing speculative cleanup. S01 made terminal enrichment outcomes explicit across the backend/frontend contract so unknown, evicted, and failed jobs stop polling and surface analyst-visible failure state without breaking the existing success path. S02 then removed the duplicate live/history rendering seam by extracting a shared stateful result-application coordinator and making `.page-results[data-results-owner]` the exclusive runtime ownership contract, preserving parity while preventing accidental history polling. S03 formalized the proof floor SentinelX should use for optimization work: `make verify-fast` remains the routine default lane, `make verify-deep` remains the browser-sensitive escalation lane, and mocked-online E2E runs now stay deterministic by patching orchestration only inside the test fixture. S04 closed the persistence/helper question with evidence rather than theory: it shipped additive helper-local History Save Diagnostics on `/settings`, recorded a ranked keep/change assessment, and deliberately preserved the WAL-backed stores, full-results history replay, and cursor polling semantics because the milestone produced no proof they were the real bottleneck.

Closeout work then reconciled the milestone ledger so the milestone could be truthfully completed. S05 backfilled the missing assessment artifacts, refreshed focused continuity proof, and rendered milestone validation. The current completion turn confirmed the milestone is now genuinely ready to close: the requirements ledger contains `R040`, fresh verification passed across contract, integration, and operational surfaces, and the milestone leaves a coherent decision record rather than partial artifacts.

## Decision Re-evaluation

| Decision | Outcome | Re-evaluation |
|---|---|---|
| D050 — risk-first M012 order | Executed as planned | Still valid. Starting at the live enrichment seam produced concrete user-visible wins and made every later optimization decision better grounded. |
| D051 — storage/helper rewrites must be measurement-gated | Confirmed by S04 | Still valid. The shipped diagnostics and assessment found no evidence justifying WAL-store or helper-path rewrites now. |
| D052 — optimization proof must be measured or cross-boundary and include the real analyst flow | Confirmed by S01–S05 | Still valid. The strongest milestone outcomes came from proving behavior on the real UI/API seam and carrying that proof through validation. |
| D053 — shared live/history coordination belongs in `result-application.ts` with explicit single-owner dispatch | Shipped in S02 | Still valid. Parity, non-polling, and ownership tests show this is the right seam. |
| D054 — separate fast/deep proof lanes, with deterministic browser mocks at the fixture boundary | Shipped in S03 | Still valid. Fresh `make verify-fast` evidence and prior deep-lane proof show the split is trustworthy and cheaper to use correctly. |
| D055 — S04 should ship additive diagnostics plus a ranked keep/change assessment, not a rewrite | Shipped in S04 | Still valid. `/settings` diagnostics created a low-regret inspection seam without disturbing continuity-critical runtime contracts. |
| D056 — keep WAL stores, full-results replay, and cursor semantics unless future measurement disproves current evidence | Confirmed in S04 and at closeout | Still valid. Nothing in closeout verification contradicted the keep decision. |

No M012 decision currently needs immediate reversal; the only revisit trigger is future measurement from the new helper diagnostics or live behavior showing real persistence/helper pain.

## Success Criteria Results

- **Major SentinelX subsystems were reviewed with evidence-backed findings or explicit leave-alone conclusions:** S01 covered the backend/frontend live status seam, S02 covered frontend live/history rendering ownership and parity, S03 covered the contributor verification loop, and S04 covered persistence/helper seams. Slice summaries plus fresh closeout verification (`266 passed`, `73 passed`, `make verify-fast` green) provide the evidence spine.
- **The milestone leaves a ranked do-now / do-next / later / leave-alone plan:** S04 shipped `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` and D056, explicitly keeping WAL stores, history replay, and cursor semantics in the leave-alone bucket unless future diagnostics or measurement justify change.
- **At least one high-risk live seam improvement shipped through the real analyst workflow:** S01 delivered additive terminal enrichment metadata and analyst-visible terminal failure handling on the real polling/results path; S02 preserved that contract while unifying live/history application through the actual results surface.
- **Continuity requirements R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040 have an explicit ownership path across the milestone:** S01/S02 owned the live-status and rendering continuity seams, S03 owned the verification-floor continuity seam, S04 owned the persistence/helper keep decision, and the reconciled requirements ledger now includes validated `R040` with fresh closeout evidence.

## Definition of Done Results

- **All roadmap slices are complete:** `gsd_milestone_status(M012)` reports S01–S05 all `complete`, with every slice task count fully done.
- **All slice summaries exist:** `find .gsd/milestones/M012 -maxdepth 3 -type f` confirmed `S01-SUMMARY.md` through `S05-SUMMARY.md` plus `M012-VALIDATION.md` are present; a follow-up listing confirmed slice assessment/UAT artifacts are present where expected.
- **Cross-slice integration works:** S01’s additive terminal-status and cursor contract is the seam S02 preserves in the shared result-application path; S03’s verification-lane split protects the browser-visible contract S02 established; S04 deliberately leaves live/history and WAL-store seams untouched while adding helper diagnostics; fresh closeout verification passed across both focused contract tests (`266 passed`) and persistence/helper tests (`73 passed`), and `make verify-fast` passed (`955 passed, 113 deselected`, Vitest `78 passed`, clean `tsc`, clean production build).
- **Code changes exist outside `.gsd/`:** because this repository closes milestones directly on `main`, `git diff --stat HEAD $(git merge-base HEAD main)` is empty at the branch tip. Using the milestone-start equivalent diff from pre-M012 commit `3a9200a` to `HEAD` showed 31 non-`.gsd/` files changed, including `app/routes/_helpers.py`, `app/enrichment/orchestrator.py`, `app/static/src/ts/modules/result-application.ts`, `app/routes/settings.py`, `Makefile`, and multiple tests.
- **Horizontal checklist:** none was present in the roadmap, so there were no unchecked horizontal checklist items to carry forward.

## Requirement Outcomes

- **R040 — status reconfirmed/updated as validated with current evidence.** The requirement now has a canonical row in `.gsd/REQUIREMENTS.md`, and this completion turn refreshed its validation text through `gsd_requirement_update`. Evidence: `Makefile` and `README.md` expose/document `verify-fast`, `verify-deep`, and `verify`; fresh closeout proof passed with `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q` → `266 passed in 0.96s`, `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` → `73 passed in 1.75s`, and `make verify-fast` → `955 passed, 113 deselected`, Vitest `78 passed`, clean `npx tsc --noEmit`, successful production build.
- **No other requirement status transitions were needed at milestone close.** R008, R009, R010, R014, R015, R018, R019, R020, and R022 already had canonical validated rows; M012 refreshed their proof surfaces and ownership mapping but did not require a new status change.

## Deviations

None in the delivered milestone scope. The only audit nuance at closeout was that code-change verification on the linear `main` branch required a milestone-start diff (`3a9200a..HEAD`) rather than the literal `HEAD` vs `merge-base main` form, which is empty when the branch being completed is itself `main`.

## Follow-ups

Use the new `/settings` History Save Diagnostics as the first signal for any future persistence/helper follow-up. Only schedule deeper store/helper rewrites if those counters or realistic load measurements show contention, failures, skips, write amplification, or request-path waste. If browser-visible results-surface changes return in a future milestone, keep using `make verify-fast` as the routine floor and escalate to `make verify-deep` only when the change crosses the browser/live seam.
