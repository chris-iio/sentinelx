# M003: System Efficiency & Completeness

**Gathered:** 2026-03-20
**Status:** Ready for planning

## Project Description

SentinelX is a universal threat intelligence hub for SOC analysts. M001–M002 delivered the extraction pipeline and the results page rework. M003 is a correctness and efficiency pass across all four layers: backend concurrency, frontend rendering, IOC extraction completeness, and the detail page design.

## Why This Milestone

The system works but has known inefficiencies and gaps that should be fixed before adding new features:
- The global `max_workers=4` bottleneck serializes zero-auth providers behind VT's rate limit
- Blind immediate retry on 429 burns API quota
- Email addresses are silently dropped by the classifier despite iocsearcher already extracting them
- The detail page is a design regression from the M002 results page
- `updateSummaryRow()` rebuilds the summary DOM 14× per IOC during streaming

## User-Visible Outcome

### When this milestone is complete, the user can:

- Submit 10 IPs and see zero-auth provider results (Shodan, DNS, ip-api, ASN) arrive significantly earlier — they're no longer queued behind VT's 4/min constraint
- Paste an email header containing `user@evil[.]com` and see the email address extracted into an EMAIL group in results
- Click "View full detail →" and land on a detail page that visually matches the results page (quiet precision design, readable provider fields)

### Entry point / environment

- Entry point: `flask run` (local dev) — submit text via POST /analyze
- Environment: local dev
- Live dependencies involved: enrichment provider APIs (for S01 rate-limit testing), none for others (unit tests + E2E with mocking)

## Completion Class

- Contract complete means: orchestrator unit tests prove per-provider semaphore behavior; pipeline unit tests prove email classification; TS typecheck passes; build ≤ 30KB
- Integration complete means: E2E suite ≥ 99 passing; email IOCs render in results page; detail page visually verified
- Operational complete means: none (no service lifecycle changes)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `python3 -m pytest tests/ -q` passes with ≥ 99 E2E tests and all new unit tests
- `make typecheck` exits 0
- `wc -c app/static/dist/main.js` ≤ 30000 bytes
- Email address extracted from test input and displayed in results E2E
- Detail page E2E test verifies M002 design tokens present

## Risks and Unknowns

- **Per-provider semaphore vs. rate-limit correctness** — VT's free tier is 4 req/min (per minute), but a semaphore controls concurrency (simultaneous requests), not rate. 4 concurrent VT requests could all fire in <1s and still hit the rate limit. The pragmatic mitigation: keep the semaphore at 4 (which already respected the limit by accident), but fix the more urgent issue of zero-auth providers being blocked. True rate limiting (token bucket) is out of scope — too complex for the actual symptom.
- **Email type filter in the results page** — `filter.ts` wires type filter buttons from data attributes in the template. Adding IOCType.EMAIL requires a new filter button entry and verifying the filter wiring picks it up automatically.

## Existing Codebase / Prior Art

- `app/enrichment/orchestrator.py` — `EnrichmentOrchestrator`, `_do_lookup()`, `enrich_all()`. The `max_workers=4` and blind retry logic live here.
- `app/pipeline/models.py` — `IOCType` enum. Add `EMAIL = "email"` here.
- `app/pipeline/classifier.py` — `classify()`. Add email regex + IOCType.EMAIL case.
- `app/pipeline/extractor.py` — `extract_iocs()`. iocsearcher already emits `email` type — no extraction change needed, just classifier + IOCType.
- `app/pipeline/normalizer.py` — defanging patterns. Add `[@]`/`[at]` → `@` patterns (already present — verify coverage).
- `app/static/src/ts/modules/row-factory.ts` — `updateSummaryRow()`. Add debounce here.
- `app/static/src/ts/modules/enrichment.ts` — `sortTimers` map pattern is the model for the summary row debounce.
- `app/templates/ioc_detail.html` — current detail page, pre-M002 design. Full rework target for S03.
- `app/static/src/input.css` — design tokens. `--bg-secondary`, `--border`, `--text-secondary`, `--verdict-*` tokens already defined and should be reused in detail page.
- `tests/e2e/conftest.py` — route-mocking infrastructure, reusable for new E2E tests.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R014 — per-provider concurrency control (S01)
- R015 — 429 backoff (S01)
- R016 — email extraction + display (S02)
- R012 — detail page design refresh (S03)
- R017 — summary row debounce (S04)

## Scope

### In Scope

- Per-provider semaphore: raise global workers, add VT-specific cap at 4 concurrent
- 429 backoff: exponential with jitter on rate-limit errors, immediate retry preserved for non-rate-limit errors
- `IOCType.EMAIL` in pipeline models + classifier + extractor
- Email display in results page (ioc-type-badge, filter button, no enrichment)
- Detail page CSS rework to match M002 design tokens
- Graph label truncation fix (currently 12 chars max in graph.ts)
- `updateSummaryRow()` debounce at 100ms per IOC
- E2E test updates for all of the above

### Out of Scope / Non-Goals

- Email enrichment adapters (display-only for now)
- Input page design refresh (R013 stays deferred)
- True token-bucket rate limiting (semaphore is sufficient)
- New enrichment providers
- Relationship graph pivoting or interactivity

## Technical Constraints

- All DOM construction must remain createElement + textContent (SEC-08) — no innerHTML
- Production bundle must stay ≤ 30KB (`wc -c app/static/dist/main.js`)
- `make typecheck` must exit 0 after every TS change
- All 99 existing E2E tests must continue passing

## Integration Points

- iocsearcher — already emits `email` type from `_searcher.search_data()`; no library change needed
- Flask route `/detail/<ioc_type>/<path:ioc_value>` — detail page template only; route unchanged
- EnrichmentOrchestrator — semaphore injected at dispatch time; orchestrator public API unchanged

## Open Questions

- None — scope is well-defined from investigation.
