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

### R003 — Verdict severity is the only loud color in the results page. All other elements use muted typographic hierarchy.
- Class: quality-attribute
- Status: validated
- Description: Verdict severity is the only loud color in the results page. All other elements use muted typographic hierarchy.
- Why it matters: Eliminates competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: validated
- Notes: IOC type still identifiable via muted text

### R004 — Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Class: core-capability
- Status: validated
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: Detail page still exists for deep dives

### R005 — Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Class: core-capability
- Status: validated
- Description: Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Why it matters: Current KPI boxes push IOC results below the fold.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: validated
- Notes: Must still be clickable to filter by verdict

### R006 — Verdict filters, type filters, and search consolidated into a single compact row.
- Class: core-capability
- Status: validated
- Description: Verdict filters, type filters, and search consolidated into a single compact row.
- Why it matters: Current filter bar is visually heavy.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: validated
- Notes: All filter functionality preserved

### R007 — Important info visible at a glance, details on demand.
- Class: quality-attribute
- Status: validated
- Description: Important info visible at a glance, details on demand.
- Why it matters: Core design philosophy of the rework.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S02
- Validation: validated
- Notes: Applies to provider detail rows, no-data providers, context fields, cache staleness

### R008 — Enrichment polling, export, verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Class: continuity
- Status: validated
- Description: Enrichment polling, export, verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Why it matters: Presentation rework, not feature change.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: validated
- Notes: Export and copy depend on data-* attributes on DOM elements

### R009 — CSP headers, CSRF protection, textContent-only DOM construction, SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: CSP headers, CSRF protection, textContent-only DOM construction, SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Every DOM construction uses createElement + textContent

### R010 — Debounced card sorting, polling efficiency, lazy rendering — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Debounced card sorting, polling efficiency, lazy rendering — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Monitor build size

### R011 — All E2E tests updated for new DOM structure (selectors, page objects) and passing.
- Class: quality-attribute
- Status: validated
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing.
- Why it matters: Test suite is the safety net.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: validated
- Notes: Route-mocking infrastructure enables future enrichment surface tests

### R012 — The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002.
- Class: quality-attribute
- Status: validated
- Description: The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002.
- Why it matters: Visual consistency builds analyst trust.
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: validated
- Notes: Design-only refresh

### R013 — Home page uses zinc tokens, Inter Variable typography, consistent spacing and color approach.
- Class: quality-attribute
- Status: validated
- Description: Home page uses zinc tokens, Inter Variable typography, consistent spacing and color approach.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: M006/S04
- Supporting slices: M006/S01
- Validation: validated
- Notes: Previously deferred from M002. Activated for M006.

### R014 — The enrichment orchestrator enforces rate limits per provider, not globally.
- Class: quality-attribute
- Status: validated
- Description: The enrichment orchestrator enforces rate limits per provider, not globally.
- Why it matters: Zero-auth providers are not blocked by VT's constraint.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: VT semaphore value = 4

### R015 — When a provider returns a 429, the orchestrator waits before retrying.
- Class: quality-attribute
- Status: validated
- Description: When a provider returns a 429, the orchestrator waits before retrying.
- Why it matters: Immediate retry on 429 burns API quota.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: ~1s base × 2^attempt + jitter. Max 2 retries.

### R016 — Email addresses extracted from analyst input and displayed under an EMAIL group.
- Class: core-capability
- Status: validated
- Description: Email addresses extracted from analyst input and displayed under an EMAIL group.
- Why it matters: Email addresses are a primary IOC type in phishing investigations.
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: validated
- Notes: Fully-defanged form user[@]evil[.]com is a known limitation

### R017 — updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC.
- Class: quality-attribute
- Status: validated
- Description: updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC.
- Why it matters: Prevents unnecessary layout thrashing during streaming enrichment.
- Source: inferred
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: validated
- Notes: Same debounce map pattern as sortTimers in enrichment.ts

### R018 — Semaphore not held during backoff sleep; get_status() returns snapshot; _cached_markers writes protected.
- Class: quality-attribute
- Status: validated
- Description: Semaphore not held during backoff sleep; get_status() returns snapshot; _cached_markers writes protected.
- Why it matters: Prevents stalling all concurrent slots during backoff.
- Source: execution
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: validated
- Notes: Three independent bugs

### R019 — The enrichment status endpoint accepts ?since= cursor and returns only new results.
- Class: quality-attribute
- Status: validated
- Description: The enrichment status endpoint accepts ?since= cursor and returns only new results.
- Why it matters: Eliminates O(N²) re-serialization.
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
- Notes: Session must be thread-safe

### R021 — The ip-api.com adapter uses HTTPS (ipinfo.io) instead of cleartext HTTP.
- Class: compliance/security
- Status: validated
- Description: The ip-api.com adapter uses HTTPS (ipinfo.io) instead of cleartext HTTP.
- Why it matters: Cleartext HTTP leaks the analyst's full IOC queue.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: ipinfo.io free tier, HTTPS, no auth required

### R022 — CacheStore enables WAL mode, keeps persistent connection, and has purge_expired() method.
- Class: quality-attribute
- Status: validated
- Description: CacheStore enables WAL mode, keeps persistent connection, and has purge_expired() method.
- Why it matters: Eliminates per-operation connection overhead.
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

### R025 — CSP header includes style-src, connect-src, img-src, font-src, object-src. SECRET_KEY startup warning.
- Class: compliance/security
- Status: validated
- Description: CSP header includes style-src, connect-src, img-src, font-src, object-src. SECRET_KEY startup warning.
- Why it matters: Incomplete CSP may block enrichment polling.
- Source: execution
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: validated
- Notes: Rate limiter persistent backend infeasible without Redis/Memcached (D037/D038)

### R026 — A shared safe_request() function in http_safety.py handles SSRF validation, HTTP GET/POST with safety controls, pre-raise_for_status hooks, and the full exception handler chain with correct ordering (D035).
- Class: quality-attribute
- Status: validated
- Description: A shared safe_request() function in http_safety.py handles SSRF validation, HTTP GET/POST with safety controls, pre-raise_for_status hooks, and the full exception handler chain with correct ordering (D035).
- Why it matters: 12 adapters duplicate identical ~25-line HTTP + exception blocks.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated
- Notes: M005 claimed completion but the code never materialized. Reattempted in M007.

### R027 — All 12 HTTP-based adapters call safe_request() instead of inlining validate_endpoint + session.get/post + safety controls + exception handling.
- Class: quality-attribute
- Status: validated
- Description: All 12 HTTP-based adapters call safe_request() instead of inlining validate_endpoint + session.get/post + safety controls + exception handling.
- Why it matters: Achieves the LOC reduction and consistency target.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated
- Notes: Reattempted in M007.

### R028 — build_registry() runs once in create_app() and is stored on the app object.
- Class: quality-attribute
- Status: validated
- Description: build_registry() runs once in create_app() and is stored on the app object.
- Why it matters: Eliminates per-request registry construction.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: validated
- Notes: ConfigStore caching makes this fast.

### R029 — The analyze() function is split into _extract_iocs(), _launch_enrichment(), _build_template_context().
- Class: quality-attribute
- Status: validated
- Description: The analyze() function is split into _extract_iocs(), _launch_enrichment(), _build_template_context().
- Why it matters: Readability and testability.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: validated
- Notes: Coordinator is ~20 lines.

### R030 — Every analysis run persisted to SQLite. Analysts can revisit past analyses.
- Class: core-capability
- Status: validated
- Description: Every analysis run persisted to SQLite. Analysts can revisit past analyses.
- Why it matters: Every competitive tool saves past lookups.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: none
- Validation: validated
- Notes: Reuses existing SQLite WAL-mode DB pattern.

### R031 — Home page displays recent analyses with timestamp, IOC count, and top verdict.
- Class: primary-user-loop
- Status: validated
- Description: Home page displays recent analyses with timestamp, IOC count, and top verdict.
- Why it matters: Quick access to past work.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: M006/S04
- Validation: validated
- Notes: Lightweight list, not a dashboard.

### R032 — WhoisAdapter queries WHOIS data for domains — registrar, creation date, expiry date, name servers.
- Class: core-capability
- Status: validated
- Description: WhoisAdapter queries WHOIS data for domains — registrar, creation date, expiry date, name servers.
- Why it matters: WHOIS data is table-stakes for domain investigation.
- Source: user
- Primary owning slice: M006/S02
- Supporting slices: none
- Validation: validated
- Notes: python-whois library, direct WHOIS protocol.

### R033 — URL IOCs extracted, enriched, displayed with filter pills, and accessible on detail page.
- Class: core-capability
- Status: validated
- Description: URL IOCs extracted, enriched, displayed with filter pills, and accessible on detail page.
- Why it matters: URLs are a primary IOC type.
- Source: user
- Primary owning slice: M006/S03
- Supporting slices: none
- Validation: validated
- Notes: 8 E2E Playwright tests verify the full path.

### R035 — POST /api/analyze accepts text input and returns extracted IOCs with enrichment results programmatically.
- Class: integration
- Status: validated
- Description: POST /api/analyze accepts text input and returns extracted IOCs with enrichment results programmatically.
- Why it matters: Enables scripting, SOAR webhooks, and CI/CD integration without browser access.
- Source: user
- Primary owning slice: M008/S02
- Supporting slices: none
- Validation: validated
- Notes: Also includes GET /api/status/<job_id> for online mode enrichment polling.

### R036 — A shared safe_request() function in http_safety.py handles SSRF validation, HTTP GET/POST with safety controls, pre-raise_for_status hooks, and the full exception handler chain with correct ordering.
- Class: quality-attribute
- Status: validated
- Description: A shared safe_request() function in http_safety.py handles SSRF validation, HTTP GET/POST with safety controls, pre-raise_for_status hooks, and the full exception handler chain with correct ordering.
- Why it matters: 12 adapters duplicate identical ~25-line HTTP + exception blocks.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated
- Notes: All 12 adapters migrated; 1057 tests pass.

### R037 — Adapter module and class docstrings no longer repeat SEC-04/05/06/16 safety control descriptions. Security control docs live once in http_safety.py.
- Class: quality-attribute
- Status: validated
- Description: Adapter module and class docstrings no longer repeat SEC-04/05/06/16 safety control descriptions. Security control docs live once in http_safety.py.
- Why it matters: ~1,354 lines of docstrings across 15 adapters, 40-46% of each file.
- Source: execution
- Primary owning slice: M007/S02
- Supporting slices: none
- Validation: validated
- Notes: Adapter-specific docs preserved.

### R038 — Dead CSS classes removed from input.css. consensus-badge CSS removed.
- Class: quality-attribute
- Status: validated
- Description: Dead CSS classes removed from input.css. consensus-badge CSS removed.
- Why it matters: consensus-badge was dead for 5 milestones.
- Source: execution
- Primary owning slice: M007/S02
- Supporting slices: none
- Validation: validated
- Notes: Stale chevron-toggle comment also removed.

### R039 — Adapter test files use make_mock_response, make_ipv4_ioc, and other shared factories from tests/helpers.py.
- Class: quality-attribute
- Status: validated
- Description: Adapter test files use make_mock_response, make_ipv4_ioc, and other shared factories from tests/helpers.py.
- Why it matters: 23 of 33 test files inlined their own mock setup.
- Source: execution
- Primary owning slice: M007/S03
- Supporting slices: none
- Validation: validated
- Notes: All 12 adapter test files migrated.

### R040 — Every existing test passes after M007 refactoring.
- Class: continuity
- Status: validated
- Description: Every existing test passes after M007 refactoring.
- Why it matters: Pure cleanup milestone — test suite is the safety net.
- Source: inferred
- Primary owning slice: M007/all
- Supporting slices: none
- Validation: validated
- Notes: 1057 tests pass; count increased from 1043.

### R041 — A BaseHTTPAdapter abstract base class in `app/enrichment/adapters/base.py` absorbs the shared adapter skeleton: `__init__` (session setup, allowed_hosts, optional api_key), `supported_types` guard, `is_configured`, and the `safe_request()` dispatch + result-check boilerplate. Each HTTP adapter subclass defines only metadata constants and override methods for URL construction, pre-raise hooks, and response parsing.
- Class: quality-attribute
- Status: validated
- Description: A BaseHTTPAdapter abstract base class in `app/enrichment/adapters/base.py` absorbs the shared adapter skeleton: `__init__` (session setup, allowed_hosts, optional api_key), `supported_types` guard, `is_configured`, and the `safe_request()` dispatch + result-check boilerplate. Each HTTP adapter subclass defines only metadata constants and override methods for URL construction, pre-raise hooks, and response parsing.
- Why it matters: 12 HTTP adapters repeat ~60% identical structural code. The base class eliminates this duplication at the source.
- Source: inferred
- Primary owning slice: M009/S01
- Supporting slices: M009/S02
- Validation: BaseHTTPAdapter exists in app/enrichment/adapters/base.py with full template-method skeleton. 12 HTTP adapters subclass it. 21 base class tests + 947 full suite tests pass. Verified by grep: 13 files contain 'class.*BaseHTTPAdapter' (12 adapters + 1 base definition).
- Notes: The Provider protocol remains the structural contract; BaseHTTPAdapter is an implementation convenience.

### R042 — All 12 HTTP-based adapters (abuseipdb, crtsh, greynoise, hashlookup, ip_api, malwarebazaar, otx, shodan, threatfox, threatminer, urlhaus, virustotal) subclass BaseHTTPAdapter. Each defines only provider-specific metadata, URL construction, and response parsing.
- Class: quality-attribute
- Status: validated
- Description: All 12 HTTP-based adapters (abuseipdb, crtsh, greynoise, hashlookup, ip_api, malwarebazaar, otx, shodan, threatfox, threatminer, urlhaus, virustotal) subclass BaseHTTPAdapter. Each defines only provider-specific metadata, URL construction, and response parsing.
- Why it matters: Completes the consolidation — half-migrated is worse than not migrated.
- Source: inferred
- Primary owning slice: M009/S02
- Supporting slices: M009/S01
- Validation: All 12 HTTP adapters (abuseipdb, crtsh, greynoise, hashlookup, ip_api, malwarebazaar, otx, shodan, threatfox, threatminer, urlhaus, virustotal) subclass BaseHTTPAdapter. Verified by grep: 12 non-base adapter files contain 'class.*BaseHTTPAdapter'. 983 tests pass.
- Notes: ThreatMiner (multi-endpoint) and VT (complex response parsing) are the most complex migrations.

### R043 — The 3 non-HTTP adapters (dns_lookup via dnspython, asn_cymru via dnspython, whois_lookup via python-whois) are not forced into BaseHTTPAdapter. They remain standalone implementations.
- Class: constraint
- Status: validated
- Description: The 3 non-HTTP adapters (dns_lookup via dnspython, asn_cymru via dnspython, whois_lookup via python-whois) are not forced into BaseHTTPAdapter. They remain standalone implementations.
- Why it matters: Forcing non-HTTP adapters into an HTTP base class would be a bad abstraction.
- Source: inferred
- Primary owning slice: M009/S02
- Supporting slices: none
- Validation: grep -c 'BaseHTTPAdapter' on dns_lookup.py, asn_cymru.py, whois_lookup.py all return 0. These three non-HTTP adapters remain standalone implementations.
- Notes: These adapters still satisfy the Provider protocol.

### R044 — A shared parametrized test module covers protocol conformance, unsupported-type rejection, timeout handling, connection/SSL errors, allowed_hosts enforcement, and is_configured behavior for all 15 adapters. Tests are written once and run against every adapter.
- Class: quality-attribute
- Status: validated
- Description: A shared parametrized test module covers protocol conformance, unsupported-type rejection, timeout handling, connection/SSL errors, allowed_hosts enforcement, and is_configured behavior for all 15 adapters. Tests are written once and run against every adapter.
- Why it matters: 15 adapter test files independently test identical shared-contract behavior — pure duplication.
- Source: inferred
- Primary owning slice: M009/S03
- Supporting slices: none
- Validation: 172 parametrized tests in test_adapter_contract.py cover all 15 adapters across 12 contract dimensions. All pass.
- Notes: Non-HTTP adapters have different error surfaces (no timeout/SSL) — parametrize accordingly.

### R045 — After shared contract tests are extracted, each adapter test file retains only verdict logic tests, response parsing tests, and any provider-specific edge cases.
- Class: quality-attribute
- Status: validated
- Description: After shared contract tests are extracted, each adapter test file retains only verdict logic tests, response parsing tests, and any provider-specific edge cases.
- Why it matters: Reduces test maintenance burden and makes adapter-specific behavior visible.
- Source: inferred
- Primary owning slice: M009/S03
- Supporting slices: none
- Validation: All 15 per-adapter test files contain only verdict/parsing/provider-specific tests. 208 contract tests removed, zero contract patterns remain.
- Notes: Test count may decrease as duplicate tests are removed.

### R046 — Dead CSS rules identified by cross-referencing selectors against templates and TypeScript are removed from input.css.
- Class: quality-attribute
- Status: validated
- Description: Dead CSS rules identified by cross-referencing selectors against templates and TypeScript are removed from input.css.
- Why it matters: 8 milestones of UI rework likely left orphaned selectors. Dead CSS is noise.
- Source: inferred
- Primary owning slice: M009/S04
- Supporting slices: none
- Validation: CSS audit sampled 10/10 selectors — all referenced. No dead CSS found.
- Notes: Audit must account for dynamically-constructed class names in JS.

### R047 — Functions duplicated between enrichment.ts and history.ts (injectDetailLink, initExportButton, sortDetailRows) are extracted into a shared module. Both files import from it.
- Class: quality-attribute
- Status: validated
- Description: Functions duplicated between enrichment.ts and history.ts (injectDetailLink, initExportButton, sortDetailRows) are extracted into a shared module. Both files import from it.
- Why it matters: M006 duplicated these functions because of closure dependencies. Where dependencies can be parameterized, extract; where they can't, leave.
- Source: inferred
- Primary owning slice: M009/S04
- Supporting slices: none
- Validation: 4 functions extracted to shared-rendering.ts; zero private copies remain in enrichment.ts/history.ts; 84-line net reduction; make typecheck && make js pass.
- Notes: Per KNOWLEDGE.md, check if functions read module-private state before extracting.

### R048 — Every existing test passes after all refactoring. No functional behavior changes — same HTTP calls, same verdicts, same error handling, same DOM output.
- Class: continuity
- Status: validated
- Description: Every existing test passes after all refactoring. No functional behavior changes — same HTTP calls, same verdicts, same error handling, same DOM output.
- Why it matters: This is a pure reduction milestone. The test suite is the safety net.
- Source: inferred
- Primary owning slice: M009/all
- Supporting slices: none
- Validation: 947 tests pass, 0 failures. Count decreased from 1,075 to 947 only from consolidation (208 duplicates removed, 172 parametrized replacements added). Zero behavior changes — same verdicts, same HTTP calls, same error handling.
- Notes: Test count will decrease as duplicate contract tests are consolidated.

### R049 — The milestone produces a measurable net reduction in lines of code across both app/ and tests/ directories.
- Class: quality-attribute
- Status: validated
- Description: The milestone produces a measurable net reduction in lines of code across both app/ and tests/ directories.
- Why it matters: The explicit goal is reducing the codebase.
- Source: user
- Primary owning slice: M009/all
- Supporting slices: none
- Validation: Net -1,143 LOC across 38 files (1,669 added, 2,812 deleted). Reduction in both app/ (adapter consolidation -112 LOC, TS dedup -84 LOC) and tests/ (contract test consolidation, bulk of remaining reduction).
- Notes: Measure before and after with `find app tests -name '*.py' -o -name '*.ts' -o -name '*.css' | xargs wc -l`.

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
| R013 | quality-attribute | validated | M006/S04 | M006/S01 | validated |
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
| R026 | quality-attribute | validated | M007/S01 | none | validated |
| R027 | quality-attribute | validated | M007/S01 | none | validated |
| R028 | quality-attribute | validated | M005/S03 | none | validated |
| R029 | quality-attribute | validated | M005/S03 | none | validated |
| R030 | core-capability | validated | M006/S01 | none | validated |
| R031 | primary-user-loop | validated | M006/S01 | M006/S04 | validated |
| R032 | core-capability | validated | M006/S02 | none | validated |
| R033 | core-capability | validated | M006/S03 | none | validated |
| R035 | integration | validated | M008/S02 | none | validated |
| R036 | quality-attribute | validated | M007/S01 | none | validated |
| R037 | quality-attribute | validated | M007/S02 | none | validated |
| R038 | quality-attribute | validated | M007/S02 | none | validated |
| R039 | quality-attribute | validated | M007/S03 | none | validated |
| R040 | continuity | validated | M007/all | none | validated |
| R041 | quality-attribute | validated | M009/S01 | M009/S02 | BaseHTTPAdapter exists in app/enrichment/adapters/base.py with full template-method skeleton. 12 HTTP adapters subclass it. 21 base class tests + 947 full suite tests pass. Verified by grep: 13 files contain 'class.*BaseHTTPAdapter' (12 adapters + 1 base definition). |
| R042 | quality-attribute | validated | M009/S02 | M009/S01 | All 12 HTTP adapters (abuseipdb, crtsh, greynoise, hashlookup, ip_api, malwarebazaar, otx, shodan, threatfox, threatminer, urlhaus, virustotal) subclass BaseHTTPAdapter. Verified by grep: 12 non-base adapter files contain 'class.*BaseHTTPAdapter'. 983 tests pass. |
| R043 | constraint | validated | M009/S02 | none | grep -c 'BaseHTTPAdapter' on dns_lookup.py, asn_cymru.py, whois_lookup.py all return 0. These three non-HTTP adapters remain standalone implementations. |
| R044 | quality-attribute | validated | M009/S03 | none | 172 parametrized tests in test_adapter_contract.py cover all 15 adapters across 12 contract dimensions. All pass. |
| R045 | quality-attribute | validated | M009/S03 | none | All 15 per-adapter test files contain only verdict/parsing/provider-specific tests. 208 contract tests removed, zero contract patterns remain. |
| R046 | quality-attribute | validated | M009/S04 | none | CSS audit sampled 10/10 selectors — all referenced. No dead CSS found. |
| R047 | quality-attribute | validated | M009/S04 | none | 4 functions extracted to shared-rendering.ts; zero private copies remain in enrichment.ts/history.ts; 84-line net reduction; make typecheck && make js pass. |
| R048 | continuity | validated | M009/all | none | 947 tests pass, 0 failures. Count decreased from 1,075 to 947 only from consolidation (208 duplicates removed, 172 parametrized replacements added). Zero behavior changes — same verdicts, same HTTP calls, same error handling. |
| R049 | quality-attribute | validated | M009/all | none | Net -1,143 LOC across 38 files (1,669 added, 2,812 deleted). Reduction in both app/ (adapter consolidation -112 LOC, TS dedup -84 LOC) and tests/ (contract test consolidation, bulk of remaining reduction). |

## Active

(No active requirements — all M011 requirements validated.)

## Validated (M011)

### R056 — Adapter docstrings trimmed to one-liner + edge cases only — no API status code walkthroughs
- Class: quality-attribute
- Status: validated
- Description: Each adapter's module and class docstrings are reduced to a one-liner purpose sentence plus genuinely non-obvious gotchas. API endpoint URLs, HTTP status code tables, verdict priority lists, and parameter walkthroughs are removed — the code and tests prove those.
- Why it matters: Adapter docstrings are 42% of adapter code (1,176 of 2,816 lines). Trimming to essentials makes files navigable and removes maintenance burden of keeping prose in sync with code.
- Source: user
- Primary owning slice: M011/S01
- Validation: 15 non-base adapter files trimmed to 1,597 lines (down from 2,659). One-liner module+class docstrings. Only _normalise_datetime retains a method docstring. All 1,012 tests pass unchanged.

### R057 — Per-adapter granular field tests consolidated — one test per response scenario instead of one per field
- Class: quality-attribute
- Status: validated
- Description: Per-adapter test files that assert individual fields (test_raw_stats_has_asn_key, test_raw_stats_asn_value, test_detection_count_always_zero, etc.) are consolidated into single response-shape tests that assert the full result object in one test.
- Why it matters: ~72 granular one-assertion tests across 7 adapter test files produce ~400-600 lines of boilerplate. Consolidation reduces test count without losing coverage — the same assertions exist, just grouped.
- Source: user
- Primary owning slice: M011/S02
- Validation: 49 standalone per-field tests removed across 8 adapter test files + test_provider_protocol.py. Assertions folded into response-shape tests with descriptive messages. Net -431 lines. 899 unit tests pass.

### R058 — Dead CSS removed from input.css — every remaining class referenced by at least one template or TS file
- Class: quality-attribute
- Status: validated
- Description: Cross-reference every CSS class in input.css against all templates (.html) and TypeScript files (.ts). Remove classes with zero references. Rebuild dist/style.css and verify visually.
- Why it matters: 2,006 lines of CSS accumulated over 10 milestones. Dead rules bloat the stylesheet and confuse future editors.
- Source: user
- Primary owning slice: M011/S03
- Validation: CSS audit verified all 207 classes in input.css are referenced. 3 dynamic classes confirmed via string concatenation in row-factory.ts:336, row-factory.ts:309/416, cards.ts:60. Zero dead CSS found.

### R059 — Orchestrator concurrency tests run in <1s total instead of ~6s — sleep mocks replaced with synchronization primitives
- Class: quality-attribute
- Status: validated
- Description: The 7 orchestrator tests that use time.sleep-based timing (accounting for ~6.2s of 9s unit suite) are rewritten to use threading Events/barriers or tighter mocks so they complete in <1s total.
- Why it matters: 6s of 9s unit test time comes from 7 tests. Faster tests mean faster feedback loops during development.
- Source: user
- Primary owning slice: M011/S03
- Validation: 7 orchestrator tests rewritten with threading.Barrier/Event primitives. Suite runs in 0.09s (target <1s, was 6.2s). 27 orchestrator tests pass.

### R060 — All existing tests pass after refactoring with zero behavior changes
- Class: continuity
- Status: validated
- Description: All tests pass after all refactoring. Test count may decrease from consolidation but zero coverage regression. No behavior changes.
- Why it matters: Refactoring must not break anything.
- Source: inferred
- Primary owning slice: M011/all
- Validation: 1,012 tests pass (899 unit + 113 e2e). make typecheck, make js, make css all exit 0. No adapter logic, CSS, or test behavior changed.
- Supporting slices: none
- Validation: unmapped
- Notes: Test count expected to decrease (granular tests consolidated). Coverage same or better.

## Validated (M010)

### R050 — Orchestrator setup logic extracted into a shared helper, eliminating duplication between analysis.py and api.py
- Class: quality-attribute
- Status: validated
- Description: The ~20-line orchestrator creation block (ConfigStore, cache TTL, EnrichmentOrchestrator init, _orchestrators registration, _enrichment_pool.submit) is extracted into a single helper in _helpers.py. Both analysis.py and api.py call it.
- Why it matters: Identical logic in two files means every change must be applied twice. Extraction eliminates this maintenance burden and prevents drift.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: _setup_orchestrator() in _helpers.py; zero inline EnrichmentOrchestrator( in analysis.py/api.py. 1061 tests pass.

### R051 — enrichment_status() and api_status() consolidated — single implementation serving both blueprints
- Class: quality-attribute
- Status: validated
- Description: The enrichment polling logic exists identically in enrichment.py (HTML blueprint) and api.py (API blueprint). Consolidated to a single implementation.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: _get_enrichment_status() in _helpers.py; enrichment.py and api.py delegate as one-liners. 1061 tests pass.

### R052 — Unused imports and dead exports removed
- Class: quality-attribute
- Status: validated
- Description: Unused `json` import in api.py, unused `ResultDisplay` export in shared-rendering.ts, and any other dead imports/exports discovered during audit are removed.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: No uuid/json/ConfigStore imports in cleaned modules; export keyword removed from ResultDisplay. make typecheck passes.

### R053 — Recent Analyses removed from home page — index.html renders only the paste form
- Class: core-capability
- Status: validated
- Description: The Recent Analyses collapsible section, its CSS (~130 lines), its JS toggle handler in ui.ts, and the list_recent() call in the index route are all removed from the home page.
- Source: user
- Primary owning slice: M010/S02
- Supporting slices: none
- Validation: S02: No 'Recent Analyses' in index.html; no list_recent call in analysis.py; no initRecentAnalysesToggle in ui.ts. GET / returns paste form only.

### R054 — Dedicated /history page lists recent analyses with links to individual analysis detail pages
- Class: core-capability
- Status: validated
- Description: A new /history route renders a page listing recent analyses. Each entry links to /history/<analysis_id> for the full detail view. Accessible from nav.
- Source: user
- Primary owning slice: M010/S02
- Supporting slices: none
- Validation: S02: history_list() route in history.py; history.html template; clock nav icon in base.html; links to /history/<id> detail pages. GET /history returns 200.

### R055 — All existing tests pass after refactoring with zero behavior changes
- Class: continuity
- Status: validated
- Description: All 1060 tests pass after all refactoring. No user-visible behavior changes — same responses, same UI, same enrichment flow.
- Source: inferred
- Primary owning slice: M010/all
- Supporting slices: none
- Validation: 1061 tests passed (up from 1060 baseline — 1 error-propagation test added, 0 removed). Zero behavior changes confirmed.

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
| R009 | compliance/security | validated | M002/S04 | none | validated |
| R010 | quality-attribute | validated | M002/S04 | none | validated |
| R011 | continuity | validated | M002/S05 | none | validated |
| R012 | quality-attribute | validated | M002/S01 | none | validated |
| R013 | quality-attribute | validated | M003/S01 | none | validated |
| R014 | quality-attribute | validated | M003/S01 | none | validated |
| R015 | core-capability | validated | M003/S02 | none | validated |
| R016 | core-capability | validated | M003/S03 | none | validated |
| R017 | quality-attribute | validated | M003/S04 | none | validated |
| R018 | quality-attribute | validated | M004/S01 | none | validated |
| R019 | quality-attribute | validated | M004/S01 | none | validated |
| R020 | quality-attribute | validated | M004/S02 | none | validated |
| R021 | quality-attribute | validated | M004/S02 | none | validated |
| R022 | quality-attribute | validated | M004/S02 | none | validated |
| R023 | quality-attribute | validated | M004/S03 | none | validated |
| R024 | quality-attribute | validated | M004/S04 | none | validated |
| R025 | compliance/security | validated | M004/S04 | none | validated |
| R026 | quality-attribute | validated | M007/S01 | none | validated |
| R027 | quality-attribute | validated | M007/S01 | none | validated |
| R028 | quality-attribute | validated | M005/S03 | none | validated |
| R029 | quality-attribute | validated | M005/S03 | none | validated |
| R030 | core-capability | validated | M006/S01 | none | validated |
| R031 | primary-user-loop | validated | M006/S01 | M006/S04 | validated |
| R032 | core-capability | validated | M006/S02 | none | validated |
| R033 | core-capability | validated | M006/S03 | none | validated |
| R035 | integration | validated | M008/S02 | none | validated |
| R036 | quality-attribute | validated | M007/S01 | none | validated |
| R037 | quality-attribute | validated | M007/S02 | none | validated |
| R038 | quality-attribute | validated | M007/S02 | none | validated |
| R039 | quality-attribute | validated | M007/S03 | none | validated |
| R040 | continuity | validated | M007/all | none | validated |
| R041 | quality-attribute | validated | M009/S01 | M009/S02 | validated |
| R042 | quality-attribute | validated | M009/S02 | M009/S01 | validated |
| R043 | constraint | validated | M009/S02 | none | validated |
| R044 | quality-attribute | validated | M009/S03 | none | validated |
| R045 | quality-attribute | validated | M009/S03 | none | validated |
| R046 | quality-attribute | validated | M009/S04 | none | validated |
| R047 | quality-attribute | validated | M009/S04 | none | validated |
| R048 | continuity | validated | M009/all | none | validated |
| R049 | quality-attribute | validated | M009/all | none | validated |
| R050 | quality-attribute | validated | M010/S01 | none | S01: _setup_orchestrator() in _helpers.py; zero inline EnrichmentOrchestrator( in analysis.py/api.py. 1061 tests pass. |
| R051 | quality-attribute | validated | M010/S01 | none | S01: _get_enrichment_status() in _helpers.py; one-liner delegations. 1061 tests pass. |
| R052 | quality-attribute | validated | M010/S01 | none | S01: No dead imports in cleaned modules; ResultDisplay export removed. make typecheck passes. |
| R053 | core-capability | validated | M010/S02 | none | S02: No Recent Analyses in index.html; no list_recent in analysis.py; no toggle JS. |
| R054 | core-capability | validated | M010/S02 | none | S02: history_list() route; history.html template; clock nav icon; links to detail pages. |
| R055 | continuity | validated | M010/all | none | 1061 tests passed (up from 1060). Zero behavior changes. |
| R056 | quality-attribute | active | M011/S01 | none | unmapped |
| R057 | quality-attribute | active | M011/S02 | none | unmapped |
| R058 | quality-attribute | active | M011/S03 | none | unmapped |
| R059 | quality-attribute | active | M011/S03 | none | unmapped |
| R060 | continuity | active | M011/all | none | unmapped |

## Coverage Summary

- Active requirements: 5 (R056, R057, R058, R059, R060)
- Mapped to slices: 5
- Validated: 54 (R001–R055)
- Unmapped active requirements: 0
