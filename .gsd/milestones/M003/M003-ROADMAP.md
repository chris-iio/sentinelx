# M003: System Efficiency & Completeness

**Vision:** Fix the known correctness and efficiency gaps in the extraction pipeline, enrichment backend, frontend rendering, and detail page — without adding new features. When M003 is done, the existing system works as well as it should have from the start.

## Success Criteria

- Zero-auth enrichment providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) complete independently of VT's rate limit
- VT 429 responses trigger backoff, not immediate quota-burning retry
- Email addresses in analyst input are extracted and displayed in a distinct EMAIL group
- The per-IOC detail page matches the M002 quiet precision design language
- Summary row DOM rebuilds are debounced — max 1-2 per IOC during streaming enrichment

## Key Risks / Unknowns

- **Semaphore vs. rate-limiting distinction** — a concurrency semaphore of 4 is not a true rate limiter (4 req/min). It prevents >4 simultaneous VT calls but doesn't enforce the 1-minute window. This is acceptable: the existing behavior already worked under VT's limit by coincidence, and fixing zero-auth starvation is the real goal. True token-bucket rate limiting is out of scope.
- **Email filter wiring** — `filter.ts` builds type filter buttons from template data attributes. Adding EMAIL to IOCType must be confirmed to flow through to the filter bar automatically; a missed wiring would cause EMAIL IOCs to be unfiltered/unreachable via type filter.

## Proof Strategy

- Semaphore behavior → retire in S01 by writing orchestrator unit tests that assert VT calls are capped at 4 concurrent while a zero-auth provider (mocked) completes without waiting
- Email filter wiring → retire in S02 by E2E test that submits text with email addresses and asserts the EMAIL filter button appears and filters correctly

## Verification Classes

- Contract verification: pytest unit tests for orchestrator semaphore + backoff; pytest unit tests for email classifier; make typecheck; bundle size gate
- Integration verification: E2E test confirms email IOCs render in results page; E2E test confirms detail page uses M002 design tokens
- Operational verification: none
- UAT / human verification: visual inspection of detail page design

## Milestone Definition of Done

This milestone is complete only when all are true:

- S01: orchestrator unit tests prove VT semaphore cap + 429 backoff behavior
- S02: email IOC extraction unit tests pass; EMAIL group renders in E2E results page
- S03: detail page E2E verifies M002 design tokens; graph labels untruncated
- S04: summary row debounce verified; all ≥ 99 E2E tests passing; make typecheck clean; bundle ≤ 30KB
- R012, R014, R015, R016, R017 all validated

## Requirement Coverage

- Covers: R014, R015, R016, R017
- Activates from deferred: R012
- Leaves for later: R013
- Orphan risks: none

## Slices

- [x] **S01: Per-Provider Concurrency & 429 Backoff** `risk:high` `depends:[]`
  > After this: orchestrator unit tests prove zero-auth providers run freely while VT is capped at 4 concurrent; 429 triggers backoff delay before retry.

- [ ] **S02: Email IOC Extraction & Display** `risk:medium` `depends:[]`
  > After this: paste text with `user@evil[.]com` → EMAIL group appears in results with extracted address; no enrichment fires.

- [ ] **S03: Detail Page Design Refresh** `risk:medium` `depends:[]`
  > After this: `/detail/ipv4/1.2.3.4` visually matches M002 design — quiet precision tokens, verdict-only color, graph labels untruncated.

- [ ] **S04: Frontend Render Efficiency & Integration Verification** `risk:low` `depends:[S01,S02,S03]`
  > After this: summary row debounce in place; full E2E suite ≥ 99 tests passing covering all M003 changes; make typecheck clean; bundle ≤ 30KB.

## Boundary Map

### S01 → S04

Produces:
- `app/enrichment/orchestrator.py` — `_do_lookup()` with per-provider semaphore dict and 429-aware backoff retry
- `tests/test_orchestrator.py` (or equivalent) — unit tests for semaphore cap and backoff behavior

Consumes:
- nothing (independent)

### S02 → S04

Produces:
- `app/pipeline/models.py` — `IOCType.EMAIL = "email"`
- `app/pipeline/classifier.py` — email regex + classify case returning IOCType.EMAIL
- `app/templates/partials/_ioc_card.html` — ioc-type-badge--email CSS variant (or inherits zinc neutral)
- `app/templates/results.html` — EMAIL section in grouped type rendering (if not already auto-handled by Jinja loop)
- `app/static/src/input.css` — ioc-type-badge--email rule if needed
- Unit tests for email extraction + classification

Consumes:
- nothing (independent)

### S03 → S04

Produces:
- `app/templates/ioc_detail.html` — full rework using M002 design tokens
- `app/static/src/input.css` — detail page CSS rules using existing design tokens
- Graph label truncation fix in `app/static/src/ts/modules/graph.ts`

Consumes:
- nothing (independent)

### S04 (integration)

Produces:
- `app/static/src/ts/modules/row-factory.ts` — debounced `updateSummaryRow()` using 100ms timer per IOC
- `app/static/src/ts/modules/enrichment.ts` — debounce timer map for summary rows
- Updated E2E tests covering S01–S03 outcomes
- Final verified: make typecheck clean, bundle ≤ 30KB, ≥ 99 E2E passing

Consumes from S01:
- Orchestrator changes (verified in unit tests; no E2E surface change)

Consumes from S02:
- IOCType.EMAIL + classifier + template changes (E2E verifies EMAIL group renders)

Consumes from S03:
- Detail page rework (E2E verifies design tokens present on detail page)
