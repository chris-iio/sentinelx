---
id: M015
title: "Intake Workbench"
status: complete
completed_at: 2026-04-26T12:05:56.723Z
key_decisions:
  - Server-render compact Recent Analyses on `/` with bounded `HistoryStore.list_recent(limit=4)` and existing `/history/<id>` links instead of adding a client fetch/polling system.
  - Use a dominant command card plus compact secondary recent rail on desktop, stacked recent list on mobile, to preserve the fast paste-first hierarchy.
  - Clarify Offline/Online mode by enhancing the existing native button/hidden-input contract rather than replacing the semantics with a custom switch.
  - Keep pre-submit IOC preview, provider/enrichment changes, heavy dashboarding, and results/detail redesign out of M015 to protect the fast intake scope.
  - Fix mobile overflow by widening only the index page shell and constraining decorative pseudo-element overflow, avoiding shell clipping that would interfere with clickable recent rows.
key_files:
  - app/templates/index.html
  - app/routes/analysis.py
  - app/static/src/input.css
  - app/static/src/ts/modules/form.ts
  - app/static/src/ts/modules/form.test.ts
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/test_index_intake_contract.py
  - tests/test_history_routes.py
  - tests/e2e/conftest.py
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_homepage.py
  - tests/e2e/test_ui_controls.py
  - .gsd/REQUIREMENTS.md
  - .gsd/PROJECT.md
lessons_learned:
  - Preserve stable form selectors and route semantics first, then layer visual restructuring with focused contract tests and browser proof.
  - Secondary data surfaces on `/` must be bounded and fail-open so history storage availability never becomes a prerequisite for paste-and-extract.
  - Mode-state UI should render from one normalized state path; otherwise hidden inputs, ARIA state, visible status copy, and submit styling can drift apart.
  - Responsive overflow fixes on interactive pages should avoid broad clipping because clipping can hide real layout problems and interfere with click targets.
  - Final intake workbench proof needs both route/security assertions and browser assertions because the risk is cross-slice composition, not any single markup change.
---

# M015: Intake Workbench

**Redesigned SentinelX `/` into a fast analyst Intake Workbench with a dominant paste command card, clearer Offline/Online mode, compact fail-open Recent Analyses, and preserved extraction/history/security behavior.**

## What Happened

M015 converted the SentinelX home page from a thin textarea entry point into a fast analyst Intake Workbench while keeping the original paste-to-results loop intact. S01 established the command-card foundation around `.page-index`, `.intake-workbench`, and `.command-card`, preserving the POST `/analyze` form, CSRF, stable form IDs, hidden offline `mode` input, submit enablement, and default Offline paste-to-results path. S02 clarified the Offline/Online choice with visible help/status copy while retaining the native button plus `aria-pressed` and hidden-input form contract; `form.ts` now renders hidden input state, widget data, ARIA state, visible status, and submit-button mode class from one normalized state path. S03 added compact Recent Analyses as a secondary, server-rendered rail/list: GET `/` performs one bounded `HistoryStore.list_recent(limit=4)` read, renders linked rows/empty/unavailable states safely, and fails open so storage trouble cannot block intake. S04 assembled and proved the whole workbench, adding integrated route/security and browser assertions, fixing a real mobile overflow issue by widening only the index page shell and constraining the decorative pseudo-element, and re-running the broad regression lanes.

Code-change verification passed. The current branch is `main`, so the direct merge-base diff against `main` is intentionally empty (`HEAD` equals the merge base). Milestone-scoped commit evidence with `GSD-Task: S01/T01` through `S04/T02` shows non-`.gsd/` implementation/test changes in `app/templates/index.html`, `app/routes/analysis.py`, `app/static/src/input.css`, `app/static/src/ts/modules/form.ts`, generated `app/static/dist/*`, and route/Playwright/Vitest tests. Fresh closeout verification also re-ran `make verify-fast` successfully: 1026 non-E2E pytest tests passed, 87 Vitest tests passed, `npx tsc --noEmit` passed, and `make build` regenerated assets.

Decision re-evaluation:

| Decision | Built outcome | Still valid? | Next action |
|---|---|---:|---|
| D070 — Server-render recent summaries on `/` using `HistoryStore.list_recent(limit)` and `/history/<id>` links. | S03/S04 shipped bounded server-rendered recent rows, empty/unavailable states, safe links, and a real browser resume click into `/history/<id>`. | Yes | Revisit only if future requirements need live refresh or richer filtering. |
| D071 — Use dominant command card plus compact secondary recent rail on desktop and stacked list on mobile. | S01/S03/S04 shipped and proved command-card dominance, secondary recent rail, mobile stacking, and no 390px overflow. | Yes | Keep this as the intake-page layout baseline. |
| D072 — Clarify existing mode toggle while preserving stable hidden-input and selector semantics. | S02/S04 preserved `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, native button/ARIA behavior, and route semantics while improving copy/status clarity. | Yes | Revisit only if future accessibility review finds the button pattern insufficient. |
| D073 — Exclude pre-submit preview, provider/enrichment changes, dashboarding, and results/detail redesign from M015. | All slices maintained scope boundaries; S04 explicitly verified no preview surfaces and full extraction/history/security continuity. | Yes | Treat preview/provider/dashboard/results work as separate future milestones if prioritized. |

## Success Criteria Results

| Success criterion | Result | Evidence |
|---|---:|---|
| `/` functions as a fast analyst intake workbench with paste dominant. | PASS | S01 delivered `.page-index`, `.intake-workbench`, and `.command-card`; S04 re-proved stable paste form, submit enablement, command-card dominance, and no preview surface. |
| Primary flow remains paste → choose Offline/Online → Extract → results, with no pre-submit preview. | PASS | S01 proved default Offline extraction; S02 proved offline/online route behavior; S04 re-proved Offline paste-to-results from the assembled page and absence of `.ioc-preview`, `.preview-rail`, and pre-submit `.page-results`. |
| Offline/Online mode is clearer while preserving hidden `mode` contract and accessibility behavior. | PASS | S02 added visible heading/help/status copy and centralized state sync in `form.ts`; Vitest/Playwright/route proof covered hidden input, `aria-pressed`, keyboard activation, status copy, and online-without-provider behavior. |
| Compact Recent Analyses appears when history exists and links to saved reload routes. | PASS | S03 added `HistoryStore.list_recent(limit=4)`, `.recent-analysis-row`, and `url_for('main.history_detail', ...)` links; S04 clicked a seeded row into `/history/<id>`. |
| History listing failures never block paste or extraction. | PASS | S03/S04 route and browser tests cover exception handling, sanitized warning logging, unavailable state, preserved form/CSRF/mode controls, and continued submit enablement. |
| Desktop/mobile layouts preserve command-card priority and keep history secondary. | PASS | S03 proved rail hierarchy/mobile stacking; S04 proved desktop dominance, mobile rail below command card, no horizontal overflow at 390px, and fixed the shell overflow without clipping interactive rows. |
| Existing extraction, enrichment, history reload, CSRF/security, TypeScript/build, and E2E behavior remain intact. | PASS | S04 passed 27 route/security/history tests, 34 focused browser assembly tests, `make verify-fast`, and full E2E (125 tests). Fresh closeout re-ran `make verify-fast` successfully. |

## Definition of Done Results

| Definition-of-done item | Result | Evidence |
|---|---:|---|
| Code changes exist for the milestone. | PASS | Direct diff against `main` is empty because `HEAD` already equals `main`/merge-base, so commit evidence was used. Recent M015-scoped commits with `GSD-Task: S01/T01` through `S04/T02` touch non-`.gsd/` files including `app/templates/index.html`, `app/routes/analysis.py`, `app/static/src/input.css`, `app/static/src/ts/modules/form.ts`, generated assets, and tests. |
| All roadmap slices are complete. | PASS | `.gsd/milestones/M015/M015-ROADMAP.md` has `[x]` for S01, S02, S03, and S04; `gsd_milestone_status` reports all four slices complete with all eight tasks done. |
| Slice summaries exist. | PASS | `S01-SUMMARY.md`, `S02-SUMMARY.md`, `S03-SUMMARY.md`, and `S04-SUMMARY.md` are present and each reports `verification_result: passed`. |
| Cross-slice integration points work. | PASS | S04 consumed S01 command-card selectors, S02 mode contract, and S03 recent rail/fail-open history behavior, then proved them together with integrated route/security tests and Playwright flows. |
| Verification evidence is current. | PASS | Fresh milestone-close `make verify-fast` passed: 1026 pytest, 87 Vitest, TypeScript, and build. S04 also records passing full E2E with 125 tests after final code changes. |
| Horizontal checklist, if present. | PASS | No separate Horizontal Checklist was present in the M015 roadmap; equivalent cross-cutting items were verified through the roadmap success criteria and M015 validation artifact. |

## Requirement Outcomes

| Requirement | Outcome | Evidence |
|---|---|---|
| R013 | Validated before closeout; remains validated. | S01 delivered command-card DOM/CSS foundation and focused route/build/TypeScript/Playwright proof. |
| R070 | Validated before closeout; remains validated. | S04 final integrated proof covers fast workbench, stable paste form, submit enablement, secondary recent rail, no preview surfaces, and fail-open history. |
| R071 | Validated before closeout; remains validated. | S04 re-proved paste → Offline → Extract → results in the final assembled layout with no enrichment polling. |
| R072 | Validated before closeout; remains validated. | S02 verified clearer Offline/Online copy/status and preserved hidden `mode` semantics through route, Vitest, TypeScript/build, and Playwright checks. |
| R073 | Validated before closeout; remains validated. | S03 delivered bounded server-rendered Recent Analyses and `/history/<id>` links; S04 proved real resume navigation. |
| R074 | Validated before closeout; remains validated. | S03/S04 prove fail-open history behavior with preserved form, CSRF, mode controls, and submit path. |
| R075 | Validated before closeout; remains validated. | S04 proves desktop dominance, mobile stacking below the command card, and no horizontal overflow. |
| R076 | Updated from active to validated during milestone closeout. | `gsd_requirement_update` recorded S04 final regression evidence plus fresh closeout `make verify-fast` evidence covering extraction, enrichment continuity, history reload/resume, CSRF/security, TypeScript/build, generated assets, Vitest, and E2E behavior. |
| R077–R079 | Remain deferred. | M015 deliberately excluded pre-submit preview, email/phishing enrichment depth, and API/automation polish. |
| R080–R082 | Remain out-of-scope anti-features. | M015 did not build a heavy dashboard, did not alter provider/enrichment behavior, and did not redesign results/detail pages. |

## Deviations

No feature-scope deviations. S03 additionally passed recent-analysis context to no-input POST error re-renders to keep the shared index template consistent, and S04 made one CSS/layout fix after new browser assertions exposed mobile horizontal overflow; both were within the intended integration and polish scope.

## Follow-ups

No M015 remediation is required. Future milestones may separately consider pre-submit extraction preview, richer history filtering/live refresh, email/phishing enrichment depth, or API/automation polish if they become primary goals. Continue using `.page-index`, `.intake-workbench`, `.command-card`, `.recent-analyses-rail`, and the preserved mode/form selectors as the intake page baseline.
