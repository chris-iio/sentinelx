---
verdict: pass
remediation_round: 2
---

# Milestone Validation: M003

## Success Criteria Checklist

- [x] **Zero-auth enrichment providers complete independently of VT's rate limit** — S01 delivered a per-provider semaphore dict in `EnrichmentOrchestrator` keyed by `adapter.name`, guarded by `requires_api_key=True`. VT is capped at 4 concurrent; zero-auth providers are ungated. `max_workers` raised to 20. `TestPerProviderSemaphore` (3 tests) proves zero-auth providers run freely while VT is capped. All 22 orchestrator tests pass.

- [x] **VT 429 responses trigger backoff, not immediate quota-burning retry** — S01 delivered `_is_rate_limit_error()` static method and exponential backoff in `_do_lookup_body()`: base 15 s × 2^n + uniform(0, 2) jitter, up to 2 retries. Non-429 errors preserve existing immediate single-retry behavior. `TestBackoff429` (4 tests) covers all retry paths. `logging.warning()` emitted on each backoff sleep.

- [x] **Email addresses extracted and displayed in a distinct EMAIL group** — S02 delivered `IOCType.EMAIL = "email"` in `models.py`, custom `_RE_EMAIL_EXTRACT` regex in `extractor.py` (handles `@`, `[@]`, `(@)`, `[at]` separators; `[.]`, `(.)`, `[dot]` dot variants), classifier step 7.5 in `classifier.py`, route guard in `routes.py` excluding EMAIL from `provider_counts`, neutral CSS badge + filter pill. 9 unit/integration tests + 6 E2E tests all passing. 105 total E2E pass with EMAIL filter pill, filtering behaviour, active state, reset, and badge class confirmed.

- [x] **Per-IOC detail page matches M002 quiet precision design language** — S03 delivered full rework of `ioc_detail.html` with stacked provider cards (zinc surfaces, verdict-only color, no inline `<style>` block). 25 CSS rules added to `input.css` inside `@layer components` using existing design tokens exclusively. Graph labels untruncated: Python slicing (`[:20]`/`[:12]`) removed from `routes.py`; JS `.slice(0,12)`/`.slice(0,20)` removed from `graph.ts`; viewBox widened to 700×450 with `orbitRadius=170`. Regression test `test_detail_graph_labels_untruncated` asserts "Shodan InternetDB" in `data-graph-nodes`. All 13 detail route tests pass.

- [x] **Summary row DOM rebuilds debounced — max 1–2 per IOC during streaming enrichment** — S04 delivered `summaryTimers: Map<string, ReturnType<typeof setTimeout>>` debounce map in `enrichment.ts` and `debouncedUpdateSummaryRow()` wrapper replacing the direct `updateSummaryRow()` call at line 359. 100 ms timer per IOC; clear/set/delete lifecycle mirrors the established `sortTimers` pattern. `grep -c 'summaryTimers' enrichment.ts` ≥ 3 confirmed.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Orchestrator unit tests prove VT semaphore cap (4 concurrent) + 429 exponential backoff | `orchestrator.py` per-provider semaphore dict + `_do_lookup_body()` backoff; `TestPerProviderSemaphore` (3) + `TestBackoff429` (4) = 22 total orchestrator tests passing | pass |
| S02 | Email IOC extraction unit tests pass; EMAIL group renders in E2E results page | `IOCType.EMAIL`, `_RE_EMAIL_EXTRACT`, classifier step 7.5, route guard, neutral badge/pill CSS; 9 unit tests + 6 E2E tests; 85 unit + 105 E2E all passing | pass |
| S03 | Detail page E2E verifies M002 design tokens; graph labels untruncated | `ioc_detail.html` reworked with stacked provider cards; all label truncation removed; regression test for "Shodan InternetDB"; bundle 26 KB; 13 tests passing | pass |
| S04 | Summary row debounce in place; ≥ 99 E2E passing; make typecheck clean; bundle ≤ 30 KB | `summaryTimers` debounce added; 817 unit tests 0 failures; 105 E2E 0 failures; typecheck exit 0; bundle 26,783 bytes | pass |

## Cross-Slice Integration

All boundary map entries align with what was actually built:

- **S01 → S04**: Orchestrator semaphore + backoff verified by unit tests (no E2E surface change). S04 confirmed no integration gap — orchestrator unchanged from S04's perspective.
- **S02 → S04**: `IOCType.EMAIL` addition required two S04 test fixes (OTX `supported_types` count 8→9; HTML dedup occurrence count <10→<20). Both fixed in S04/T02 with correct rationale. EMAIL filter pill confirmed surviving full integration run.
- **S03 → S04**: Detail page rework consumed by S04's E2E suite; design token assertions and graph label regression test confirmed in S03 and not broken by S04 changes.
- **S04 (integration)**: All four milestone gates satisfied simultaneously — unit tests (817), E2E (105), typecheck, and bundle — with S01–S03 changes fully integrated.

No boundary mismatches found.

## Requirement Coverage

| Requirement | Owner | Status |
|-------------|-------|--------|
| R012 — detail page design refresh | S03 | Addressed: full `ioc_detail.html` rework, M002 design tokens, label truncation fix, regression test |
| R014 — per-provider concurrency control | S01 | Addressed: semaphore dict, VT capped at 4, zero-auth providers ungated, unit tests prove behavior |
| R015 — 429 exponential backoff | S01 | Addressed: `_is_rate_limit_error()` + backoff in `_do_lookup_body()`, `TestBackoff429` covers all paths |
| R016 — email extraction + display | S02 | Addressed: full pipeline (models → classifier → extractor → template → CSS), 9 unit + 6 E2E tests |
| R017 — summary row debounce | S04 | Addressed: `summaryTimers` map + `debouncedUpdateSummaryRow()` at 100 ms per IOC |

All five active requirements (R012, R014, R015, R016, R017) are substantiated by slice deliverables and passing tests. No active requirements are orphaned.

## Verdict Rationale

This is remediation round 2. No remediation slices were added at any prior round — round 0 passed and round 1 reconfirmed. All four slices report `verification_result: passed`. The M003 Milestone Definition of Done is fully satisfied:

- S01 ✅ orchestrator unit tests prove semaphore cap + backoff
- S02 ✅ email extraction unit tests pass; EMAIL group renders in E2E
- S03 ✅ detail page E2E verifies M002 design tokens; graph labels untruncated
- S04 ✅ debounce in place; 105 E2E passing (> 99 minimum); typecheck clean; bundle 26,783 bytes (< 30,000 limit)
- R012, R014, R015, R016, R017 all addressed with test evidence ✅

No gaps, regressions, or missing deliverables were found. Verdict: **pass**.
