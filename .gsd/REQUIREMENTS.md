# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R036 — Shared `safe_request()` consolidates HTTP boilerplate across all 12 HTTP adapters
- Class: quality-attribute
- Status: validated
- Description: A shared `safe_request()` function in `http_safety.py` handles SSRF validation, HTTP GET/POST with safety controls (timeout, no redirects, streaming byte cap), pre-raise_for_status hooks (429, 404), and the full exception handler chain (Timeout → HTTPError → SSLError → ConnectionError → Exception) with correct ordering (D035). All 12 HTTP adapters call it instead of inlining the boilerplate.
- Why it matters: 12 adapters duplicate identical ~25-line HTTP + exception blocks. Consolidation eliminates the class of bugs where one adapter's handler chain drifts from the canonical order.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated — safe_request() consolidates all HTTP boilerplate; all 12 adapters migrated; 1057 tests pass
- Notes: M005 planned this work (R026/R027) but the code never landed — safe_request() does not exist in http_safety.py and adapters still inline the full boilerplate. This is a reattempt.

### R037 — Adapter docstrings trimmed — SEC control descriptions centralized, not repeated per-adapter
- Class: quality-attribute
- Status: validated
- Description: Adapter module and class docstrings no longer repeat SEC-04/05/06/16 safety control descriptions. Security control docs live once in http_safety.py. Each adapter docstring documents only adapter-specific behavior (API endpoint, verdict logic, response format).
- Why it matters: ~1,354 lines of docstrings across 15 adapters, 40-46% of each file. The SEC control text is identical in every adapter — pure copy-paste bloat.
- Source: execution
- Primary owning slice: M007/S02
- Supporting slices: none
- Validation: validated — zero SEC-04/05/06/07/16 references in adapter files; 77 lines of duplicated docstrings removed
- Notes: Adapter-specific docs (endpoint behavior, verdict thresholds, API key requirements) are preserved. Only the duplicated SEC boilerplate is removed.

### R038 — Dead CSS removed (consensus-badge and any other confirmed dead selectors)
- Class: quality-attribute
- Status: validated
- Description: Dead CSS classes are removed from input.css. consensus-badge CSS (kept since M001/D003 for rollback) is removed. Any test-only references updated.
- Why it matters: consensus-badge has been dead for 5 milestones. Dead CSS is noise in the stylesheet.
- Source: execution
- Primary owning slice: M007/S02
- Supporting slices: none
- Validation: validated — consensus-badge CSS absent from input.css; stale chevron-toggle comment removed
- Notes: The row-factory.test.ts assertion that consensus-badge doesn't exist should be removed too — testing for the absence of deleted code is pointless.

### R039 — Test files use shared `tests/helpers.py` factories instead of inlining mock setup
- Class: quality-attribute
- Status: validated
- Description: Adapter test files use `make_mock_response`, `make_ipv4_ioc`, and other shared factories from `tests/helpers.py` instead of inlining their own MagicMock setup. New helper factories added as needed.
- Why it matters: 23 of 33 test files inline their own mock setup. Standardizing on shared helpers reduces test maintenance burden.
- Source: execution
- Primary owning slice: M007/S03
- Supporting slices: none
- Validation: validated — all 12 adapter test files use shared make_*_ioc() and mock_adapter_session(); zero inline IOC or MagicMock patterns remain
- Notes: Only mechanical DRY-up — no test behavior changes. Tests that already use helpers are left alone.

### R040 — All 1043 existing tests pass with zero behavior changes
- Class: continuity
- Status: validated
- Description: Every existing test passes after all refactoring. No functional behavior changes — same HTTP calls, same verdicts, same error handling, same DOM output.
- Why it matters: This is a pure cleanup milestone. The test suite is the safety net proving nothing broke.
- Source: inferred
- Primary owning slice: M007/all
- Supporting slices: none
- Validation: validated — 1057 tests pass; count increased from 1043 (14 new safe_request tests); zero behavior changes
- Notes: Test count may decrease slightly if redundant absence-tests (e.g., consensus-badge) are removed.

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

### R003 — Verdict severity is the only loud color in the results page.
- Class: quality-attribute
- Status: validated
- Description: Verdict severity is the only loud color in the results page. All other elements use muted typographic hierarchy.
- Why it matters: Eliminates competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: validated
- Notes: IOC type still identifiable via muted text

### R004 — Clicking an IOC row expands full provider details inline, below the row.
- Class: core-capability
- Status: validated
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: validated
- Notes: Detail page still exists for deep dives

### R005 — Verdict counts displayed as a compact inline summary bar.
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

### R007 — Less important information hidden by default but accessible through intentional interaction.
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
- Description: All existing functionality preserved through the rework.
- Why it matters: Presentation rework, not feature change.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: validated
- Notes: Export and copy depend on data-* attributes on DOM elements

### R009 — CSP headers, CSRF protection, textContent-only DOM construction, SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: Security posture cannot regress during a UI redesign.
- Why it matters: Security posture cannot regress.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Every DOM construction uses createElement + textContent

### R010 — Debounced card sorting, polling efficiency, lazy rendering — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Performance characteristics maintained or improved.
- Why it matters: A lightweight tool must feel lightweight.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: validated
- Notes: Monitor build size

### R011 — All E2E tests updated for new DOM structure and passing.
- Class: quality-attribute
- Status: validated
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing.
- Why it matters: Test suite is the safety net.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: validated
- Notes: Route-mocking infrastructure enables future enrichment surface tests

### R012 — The per-IOC detail page matches the quiet precision design system.
- Class: quality-attribute
- Status: validated
- Description: The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002.
- Why it matters: Visual consistency builds analyst trust.
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: validated
- Notes: Design-only refresh

### R013 — Input/home page matches the quiet precision design language.
- Class: quality-attribute
- Status: validated
- Description: Home page uses zinc tokens, Inter Variable typography, consistent spacing and color approach.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: M006/S04
- Supporting slices: M006/S01
- Validation: validated
- Notes: Previously deferred from M002. Activated for M006.

### R014 — Per-provider concurrency semaphores.
- Class: quality-attribute
- Status: validated
- Description: The enrichment orchestrator enforces rate limits per provider, not globally.
- Why it matters: Zero-auth providers are not blocked by VT's constraint.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: VT semaphore value = 4

### R015 — Exponential backoff with jitter for 429 errors.
- Class: quality-attribute
- Status: validated
- Description: When a provider returns a 429, the orchestrator waits before retrying.
- Why it matters: Immediate retry on 429 burns API quota.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: validated
- Notes: ~1s base × 2^attempt + jitter. Max 2 retries.

### R016 — Email IOC extraction and display.
- Class: core-capability
- Status: validated
- Description: Email addresses extracted from analyst input and displayed under an EMAIL group.
- Why it matters: Email addresses are a primary IOC type in phishing investigations.
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: validated
- Notes: Fully-defanged form user[@]evil[.]com is a known limitation

### R017 — Debounced updateSummaryRow() at 100ms per IOC.
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
- Description: Three independent concurrency bugs fixed in orchestrator.py.
- Why it matters: Prevents stalling all concurrent slots during backoff.
- Source: execution
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: validated
- Notes: Three independent bugs

### R019 — Polling cursor via ?since= parameter.
- Class: quality-attribute
- Status: validated
- Description: The enrichment status endpoint accepts ?since= cursor and returns only new results.
- Why it matters: Eliminates O(N²) re-serialization.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: Wire protocol change; E2E-verified

### R020 — Every adapter uses requests.Session for connection pooling.
- Class: quality-attribute
- Status: validated
- Description: Every adapter stores a requests.Session as self._session and uses it for all HTTP calls.
- Why it matters: Eliminates TCP+TLS handshake overhead per lookup.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: Session must be thread-safe

### R021 — GeoIP adapter uses HTTPS (ipinfo.io).
- Class: compliance/security
- Status: validated
- Description: The ip-api.com adapter uses HTTPS (ipinfo.io) instead of cleartext HTTP.
- Why it matters: Cleartext HTTP leaks the analyst's full IOC queue.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: ipinfo.io free tier, HTTPS, no auth required

### R022 — CacheStore WAL mode with persistent connection and purge_expired().
- Class: quality-attribute
- Status: validated
- Description: CacheStore enables WAL mode, keeps persistent connection, and has purge_expired() method.
- Why it matters: Eliminates per-operation connection overhead.
- Source: execution
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: validated
- Notes: WAL mode persists in the DB file

### R023 — Frontend O(N²) DOM work eliminated.
- Class: quality-attribute
- Status: validated
- Description: findCopyButtonForIoc() uses attribute selector, updateDashboardCounts() called once per tick, applyFilter() debounced, verdictSeverityIndex() uses Map, graph layout uses index Map.
- Why it matters: Eliminates O(N²) DOM work during enrichment.
- Source: execution
- Primary owning slice: M004/S03
- Supporting slices: none
- Validation: validated
- Notes: Dead exports also removed in S03

### R024 — TypeScript incremental builds and email CSS safelist.
- Class: quality-attribute
- Status: validated
- Description: tsconfig.json has incremental:true. tailwind.config.js safelist includes email badge/filter classes.
- Why it matters: Faster typecheck; prevents email CSS purge regression.
- Source: execution
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: validated
- Notes: Fix safelist BEFORE removing dist glob

### R025 — Full CSP header set and SECRET_KEY startup warning.
- Class: compliance/security
- Status: validated
- Description: CSP header includes style-src, connect-src, img-src, font-src, object-src. SECRET_KEY startup warning.
- Why it matters: Incomplete CSP may block enrichment polling.
- Source: execution
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: validated
- Notes: Rate limiter persistent backend infeasible without Redis/Memcached (D037/D038)

### R026 — safe_request() function in http_safety.py
- Class: quality-attribute
- Status: validated
- Description: A shared `safe_request()` function in `http_safety.py` handles SSRF validation, HTTP GET/POST with safety controls, pre-raise_for_status hooks, and the full exception handler chain with correct ordering (D035).
- Why it matters: 12 adapters duplicate identical ~25-line HTTP + exception blocks.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated — safe_request() exists in http_safety.py with 14 unit tests covering GET/POST, SSRF, all exception types, and hooks
- Notes: M005 claimed completion but the code never materialized. Reattempted in M007.

### R027 — All 12 HTTP adapters use safe_request()
- Class: quality-attribute
- Status: validated
- Description: All 12 HTTP-based adapters call `safe_request()` instead of inlining validate_endpoint + session.get/post + safety controls + exception handling.
- Why it matters: Achieves the LOC reduction and consistency target.
- Source: execution
- Primary owning slice: M007/S01
- Supporting slices: none
- Validation: validated — all 12 HTTP adapters call safe_request(), zero import requests.exceptions, zero call validate_endpoint directly
- Notes: M005 claimed completion but adapters still inline the full boilerplate. Reattempted in M007.

### R028 — Registry cached at startup.
- Class: quality-attribute
- Status: validated
- Description: `build_registry()` runs once in `create_app()` and is stored on the app object.
- Why it matters: Eliminates per-request registry construction.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: validated
- Notes: ConfigStore caching makes this fast; this is a cleanliness fix.

### R029 — analyze() decomposed into focused helpers.
- Class: quality-attribute
- Status: validated
- Description: The `analyze()` function is split into `_extract_iocs()`, `_launch_enrichment()`, `_build_template_context()`.
- Why it matters: Readability and testability.
- Source: execution
- Primary owning slice: M005/S03
- Supporting slices: none
- Validation: validated
- Notes: Coordinator is ~20 lines.

### R030 — Analysis history persisted to SQLite.
- Class: core-capability
- Status: validated
- Description: Every analysis run persisted to SQLite. Analysts can revisit past analyses.
- Why it matters: Every competitive tool saves past lookups.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: none
- Validation: validated
- Notes: Reuses existing SQLite WAL-mode DB pattern.

### R031 — Recent analyses list on home page.
- Class: primary-user-loop
- Status: validated
- Description: Home page displays recent analyses with timestamp, IOC count, and top verdict.
- Why it matters: Quick access to past work.
- Source: user
- Primary owning slice: M006/S01
- Supporting slices: M006/S04
- Validation: validated
- Notes: Lightweight list, not a dashboard.

### R032 — WHOIS domain enrichment adapter.
- Class: core-capability
- Status: validated
- Description: WhoisAdapter queries WHOIS data for domains — registrar, creation date, expiry date, name servers.
- Why it matters: WHOIS data is table-stakes for domain investigation.
- Source: user
- Primary owning slice: M006/S02
- Supporting slices: none
- Validation: validated
- Notes: python-whois library, direct WHOIS protocol.

### R033 — URL IOC end-to-end support.
- Class: core-capability
- Status: validated
- Description: URL IOCs extracted, enriched, displayed with filter pills, and accessible on detail page.
- Why it matters: URLs are a primary IOC type.
- Source: user
- Primary owning slice: M006/S03
- Supporting slices: none
- Validation: validated
- Notes: 8 E2E Playwright tests verify the full path.

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
| R035 | integration | deferred | none | none | unmapped |
| R036 | quality-attribute | validated | M007/S01 | none | validated |
| R037 | quality-attribute | validated | M007/S02 | none | validated |
| R038 | quality-attribute | validated | M007/S02 | none | validated |
| R039 | quality-attribute | validated | M007/S03 | none | validated |
| R040 | continuity | validated | M007/all | none | validated |

## Coverage Summary

- Active requirements: 0
- Mapped to slices: 7
- Validated: 40
- Unmapped active requirements: 0
