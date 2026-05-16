# M020 Optimization Audit — SentinelX

- Mode: `baseline`
- Generated at: `2026-05-16 08:35:45 UTC`
- Repo root: `/home/chris/projects/sentinelx`
- Output path: `.gsd/milestones/M020/M020-AUDIT.md`

## Workflow contract

- A finding must be backed by **measurement when practical**. If direct measurement is awkward or too invasive, the finding must cite **explicit code-path reasoning** instead of taste-based cleanup language.
- Every finding must land in exactly one ranked bucket: `do now`, `do next`, `later`, or `leave alone`.
- Every finding must call out the continuity guardrails it could endanger and the verification lanes that must be rerun before claiming the optimization is safe.
- `leave alone` is a valid outcome when current architecture is already intentional and the evidence does not justify churn.

## Command surface

| Entry point | Command | Purpose |
| --- | --- | --- |
| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |
| Template scaffold | `python3 tools/optimization_audit.py --milestone-id M020 --mode template --output .gsd/milestones/M020/M020-AUDIT-TEMPLATE.md` | Create a reusable milestone-local ranked artifact template. |
| Working baseline artifact | `python3 tools/optimization_audit.py --milestone-id M020 --mode baseline --output .gsd/milestones/M020/M020-AUDIT.md` | Create/update the current audit document used by later optimization slices. |
| Convenience targets | `make audit-m020-template` / `make audit-m020` | Repo-native wrappers around the same workflow for contributors. |

## Verification lanes

| Lane | Command | Use when |
| --- | --- | --- |
| verify-fast | `make verify-fast` | Default rerun lane for backend/frontend logic, build/test plumbing, and any finding that does not change mocked-online browser behavior. |
| verify-deep | `make verify-deep` | Required whenever a change touches live enrichment orchestration, polling/status flow, results-page DOM/state, or mocked-online browser seams. |
| verify | `make verify` | Full pre-handoff lane when downstream slices need the unambiguous repo-wide proof command. |

## Verified rerun checklist

| Step | Proof surface | Command | Required when | Expected durable evidence |
| --- | --- | --- | --- | --- |
| 1 | M020 workflow runner + aggressive rewrite artifact refresh | `python3 tools/optimization_audit.py --milestone-id M020 --mode baseline --output .gsd/milestones/M020/M020-AUDIT.md` | Every M020 slice before handoff. | Updated M020 audit artifact with current shipped, rejected, deferred, and leave-alone outcomes. |
| 2 | Focused seam regression lane | Run the target-specific pytest/vitest command listed on the finding row. | Every shipped or explicitly rejected rewrite target. | Fresh focused proof tied to the changed seam or rejection evidence. |
| 3 | Fast local regression lane | `make verify-fast` | Every implementation slice, including audit-runner changes. | Unit, integration, frontend, typecheck, and build proof remain green. |
| 4 | Deterministic mocked-online browser proof | `make verify-deep` | Browser-visible or live-enrichment-visible rewrites. | Analyst-visible mocked-online workflows still pass end-to-end. |
| 5 | Final integration proof | `make verify` plus refreshed generated M020 audit. | S05 closeout. | Final artifact records shipped/rejected outcomes and the full app verification lane passes. |

## Continuity guardrails

| Requirement | Continuity guardrail |
| --- | --- |
| R008 | Preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity. |
| R009 | Preserve CSP, CSRF, SSRF allowlist, host validation, and DOM-safety constraints. |
| R010 | Preserve or improve polling/render efficiency. |
| R014 | Preserve per-provider concurrency behavior unless evidence proves a better approach. |
| R015 | Preserve 429 backoff behavior unless evidence proves a better approach. |
| R018 | Preserve semaphore/backoff and snapshot correctness unless evidence proves otherwise. |
| R019 | Preserve cursor-based polling efficiency unless evidence proves otherwise. |
| R020 | Preserve persistent HTTP session behavior where still justified. |
| R022 | Preserve WAL-mode cache/history store behavior unless evidence supports change. |
| R040 | Keep strong verification continuity while refactoring and optimizing. |

## Measurement captures

| Capture | Command | Exit | Duration (ms) | Summary |
| --- | --- | ---: | ---: | --- |
| runtime-provider-diagnostics | `internal benchmark: EnrichmentOrchestrator synthetic runtime/provider diagnostics` | 0 | 4 | provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e; dispatch=4; attempts=5; cache-hit ratio 1/5 (20%); retries=1 (429=1); errors=1; latency total=2.25s max=1.00s. |
| status-snapshot-scaling | `internal benchmark: EnrichmentOrchestrator.get_status() snapshot scaling` | 0 | 33 | 400 polls at 5000 retained results: `get_status()` 31.00ms vs `get_incremental_status(since=4990)` 2.44ms (12.7x faster) while returning 10 tail rows with next_since=5000. |
| cache-store-tempdb | `internal benchmark: CacheStore temp WAL put/get loop` | 0 | 24 | Temp WAL cache DB: 250 puts in 10.18ms, 250 TTL reads in 1.35ms, 250 hits, 250 retained rows. |
| cache-stats-query-count | `internal benchmark: CacheStore.stats aggregate query count` | 0 | 13 | CacheStore.stats() executed 1 SELECT for total_entries=1 and oldest_present=True: SELECT COUNT(*), MIN(cached_at) FROM enrichment_cache. |
| history-store-tempdb | `internal benchmark: HistoryStore temp WAL save/list/load loop` | 0 | 15 | Temp WAL history DB: 180 saves in 3.00ms, list_recent(20) in 0.09ms, single load in 0.05ms, latest total_count=1, recent rows=20. |
| pipeline-duplicate-candidates | `internal benchmark: run_pipeline normalized duplicate candidate gate` | 0 | 64 | 7 raw URL variants normalize to 1 IOC value(s); classify calls=1; output values=http://evil.com. |

## Seam checklist

### runtime/provider

- Continuity focus: Orchestrator concurrency, cache interaction, retry/backoff behavior, and provider dispatch cost.
- Audit prompt 1: What work is measured here, and what hot-path reasoning is still required?
- Audit prompt 2: Which guardrails and rerun lanes must stay attached if we change this seam?

### request/status

- Continuity focus: Flask route/helper status flow, next_since continuity, and history-save diagnostics.
- Audit prompt 1: What request-path work is actually hot versus only structurally central?
- Audit prompt 2: If a finding changes analyst-visible status behavior, which proof lane catches it?

### persistence

- Continuity focus: SQLite WAL cache/history store access, locking, query shape, and post-enrichment durability.
- Audit prompt 1: Is there measured contention, or should this seam remain a leave-alone decision?
- Audit prompt 2: What evidence would justify revisiting long-lived WAL-backed connections?

### frontend/render

- Continuity focus: Polling cadence, shared live/history result application, and DOM/render churn.
- Audit prompt 1: What analyst-visible work is actually happening per poll or per render flush?
- Audit prompt 2: Does the finding preserve live/history parity and deterministic mocked-online proof?

## Ranked finding schema

Use the same table shape in every bucket. Required fields per row:

- **Finding** — one concrete optimization or keep-decision.
- **Seam** — `runtime/provider`, `request/status`, `persistence`, or `frontend/render`.
- **Evidence kind** — `measurement` or `code-path reasoning`.
- **Evidence summary** — cite the measurement, command capture, or the exact path reasoning that justifies the rank.
- **Continuity guardrails** — list the requirement IDs that must remain protected.
- **Rerun lanes** — at minimum one of `make verify-fast`, `make verify-deep`, or `make verify`.
- **Continuity notes** — state what behavior must remain true after the future change ships, or why the seam should stay untouched.

## M020 aggressive rewrite contract

- Project map grounding: `docs/project-map.md` is present and anchors this audit to SentinelX as a local analyst IOC triage workbench: paste investigation text, extract IOCs, optionally enrich them, then review verdict-first results with history, details, filters, copy/export, and diagnostics.
- Milestone intent: M020 is an audit-led aggressive refactor and deep optimization pass, not a cosmetic cleanup pass.
- Decisions: D081 uses audit-led rewrites; D082 keeps the strict proof bar; D083 preserves the analyst IOC triage loop as the integration contract.
- Requirements: R094 requires this source-generated milestone audit surface; R095 ranks aggressive rewrite candidates; R096 ties shipped or rejected outcomes to evidence; R097 preserves analyst workflows; R098 requires focused, fast, deep, and final verification lanes; R099 preserves diagnostics, failure visibility, and redaction boundaries; R100 records durable generated audit and closeout outcomes.
- S01 produces this generated audit artifact and ranked rewrite list. S02 consumed the highest-confidence route-helper candidate. S03 shipped the diagnostics policy extraction. S04 measured and rejected/deferred frontend virtualization promotion. S05 refreshes final shipped/rejected outcomes and full verification proof.

## Baseline stance

- Do now: S02 shipped duplicate route IOC grouping and response construction behind shared helpers across analysis, API, and history replay, with focused route/API/history proof.
- Do now: S03 shipped diagnostics sanitization policy extraction, centralizing archive, source, and redaction caps while preserving secret-redaction behavior.
- Do now: S04 measured large-result frontend render pressure and keeps the current severity-change gate; virtualization remains deferred.
- Leave alone: provider concurrency/backoff/session semantics remain explicit keep-decisions unless fresh runtime/provider measurements overturn the M017 evidence.
- Evidence standard: every M020 rewrite must be shipped or rejected with measurement when practical, or explicit code-path reasoning plus focused regression proof; no row should be closed with placeholder prose.

## Ranked findings

### do now

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Keep S02's duplicate route IOC grouping rewrite on the shared route helper seam. | request/status | code-path reasoning + focused regression proof | `app/routes/analysis.py`, `app/routes/api.py`, and `app/routes/history.py` were the highest-confidence M020 rewrite target because those request surfaces rebuilt IOC template context, grouped persisted IOC rows, and serialized/grouped JSON API payloads separately after prior micro-optimizations. S02 now centralizes those builders in `app/routes/_helpers.py` through `_ioc_template_context()`, `_history_ioc_template_context()`, `_group_iocs_for_template()`, `_group_history_iocs()`, and `_serialized_ioc_response_payload()`, while the route modules keep thin imports for their response-specific behavior. Focused proof is `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`. | R008, R009, R010, R040, R094, R095, R096, R097, R098, R099 | `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`; `make verify-fast` | Preserve online admission, missing-provider redirects, grouped template IOC data, JSON API shape, empty history replay, diagnostics, CSRF/DOM safety, and secret redaction while keeping duplicate route-owned IOC grouping and serialization code behind the shared helper seam. |
| Keep S03's diagnostics sanitization caps behind the shared immutable policy object. | request/status | code-path reasoning + focused regression proof | `app/diagnostics/policy.py` now owns `DiagnosticSanitizationPolicy` and `DIAGNOSTIC_SANITIZATION_POLICY`, an immutable caps object shared by `app/diagnostics/assembler.py`, `app/diagnostics/redaction.py`, and `app/diagnostics/sources.py`. Assembler archive-path and generated-filename bounds, runtime source byte/string/list/dict/depth caps, and redaction depth/label caps now derive from that policy while the existing optimized helper names remain stable. Focused proof is `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py`. | R009, R040, R096, R097, R098, R099 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py`; `make verify-fast` | Preserve exact-secret longest-first replacement, configured-secret inventory labels, archive path rejection, manifest collision checks, truncation caps, and secret-free diagnostic bundles while keeping diagnostics caps centralized. |
| Keep large-result frontend rendering on the severity-change gate and defer virtualization. | frontend/render | work-count measurement + focused regression proof | `app/static/src/ts/modules/result-application.test.ts::measures large-result render pressure at the severity-change gate` builds a 240-card results fixture. After the initial clean verdict, a second provider result with the same severity performs zero `.ioc-card` whole-grid scans, zero dashboard recounts, and zero sort calls. A later malicious severity change performs exactly one document-level card scan for dashboard counts and one grid-level card scan for the debounced sort. Current evidence supports preserving the severity-change gate rather than promoting DOM virtualization. | R008, R009, R010, R019, R040, R096, R097, R098 | `npx vitest run app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`; `make verify-deep` if virtualization is reconsidered | Preserve filtering, sorting, copy/export, detail links, expansion state, textContent-safe rendering, and the severity-change gate. Reconsider virtualization only with evidence beyond this 240-card work-count fixture. |

### do next

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh S05's closeout audit after every shipped or rejected rewrite so downstream proof stays current. | audit/proof handoff | code-path reasoning + generated artifact proof | S05 depends on the generated M020 audit being the DB-independent handoff for shipped, rejected, deferred, and leave-alone outcomes. The runner already records command-surface rows, measurement captures, rerun lanes, and ranked finding rows, so the next optimization step is to keep refreshing `make audit-m020` after each implementation slice rather than letting S02-S04 proof drift from the final closeout artifact. | R040, R094, R095, R096, R097, R098, R099, R100 | `make audit-m020`; `python3 -m pytest -q tests/test_optimization_audit.py`; `make verify-fast` | Preserve the generated artifact as the inspection surface for future agents: every closeout update must keep command-surface rows, failed-capture visibility, proof lanes, and ranked shipped/rejected/deferred/leave-alone outcomes synchronized. |

### later

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Defer frontend DOM virtualization until measured result-card counts justify the browser-visible regression surface. | frontend/render | code-path reasoning | M017 removed repeated coordinator-local DOM lookup work and narrowed flush-wide recount/reorder calls. A deeper virtualization rewrite would touch `app/static/src/ts/modules/result-application.ts`, `row-factory.ts`, filters, copy/export, and E2E-visible DOM contracts. Current audit captures do not show enough large-result browser pressure to justify that risk for M020 S02. | R008, R009, R010, R019, R040, R096, R097, R098 | `npx vitest run`; `make verify-deep`; `make verify` when promoted | Promote only with a fixture or browser measurement showing card-count pressure. Preserve filtering, sorting, copy/export, detail links, expansion state, textContent-safe rendering, and mocked-online browser proof. |

### leave alone

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Leave provider concurrency/backoff semantics alone during M020 unless fresh live evidence contradicts the M017 keep-decision. | runtime/provider | measurement + code-path reasoning | The M017 `runtime-provider-diagnostics` capture showed cache hits did not dominate dispatch cost, while tests protect semaphore scope, 429 backoff, cached markers, and diagnostics. M020 should not rewrite provider scheduling simply because it is complex; complexity here reflects quota and failure semantics. | R014, R015, R018, R020, R040, R099 | `python3 -m pytest -q tests/test_orchestrator.py`; `make verify-deep` for live-enrichment-visible changes | Preserve per-provider concurrency caps, retry/backoff, adapter-owned sessions, cache-hit markers, terminal failure visibility, and diagnostics unless a new measurement proves a better contract. |

## M020 audit notes

- This baseline intentionally contains no placeholder rows; each bucket records a current do-now/do-next/later/leave-alone decision.
- Re-run with `make audit-m020` after each implementation slice so S05 can consume current shipped/rejected outcome language.
- Failed optional capture commands are recorded in the measurement table with nonzero exits so incomplete proof remains visible rather than hidden.
