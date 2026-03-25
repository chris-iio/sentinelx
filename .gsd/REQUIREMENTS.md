# Requirements

This file is the explicit capability and coverage contract for the project.

## Validated

### R001 — IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Class: core-capability
- Status: validated
- Description: IOC results render in a single-column, full-width layout replacing the current 2-column card grid. Each IOC gets the full page width for data presentation.
- Why it matters: Eliminates cramped hashes, gives context and provider numbers room to breathe, establishes natural top-to-bottom scan flow for triage.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: none
- Validation: validated
- Notes: Long hashes (SHA256) and URLs must render without wrapping awkwardly

### R002 — Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Class: primary-user-loop
- Status: validated
- Description: Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Why it matters: The analyst's primary workflow is scanning results for actionable IOCs. Every click required to see key data slows triage.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: validated
- Notes: This is the hardest design challenge — dense data that reads cleanly

### R003 — Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Class: quality-attribute
- Status: validated
- Description: Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Why it matters: Eliminates the "wall of badges" junior-project aesthetic. Analyst's eye lands on what matters without parsing competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: validated
- Notes: IOC type still needs to be identifiable — just via muted text, not bright colored badges

### R004 — Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Class: core-capability
- Status: validated
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context — no page load, no back-button navigation, results list stays visible.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: Detail page still exists for deep dives — linked from expanded view

### R005 — Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Class: core-capability
- Status: validated
- Description: Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Why it matters: Current KPI boxes push IOC results below the fold. Compact dashboard gives the same information while keeping IOCs visible.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: validated
- Notes: Must still be clickable to filter by verdict

### R006 — Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Class: core-capability
- Status: validated
- Description: Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Why it matters: Current filter bar is visually heavy and pushes IOC content down.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: validated
- Notes: All filter functionality preserved — verdict toggle, type toggle, text search

### R007 — Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Class: quality-attribute
- Status: validated
- Description: Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Why it matters: Core design philosophy of the rework. Information hierarchy through showing vs. hiding rather than through competing visual weight.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S02
- Validation: validated
- Notes: Applies to: provider detail rows, no-data providers, context fields, cache staleness

### R008 — Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Class: continuity
- Status: validated
- Description: Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Why it matters: This is a presentation rework, not a feature change. Nothing should regress.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: validated
- Notes: Export and copy depend on data-* attributes on DOM elements — must preserve or migrate

### R009 — CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress during a UI redesign.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Every DOM construction in new TypeScript code must use createElement + textContent

### R010 — Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Monitor build size — current main.js is 27,226 bytes (minified prod)

### R011 — All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Class: quality-attribute
- Status: validated
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Why it matters: Test suite is the safety net that proves the redesign doesn't break functionality.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: validated
- Notes: Route-mocking infrastructure in conftest.py enables future enrichment surface tests

### R012 — The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002.
- Class: quality-attribute
- Status: validated
- Description: The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002.
- Why it matters: Visual consistency builds analyst trust.
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: validated
- Notes: Design-only refresh — no new data or structural features

### R013 — Update the input/home page to match the quiet precision design language established in M002 — zinc tokens, Inter Variable typography, consistent spacing and color approach.
- Class: quality-attribute
- Status: validated
- Description: Update the input/home page to match the quiet precision design language established in M002 — zinc tokens, Inter Variable typography, consistent spacing and color approach.
- Why it matters: Visual consistency across pages. The home page is the first thing analysts see.
- Source: inferred
- Primary owning slice: M006/S04
- Supporting slices: M006/S01
- Validation: .page-index uses flex-direction:column + align-items:center. All transitions use --duration-fast/--ease-out-quart tokens. .alert-error uses var(--verdict-malicious-text). .btn uses explicit property list. 1043 tests pass. (M006/S04)
- Notes: Previously deferred from M002. Activated for M006. Depends on S01 because recent analyses list needs styling.

### R014 — The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests. Zero-auth providers are not blocked by VT's constraint.
- Class: quality-attribute
- Status: validated
- Description: The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests. Zero-auth providers are not blocked by VT's constraint.
- Why it matters: Zero-auth providers with no rate limits are artificially bottlenecked behind VT.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: Per-provider semaphore pattern. VT semaphore value = 4.

### R015 — When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter.
- Class: quality-attribute
- Status: validated
- Description: When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter.
- Why it matters: Immediate retry on 429 burns API quota.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: ~1s base × 2^attempt + jitter. Max 2 retries.

### R016 — Email addresses are extracted from analyst input and displayed in the results page under an EMAIL group. No enrichment providers wired — display only.
- Class: core-capability
- Status: validated
- Description: Email addresses are extracted from analyst input and displayed in the results page under an EMAIL group. No enrichment providers wired — display only.
- Why it matters: Email addresses are a primary IOC type in phishing investigations.
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: validated
- Notes: Fully-defanged form user[@]evil[.]com is a known limitation

### R017 — updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC, matching the sortDetailRows pattern.
- Class: quality-attribute
- Status: validated
- Description: updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC, matching the sortDetailRows pattern.
- Why it matters: Prevents unnecessary layout thrashing during streaming enrichment.
- Source: inferred
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: validated
- Notes: Same debounce map pattern as sortTimers in enrichment.ts

### R018 — The semaphore must not be held during time.sleep() backoff. get_status() returns a snapshot. _cached_markers writes protected by _lock.
- Class: quality-attribute
- Status: validated
- Description: The semaphore must not be held during time.sleep() backoff. get_status() returns a snapshot. _cached_markers writes protected by _lock.
- Why it matters: Prevents stalling all concurrent slots during backoff.
- Source: execution
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: validated
- Notes: Three independent bugs in orchestrator.py

### R019 — The enrichment status endpoint accepts ?since= cursor and returns only new results.
- Class: quality-attribute
- Status: validated
- Description: The enrichment status endpoint accepts ?since= cursor and returns only new results.
- Why it matters: Eliminates O(N²) re-serialization of full results on every poll tick.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: Wire protocol change; E2E-verified

### R020 — Every adapter stores a requests.Session as self._session and uses it for all HTTP calls.
- Class: quality-attribute
- Status: validated
- Description: Every adapter stores a requests.Session as self._session and uses it for all HTTP calls.
- Why it matters: Eliminates TCP+TLS handshake overhead per lookup.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: Session must be thread-safe — only get() calls, no header mutation between calls

### R021 — The ip-api.com adapter uses HTTPS (ipinfo.io) instead of cleartext HTTP.
- Class: compliance/security
- Status: validated
- Description: The ip-api.com adapter uses HTTPS (ipinfo.io) instead of cleartext HTTP.
- Why it matters: Cleartext HTTP leaks the analyst's full IOC queue to network observers.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: ipinfo.io free tier, HTTPS, no auth required

### R022 — CacheStore enables WAL mode, keeps a persistent connection, and has purge_expired() method.
- Class: quality-attribute
- Status: validated
- Description: CacheStore enables WAL mode, keeps a persistent connection, and has purge_expired() method.
- Why it matters: Eliminates per-operation connection overhead and enables concurrent readers.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: WAL mode persists in the DB file

### R023 — findCopyButtonForIoc() uses attribute selector, updateDashboardCounts() called once per tick, applyFilter() debounced, verdictSeverityIndex() uses Map, graph layout uses index Map.
- Class: quality-attribute
- Status: validated
- Description: findCopyButtonForIoc() uses attribute selector, updateDashboardCounts() called once per tick, applyFilter() debounced, verdictSeverityIndex() uses Map, graph layout uses index Map.
- Why it matters: Eliminates O(N²) DOM work during enrichment.
- Source: execution
- Primary owning slice: M004/S03
- Supporting slices: none
- Validation: validated
- Notes: Dead exports also removed in S03

### R024 — tsconfig.json has incremental:true. tailwind.config.js safelist includes email badge/filter classes.
- Class: quality-attribute
- Status: validated
- Description: tsconfig.json has incremental:true. tailwind.config.js safelist includes email badge/filter classes.
- Why it matters: Faster typecheck; prevents email CSS purge regression.
- Source: execution
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: validated
- Notes: Fix safelist BEFORE removing dist glob

### R025 — CSP header includes style-src, connect-src, img-src, font-src, object-src. SECRET_KEY startup warning. Rate limiter kept as memory:// (documented constraint).
- Class: compliance/security
- Status: validated
- Description: CSP header includes style-src, connect-src, img-src, font-src, object-src. SECRET_KEY startup warning. Rate limiter kept as memory:// (documented constraint).
- Why it matters: Incomplete CSP may block enrichment polling. Auto-generated SECRET_KEY invalidates sessions.
- Source: execution
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: validated
- Notes: Rate limiter persistent backend infeasible without Redis/Memcached (D037/D038)

### R026 — A shared `safe_request()` function in `http_safety.py` handles SSRF validation, HTTP GET/POST with safety controls (timeout, no redirects, streaming byte cap), pre-raise_for_status hooks (429, 404), and the full exception handler chain (Timeout → HTTPError → SSLError → ConnectionError → Exception) with correct ordering (D035).
- Class: quality-attribute
- Status: validated
- Description: A shared `safe_request()` function in `http_safety.py` handles SSRF validation, HTTP GET/POST with safety controls (timeout, no redirects, streaming byte cap), pre-raise_for_status hooks (429, 404), and the full exception handler chain (Timeout → HTTPError → SSLError → ConnectionError → Exception) with correct ordering (D035).
- Why it matters: 12 adapters duplicate identical ~25-line HTTP + exception blocks. Consolidation eliminates the class of bugs where one adapter's handler chain drifts from the canonical order.
- Source: execution
- Primary owning slice: M005/S01
- Supporting slices: M005/S02
- Validation: safe_request() exists in http_safety.py with 16 unit tests (test_http_safety.py) covering GET, POST, 404 hook, 429 hook, all 5 exception types, D035 ordering proof, SSRF validation, headers/params passthrough. 3 pilot adapters migrated. 960 tests pass.
- Notes: Must preserve SSLError before ConnectionError ordering (D035). DNS adapters (dns_lookup, asn_cymru) are excluded — they don't use HTTP.

### R027 — All 12 HTTP-based adapters call `safe_request()` instead of inlining validate_endpoint + session.get/post + safety controls + exception handling. Each adapter's `lookup()` is reduced to: build URL/params → call `safe_request()` → parse body.
- Class: quality-attribute
- Status: validated
- Description: All 12 HTTP-based adapters call `safe_request()` instead of inlining validate_endpoint + session.get/post + safety controls + exception handling. Each adapter's `lookup()` is reduced to: build URL/params → call `safe_request()` → parse body.
- Why it matters: Achieves the ~40% LOC reduction target descoped from M004. Makes adapters easier to read, review, and extend.
- Source: execution
- Primary owning slice: M005/S02
- Supporting slices: M005/S01
- Validation: All 12 HTTP adapters call safe_request() (grep confirms 34 references, ≥1 per adapter). Zero requests.exceptions.Timeout in any adapter file. Zero validate_endpoint/read_limited in HTTP adapter code. 960 tests pass. Each adapter's lookup() is reduced to: build URL/params → call safe_request() → parse body.
- Notes: S01/T02 migrates 3 pilot adapters (Shodan, AbuseIPDB, MalwareBazaar) to prove the pattern. S02 completes the remaining 9.

### R028 — `build_registry()` runs once in `create_app()` and is stored on the app object. `analyze()` reads from the cached registry. `settings_post()` rebuilds it when API keys change.
- Class: quality-attribute
- Status: validated
- Description: `build_registry()` runs once in `create_app()` and is stored on the app object. `analyze()` reads from the cached registry. `settings_post()` rebuilds it when API keys change.
- Why it matters: Eliminates per-request registry construction. Although fast (<1ms with ConfigStore caching), it's unnecessary repeated work and a code smell.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: `build_registry()` called once in `create_app()`, stored as `app.registry`. `analyze()` reads `current_app.registry`. `settings_post()` rebuilds on key change. 960 tests pass.
- Notes: ConfigStore caching (M004/S02) already makes this fast; this is a cleanliness fix.

### R029 — The `analyze()` function (~90 lines) is split into focused helpers for extraction, enrichment launch, and template context building.
- Class: quality-attribute
- Status: validated
- Description: The `analyze()` function (~90 lines) is split into focused helpers for extraction, enrichment launch, and template context building.
- Why it matters: Readability and testability. Each helper can be understood and tested independently.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: `analyze()` decomposed into `_extract_iocs()`, `_launch_enrichment()`, `_build_template_context()`. Coordinator is ~20 lines. 960 tests pass.
- Notes: Routes decomposition was descoped from M004. The function is readable at ~90 lines but mixes extraction, orchestration, and template concerns.

### R030 — Every analysis run (input text, extracted IOCs, and full enrichment results) is persisted to SQLite. Analysts can revisit past analyses and see the complete results page from stored data without re-querying providers.
- Class: core-capability
- Status: validated
- Description: Every analysis run (input text, extracted IOCs, and full enrichment results) is persisted to SQLite. Analysts can revisit past analyses and see the complete results page from stored data without re-querying providers.
- Why it matters: Every competitive tool saves past lookups. Ephemeral results mean lost work — analysts paste the same IOCs repeatedly.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: none
- Validation: HistoryStore persists every online analysis to SQLite. load_analysis reconstructs full results via /history/<id>. 20 unit + 13 route tests verify roundtrip persistence. (M006/S01)
- Notes: Reuse existing SQLite WAL-mode DB pattern from CacheStore. Store input text, IOC list, and serialized enrichment results per run.

### R031 — The home page displays a list of recent analyses below the input form — showing timestamp, IOC count, and top verdict. Clicking a row reloads the full results page from stored data.
- Class: primary-user-loop
- Status: validated
- Description: The home page displays a list of recent analyses below the input form — showing timestamp, IOC count, and top verdict. Clicking a row reloads the full results page from stored data.
- Why it matters: Quick access to past work without a separate UI or navigation. Keeps the tool lightweight.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: M006/S04
- Validation: Home page shows recent analyses with timestamp, IOC count, verdict badge. Click navigates to /history/<id> for full reload. Verified by test_index_shows_recent_analyses, test_index_shows_verdict_badge. (M006/S01)
- Notes: Lightweight list, not a dashboard. Must not add visual weight to the home page.

### R032 — A new enrichment adapter queries WHOIS data for domain IOCs — returning registrar, creation date, expiry date, and name servers. Uses the python-whois library (direct WHOIS protocol, no API key required).
- Class: core-capability
- Status: validated
- Description: A new enrichment adapter queries WHOIS data for domain IOCs — returning registrar, creation date, expiry date, and name servers. Uses the python-whois library (direct WHOIS protocol, no API key required).
- Why it matters: WHOIS data is table-stakes for domain investigation. Creation date reveals newly-registered suspicious domains. Registrar and expiry provide investigation context.
- Source: user
- Primary owning slice: M006/S02
- Supporting slices: none
- Validation: WhoisAdapter registered as 15th provider. 56 unit tests verify registrar/creation_date/expiration_date/name_servers/org extraction, datetime polymorphism, domain-not-found handling, quota/command errors, graceful degrade. (M006/S02)
- Notes: Data quality varies by TLD registrar. Adapter must handle missing/malformed fields gracefully. Follows DnsAdapter pattern (no HTTP, no safe_request()).

### R033 — URL IOCs extracted from analyst input are enriched by URLhaus, OTX, VirusTotal, and ThreatFox. Results display correctly in the results page with filter pills, and the detail page handles URL values containing slashes.
- Class: core-capability
- Status: validated
- Description: URL IOCs extracted from analyst input are enriched by URLhaus, OTX, VirusTotal, and ThreatFox. Results display correctly in the results page with filter pills, and the detail page handles URL values containing slashes.
- Why it matters: URLs are a primary IOC type in phishing and malware delivery investigations. Backend support exists but has never been E2E tested.
- Source: user
- Primary owning slice: M006/S03
- Supporting slices: none
- Validation: 8 E2E Playwright tests verify URL IOC extraction, card rendering with type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href at /ioc/url/. Flask test client confirms /ioc/url/https://evil.com/payload.exe returns HTTP 200. (M006/S03)
- Notes: Backend extraction, classification, and 4 provider adapters already exist. CSS classes safelisted. This is a polish and verification pass.

## Deferred

### R035 — A JSON API endpoint (POST /api/analyze) accepts text input and returns extracted IOCs with enrichment results programmatically.
- Class: integration
- Status: deferred
- Description: A JSON API endpoint (POST /api/analyze) accepts text input and returns extracted IOCs with enrichment results programmatically.
- Why it matters: Enables scripting, SOAR webhooks, and CI/CD integration without browser access.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: User explicitly deferred from M006. Candidate for future milestone.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | validated | M002/S01 | none | validated |
| R002 | primary-user-loop | validated | M002/S02 | M002/S01 | validated |
| R003 | quality-attribute | validated | M002/S01 | M002/S02, M002/S03 | validated |
| R004 | core-capability | validated | M002/S03 | none | validated |
| R005 | core-capability | validated | M002/S02 | M002/S01 | validated |
| R006 | core-capability | validated | M002/S02 | M002/S01 | validated |
| R007 | quality-attribute | validated | M002/S03 | M002/S02 | validated |
| R008 | continuity | validated | M002/S04 | M002/S01, M002/S02, M002/S03 | validated |
| R009 | compliance/security | validated | M002/S04 | all | validated |
| R010 | quality-attribute | validated | M002/S04 | all | validated |
| R011 | quality-attribute | validated | M002/S05 | none | validated |
| R012 | quality-attribute | validated | M003/S03 | none | validated |
| R013 | quality-attribute | validated | M006/S04 | M006/S01 | .page-index uses flex-direction:column + align-items:center. All transitions use --duration-fast/--ease-out-quart tokens. .alert-error uses var(--verdict-malicious-text). .btn uses explicit property list. 1043 tests pass. (M006/S04) |
| R014 | quality-attribute | validated | M003/S01 | none | validated |
| R015 | quality-attribute | validated | M003/S01 | none | validated |
| R016 | core-capability | validated | M003/S02 | none | validated |
| R017 | quality-attribute | validated | M003/S04 | none | validated |
| R018 | quality-attribute | validated | M004/S01 | none | validated |
| R019 | quality-attribute | validated | M004/S02 | none | validated |
| R020 | quality-attribute | validated | M004/S02 | none | validated |
| R021 | compliance/security | validated | M004/S02 | none | validated |
| R022 | quality-attribute | validated | M004/S02 | none | validated |
| R023 | quality-attribute | validated | M004/S03 | none | validated |
| R024 | quality-attribute | validated | M004/S04 | none | validated |
| R025 | compliance/security | validated | M004/S04 | none | validated |
| R026 | quality-attribute | validated | M005/S01 | M005/S02 | safe_request() exists in http_safety.py with 16 unit tests (test_http_safety.py) covering GET, POST, 404 hook, 429 hook, all 5 exception types, D035 ordering proof, SSRF validation, headers/params passthrough. 3 pilot adapters migrated. 960 tests pass. |
| R027 | quality-attribute | validated | M005/S02 | M005/S01 | All 12 HTTP adapters call safe_request() (grep confirms 34 references, ≥1 per adapter). Zero requests.exceptions.Timeout in any adapter file. Zero validate_endpoint/read_limited in HTTP adapter code. 960 tests pass. Each adapter's lookup() is reduced to: build URL/params → call safe_request() → parse body. |
| R028 | quality-attribute | validated | M005/S03 | none | `build_registry()` called once in `create_app()`, stored as `app.registry`. `analyze()` reads `current_app.registry`. `settings_post()` rebuilds on key change. 960 tests pass. |
| R029 | quality-attribute | validated | M005/S03 | none | `analyze()` decomposed into `_extract_iocs()`, `_launch_enrichment()`, `_build_template_context()`. Coordinator is ~20 lines. 960 tests pass. |
| R030 | core-capability | validated | M006/S01 | none | HistoryStore persists every online analysis to SQLite. load_analysis reconstructs full results via /history/<id>. 20 unit + 13 route tests verify roundtrip persistence. (M006/S01) |
| R031 | primary-user-loop | validated | M006/S01 | M006/S04 | Home page shows recent analyses with timestamp, IOC count, verdict badge. Click navigates to /history/<id> for full reload. Verified by test_index_shows_recent_analyses, test_index_shows_verdict_badge. (M006/S01) |
| R032 | core-capability | validated | M006/S02 | none | WhoisAdapter registered as 15th provider. 56 unit tests verify registrar/creation_date/expiration_date/name_servers/org extraction, datetime polymorphism, domain-not-found handling, quota/command errors, graceful degrade. (M006/S02) |
| R033 | core-capability | validated | M006/S03 | none | 8 E2E Playwright tests verify URL IOC extraction, card rendering with type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href at /ioc/url/. Flask test client confirms /ioc/url/https://evil.com/payload.exe returns HTTP 200. (M006/S03) |
| R035 | integration | deferred | none | none | unmapped |

## Coverage Summary

- Active requirements: 0
- Mapped to slices: 0
- Validated: 33 (R001, R002, R003, R004, R005, R006, R007, R008, R009, R010, R011, R012, R013, R014, R015, R016, R017, R018, R019, R020, R021, R022, R023, R024, R025, R026, R027, R028, R029, R030, R031, R032, R033)
- Unmapped active requirements: 0
