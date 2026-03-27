---
id: M006
title: "Analyst Workflow & Coverage"
status: complete
completed_at: 2026-03-25T12:46:16.121Z
key_decisions:
  - UUID4 hex as history row id — avoids leaking analysis count
  - top_verdict computed at save time and stored in the row — avoids re-parsing results_json on every list_recent()
  - History save failures silently caught — enrichment results always available regardless of persistence issues
  - WhoisAdapter uses verdict='no_data' always — WHOIS is informational context, not a threat verdict source
  - WhoisAdapter registered in zero-auth section (no API key, always configured) matching DnsAdapter/CrtShAdapter pattern
  - Detail link href uses /ioc/<type>/<value> matching the Flask route, not /detail/
  - Replace transition:all with explicit property list on .btn to follow design principles
  - JS replay pattern: history.ts replays stored results through same rendering pipeline as live enrichment — single codepath, two entry points
key_files:
  - app/enrichment/history_store.py
  - app/enrichment/adapters/whois_lookup.py
  - app/routes.py
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/input.css
  - app/templates/index.html
  - app/templates/results.html
  - app/enrichment/setup.py
  - tests/test_history_store.py
  - tests/test_history_routes.py
  - tests/test_whois_lookup.py
  - tests/e2e/test_url_e2e.py
lessons_learned:
  - PROVIDER_CONTEXT_FIELDS must be updated atomically with backend provider registration — S02 task summary claimed the frontend was updated but the code change was missing, caught only at slice closure
  - Non-HTTP adapters (WHOIS port 43, DNS port 53) must not import http_safety.py — verification greps check the entire file including docstrings
  - python-whois returns polymorphic datetime fields (datetime, list, None, str) — always normalize through a helper function
  - JS replay architecture (batch replay through existing rendering functions) is simpler and more reliable than building a separate rendering path for stored data
  - Background thread wrapper pattern for secondary concerns (persistence) that must not affect primary flow (enrichment) — failures are silently caught
  - When verification greps check for literal strings, docstrings must also avoid those strings to prevent false positives
---

# M006: Analyst Workflow & Coverage

**Added analysis history persistence (SQLite HistoryStore + /history/<id> replay), WHOIS domain enrichment (15th provider), URL IOC end-to-end polish (detail link fix + 8 E2E tests), and input page design token completion — 1043 tests, zero failures.**

## What Happened

M006 closed four gaps that kept SentinelX from being a practical local tool: ephemeral results, missing WHOIS data, broken URL IOC links, and design inconsistency on the home page.

**S01 — Analysis History & Persistence (high risk).** Created HistoryStore following the CacheStore SQLite WAL-mode pattern — save_analysis() serializes IOCs and results to JSON with UUID4 hex IDs, list_recent() returns lightweight summaries ordered by timestamp, load_analysis() reconstructs full rows. Wired into three Flask touch points: a background thread wrapper saves results after enrichment (failures silently caught), GET /history/<id> loads and renders stored analysis, and index() queries recent analyses for the home page list. The JS replay module (history.ts) detects data-history-results on the results page and replays all stored results through the existing rendering pipeline — single rendering codepath, two entry points (live polling vs batch replay). 33 new tests (20 unit + 13 route integration).

**S02 — WHOIS Domain Enrichment (medium risk).** Added WhoisAdapter as the 15th enrichment provider using python-whois (direct WHOIS protocol on port 43, no HTTP, no API key, no SSRF surface). Always returns verdict='no_data' — WHOIS is informational context, not a threat verdict source. A _normalise_datetime() helper handles python-whois's polymorphic date returns. All python-whois exceptions mapped to the correct enrichment model types. Frontend PROVIDER_CONTEXT_FIELDS updated with registrar, Created, Expires, NS (tags), Org. 56 unit tests + 2 registry tests.

**S03 — URL IOC End-to-End Polish (low risk).** Fixed a bug where injectDetailLink() in both enrichment.ts and history.ts built hrefs using /detail/ instead of the Flask route's /ioc/ prefix — every "View full detail →" link was returning 404. Created 8 E2E Playwright tests covering URL card rendering, type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href.

**S04 — Input Page Redesign (low risk, depends S01).** Fixed .page-index flex-direction from row to column (input card and recent analyses list were side-by-side instead of stacking). Full audit replaced 5 hardcoded CSS values with design tokens: mode toggle transitions → --duration-fast/--ease-out-quart, .btn transition:all → explicit property list, .alert-error #ff6b6b → var(--verdict-malicious-text). The recent analyses section from S01 was already fully tokenized.

Net result: 20 files changed, +2477/-30 lines of non-GSD code. Test count grew from 960 to 1043. All 1043 tests pass. JS and CSS builds clean. No regressions.

## Success Criteria Results

**1. ✅ Analyst can submit IOCs, close the tab, return to the home page, see the past analysis in a recent list, click it, and see full results reloaded from stored data.**
Evidence: HistoryStore.save_analysis() persists every online analysis to SQLite (app/enrichment/history_store.py). index() route queries list_recent(limit=10) and renders recent analyses with verdict badges (tests/test_history_routes.py: test_index_shows_recent_analyses, test_index_shows_verdict_badge). GET /history/<id> loads stored data and renders results.html with data-history-results for JS replay (test_history_detail_200). history.ts replays stored results through the same rendering pipeline as live enrichment. 20 unit + 13 route tests verify the full loop.

**2. ✅ Domain IOC enrichment includes WHOIS data (registrar, creation date, expiry, name servers) alongside DNS records and other provider results.**
Evidence: WhoisAdapter registered as 15th provider in setup.py. Returns registrar, creation_date, expiration_date, name_servers, org in raw_stats. PROVIDER_CONTEXT_FIELDS in row-factory.ts maps these to frontend context fields. 56 unit tests verify extraction, datetime polymorphism, and error handling (tests/test_whois_lookup.py). Registry test confirms 15 providers (tests/test_registry_setup.py).

**3. ✅ URL IOCs pasted in free-form text are extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct filter pill, and accessible on the detail page.**
Evidence: Detail link href fixed from /detail/ to /ioc/ in both enrichment.ts and history.ts. 8 E2E Playwright tests in tests/e2e/test_url_e2e.py verify: URL card rendering, type badge ("URL"), filter pill visibility, filter pill filtering, active state CSS, "All Types" reset, enrichment summary row with URLhaus/VT, and detail link href containing /ioc/url/. Flask test client confirms GET /ioc/url/https://evil.com/payload.exe returns HTTP 200.

**4. ✅ Home page and results page share the same visual language — zinc tokens, Inter Variable typography, verdict-only color accents.**
Evidence: .page-index flex-direction fixed to column (line 278 of input.css). All mode toggle transitions use --duration-fast/--ease-out-quart. .btn uses explicit property list instead of transition:all. .alert-error uses var(--verdict-malicious-text) instead of hardcoded #ff6b6b. Zero hardcoded colors or timings remain in index page CSS. Verified by grep and git diff.

**5. ✅ All existing 960+ tests pass plus new tests for history, WHOIS, and URL flows.**
Evidence: `python3 -m pytest --tb=short -q` → 1043 passed in 52.57s, zero failures. Test count grew from 960 to 1043. `make js` and `make css` both build cleanly.

## Definition of Done Results

**All 4 slices marked [x] in ROADMAP.md:** S01 ✅, S02 ✅, S03 ✅, S04 ✅.

**All 4 slice summaries exist:** S01-SUMMARY.md ✅, S02-SUMMARY.md ✅, S03-SUMMARY.md ✅, S04-SUMMARY.md ✅.

**Cross-slice integration (S01 → S04):** S04 consumed the recent analyses list HTML structure from S01 — the list was already fully tokenized and only the .page-index flex layout and surrounding CSS needed fixing. No integration issues.

**Code changes verified:** `git diff --stat HEAD~1 HEAD -- ':!.gsd/'` shows 20 files changed, +2477/-30 lines. Real implementation code, not just planning artifacts.

**Full test suite passes:** 1043/1043 tests pass (52.57s), zero failures, zero regressions.

**JS and CSS builds clean:** `make js` (30.2kb bundle), `make css` — both exit 0.

## Requirement Outcomes

**R013** (quality-attribute): active → **validated** in S04. Evidence: .page-index uses flex-direction:column, all transitions tokenized, .alert-error uses var(--verdict-malicious-text), .btn uses explicit property list. 1043 tests pass.

**R030** (core-capability): active → **validated** in S01. Evidence: HistoryStore persists every online analysis to SQLite. load_analysis reconstructs full results via /history/<id>. 20 unit + 13 route tests verify roundtrip persistence.

**R031** (primary-user-loop): active → **validated** in S01. Evidence: Home page shows recent analyses with timestamp, IOC count, verdict badge. Click navigates to /history/<id> for full reload. Verified by test_index_shows_recent_analyses, test_index_shows_verdict_badge.

**R032** (core-capability): active → **validated** in S02. Evidence: WhoisAdapter registered as 15th provider. 56 unit tests verify registrar/creation_date/expiration_date/name_servers/org extraction, datetime polymorphism, domain-not-found handling, quota/command errors, graceful degrade.

**R033** (core-capability): active → **validated** in S03. Evidence: 8 E2E Playwright tests verify URL IOC extraction, card rendering with type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href at /ioc/url/. Flask test client confirms HTTP 200 for URL path.

## Deviations

Minor deviations, all backward-compatible: (1) Extended save_analysis() with optional analysis_id parameter to reuse enrichment job_id instead of always generating new UUID. (2) S03/T02 produced 8 E2E tests instead of planned 5-7, matching email IOC test granularity. (3) S02 PROVIDER_CONTEXT_FIELDS entry was added at slice closure instead of during T02 — the task summary incorrectly claimed it was done. No material deviations from milestone scope or architecture.

## Follow-ups

Future: add history deletion/management UI. Future: add pagination or infinite scroll for history list beyond 10 entries. Two transition:all usages remain on results page components (filter-pill, chevron-icon-wrapper lines 794/866 in input.css) — could be converted to explicit property lists in a future cleanup pass.
