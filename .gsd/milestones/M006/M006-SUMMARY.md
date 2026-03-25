---
id: M006
title: "Analyst Workflow & Coverage — Context"
status: complete
completed_at: 2026-03-25T12:29:26.135Z
key_decisions:
  - Used UUID4 hex as history row id (not autoincrement) — avoids leaking analysis count
  - top_verdict computed at save time and stored in the row — avoids re-parsing results_json on every list_recent()
  - History save failures silently caught — enrichment results must always be available regardless of persistence issues
  - WhoisAdapter uses verdict='no_data' always — WHOIS is informational context, not a threat verdict source
  - WhoisAdapter handles FailedParsingWhoisOutputError and UnknownTldError as graceful degrades rather than hard failures
  - Detail link href uses /ioc/<type>/<value> matching Flask route, not /detail/
  - Replace transition:all with explicit property list on .btn to follow 'never use transition: all' design principle
  - Map .alert-error hardcoded #ff6b6b to var(--verdict-malicious-text) design token
key_files:
  - app/enrichment/history_store.py
  - app/enrichment/adapters/whois_lookup.py
  - app/enrichment/setup.py
  - app/routes.py
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/input.css
  - app/templates/index.html
  - app/templates/results.html
  - tests/test_history_store.py
  - tests/test_history_routes.py
  - tests/test_whois_lookup.py
  - tests/e2e/test_url_e2e.py
  - requirements.txt
lessons_learned:
  - JS replay pattern (history.ts) reusing the same rendering pipeline as live enrichment avoids divergence — single rendering codepath with two entry points is much more maintainable than duplicating rendering logic
  - Non-HTTP adapters (WHOIS on port 43, DNS on port 53) must not import http_safety.py — protocol-specific adapters have different security surfaces
  - python-whois datetime fields are polymorphic (single datetime, list, None, str) — always normalize with a helper before storing
  - Frontend detail link hrefs must match Flask routes exactly (/ioc/ not /detail/) — E2E tests are essential for catching this class of bug that unit tests miss
  - PROVIDER_CONTEXT_FIELDS in row-factory.ts must be updated atomically with backend provider registration — the T02 task summary claimed it was done but the code change was missing, caught only during slice closure verification
  - The HistoryStore WAL-mode SQLite pattern (same as CacheStore) is now proven twice — it's the standard for any new local persistence needs
---

# M006: Analyst Workflow & Coverage — Context

**Closed four analyst-facing gaps: persistent analysis history with home-page listing and full replay, WHOIS domain enrichment as the 15th provider, URL IOC end-to-end polish with 8 E2E tests, and input page redesign to quiet-precision design tokens.**

## What Happened

M006 delivered four independent-but-coherent improvements that make SentinelX more useful as a daily analysis tool without adding infrastructure complexity.

**S01 — Analysis History & Persistence (high risk, delivered clean).** Added HistoryStore class following the CacheStore SQLite WAL-mode pattern. Every online analysis is now persisted with UUID4 hex ID, top_verdict computed at save time, and full IOC/results JSON. The home page shows the 10 most recent analyses with verdict badges, IOC counts, and timestamps. Clicking any entry navigates to /history/<id> where a JS replay module (history.ts) pushes stored results through the exact same rendering pipeline as live enrichment — single rendering codepath, two entry points. 20 unit tests + 13 route integration tests. Background save failures are silently caught so enrichment always works regardless of persistence issues.

**S02 — WHOIS Domain Enrichment (medium risk, delivered clean).** Created WhoisAdapter as the 15th enrichment provider using python-whois on port 43 — no HTTP, no SSRF surface. WHOIS always returns verdict='no_data' since it's informational context, not a threat signal. A _normalise_datetime() helper handles python-whois's polymorphic date returns (single, list, None, str). Error handling maps all python-whois exception types to the correct enrichment model responses. Frontend renders registrar, Created, Expires, NS (as tags), and Org in context field rows. 56 unit tests cover every path. Registered in zero-auth section matching DnsAdapter/CrtShAdapter pattern.

**S03 — URL IOC End-to-End Polish (low risk, delivered clean).** Discovered and fixed a broken detail link: injectDetailLink() in both enrichment.ts and history.ts built hrefs with /detail/ but the Flask route is /ioc/. Fixed both files, rebuilt JS. Created 8 E2E Playwright tests covering URL card rendering, type badge, filter pill, enrichment with URLhaus/VT mocks, and detail link href — following the exact email IOC test pattern for consistency.

**S04 — Input Page Redesign (low risk, delivered clean).** Fixed .page-index flex-direction from row to column so the input card and recent analyses list stack vertically. Audited all index page CSS: replaced 3 hardcoded transition timings with design tokens, replaced transition:all on .btn with explicit property list, replaced hardcoded #ff6b6b on .alert-error with var(--verdict-malicious-text). No template changes needed — S01's recent analyses section was already fully tokenized.

All four slices delivered without blockers or replans. The full test suite grew from ~960 to 1043 tests with zero regressions.

## Success Criteria Results

### 1. Analyst can submit IOCs, close the tab, return to the home page, see the past analysis in a recent list, click it, and see full results reloaded from stored data
**✅ MET.** S01 delivered HistoryStore with save_analysis()/list_recent()/load_analysis(), the /history/<id> route, recent analyses list on the home page, and history.ts JS replay module. 20 unit tests + 13 route integration tests verify the full roundtrip. test_history_detail_returns_200 confirms stored analysis loads. test_index_shows_recent_analyses confirms home page listing.

### 2. Domain IOC enrichment includes WHOIS data (registrar, creation date, expiry, name servers) alongside DNS records and other provider results
**✅ MET.** S02 delivered WhoisAdapter as the 15th provider. 56 unit tests verify registrar/creation_date/expiration_date/name_servers/org extraction. WHOIS is in CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS in row-factory.ts. Registry test confirms 15 providers registered.

### 3. URL IOCs pasted in free-form text are extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct filter pill, and accessible on the detail page
**✅ MET.** S03 fixed broken /detail/ → /ioc/ links and added 8 E2E Playwright tests covering: URL card rendering, type badge ("URL"), filter pill visibility/filtering/active state/reset, enrichment summary row with URLhaus/VT mock, and detail link href containing /ioc/url/. Flask test client confirms GET /ioc/url/https://evil.com/payload.exe returns HTTP 200.

### 4. Home page and results page share the same visual language — zinc tokens, Inter Variable typography, verdict-only color accents
**✅ MET.** S04 fixed .page-index flex layout, replaced all remaining hardcoded colors (#ff6b6b) and transition timings with design tokens. Zero hardcoded colors remain in index page CSS. All pages now use the same token system.

### 5. All existing 960+ tests pass plus new tests for history, WHOIS, and URL flows
**✅ MET.** Full test suite: 1043 passed in 52.71s, zero failures, zero regressions. New tests: 20 (history store) + 13 (history routes) + 56 (WHOIS) + 8 (URL E2E) + 2 (registry WHOIS) + assorted = 83+ new tests.

## Definition of Done Results

- **All 4 slices marked [x]:** ✅ S01, S02, S03, S04 all complete with summaries.
- **All slice summaries exist:** ✅ S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md, S04-SUMMARY.md all present.
- **Cross-slice integration (S01→S04):** ✅ S04 consumed S01's recent analyses list HTML structure and styled it with design tokens. No changes to S01's template structure were needed.
- **No blockers discovered:** ✅ All 4 slices delivered without replans.
- **Code changes verified:** ✅ 20 files changed, 2477 insertions across app code, templates, CSS, JS, and tests.
- **Full test suite green:** ✅ 1043 passed, 0 failed.

## Requirement Outcomes

### R030 — Analysis History Persistence
**Active → Validated.** HistoryStore persists every online analysis to SQLite. load_analysis reconstructs full results via /history/<id>. 20 unit + 13 route tests verify roundtrip persistence.

### R031 — Recent Analyses Home Page
**Active → Validated.** Home page shows recent analyses with timestamp, IOC count, verdict badge. Click navigates to /history/<id> for full reload. Verified by test_index_shows_recent_analyses, test_index_shows_verdict_badge.

### R032 — WHOIS Domain Enrichment
**Active → Validated.** WhoisAdapter registered as 15th provider. 56 unit tests verify: registrar/creation_date/expiration_date/name_servers/org extraction, datetime polymorphism, domain-not-found handling, quota/command errors, graceful degrade. WHOIS in CONTEXT_PROVIDERS and PROVIDER_CONTEXT_FIELDS. 1035+ tests pass, typecheck clean.

### R033 — URL IOC End-to-End
**Active → Validated.** 8 E2E Playwright tests verify URL IOC extraction, card rendering with type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href at /ioc/url/. Flask test client confirms /ioc/url/https://evil.com/payload.exe returns HTTP 200. 930+ unit tests pass.

### R013 — Design Token Consistency
**Active → Validated.** .page-index uses flex-direction:column + align-items:center. All transitions use --duration-fast/--ease-out-quart tokens. .alert-error uses var(--verdict-malicious-text). .btn uses explicit property list. All 1043 tests pass with zero regressions.

## Deviations

Minor deviations, all backward-compatible: Extended save_analysis() with optional analysis_id parameter to reuse enrichment job_id (plan assumed new UUID always). T02 URL E2E produced 8 tests instead of planned 5-7 — added type badge and enrichment summary row tests for better coverage. PROVIDER_CONTEXT_FIELDS WHOIS entry was missing after T02 and had to be added during slice closure verification.

## Follow-ups

History deletion/management UI. Pagination or infinite scroll for history list beyond 10 entries. Two remaining transition:all usages on results page components (.filter-pill, .chevron-icon-wrapper) could be converted to explicit property lists.
