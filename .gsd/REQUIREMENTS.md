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
- Validation: S01 added display:flex;flex-direction:column to .ioc-card; #ioc-cards-grid uses grid-template-columns:1fr with no 2-column breakpoint. Confirmed by 99/99 E2E passing and grep confirming zero grid-cols-2 or repeat(2 in input.css.
- Notes: Long hashes (SHA256) and URLs must render without wrapping awkwardly

### R002 — Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Class: primary-user-loop
- Status: validated
- Description: Without any interaction, each IOC row shows: worst verdict, real-world context (GeoIP/ASN for IPs, DNS A records for domains), and key provider numbers (detection ratios, report counts).
- Why it matters: The analyst's primary workflow is scanning results for actionable IOCs. Every click required to see key data slows triage.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S02 delivered enrichment slot CSS — .enrichment-slot--loaded opacity:1 override, context-line padding fix, micro-bar width tuned. row-factory.ts and enrichment.ts wired verdict badge, context line, provider stat line, micro-bar, staleness badge into .enrichment-slot. S05 added 8 enrichment surface E2E tests confirming .ioc-summary-row, .verdict-micro-bar, .enrichment-slot--loaded all present after route-mocked polling. 99/99 passing.
- Notes: This is the hardest design challenge — dense data that reads cleanly

### R003 — Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Class: quality-attribute
- Status: validated
- Description: Verdict severity is the only loud color in the results page. All other elements (type indicators, context, provider names, buttons) use muted typographic hierarchy — font weight, size, and opacity rather than competing colors.
- Why it matters: Eliminates the "wall of badges" junior-project aesthetic. Analyst's eye lands on what matters without parsing competing visual signals.
- Source: user
- Primary owning slice: M002/S01
- Supporting slices: M002/S02, M002/S03
- Validation: S01 collapsed all 8 IOC type badge variants to single zinc neutral rule. S03 confirmed expanded panel uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover). S04 T02 grep audit confirmed zero bright non-verdict colors in dist CSS. 99/99 E2E passing.
- Notes: IOC type still needs to be identifiable — just via muted text, not bright colored badges

### R004 — Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Class: core-capability
- Status: validated
- Description: Clicking an IOC row expands full provider details inline, below the row. No page navigation required for the 80% triage case.
- Why it matters: Keeps analyst in context — no page load, no back-button navigation, results list stays visible.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: none
- Validation: S03 delivered .ioc-summary-row as whole-row click target; wireExpandToggles() event delegation on .page-results; .enrichment-details toggles .is-open; aria-expanded state maintained; keyboard Enter/Space supported; injectDetailLink() injects "View full detail →" with encodeURIComponent href at /detail/<type>/<value>. S05 test_expand_collapse_ioc_row and test_detail_link_injected pass. 99/99 E2E passing.
- Notes: Detail page still exists for deep dives (relationship graph, annotations) — linked from expanded view

### R005 — Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Class: core-capability
- Status: validated
- Description: Verdict counts (malicious/suspicious/clean/known_good/no_data) displayed as a compact inline summary bar instead of 5 large KPI boxes.
- Why it matters: Current KPI boxes push IOC results below the fold. Compact dashboard gives the same information while keeping IOCs visible.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S01 restructured _verdict_dashboard.html to flex-direction:row with border-right dividers and verdict-colored count text. S04 T01 wiring matrix confirmed filter.ts binds .verdict-kpi-card[data-verdict] for click-to-filter. 99/99 E2E passing including verdict filter tests.
- Notes: Must still be clickable to filter by verdict

### R006 — Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Class: core-capability
- Status: validated
- Description: Verdict filters, type filters, and search consolidated into a single compact row instead of the current 3-stacked rows.
- Why it matters: Current filter bar is visually heavy and pushes IOC content down. Lightweight tool should have lightweight chrome.
- Source: user
- Primary owning slice: M002/S02
- Supporting slices: M002/S01
- Validation: S01 restructured _filter_bar.html to single flex row with flex-wrap. S04 T01 wiring matrix confirmed all filter functionality (verdict toggle, type toggle, text search) intact. 99/99 E2E passing.
- Notes: All filter functionality preserved — verdict toggle, type toggle, text search

### R007 — Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Class: quality-attribute
- Status: validated
- Description: Less important information is hidden by default but accessible through intentional interaction (expand, hover, click). Important info visible at a glance, details on demand.
- Why it matters: Core design philosophy of the rework. Information hierarchy through showing vs. hiding rather than through competing visual weight.
- Source: user
- Primary owning slice: M002/S03
- Supporting slices: M002/S02
- Validation: S03 delivered expand/collapse gate — provider details hidden by default in .enrichment-details, revealed on deliberate click/keypress. Summary row always shows at-a-glance surface. "View full detail →" link only visible in expanded state. S05 test_enrichment_section_in_expanded_row confirms progressive disclosure behavior. 99/99 E2E passing.
- Notes: Applies to: provider detail rows, no-data providers, context fields, cache staleness

### R008 — Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Class: continuity
- Status: validated
- Description: Enrichment polling, export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar — all working.
- Why it matters: This is a presentation rework, not a feature change. Nothing should regress.
- Source: user
- Primary owning slice: M002/S04
- Supporting slices: M002/S01, M002/S02, M002/S03
- Validation: S04 T01 produced 18-point wiring verification matrix (file:line evidence). allResults[] accumulation → export.ts via closure confirmed; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard. 91/91 E2E at S04 close; 99/99 at S05 close.
- Notes: Export and copy depend on data-* attributes on DOM elements — must preserve or migrate

### R009 — CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress during a UI redesign.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 T02 six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only. document.write/eval() return zero matches (grep exit 1). row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout.
- Notes: Every DOM construction in new TypeScript code must use createElement + textContent

### R010 — Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight. Performance regressions during redesign are common and unacceptable.
- Source: inferred
- Primary owning slice: M002/S04
- Supporting slices: all
- Validation: S04 T03 production bundle 27,226 bytes (≤ 30KB gate). 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts.
- Notes: Monitor build size — current main.js is 27,226 bytes (minified prod)

### R011 — All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Class: quality-attribute
- Status: validated
- Description: All E2E tests updated for new DOM structure (selectors, page objects) and passing. No reduction in coverage.
- Why it matters: Test suite is the safety net that proves the redesign doesn't break functionality.
- Source: inferred
- Primary owning slice: M002/S05
- Supporting slices: none
- Validation: python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed (up from 91 baseline). ResultsPage page object expanded from 118 to 266 lines. 8 new tests added. No tests removed.
- Notes: Route-mocking infrastructure in conftest.py enables future enrichment surface tests without external API dependency.

### R012 — The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002 — verdict-only color, zinc neutrals for chrome, consistent typography hierarchy, graph labels untruncated.
- Class: quality-attribute
- Status: validated
- Description: The per-IOC detail page (ioc_detail.html) is updated to match the quiet precision design system established in M002 — verdict-only color, zinc neutrals for chrome, consistent typography hierarchy, graph labels untruncated.
- Why it matters: Landing on the detail page from the results page currently feels like a regression. Visual consistency builds analyst trust.
- Source: inferred
- Primary owning slice: M003/S03
- Supporting slices: none
- Validation: S03 applied M002 design tokens to ioc_detail.html: stacked .detail-provider-card layout with --bg-secondary surfaces, --border dividers, --text-primary/--text-secondary typography, --font-mono for IOC code, verdict-badge--{verdict} as only color class. Inline <style> block removed. Graph labels untruncated (routes.py and graph.ts [:N] slices removed). 13 tests pass: test_detail_page_with_results asserts detail-provider-card, verdict-badge--malicious, and absence of <style>; test_detail_graph_labels_untruncated asserts "Shodan InternetDB" appears verbatim in data-graph-nodes.
- Notes: Design-only refresh — no new data or structural features. R013 (input page) stays deferred.

### R014 — The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests (free tier). Zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are not blocked by VT's constraint.
- Class: quality-attribute
- Status: validated
- Description: The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests (free tier). Zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are not blocked by VT's constraint.
- Why it matters: Current `max_workers=4` serializes all 14 providers to 4 concurrent threads. Zero-auth providers with no rate limits are artificially bottlenecked behind VT. An analyst with 10 IPs waits far longer than necessary.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: S01 added per-provider semaphore dict in orchestrator._do_lookup(): VT gets Semaphore(4), zero-auth providers get Semaphore(8). Unit tests in tests/test_orchestrator.py assert VT calls are capped at 4 concurrent while zero-auth providers run freely. All 828 unit tests + 99 E2E tests passing at M003 close.
- Notes: Per-provider semaphore pattern. VT semaphore value = 4. All other providers default to a higher ceiling (e.g. 8 concurrent).

### R015 — When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter — rather than immediately retrying (which consumes quota and is likely to fail again).
- Class: quality-attribute
- Status: validated
- Description: When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter — rather than immediately retrying (which consumes quota and is likely to fail again).
- Why it matters: The current blind immediate retry on any EnrichmentError burns API quota on 429s. Two consecutive 429s from VT waste 2 of the 4/min allowance.
- Source: inferred
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: S01 added 429-aware backoff retry in orchestrator._do_lookup_inner(): exponential backoff with jitter using _BACKOFF_BASE and _MAX_RATE_LIMIT_RETRIES constants. Unit tests assert time.sleep is called with delay >= _BACKOFF_BASE on 429 response. All 828 unit tests + 99 E2E tests passing at M003 close.
- Notes: Retry delay: ~1s base × 2^attempt + jitter. Max 2 retries. Non-429 errors can retry immediately (they're not quota burns).

### R016 — Email addresses (e.g. `user@evil.com`, defanged `user[@]evil[.]com`) are extracted from analyst input and displayed in the results page under an EMAIL group. No enrichment providers are wired for email — display only.
- Class: core-capability
- Status: validated
- Description: Email addresses (e.g. `user@evil.com`, defanged `user[@]evil[.]com`) are extracted from analyst input and displayed in the results page under an EMAIL group. No enrichment providers are wired for email — display only.
- Why it matters: Analysts paste email headers and phishing reports constantly. Email addresses are a primary IOC type in phishing investigations and are currently silently dropped.
- Source: user
- Primary owning slice: M003/S02
- Supporting slices: none
- Validation: S02 added IOCType.EMAIL to models.py, email regex classifier in classifier.py at precedence position 8 (before Domain), OTX adapter explicit frozenset excluding EMAIL. CSS badge (.ioc-type-badge--email) in input.css and dist/style.css. Filter pill (.filter-pill--email.filter-pill--active) in both CSS files. 6 E2E tests added to test_results_page.py confirming: email cards render, EMAIL filter pill appears, filtering shows only email cards, active state works, All Types resets, badge is visible. 105/105 E2E passing, 828/828 unit tests passing. Fully-defanged form user[@]evil[.]com is a known limitation (iocsearcher doesn't extract it; domain is extracted instead).
- Notes: iocsearcher already extracts emails (type "email"). Requires: IOCType.EMAIL enum value, classifier case, display in results template, ioc-type-badge CSS variant. No enrichment adapters.

### R017 — updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC, matching the sortDetailRows pattern. During streaming enrichment, a 10-provider IOC triggers 1-2 summary row rebuilds instead of 10.
- Class: quality-attribute
- Status: validated
- Description: updateSummaryRow() in row-factory.ts is debounced at 100ms per IOC, matching the sortDetailRows pattern. During streaming enrichment, a 10-provider IOC triggers 1-2 summary row rebuilds instead of 10.
- Why it matters: Each rebuild does a full DOM teardown (textContent="") and reconstruction. On a large result set with many IOCs streaming simultaneously, this causes unnecessary layout thrashing.
- Source: inferred
- Primary owning slice: M003/S04
- Supporting slices: none
- Validation: S04 applied summaryTimers debounce map in enrichment.ts: declaration + debouncedUpdateSummaryRow() wrapper + replaced direct updateSummaryRow() call. grep -c 'summaryTimers' enrichment.ts → 4. make typecheck → exit 0. bundle 26,783 bytes ≤ 30KB. 828 unit tests + 99 E2E tests all passing.
- Notes: Same debounce map pattern as sortTimers in enrichment.ts. Final rebuild must always fire after last result for an IOC.

### R018 — The semaphore acquired for a provider must not be held during `time.sleep()` backoff. `get_status()` must return a snapshot of the results list, not the live shared reference. `_cached_markers` writes must be protected by `_lock`.
- Class: quality-attribute
- Status: validated
- Description: The semaphore acquired for a provider must not be held during `time.sleep()` backoff. `get_status()` must return a snapshot of the results list, not the live shared reference. `_cached_markers` writes must be protected by `_lock`.
- Why it matters: Under concurrent 429s, all 4 VT semaphore slots can sleep simultaneously, stalling every queued IOC for 47+ seconds. Shallow-copy race can produce `RuntimeError` under load. Unsynchronized dict mutation produces incorrect snapshots during concurrent resize.
- Source: execution (audit)
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: S01 fixed all three concurrency invariants: (1) semaphore released before time.sleep() backoff via _single_attempt() + explicit sem.acquire()/release() in _do_lookup(); (2) get_status() returns list() snapshot not live reference; (3) _cached_markers reads/writes protected by _lock. Three dedicated unit tests prove each invariant independently. All 944 tests passing.
- Notes: Three independent bugs in orchestrator.py; must all be fixed in S01

### R019 — The `/enrichment/status/<job_id>` endpoint must accept a `?since=<index>` cursor and return only `results[since:]`. The frontend polling loop must use this cursor instead of the client-side `rendered` dedup map.
- Class: quality-attribute
- Status: validated
- Description: The `/enrichment/status/<job_id>` endpoint must accept a `?since=<index>` cursor and return only `results[since:]`. The frontend polling loop must use this cursor instead of the client-side `rendered` dedup map.
- Why it matters: Current implementation re-serializes and re-transmits the full accumulated results list on every 750ms tick. For a 50-IOC batch, the final ticks each transmit 50 results when only 1-2 are new — O(N²) total work and bandwidth.
- Source: execution (audit)
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: S02/T01: enrichment_status() reads ?since= param (default 0), returns results[since:] and next_since: len(results). enrichment.ts replaced rendered dedup map with since counter — polls with ?since=${since}, updates since=data.next_since. 4 new unit tests (since=2 returns slice, since=0 full, no param full, since=99 empty) + E2E mock includes next_since. 6/6 enrichment_status tests pass. grep -c 'rendered' enrichment.ts returns 0.
- Notes: Wire protocol change; must be E2E-verified for off-by-one correctness

### R020 — Every adapter must store a `requests.Session` as `self._session` (created in `__init__`) and use it for all HTTP calls. No bare `requests.get()` or ephemeral per-call `requests.Session()`.
- Class: quality-attribute
- Status: validated
- Description: Every adapter must store a `requests.Session` as `self._session` (created in `__init__`) and use it for all HTTP calls. No bare `requests.get()` or ephemeral per-call `requests.Session()`.
- Why it matters: New TCP+TLS handshake on every `lookup()` call adds 50–150ms per provider per IOC. For a 20-IOC batch across 14 providers, this is 1–4 seconds of pure connection overhead per job.
- Source: execution (audit)
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: S02/T02: All 12 adapters have self._session = requests.Session() in __init__. 7 API-key adapters moved auth headers to session-level. grep -rn 'requests\.get\|requests\.post' adapters/*.py returns 0 code hits. grep -rl 'self._session' adapters/*.py returns 12. All 12 test files mock adapter._session directly. 839 unit tests pass.
- Notes: Session must be thread-safe — only `get()` calls, no header mutation between calls

### R021 — The ip-api.com adapter must be replaced or switched to an HTTPS endpoint. The `IP_API_BASE` constant must not use `http://`.
- Class: compliance/security
- Status: validated
- Description: The ip-api.com adapter must be replaced or switched to an HTTPS endpoint. The `IP_API_BASE` constant must not use `http://`.
- Why it matters: Cleartext HTTP leaks the analyst's full IOC queue (all IPs being investigated) to any network observer — MITM, ISP, or LAN adversary. Responses can also be injected to produce false verdicts.
- Source: execution (audit)
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: S02/T03: ip_api.py rewritten for https://ipinfo.io/{ip}/json. IPINFO_BASE uses https://. grep 'http://' ip_api.py returns 0. ALLOWED_API_HOSTS: ipinfo.io added, ip-api.com removed. 404-based private IP handling. _parse_response() maps ipinfo.io fields (country→country_code, org→ASN+ISP, hostname→reverse). 50/50 test_ip_api.py tests pass with ipinfo.io fixtures.
- Notes: ipinfo.io free tier supports HTTPS with no auth required; suitable replacement

### R022 — `CacheStore.__init__` must enable WAL mode (`PRAGMA journal_mode=WAL`) and keep a persistent connection. A `purge_expired(ttl_seconds)` method must exist that deletes entries older than the TTL.
- Class: quality-attribute
- Status: validated
- Description: `CacheStore.__init__` must enable WAL mode (`PRAGMA journal_mode=WAL`) and keep a persistent connection. A `purge_expired(ttl_seconds)` method must exist that deletes entries older than the TTL.
- Why it matters: New connection per operation creates 200+ open/close cycles per enrichment batch and serializes concurrent readers behind writers (no WAL). Without purge, expired entries accumulate indefinitely, degrading `stats()` and scan performance over time.
- Source: execution (audit)
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: S02/T04: CacheStore.__init__ executes PRAGMA journal_mode=WAL (L51 of store.py) and keeps persistent self._conn. purge_expired(ttl_seconds) method exists at L155 and deletes entries older than TTL, returning row count. 34/34 cache+config tests pass. All 944 tests pass.
- Notes: WAL mode persists in the DB file; test fixtures must use temp files

### R023 — `findCopyButtonForIoc()` must use an attribute selector (O(1)); `updateDashboardCounts()` must be called once per poll tick outside the result render loop; `applyFilter()` must be debounced (≥ 100ms); `verdictSeverityIndex()` must use a pre-built Map; graph layout must pre-build an index Map before the edge loop.
- Class: quality-attribute
- Status: validated
- Description: `findCopyButtonForIoc()` must use an attribute selector (O(1)); `updateDashboardCounts()` must be called once per poll tick outside the result render loop; `applyFilter()` must be debounced (≥ 100ms); `verdictSeverityIndex()` must use a pre-built Map; graph layout must pre-build an index Map before the edge loop.
- Why it matters: These five patterns produce O(N²) total DOM work during enrichment. For 50 IOCs × 10 providers, `findCopyButtonForIoc` alone does 500 full document traversals where 500 single-selector lookups would suffice.
- Source: execution (audit)
- Primary owning slice: M004/S03
- Supporting slices: none
- Validation: S03 applied all 5 R023 patterns: (1) findCopyButtonForIoc() uses querySelector attribute selector with CSS.escape() — grep confirms no querySelectorAll copy-btn. (2) updateDashboardCounts() + sortCardsBySeverity() moved outside per-result loop, called once per poll tick guarded by results.length > 0. (3) applyFilter() debounced at 100ms on search input with clearTimeout/setTimeout pattern — click handlers remain synchronous. (4) verdictSeverityIndex() uses SEVERITY_MAP (ReadonlyMap built at module load) — no indexOf in ioc.ts. (5) graph.ts builds nodeIndexMap before edge loop, replaces .find()/.indexOf() with Map.get(). npx tsc --noEmit clean. 105 E2E tests pass. 944 total tests pass.
- Notes: Dead exports `computeConsensus`/`consensusBadgeClass` also covered in S03

### R024 — `tsconfig.json` must include `"incremental": true`. `tailwind.config.js` content glob must not include `dist/main.js`. The safelist must include `ioc-type-badge--email` and `filter-pill--email` (and active variant).
- Class: quality-attribute
- Status: validated
- Description: `tsconfig.json` must include `"incremental": true`. `tailwind.config.js` content glob must not include `dist/main.js`. The safelist must include `ioc-type-badge--email` and `filter-pill--email` (and active variant).
- Why it matters: Without incremental compilation, every `make typecheck` re-checks all files from scratch (~2.5s). The dist glob causes Tailwind to redundantly parse the compiled bundle. Without the email safelist, removing the dist glob silently purges email badge/filter classes (latent regression from M003/S02).
- Source: execution (audit)
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: S04/T02: `tsconfig.json` has `"incremental": true` in compilerOptions — confirmed via grep. `tailwind.config.js` safelist includes `ioc-type-badge--email` and `filter-pill--email` — confirmed via grep. `npx tsc --noEmit` exits 0 (clean). 944 tests pass.
- Notes: Fix safelist BEFORE removing dist glob to avoid purge regression

### R025 — CSP header must include `style-src`, `connect-src 'self'`, `img-src`, `font-src`, and `object-src 'none'`. Rate limiter must use a persistent storage backend (filesystem or Redis), not `memory://`. When `SECRET_KEY` is not set in environment, a startup warning must be logged.
- Class: compliance/security
- Status: validated
- Description: CSP header must include `style-src`, `connect-src 'self'`, `img-src`, `font-src`, and `object-src 'none'`. Rate limiter must use a persistent storage backend (filesystem or Redis), not `memory://`. When `SECRET_KEY` is not set in environment, a startup warning must be logged.
- Why it matters: Incomplete CSP blocks inline styles and may block the `/enrichment/status/` fetch poll in strict browser contexts. Memory-backed rate limiter resets on restart and is multiplied per worker. Auto-generated `SECRET_KEY` silently invalidates all sessions and CSRF tokens on every restart.
- Source: execution (audit)
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: S04/T03: CSP header expanded to 7 directives (default-src, script-src, style-src, connect-src, img-src, font-src, object-src 'none') — confirmed via grep and live HTTP response test. SECRET_KEY startup warning implemented — confirmed fires at WARNING level when env var unset, silent when set. Rate limiter exception: kept as memory:// because the `limits` library has no filesystem backend (only Redis/Memcached/MongoDB); adding external services inappropriate for single-process local tool (D037/D038). 944 tests pass.
- Notes: Rate limiter persistent backend sub-requirement is documented as infeasible without external infrastructure. If Redis is ever added for other features, rate limiter can piggyback. See D037/D038.

## Deferred

### R013 — Update the input/home page to match the new design language.
- Class: quality-attribute
- Status: deferred
- Description: Update the input/home page to match the new design language.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Deferred — input page is minimal and functional; not worth disrupting M003 scope

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | validated | M002/S01 | none | S01 added display:flex;flex-direction:column to .ioc-card; #ioc-cards-grid uses grid-template-columns:1fr with no 2-column breakpoint. Confirmed by 99/99 E2E passing and grep confirming zero grid-cols-2 or repeat(2 in input.css. |
| R002 | primary-user-loop | validated | M002/S02 | M002/S01 | S02 delivered enrichment slot CSS — .enrichment-slot--loaded opacity:1 override, context-line padding fix, micro-bar width tuned. row-factory.ts and enrichment.ts wired verdict badge, context line, provider stat line, micro-bar, staleness badge into .enrichment-slot. S05 added 8 enrichment surface E2E tests confirming .ioc-summary-row, .verdict-micro-bar, .enrichment-slot--loaded all present after route-mocked polling. 99/99 passing. |
| R003 | quality-attribute | validated | M002/S01 | M002/S02, M002/S03 | S01 collapsed all 8 IOC type badge variants to single zinc neutral rule. S03 confirmed expanded panel uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover). S04 T02 grep audit confirmed zero bright non-verdict colors in dist CSS. 99/99 E2E passing. |
| R004 | core-capability | validated | M002/S03 | none | S03 delivered .ioc-summary-row as whole-row click target; wireExpandToggles() event delegation on .page-results; .enrichment-details toggles .is-open; aria-expanded state maintained; keyboard Enter/Space supported; injectDetailLink() injects "View full detail →" with encodeURIComponent href at /detail/<type>/<value>. S05 test_expand_collapse_ioc_row and test_detail_link_injected pass. 99/99 E2E passing. |
| R005 | core-capability | validated | M002/S02 | M002/S01 | S01 restructured _verdict_dashboard.html to flex-direction:row with border-right dividers and verdict-colored count text. S04 T01 wiring matrix confirmed filter.ts binds .verdict-kpi-card[data-verdict] for click-to-filter. 99/99 E2E passing including verdict filter tests. |
| R006 | core-capability | validated | M002/S02 | M002/S01 | S01 restructured _filter_bar.html to single flex row with flex-wrap. S04 T01 wiring matrix confirmed all filter functionality (verdict toggle, type toggle, text search) intact. 99/99 E2E passing. |
| R007 | quality-attribute | validated | M002/S03 | M002/S02 | S03 delivered expand/collapse gate — provider details hidden by default in .enrichment-details, revealed on deliberate click/keypress. Summary row always shows at-a-glance surface. "View full detail →" link only visible in expanded state. S05 test_enrichment_section_in_expanded_row confirms progressive disclosure behavior. 99/99 E2E passing. |
| R008 | continuity | validated | M002/S04 | M002/S01, M002/S02, M002/S03 | S04 T01 produced 18-point wiring verification matrix (file:line evidence). allResults[] accumulation → export.ts via closure confirmed; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard. 91/91 E2E at S04 close; 99/99 at S05 close. |
| R009 | compliance/security | validated | M002/S04 | all | S04 T02 six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only. document.write/eval() return zero matches (grep exit 1). row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout. |
| R010 | quality-attribute | validated | M002/S04 | all | S04 T03 production bundle 27,226 bytes (≤ 30KB gate). 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts. |
| R011 | quality-attribute | validated | M002/S05 | none | python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed (up from 91 baseline). ResultsPage page object expanded from 118 to 266 lines. 8 new tests added. No tests removed. |
| R012 | quality-attribute | validated | M003/S03 | none | S03 applied M002 design tokens to ioc_detail.html: stacked .detail-provider-card layout with --bg-secondary surfaces, --border dividers, --text-primary/--text-secondary typography, --font-mono for IOC code, verdict-badge--{verdict} as only color class. Inline <style> block removed. Graph labels untruncated (routes.py and graph.ts [:N] slices removed). 13 tests pass: test_detail_page_with_results asserts detail-provider-card, verdict-badge--malicious, and absence of <style>; test_detail_graph_labels_untruncated asserts "Shodan InternetDB" appears verbatim in data-graph-nodes. |
| R013 | quality-attribute | deferred | none | none | unmapped |
| R014 | quality-attribute | validated | M003/S01 | none | S01 added per-provider semaphore dict in orchestrator._do_lookup(): VT gets Semaphore(4), zero-auth providers get Semaphore(8). Unit tests in tests/test_orchestrator.py assert VT calls are capped at 4 concurrent while zero-auth providers run freely. All 828 unit tests + 99 E2E tests passing at M003 close. |
| R015 | quality-attribute | validated | M003/S01 | none | S01 added 429-aware backoff retry in orchestrator._do_lookup_inner(): exponential backoff with jitter using _BACKOFF_BASE and _MAX_RATE_LIMIT_RETRIES constants. Unit tests assert time.sleep is called with delay >= _BACKOFF_BASE on 429 response. All 828 unit tests + 99 E2E tests passing at M003 close. |
| R016 | core-capability | validated | M003/S02 | none | S02 added IOCType.EMAIL to models.py, email regex classifier in classifier.py at precedence position 8 (before Domain), OTX adapter explicit frozenset excluding EMAIL. CSS badge (.ioc-type-badge--email) in input.css and dist/style.css. Filter pill (.filter-pill--email.filter-pill--active) in both CSS files. 6 E2E tests added to test_results_page.py confirming: email cards render, EMAIL filter pill appears, filtering shows only email cards, active state works, All Types resets, badge is visible. 105/105 E2E passing, 828/828 unit tests passing. Fully-defanged form user[@]evil[.]com is a known limitation (iocsearcher doesn't extract it; domain is extracted instead). |
| R017 | quality-attribute | validated | M003/S04 | none | S04 applied summaryTimers debounce map in enrichment.ts: declaration + debouncedUpdateSummaryRow() wrapper + replaced direct updateSummaryRow() call. grep -c 'summaryTimers' enrichment.ts → 4. make typecheck → exit 0. bundle 26,783 bytes ≤ 30KB. 828 unit tests + 99 E2E tests all passing. |
| R018 | quality-attribute | validated | M004/S01 | none | S01 fixed all three concurrency invariants: (1) semaphore released before time.sleep() backoff via _single_attempt() + explicit sem.acquire()/release() in _do_lookup(); (2) get_status() returns list() snapshot not live reference; (3) _cached_markers reads/writes protected by _lock. Three dedicated unit tests prove each invariant independently. All 944 tests passing. |
| R019 | quality-attribute | validated | M004/S02 | none | S02/T01: enrichment_status() reads ?since= param (default 0), returns results[since:] and next_since: len(results). enrichment.ts replaced rendered dedup map with since counter — polls with ?since=${since}, updates since=data.next_since. 4 new unit tests (since=2 returns slice, since=0 full, no param full, since=99 empty) + E2E mock includes next_since. 6/6 enrichment_status tests pass. grep -c 'rendered' enrichment.ts returns 0. |
| R020 | quality-attribute | validated | M004/S02 | none | S02/T02: All 12 adapters have self._session = requests.Session() in __init__. 7 API-key adapters moved auth headers to session-level. grep -rn 'requests\.get\|requests\.post' adapters/*.py returns 0 code hits. grep -rl 'self._session' adapters/*.py returns 12. All 12 test files mock adapter._session directly. 839 unit tests pass. |
| R021 | compliance/security | validated | M004/S02 | none | S02/T03: ip_api.py rewritten for https://ipinfo.io/{ip}/json. IPINFO_BASE uses https://. grep 'http://' ip_api.py returns 0. ALLOWED_API_HOSTS: ipinfo.io added, ip-api.com removed. 404-based private IP handling. _parse_response() maps ipinfo.io fields (country→country_code, org→ASN+ISP, hostname→reverse). 50/50 test_ip_api.py tests pass with ipinfo.io fixtures. |
| R022 | quality-attribute | validated | M004/S02 | none | S02/T04: CacheStore.__init__ executes PRAGMA journal_mode=WAL (L51 of store.py) and keeps persistent self._conn. purge_expired(ttl_seconds) method exists at L155 and deletes entries older than TTL, returning row count. 34/34 cache+config tests pass. All 944 tests pass. |
| R023 | quality-attribute | validated | M004/S03 | none | S03 applied all 5 R023 patterns: (1) findCopyButtonForIoc() uses querySelector attribute selector with CSS.escape() — grep confirms no querySelectorAll copy-btn. (2) updateDashboardCounts() + sortCardsBySeverity() moved outside per-result loop, called once per poll tick guarded by results.length > 0. (3) applyFilter() debounced at 100ms on search input with clearTimeout/setTimeout pattern — click handlers remain synchronous. (4) verdictSeverityIndex() uses SEVERITY_MAP (ReadonlyMap built at module load) — no indexOf in ioc.ts. (5) graph.ts builds nodeIndexMap before edge loop, replaces .find()/.indexOf() with Map.get(). npx tsc --noEmit clean. 105 E2E tests pass. 944 total tests pass. |
| R024 | quality-attribute | validated | M004/S04 | none | S04/T02: `tsconfig.json` has `"incremental": true` in compilerOptions — confirmed via grep. `tailwind.config.js` safelist includes `ioc-type-badge--email` and `filter-pill--email` — confirmed via grep. `npx tsc --noEmit` exits 0 (clean). 944 tests pass. |
| R025 | compliance/security | validated | M004/S04 | none | S04/T03: CSP header expanded to 7 directives (default-src, script-src, style-src, connect-src, img-src, font-src, object-src 'none') — confirmed via grep and live HTTP response test. SECRET_KEY startup warning implemented — confirmed fires at WARNING level when env var unset, silent when set. Rate limiter exception: kept as memory:// because the `limits` library has no filesystem backend (only Redis/Memcached/MongoDB); adding external services inappropriate for single-process local tool (D037/D038). 944 tests pass. |

## Coverage Summary

- Active requirements: 0
- Mapped to slices: 0
- Validated: 24 (R001, R002, R003, R004, R005, R006, R007, R008, R009, R010, R011, R012, R014, R015, R016, R017, R018, R019, R020, R021, R022, R023, R024, R025)
- Unmapped active requirements: 0
