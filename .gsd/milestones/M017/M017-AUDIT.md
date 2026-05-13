# M017 Optimization Audit — SentinelX

- Mode: `baseline`
- Generated at: `2026-05-13 08:38:29 UTC`
- Repo root: `/home/chris/projects/sentinelx`
- Output path: `.gsd/milestones/M017/M017-AUDIT.md`

## Workflow contract

- A finding must be backed by **measurement when practical**. If direct measurement is awkward or too invasive, the finding must cite **explicit code-path reasoning** instead of taste-based cleanup language.
- Every finding must land in exactly one ranked bucket: `do now`, `do next`, `later`, or `leave alone`.
- Every finding must call out the continuity guardrails it could endanger and the verification lanes that must be rerun before claiming the optimization is safe.
- `leave alone` is a valid outcome when current architecture is already intentional and the evidence does not justify churn.

## Command surface

| Entry point | Command | Purpose |
| --- | --- | --- |
| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |
| Template scaffold | `python3 tools/optimization_audit.py --milestone-id M017 --mode template --output .gsd/milestones/M017/M017-AUDIT-TEMPLATE.md` | Create a reusable milestone-local ranked artifact template. |
| Working baseline artifact | `python3 tools/optimization_audit.py --milestone-id M017 --mode baseline --output .gsd/milestones/M017/M017-AUDIT.md` | Create/update the current audit document used by later optimization slices. |
| Convenience targets | `make audit-m017-template` / `make audit-m017` | Repo-native wrappers around the same workflow for contributors. |

## Verification lanes

| Lane | Command | Use when |
| --- | --- | --- |
| verify-fast | `make verify-fast` | Default rerun lane for backend/frontend logic, build/test plumbing, and any finding that does not change mocked-online browser behavior. |
| verify-deep | `make verify-deep` | Required whenever a change touches live enrichment orchestration, polling/status flow, results-page DOM/state, or mocked-online browser seams. |
| verify | `make verify` | Full pre-handoff lane when downstream slices need the unambiguous repo-wide proof command. |

## Verified rerun checklist

| Step | Proof surface | Command | Required when | Expected durable evidence |
| --- | --- | --- | --- | --- |
| 1 | M017 workflow runner + identity-grounded ranked artifact refresh | `python3 tools/optimization_audit.py --milestone-id M017 --mode baseline --output .gsd/milestones/M017/M017-AUDIT.md` | Every M017 optimization slice before handoff. | Updated M017 audit artifact citing `docs/project-map.md`, R085/R087, D078-D080, S01 seam priorities, and current ranked buckets. |
| 2 | Fast local regression lane | `make verify-fast` | Every shipped optimization, including keep-decisions that changed code or build/test plumbing. | Fresh command capture or task summary evidence proving unit/integration/frontend/build checks stayed green. |
| 3 | Deterministic mocked-online browser proof | `make verify-deep` | Any change touching live enrichment orchestration, polling/status flow, shared result application, or analyst-visible DOM/state. | Fresh evidence proving the analyst-visible mocked-online browser seam still passes end-to-end. |
| 4 | S03 target confirmation | Compare `do now` against project-map priority and fresh measurement captures | Before S03 implementation starts. | Clear do-now/do-next/later/leave-alone decision explaining why the selected optimization is worth doing. |

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
| runtime-provider-diagnostics | `internal benchmark: EnrichmentOrchestrator synthetic runtime/provider diagnostics` | 0 | 67 | provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e; dispatch=4; attempts=5; cache-hit ratio 1/5 (20%); retries=1 (429=1); errors=1; latency total=2.25s max=1.00s. |
| status-snapshot-scaling | `internal benchmark: EnrichmentOrchestrator.get_status() snapshot scaling` | 0 | 2 | 400 polls at 5000 retained results: `get_status()` 1.46ms vs `get_incremental_status(since=4990)` 0.46ms (3.1x faster) while returning 10 tail rows with next_since=5000. |
| cache-store-tempdb | `internal benchmark: CacheStore temp WAL put/get loop` | 0 | 19 | Temp WAL cache DB: 250 puts in 4.64ms, 250 TTL reads in 1.36ms, 250 hits, 250 retained rows. |
| history-store-tempdb | `internal benchmark: HistoryStore temp WAL save/list/load loop` | 0 | 17 | Temp WAL history DB: 180 saves in 3.53ms, list_recent(20) in 0.07ms, single load in 0.04ms, latest total_count=1, recent rows=20. |

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

## M017 identity-grounded contract

- Project map grounding: `docs/project-map.md` is present and anchors this audit to SentinelX as a local analyst IOC triage workbench: paste investigation text, extract IOCs, optionally enrich them, then review verdict-first results with history, details, filters, copy/export, and diagnostics.
- Analyst identity: SentinelX is optimized as a fast local analyst IOC triage workbench, not as generic subsystem cleanup.
- Decisions: D078 requires `docs/project-map.md` and `.gsd/PROJECT.md` before target selection; D079 ranks work by the analyst IOC triage loop; D080 allows aggressive/moderate cross-seam optimization only with proof.
- Requirements: R085 requires product-identity-grounded optimization decisions; R087 requires measurement when practical or explicit code-path reasoning plus regression proof.
- S01 seam inventory priorities: (1) enrichment fan-out/status snapshot cost across `app/enrichment` and `app/routes`, (2) browser result rendering churn, (3) SQLite cache/history access shape, (4) IOC pipeline duplicate candidate handling in `app/pipeline`, (5) provider registration/config diagnostics clarity.
- S03 shipped proof: the do-now M017 optimization is the enrichment fan-out/status snapshot path, with measurement from `status-snapshot-scaling` and code-path proof in `app/enrichment/orchestrator.py::get_incremental_status()` plus `app/routes/_helpers.py::_get_enrichment_status()`; downstream seam inventory still cites `app/pipeline/extractor.py` for later IOC-pipeline work.

## Baseline stance

- Do now: S03 shipped the enrichment fan-out/status snapshot optimization, the highest-ranked S01 seam in SentinelX's analyst IOC triage loop, with `status-snapshot-scaling` measurement and explicit route/orchestrator code-path proof.
- Do next: browser result rendering churn remains important, but should follow the status/fan-out target unless fresh browser-visible evidence outranks it.
- Later: SQLite cache/history access shape and IOC duplicate-candidate handling need targeted tempdb/query-count or duplicate-fixture evidence before promotion.
- Leave alone: provider registration/config diagnostics clarity should not distract this optimization pass unless readiness diagnostics become the actual blocker.
- Evidence standard: every shipped optimization needs before/after measurement when practical, or explicit code-path reasoning plus regression proof; S03 now satisfies that standard for status polling, and artifacts must not expose API keys, tokens, or analyst-sensitive IOC data.

## Ranked findings

### do now

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Keep S03's shipped enrichment status polling optimization on the tail-only snapshot path for SentinelX's analyst IOC triage loop. | enrichment fan-out/status snapshot cost | measurement + code-path reasoning | `docs/project-map.md` ranks enrichment fan-out/status snapshot cost as the #1 optimization priority for the local analyst IOC triage workflow. The `status-snapshot-scaling` capture measures the old retained-list snapshot against the shipped tail accessor: `get_status()` scales with retained results while `get_incremental_status(since=4990)` returns only the tail and preserves `next_since`. Code-path proof lives in `app/enrichment/orchestrator.py::get_incremental_status()` and `app/routes/_helpers.py::_get_enrichment_status()`, where the polling route calls the incremental accessor and serializes only returned tail rows plus aligned `cached_markers`. | R085, R087, R008, R010, R018, R019, D078, D079, D080 | `python3 tools/optimization_audit.py --milestone-id M017 --mode baseline`; `make verify-fast`; add `make verify-deep` for browser-visible polling changes | S03 shipped this path with measurement and code-path proof; preserve `status`, `terminal`, `terminal_reason`, `error`, `next_since`, failure tombstones, history-save diagnostics, and redacted diagnostics without falling back to full result-list snapshots on polling. |

### do next

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Measure browser result rendering churn after the status/fan-out target, especially flush-wide recount and sort work during polling/history replay. | browser polling and result application | project-map priority + code-path reasoning | The S01 seam inventory ranks browser result rendering churn second because it sits directly in the analyst's verdict-first results review path. The M013 baseline already narrowed repeated card/slot lookups, so M017 follow-up should focus on remaining flush-wide `updateDashboardCounts()` and `sortCardsBySeverity()` work. | R085, R087, R008, R009, R010, R019 | `make verify-fast`, `make verify-deep` | Preserve live/history parity, filtering/sorting/copy/export/detail links, textContent-safe DOM construction, and deterministic mocked-online browser proof. |

### later

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Defer SQLite cache/history access-shape and IOC duplicate-candidate work until the top analyst-loop seams have fresh evidence. | local cache/history; IOC extraction pipeline | ranked project-map priority | `docs/project-map.md` ranks SQLite access shape third and duplicate IOC pipeline handling fourth. Both matter, but neither outranks the enrichment/results loop for the current M017 do-now target without new contention or duplicate-heavy fixture evidence. | R085, R087, R022, R040 | `make verify-fast` plus targeted cache/history or pipeline fixtures when promoted | Promote only with tempdb/query-count evidence or a representative duplicate-heavy text fixture showing equivalent IOC output with less work. |

### leave alone

| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |
| --- | --- | --- | --- | --- | --- | --- |
| Leave provider registration/config diagnostics clarity alone for this optimization pass unless readiness diagnostics become the blocker. | provider registration/config diagnostics | identity-grounded keep-decision | The S01 project map ranks this fifth: it supports analyst confidence and secret-redaction boundaries, but it is not the best current performance target for the paste → enrich → review loop. | R085, R087, D080 | `make verify-fast` if settings/diagnostics code changes | Do not expose API keys, tokens, or analyst-sensitive IOC data in audit artifacts, settings output, diagnostics, or command captures. |

## M017 audit notes

- This baseline intentionally contains no placeholder rows; each bucket records a current do-now/do-next/later/leave-alone decision.
- Re-run with `make audit-m017` after each optimization slice so S03/S04 can consume current command-capture rows and shipped-proof language.
- Failed optional capture commands are recorded in the measurement table with nonzero exits so unrelated artifact generation remains inspectable.
