# Requirements

This file is the explicit capability and coverage contract for the project.

## Active

### R084 — SentinelX has a durable current-state project map that explains what the app is, who it serves, and how its main analyst loop works.
- Class: core-capability
- Status: active
- Description: SentinelX has a durable current-state project map that explains what the app is, who it serves, and how its main analyst loop works.
- Why it matters: The user explicitly said the project must stop feeling unclear; future optimization and execution need a shared product/codebase identity.
- Source: user
- Primary owning slice: M017/S01
- Supporting slices: M017/S02, M017/S05
- Validation: mapped
- Notes: Separate named project map artifact plus refreshed .gsd/PROJECT.md.

### R085 — Optimization decisions are grounded in SentinelX’s product identity, not generic subsystem cleanup.
- Class: quality-attribute
- Status: active
- Description: Optimization decisions are grounded in SentinelX’s product identity, not generic subsystem cleanup.
- Why it matters: Aggressive optimization should improve what SentinelX actually is: a local analyst IOC triage workflow, not arbitrary code aesthetics.
- Source: user
- Primary owning slice: M017/S02
- Supporting slices: M017/S03, M017/S04
- Validation: mapped
- Notes: Audit must rank findings against the project map and analyst loop.

### R086 — The milestone ships the best current optimization opportunity found by the refreshed audit, even if it requires moderate refactoring across existing seams.
- Class: core-capability
- Status: active
- Description: The milestone ships the best current optimization opportunity found by the refreshed audit, even if it requires moderate refactoring across existing seams.
- Why it matters: The user asked for the best optimization the project can do, aggressively, while preserving behavior.
- Source: user
- Primary owning slice: M017/S03
- Supporting slices: M017/S04
- Validation: mapped
- Notes: If the audit proves no code change is justified, that no-change decision must be explicit and evidenced.

### R087 — Every shipped optimization has evidence: before/after measurement when practical, or explicit code-path reasoning plus regression proof.
- Class: quality-attribute
- Status: active
- Description: Every shipped optimization has evidence: before/after measurement when practical, or explicit code-path reasoning plus regression proof.
- Why it matters: Prevents optimization theater and keeps future agents from inheriting unsupported performance claims.
- Source: user
- Primary owning slice: M017/S02
- Supporting slices: M017/S03, M017/S04, M017/S05
- Validation: mapped
- Notes: Audit artifact must record why each change was worth doing.

### R088 — Aggressive optimization preserves analyst-facing IOC intake, enrichment, results, history/detail, diagnostics, and security behavior.
- Class: continuity
- Status: active
- Description: Aggressive optimization preserves analyst-facing IOC intake, enrichment, results, history/detail, diagnostics, and security behavior.
- Why it matters: The strongest optimization is only useful if the analyst workflow and safety posture remain intact.
- Source: inferred
- Primary owning slice: M017/S03
- Supporting slices: M017/S04, M017/S05
- Validation: mapped
- Notes: Continuity includes existing verified browser paths, route/status semantics, local persistence, and no secret leakage.

### R089 — M017 closeout proves the optimized project through the full verification lane, including make verify-fast and make verify-deep.
- Class: operability
- Status: active
- Description: M017 closeout proves the optimized project through the full verification lane, including make verify-fast and make verify-deep.
- Why it matters: The final state must be runnable and trustworthy, not just locally plausible from partial tests.
- Source: user
- Primary owning slice: M017/S05
- Supporting slices: none
- Validation: mapped
- Notes: Full lane is required because aggressive optimization may touch browser/results/enrichment behavior.

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
- Primary owning slice: M012/S01
- Supporting slices: M012/S02
- Validation: S04 T01 produced 18-point wiring verification matrix (file:line evidence). allResults[] accumulation → export.ts via closure confirmed; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard. 91/91 E2E at S04 close; 99/99 at S05 close.
- Notes: M012 planning maps enrichment UI workflow continuity to S01 for live-path contract hardening and S02 for shared live/history rendering follow-through.

### R009 — CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Class: compliance/security
- Status: validated
- Description: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), SSRF allowlist, host validation — all maintained.
- Why it matters: Security posture cannot regress during a UI redesign.
- Source: inferred
- Primary owning slice: M012/S01
- Supporting slices: M012/S02, M012/S03, M012/S04
- Validation: S04 T02 six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only. document.write/eval() return zero matches (grep exit 1). row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout.
- Notes: M012 treats security posture as a continuity constraint across all optimization work, with S01 verifying the first live UI/API seam changes.

### R010 — Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Class: quality-attribute
- Status: validated
- Description: Debounced card sorting, polling efficiency (750ms interval, dedup), lazy rendering of enrichment results — all unchanged or improved.
- Why it matters: A lightweight tool must feel lightweight. Performance regressions during redesign are common and unacceptable.
- Source: inferred
- Primary owning slice: M012/S01
- Supporting slices: M012/S02
- Validation: S04 T03 production bundle 27,226 bytes (≤ 30KB gate). 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts.
- Notes: Polling/render efficiency continuity is owned first by S01 because status-contract hardening must preserve cursor polling and successful incremental updates; S02 carries shared rendering-path optimization.

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

### R013 — Update the input/home page to match the new design language.
- Class: quality-attribute
- Status: validated
- Description: Update the input/home page to match the new design language.
- Why it matters: Visual consistency across pages.
- Source: inferred
- Primary owning slice: M015/S01
- Supporting slices: M015/S02, M015/S03, M015/S04
- Validation: M015/S01 delivered and verified the redesigned index command-card DOM/CSS foundation: `python3 -m pytest -q tests/test_index_intake_contract.py ...` passed 6 route/contract checks, `make build` passed, `npx tsc --noEmit` passed, and `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` passed 18 Playwright tests proving the visible command-card intake surface and offline paste-to-results path.
- Notes: M015 reactivates this deferred input/home-page design gap as part of the fast Intake Workbench scope. It should be validated by the final integrated intake proof rather than treated as a standalone cosmetic cleanup.

### R014 — The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests (free tier). Zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are not blocked by VT's constraint.
- Class: quality-attribute
- Status: validated
- Description: The enrichment orchestrator enforces rate limits per provider, not globally. VirusTotal is capped at 4 concurrent requests (free tier). Zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) are not blocked by VT's constraint.
- Why it matters: Current `max_workers=4` serializes all 14 providers to 4 concurrent threads. Zero-auth providers with no rate limits are artificially bottlenecked behind VT. An analyst with 10 IPs waits far longer than necessary.
- Source: inferred
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: S01 added per-provider semaphore dict in orchestrator._do_lookup(): VT gets Semaphore(4), zero-auth providers get Semaphore(8). Unit tests in tests/test_orchestrator.py assert VT calls are capped at 4 concurrent while zero-auth providers run freely. All 828 unit tests + 99 E2E tests passing at M003 close.
- Notes: Per-provider concurrency continuity is protected in S01 while the enrichment status contract is hardened around the live orchestrator path.

### R015 — When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter — rather than immediately retrying (which consumes quota and is likely to fail again).
- Class: quality-attribute
- Status: validated
- Description: When a provider returns a 429 rate-limit error, the orchestrator waits before retrying — exponential backoff with jitter — rather than immediately retrying (which consumes quota and is likely to fail again).
- Why it matters: The current blind immediate retry on any EnrichmentError burns API quota on 429s. Two consecutive 429s from VT waste 2 of the 4/min allowance.
- Source: inferred
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: S01 added 429-aware backoff retry in orchestrator._do_lookup_inner(): exponential backoff with jitter using _BACKOFF_BASE and _MAX_RATE_LIMIT_RETRIES constants. Unit tests assert time.sleep is called with delay >= _BACKOFF_BASE on 429 response. All 828 unit tests + 99 E2E tests passing at M003 close.
- Notes: 429 backoff behavior remains a continuity constraint and is explicitly re-verified in S01.

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
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: S01 fixed all three concurrency invariants: (1) semaphore released before time.sleep() backoff via _single_attempt() + explicit sem.acquire()/release() in _do_lookup(); (2) get_status() returns list() snapshot not live reference; (3) _cached_markers reads/writes protected by _lock. Three dedicated unit tests prove each invariant independently. All 944 tests passing.
- Notes: Semaphore/backoff/snapshot correctness is preserved and re-checked in S01 because that slice touches the runtime status seam.

### R019 — The `/enrichment/status/<job_id>` endpoint must accept a `?since=<index>` cursor and return only `results[since:]`. The frontend polling loop must use this cursor instead of the client-side `rendered` dedup map.
- Class: quality-attribute
- Status: validated
- Description: The `/enrichment/status/<job_id>` endpoint must accept a `?since=<index>` cursor and return only `results[since:]`. The frontend polling loop must use this cursor instead of the client-side `rendered` dedup map.
- Why it matters: Current implementation re-serializes and re-transmits the full accumulated results list on every 750ms tick. For a 50-IOC batch, the final ticks each transmit 50 results when only 1-2 are new — O(N²) total work and bandwidth.
- Source: execution (audit)
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: S02/T01: enrichment_status() reads ?since= param (default 0), returns results[since:] and next_since: len(results). enrichment.ts replaced rendered dedup map with since counter — polls with ?since=${since}, updates since=data.next_since. 4 new unit tests (since=2 returns slice, since=0 full, no param full, since=99 empty) + E2E mock includes next_since. 6/6 enrichment_status tests pass. grep -c 'rendered' enrichment.ts returns 0.
- Notes: Cursor-based polling remains primarily owned by S01 since the backend/frontend polling contract is the first milestone slice.

### R020 — Every adapter must store a `requests.Session` as `self._session` (created in `__init__`) and use it for all HTTP calls. No bare `requests.get()` or ephemeral per-call `requests.Session()`.
- Class: quality-attribute
- Status: validated
- Description: Every adapter must store a `requests.Session` as `self._session` (created in `__init__`) and use it for all HTTP calls. No bare `requests.get()` or ephemeral per-call `requests.Session()`.
- Why it matters: New TCP+TLS handshake on every `lookup()` call adds 50–150ms per provider per IOC. For a 20-IOC batch across 14 providers, this is 1–4 seconds of pure connection overhead per job.
- Source: execution (audit)
- Primary owning slice: M012/S01
- Supporting slices: none
- Validation: S02/T02: All 12 adapters have self._session = requests.Session() in __init__. 7 API-key adapters moved auth headers to session-level. grep -rn 'requests\.get\|requests\.post' adapters/*.py returns 0 code hits. grep -rl 'self._session' adapters/*.py returns 12. All 12 test files mock adapter._session directly. 839 unit tests pass.
- Notes: Persistent HTTP session continuity is preserved during runtime-boundary work in S01.

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
- Primary owning slice: M012/S04
- Supporting slices: M012/S01
- Validation: S02/T04: CacheStore.__init__ executes PRAGMA journal_mode=WAL (L51 of store.py) and keeps persistent self._conn. purge_expired(ttl_seconds) method exists at L155 and deletes entries older than TTL, returning row count. 34/34 cache+config tests pass. All 944 tests pass.
- Notes: WAL-mode cache behavior is intentionally left unchanged unless S04 evidence disproves the current design; S01 only protects continuity while touching the live boundary.

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
- Primary owning slice: M012/S03
- Supporting slices: M012/S01, M012/S02, M012/S04
- Validation: `Makefile` lines 82-95 define `verify-fast` (non-E2E pytest + Vitest + `npx tsc --noEmit` + `make build`), `verify-deep` (pytest `tests/e2e`), and composite `verify`. `README.md` documents when to use each lane. Fresh M012 closeout evidence on 2026-04-23: `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q` → `266 passed in 0.96s`; `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` → `73 passed in 1.75s`; `make verify-fast` → `955 passed, 113 deselected`, Vitest `78 passed`, clean `npx tsc --noEmit`, and successful production build with only the pre-existing non-blocking Browserslist warning.
- Notes: Existing test coverage remains the safety net; S03 owns the proof-loop/verification-lane work while all slices rely on targeted continuity checks.

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

### R050 — The ~20-line orchestrator creation block (ConfigStore, cache TTL, EnrichmentOrchestrator init, _orchestrators registration, _enrichment_pool.submit) is extracted into a single helper in _helpers.py. Both analysis.py and api.py call it.
- Class: quality-attribute
- Status: validated
- Description: The ~20-line orchestrator creation block (ConfigStore, cache TTL, EnrichmentOrchestrator init, _orchestrators registration, _enrichment_pool.submit) is extracted into a single helper in _helpers.py. Both analysis.py and api.py call it.
- Why it matters: Identical logic in two files means every change must be applied twice. Extraction eliminates this maintenance burden and prevents drift.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: _setup_orchestrator() in _helpers.py; zero inline EnrichmentOrchestrator( in analysis.py/api.py. 1061 tests pass.

### R051 — The enrichment polling logic exists identically in enrichment.py (HTML blueprint) and api.py (API blueprint). Consolidated to a single implementation.
- Class: quality-attribute
- Status: validated
- Description: The enrichment polling logic exists identically in enrichment.py (HTML blueprint) and api.py (API blueprint). Consolidated to a single implementation.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: _get_enrichment_status() in _helpers.py; enrichment.py and api.py delegate as one-liners. 1061 tests pass.

### R052 — Unused `json` import in api.py, unused `ResultDisplay` export in shared-rendering.ts, and any other dead imports/exports discovered during audit are removed.
- Class: quality-attribute
- Status: validated
- Description: Unused `json` import in api.py, unused `ResultDisplay` export in shared-rendering.ts, and any other dead imports/exports discovered during audit are removed.
- Source: execution
- Primary owning slice: M010/S01
- Supporting slices: none
- Validation: S01: No uuid/json/ConfigStore imports in cleaned modules; export keyword removed from ResultDisplay. make typecheck passes.

### R053 — The Recent Analyses collapsible section, its CSS (~130 lines), its JS toggle handler in ui.ts, and the list_recent() call in the index route are all removed from the home page.
- Class: core-capability
- Status: validated
- Description: The Recent Analyses collapsible section, its CSS (~130 lines), its JS toggle handler in ui.ts, and the list_recent() call in the index route are all removed from the home page.
- Source: user
- Primary owning slice: M010/S02
- Supporting slices: none
- Validation: S02: No 'Recent Analyses' in index.html; no list_recent call in analysis.py; no initRecentAnalysesToggle in ui.ts. GET / returns paste form only.

### R054 — A new /history route renders a page listing recent analyses. Each entry links to /history/<analysis_id> for the full detail view. Accessible from nav.
- Class: core-capability
- Status: validated
- Description: A new /history route renders a page listing recent analyses. Each entry links to /history/<analysis_id> for the full detail view. Accessible from nav.
- Source: user
- Primary owning slice: M010/S02
- Supporting slices: none
- Validation: S02: history_list() route in history.py; history.html template; clock nav icon in base.html; links to /history/<id> detail pages. GET /history returns 200.

### R055 — All 1060 tests pass after all refactoring. No user-visible behavior changes — same responses, same UI, same enrichment flow.
- Class: continuity
- Status: validated
- Description: All 1060 tests pass after all refactoring. No user-visible behavior changes — same responses, same UI, same enrichment flow.
- Source: inferred
- Primary owning slice: M010/all
- Supporting slices: none
- Validation: 1061 tests passed (up from 1060 baseline — 1 error-propagation test added, 0 removed). Zero behavior changes confirmed.

### R056 — Each adapter's module and class docstrings are reduced to a one-liner purpose sentence plus genuinely non-obvious gotchas. API endpoint URLs, HTTP status code tables, verdict priority lists, and parameter walkthroughs are removed — the code and tests prove those.
- Class: quality-attribute
- Status: validated
- Description: Each adapter's module and class docstrings are reduced to a one-liner purpose sentence plus genuinely non-obvious gotchas. API endpoint URLs, HTTP status code tables, verdict priority lists, and parameter walkthroughs are removed — the code and tests prove those.
- Why it matters: Adapter docstrings are 42% of adapter code (1,176 of 2,816 lines). Trimming to essentials makes files navigable and removes maintenance burden of keeping prose in sync with code.
- Source: user
- Primary owning slice: M011/S01
- Validation: 15 non-base adapter files trimmed to 1,597 lines (down from 2,659). One-liner module+class docstrings. Only _normalise_datetime retains a method docstring. All 1,012 tests pass unchanged.

### R057 — Per-adapter test files that assert individual fields (test_raw_stats_has_asn_key, test_raw_stats_asn_value, test_detection_count_always_zero, etc.) are consolidated into single response-shape tests that assert the full result object in one test.
- Class: quality-attribute
- Status: validated
- Description: Per-adapter test files that assert individual fields (test_raw_stats_has_asn_key, test_raw_stats_asn_value, test_detection_count_always_zero, etc.) are consolidated into single response-shape tests that assert the full result object in one test.
- Why it matters: ~72 granular one-assertion tests across 7 adapter test files produce ~400-600 lines of boilerplate. Consolidation reduces test count without losing coverage — the same assertions exist, just grouped.
- Source: user
- Primary owning slice: M011/S02
- Validation: 49 standalone per-field tests removed across 8 adapter test files + test_provider_protocol.py. Assertions folded into response-shape tests with descriptive messages. Net -431 lines. 899 unit tests pass.

### R058 — Cross-reference every CSS class in input.css against all templates (.html) and TypeScript files (.ts). Remove classes with zero references. Rebuild dist/style.css and verify visually.
- Class: quality-attribute
- Status: validated
- Description: Cross-reference every CSS class in input.css against all templates (.html) and TypeScript files (.ts). Remove classes with zero references. Rebuild dist/style.css and verify visually.
- Why it matters: 2,006 lines of CSS accumulated over 10 milestones. Dead rules bloat the stylesheet and confuse future editors.
- Source: user
- Primary owning slice: M011/S03
- Validation: CSS audit verified all 207 classes in input.css are referenced. 3 dynamic classes confirmed via string concatenation in row-factory.ts:336, row-factory.ts:309/416, cards.ts:60. Zero dead CSS found.

### R059 — The 7 orchestrator tests that use time.sleep-based timing (accounting for ~6.2s of 9s unit suite) are rewritten to use threading Events/barriers or tighter mocks so they complete in <1s total.
- Class: quality-attribute
- Status: validated
- Description: The 7 orchestrator tests that use time.sleep-based timing (accounting for ~6.2s of 9s unit suite) are rewritten to use threading Events/barriers or tighter mocks so they complete in <1s total.
- Why it matters: 6s of 9s unit test time comes from 7 tests. Faster tests mean faster feedback loops during development.
- Source: user
- Primary owning slice: M011/S03
- Validation: 7 orchestrator tests rewritten with threading.Barrier/Event primitives. Suite runs in 0.09s (target <1s, was 6.2s). 27 orchestrator tests pass.

### R060 — All tests pass after all refactoring. Test count may decrease from consolidation but zero coverage regression. No behavior changes.
- Class: continuity
- Status: validated
- Description: All tests pass after all refactoring. Test count may decrease from consolidation but zero coverage regression. No behavior changes.
- Why it matters: Refactoring must not break anything.
- Source: inferred
- Primary owning slice: M011/all
- Supporting slices: none
- Validation: unmapped
- Notes: Test count expected to decrease (granular tests consolidated). Coverage same or better.

### R061 — Runtime state does not block normal Git workflows.
- Class: continuity
- Status: validated
- Description: Runtime state does not block normal Git workflows.
- Why it matters: Local workflow hardening is not real if transient machine state can still wedge ordinary git operations like stash/pop.
- Source: user
- Primary owning slice: M014/S01
- Supporting slices: M014/S02, M014/S04
- Validation: Validated in M014/S01 by passing `make verify-runtime-boundary` after the verifier was narrowed to fail on blocker classes only. Focused temp-repo Git fixtures prove tracked transient `.gsd/audit/events.jsonl` conflicts are surfaced as `tracked-transient`, ignored/untracked `.gsd/state-manifest.json` and `.gsd/event-log.jsonl` no longer wedge checkout flows, and the live repo audit reports zero blocker-class findings.
- Notes: Covers the stash/pop conflict class caused by transient local state files participating in normal repo operations. The outcome must be behavioral, not just documented.

### R062 — Durable planning artifacts and transient machine state have an explicit repo boundary.
- Class: constraint
- Status: validated
- Description: Durable planning artifacts and transient machine state have an explicit repo boundary.
- Why it matters: Without a hard boundary between durable and transient state, recovery tooling becomes unsafe and git behavior stays unpredictable.
- Source: inferred
- Primary owning slice: M014/S01
- Supporting slices: M014/S02
- Validation: Validated in M014/S01 by the checked-in classifier/audit seam in `tools/runtime_state_boundary.py`, focused classifier+Git regression tests, and the supported `make verify-runtime-boundary` lane. The repo now distinguishes durable `.gsd/milestones/**` and canonical ledgers from transient `.gsd`/`.bg-shell` runtime state, while `.planning/**` remains explicit `manual-review` instead of being auto-cleaned.
- Notes: Durable milestone/context/summary artifacts stay protected; runtime/session debris is classified and managed separately.

### R063 — SentinelX has one supported local recovery entrypoint for runtime-state cleanup and repair.
- Class: operability
- Status: validated
- Description: SentinelX has one supported local recovery entrypoint for runtime-state cleanup and repair.
- Why it matters: Recovery should not depend on ad hoc git/process surgery spread across terminal history and background alerts.
- Source: user
- Primary owning slice: M014/S02
- Supporting slices: M014/S01, M014/S04
- Validation: Validated in M014/S02 by shipping `tools/runtime_state_repair.py` plus `make repair-runtime-state` as the single repo-native recovery entrypoint. Fresh proof on 2026-04-25: `python3 -m pytest -q tests/test_runtime_state_repair.py` (7 passed), `python3 -m pytest -q tests/test_runtime_state_repair_git.py` (3 passed), `make repair-runtime-state` (apply-mode no-op on live repo with 0 actionable repairs, 237 visible `.planning/**` manual-review findings, 0 failures), `make verify-runtime-boundary` (focused boundary/Git lanes green; live audit clean of tracked/unignored/conflicting/unknown blockers), and `python3 tools/runtime_state_repair.py --format json` (machine-readable repair summary/report contract).
- Notes: S02 validates the supported recovery entrypoint while intentionally leaving `.planning/**` as visible manual-review backlog rather than auto-cleaning it.

### R064 — SentinelX has one supported local dev-process path with cheap crash recovery.
- Class: operability
- Status: validated
- Description: SentinelX has one supported local dev-process path with cheap crash recovery.
- Why it matters: Local service ownership and restart behavior need a stable contract or the workflow remains fragile even after cleanup tooling exists.
- Source: user
- Primary owning slice: M014/S03
- Supporting slices: M014/S02, M014/S04
- Validation: M014/S03 slice verification passed on 2026-04-25: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` (36 passed), `make verify-runtime-boundary`, and `make verify-fast` all exited 0; live repo-native lifecycle proof also confirmed start → /api/health healthy → crash detection → restart recovery → stop using `tools/dev_server.py` / `make dev-server-stop`.
- Notes: A crashed local server should be detectable and restartable through the supported workflow without manual archaeology.

### R065 — Workflow hardening preserves existing SentinelX verification and app behavior.
- Class: continuity
- Status: validated
- Description: Workflow hardening preserves existing SentinelX verification and app behavior.
- Why it matters: A safer local workflow that regresses the actual product or its verification contract is not a net improvement.
- Source: inferred
- Primary owning slice: M014/S04
- Supporting slices: M014/S01, M014/S02, M014/S03
- Validation: Validated in M014/S04 on 2026-04-26. Fresh slice-close proof passed after the final seam state: `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` (57 passed), `make repair-runtime-state` (0 actionable repairs; `.planning/**` remained report-only/manual-review), `make verify-runtime-boundary` (blocker classes stayed at zero), live `tools/dev_server.py` start -> healthy -> forced crash -> crashed -> restart -> stop proof captured in `.gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json`, and `make verify` passed end to end (`1018` non-E2E pytest passes, `81` Vitest passes, clean TypeScript/build, `113` E2E passes).
- Notes: S04 re-proved that local workflow hardening preserved existing SentinelX verification and the supported app/dev-server behavior while closing the runtime-state seam.

### R069 — M014 ends with an explicit code review/refactor pass over the changed workflow seams.
- Class: quality-attribute
- Status: validated
- Description: M014 ends with an explicit code review/refactor pass over the changed workflow seams.
- Why it matters: Workflow hardening should close with cleanup and simplification, not just a pile of fixes that happen to pass once.
- Source: user
- Primary owning slice: M014/S04
- Supporting slices: M014/S01, M014/S02, M014/S03
- Validation: Validated in M014/S04 on 2026-04-26. `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` records an explicit seam-by-seam review of `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, focused tests, Make/docs, and the relevant ADRs. The review separated `refactor-now` from `leave-alone`, landed the minimal `app/health_contract.py` single-source refactor for `/api/health`, and explicitly preserved classifier-owned repair policy, report-only `.planning/**`, thin Make wrappers, and the single local dev-server lifecycle surface.
- Notes: The slice closed with both a durable review artifact and fresh closure proof rather than inherited summaries.

### R070 — The home page functions as a fast analyst intake workbench, with a dominant paste-and-submit command surface rather than a generic textarea-only page.
- Class: primary-user-loop
- Status: validated
- Description: The home page functions as a fast analyst intake workbench, with a dominant paste-and-submit command surface rather than a generic textarea-only page.
- Why it matters: The rest of SentinelX is mature, but the front door still feels thin compared with the results/detail surfaces.
- Source: user
- Primary owning slice: M015/S01
- Supporting slices: M015/S04
- Validation: M015/S04 final integrated proof validated the home page as a fast analyst intake workbench: route contract passed 27 checks, focused Playwright assembly passed 34 tests, `make verify-fast` passed 1026 pytest + 87 Vitest + TypeScript + build, and full E2E passed 125 tests. Proof covers stable paste form, clarified mode state, submit enablement, secondary Recent Analyses rail, no preview surfaces, and fail-open history behavior.
- Notes: The user emphasized "go fast"; this must remain a command surface, not a dashboard.

### R071 — The primary paste-to-results flow remains unchanged: paste IOC text, choose Offline or Online mode, click Extract, and reach the existing results flow.
- Class: continuity
- Status: validated
- Description: The primary paste-to-results flow remains unchanged: paste IOC text, choose Offline or Online mode, click Extract, and reach the existing results flow.
- Why it matters: A redesign that slows or changes the core analyst loop would violate the user's fast-intake direction.
- Source: user
- Primary owning slice: M015/S01
- Supporting slices: M015/S02, M015/S04
- Validation: M015/S04 re-proved the primary paste → default Offline mode → Extract → results flow in the final assembled command-card plus recent-rail layout. Fresh verification passed the focused homepage/UI/offline lane (34 tests), `make verify-fast`, and full Playwright E2E (125 tests), including an assertion that Offline extraction reaches `.page-results` without enrichment polling.
- Notes: No pre-submit extraction preview or extra staging step should be inserted.

### R072 — Offline and Online mode choice is clearer visually and textually while preserving the existing hidden `mode` form contract and submit behavior.
- Class: quality-attribute
- Status: validated
- Description: Offline and Online mode choice is clearer visually and textually while preserving the existing hidden `mode` form contract and submit behavior.
- Why it matters: Analysts should not second-guess mode selection, but the stable form semantics are already tested and should not churn unnecessarily.
- Source: user
- Primary owning slice: M015/S02
- Supporting slices: M015/S04
- Validation: M015/S02 delivered and verified the clarified Offline/Online mode UI while preserving hidden `#mode-input name="mode"` submit semantics: `python3 -m pytest -q tests/test_index_intake_contract.py ...` passed 4 contract/route checks, `npx vitest run app/static/src/ts/modules/form.test.ts` passed 6 form-module tests, `npx tsc --noEmit` exited 0, `make build` regenerated assets successfully, and focused Playwright checks passed 16/16 across mode UI controls, default offline behavior, offline extraction, and online mode indication.
- Notes: Clarify the current toggle; do not replace it with a different workflow unless implementation proves the current control cannot meet accessibility or clarity needs.

### R073 — A compact Recent Analyses list appears on the intake page when history exists, remains visually secondary to the paste command card, and links to `/history/<id>` reload routes.
- Class: primary-user-loop
- Status: validated
- Description: A compact Recent Analyses list appears on the intake page when history exists, remains visually secondary to the paste command card, and links to `/history/<id>` reload routes.
- Why it matters: Recent work should be easy to resume from the start page without turning the home page into a dashboard.
- Source: user
- Primary owning slice: M015/S03
- Supporting slices: M015/S04
- Validation: M015/S03 delivered the compact server-rendered Recent Analyses rail on `/`: GET `/` performs one bounded `HistoryStore.list_recent(limit=4)` read, renders linked `.recent-analysis-row` entries with `url_for('main.history_detail', analysis_id=...)`, keeps the rail visually secondary on desktop and stacked below the command card on mobile, and passed fresh slice proof (`make build`, `npx tsc --noEmit`, route/history/security tests: 18 passed, and focused E2E homepage/extraction tests: 22 passed).
- Notes: Use the existing server-rendered HistoryStore.list_recent(limit) path; no new API or live-refresh endpoint is planned.

### R074 — History listing failures never block the intake page; the paste form still renders and works, with a quiet degraded recent-history state or omission.
- Class: failure-visibility
- Status: validated
- Description: History listing failures never block the intake page; the paste form still renders and works, with a quiet degraded recent-history state or omission.
- Why it matters: History is secondary; the fast paste-and-extract path must stay available even if history storage is unavailable.
- Source: user
- Primary owning slice: M015/S03
- Supporting slices: M015/S04
- Validation: M015/S03 proved history listing is fail-open: route tests cover `list_recent` exceptions with sanitized warning logging, preserved status 200, preserved CSRF and stable paste form selectors, quiet unavailable state, and offline no-HTTP behavior; browser tests cover empty/unavailable states with form visibility and submit enablement. Fresh slice verification passed (`make build`, `npx tsc --noEmit`, route/history/security tests: 18 passed, focused E2E homepage/extraction tests: 22 passed).
- Notes: No retry loop, async recovery UI, or blocking alert for history failures in M015.

### R075 — The intake page uses a command-card plus compact recent rail layout that works on desktop and stacks cleanly on mobile.
- Class: quality-attribute
- Status: validated
- Description: The intake page uses a command-card plus compact recent rail layout that works on desktop and stacks cleanly on mobile.
- Why it matters: The layout must support the fast-intake mental model across common viewport sizes.
- Source: inferred
- Primary owning slice: M015/S01
- Supporting slices: M015/S03, M015/S04
- Validation: M015/S04 validated desktop and mobile command-card plus compact recent rail behavior. Playwright assertions prove the command card remains visually dominant on desktop, the populated recent rail stays secondary, mobile stacks the rail below the command card, and the page has no horizontal overflow at 390px; all focused and full browser lanes passed.
- Notes: Desktop should keep recent history as a secondary rail; mobile should stack without hiding the primary form.

### R076 — Existing extraction, enrichment, history reload, CSRF/security headers, TypeScript build, and E2E behavior remain intact after the intake redesign.
- Class: continuity
- Status: validated
- Description: Existing extraction, enrichment, history reload, CSRF/security headers, TypeScript build, and E2E behavior remain intact after the intake redesign.
- Why it matters: This is a front-door redesign, not a behavior rewrite; current SentinelX capabilities must not regress.
- Source: inferred
- Primary owning slice: M015/S04
- Supporting slices: M015/S01, M015/S02, M015/S03
- Validation: M015/S04 final regression proof passed after the intake redesign: route/security/history command passed 27 tests, focused browser assembly passed 34 tests, `make verify-fast` passed 1026 non-E2E pytest tests, 87 Vitest tests, TypeScript, and generated asset build, and the full E2E suite passed 125 tests. Fresh milestone-close verification re-ran `make verify-fast` successfully with 1026 pytest + 87 Vitest + TypeScript + build. Coverage preserved extraction, offline no-HTTP behavior, online no-provider guard, history reload/resume, CSRF/security headers, TypeScript/build, generated assets, and E2E behavior.
- Notes: Final proof should include focused backend tests, relevant E2E tests, make verify-fast, and full make verify.

### R083 — Analysts and maintainers can export a robust diagnostic log bundle for a recent analysis or runtime session, with secrets redacted and enough context to debug provider, polling, rendering, and settings failures.
- Class: operability
- Status: validated
- Description: Analysts and maintainers can export a robust diagnostic log bundle for a recent analysis or runtime session, with secrets redacted and enough context to debug provider, polling, rendering, and settings failures.
- Why it matters: Current enrichment/debug failures depend on scattered server logs, browser assertions, and test artifacts. A safe export bundle will make support and future agent debugging faster without exposing provider credentials.
- Source: user-request-2026-05-10
- Primary owning slice: TBD
- Validation: M018 delivered the diagnostic export contract, bounded/redacted assembler, Flask download route, deterministic E2E proof, and analyst guide. Fresh closeout verification for S04 ran `python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'` (3 passed), guide existence/section-count check (`GUIDE PASS`), and the full diagnostic export suite across primitives, contract, sources, assembler, integration, route, and E2E proof files (`39 passed`; `FULL DIAGNOSTIC SUITE PASS`). The proof downloads the ZIP through `/diagnostics/export`, validates manifest/archive consistency, verifies raw ZIP bytes exclude configured secret values, and checks download headers.
- Notes: Validated by M018/S04 final-assembly proof and all-slice diagnostic export regression suite. Exports are local-first, bounded, deterministic, manifest-backed, redacted, and documented for safe sharing.

## Deferred

### R066 — Automatic self-healing of transient runtime state at session start is deferred.
- Class: operability
- Status: deferred
- Description: Automatic self-healing of transient runtime state at session start is deferred.
- Why it matters: Auto-healing is attractive, but it becomes dangerous if the durable/runtime boundary is not proven first.
- Source: inferred
- Supporting slices: none
- Validation: unmapped
- Notes: Useful later, but M014 should first make cleanup rules explicit and trustworthy before making them implicit and automatic.

### R067 — Upstream GSD engine changes outside this repo to relocate or redesign runtime-state ownership are deferred.
- Class: constraint
- Status: deferred
- Description: Upstream GSD engine changes outside this repo to relocate or redesign runtime-state ownership are deferred.
- Why it matters: Repo-local hardening is lower-regret and directly shippable here; upstream engine work can follow later if still justified.
- Source: inferred
- Supporting slices: none
- Validation: unmapped
- Notes: M014 should solve the problem at the repo boundary first rather than assuming immediate changes to tooling outside the SentinelX repository.

### R077 — Pre-submit extraction preview is intentionally deferred; M015 should not show detected IOCs before the analyst clicks Extract.
- Class: deferred
- Status: deferred
- Description: Pre-submit extraction preview is intentionally deferred; M015 should not show detected IOCs before the analyst clicks Extract.
- Why it matters: Preview could be useful later, but it would add staging and complexity that conflicts with this milestone's go-fast direction.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: The user explicitly said preview stays out of scope to preserve a fast flow.

### R078 — Email/phishing enrichment depth is deferred from M015.
- Class: deferred
- Status: deferred
- Description: Email/phishing enrichment depth is deferred from M015.
- Why it matters: It is a meaningful analyst feature, but it would expand M015 from intake UX into provider strategy and external-service decisions.
- Source: prior scope
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Email IOCs are already display-capable; provider/API choices for email reputation belong in a separate milestone.

### R079 — API/automation polish is deferred from M015.
- Class: deferred
- Status: deferred
- Description: API/automation polish is deferred from M015.
- Why it matters: Programmatic workflows are a separate design target from the fast analyst browser intake experience.
- Source: prior scope
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: The REST API exists, but M015 is browser intake work, not script automation.

### R090 — Broad future optimization program beyond the best M017 target is deferred.
- Class: constraint
- Status: deferred
- Description: Broad future optimization program beyond the best M017 target is deferred.
- Why it matters: Keeps M017 focused on clarity plus the best current optimization while preserving future opportunities.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: M017 should leave ranked follow-ups, not attempt every possible optimization now.

### R091 — Major product redesign or new analyst-facing feature expansion is deferred from M017.
- Class: constraint
- Status: deferred
- Description: Major product redesign or new analyst-facing feature expansion is deferred from M017.
- Why it matters: The user asked to understand and optimize the existing project, not change its product category.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: The milestone may improve clarity and performance of existing surfaces but should not add unrelated product scope.

## Out of Scope

### R068 — M014 does not add a new analyst-facing SentinelX product capability.
- Class: anti-feature
- Status: out-of-scope
- Description: M014 does not add a new analyst-facing SentinelX product capability.
- Why it matters: This prevents scope confusion and keeps the milestone focused on reliability of the developer/operator loop.
- Source: user
- Supporting slices: none
- Validation: n/a
- Notes: This milestone is reserved for local workflow hardening and recovery, not feature expansion for analysts.

### R080 — M015 must not turn the home page into a heavy dashboard.
- Class: anti-feature
- Status: out-of-scope
- Description: M015 must not turn the home page into a heavy dashboard.
- Why it matters: A dashboard would dilute the paste-and-go primary action and conflict with the desired fast analyst workbench feel.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: The user chose go-fast intake and compact history, not equal-weight status/history panels.

### R081 — M015 must not change provider or enrichment behavior as part of the intake redesign.
- Class: anti-feature
- Status: out-of-scope
- Description: M015 must not change provider or enrichment behavior as part of the intake redesign.
- Why it matters: Changing enrichment behavior would increase risk and move the milestone away from front-door UX.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Small support changes for server-rendered history are allowed; enrichment semantics are not.

### R082 — M015 does not redesign the results or detail pages beyond necessary integration consistency with the intake page.
- Class: anti-feature
- Status: out-of-scope
- Description: M015 does not redesign the results or detail pages beyond necessary integration consistency with the intake page.
- Why it matters: This prevents a scoped intake milestone from becoming a broad visual redesign.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Results/detail surfaces are already mature; M015 focuses on the start page.

### R092 — Optimization theater: speculative rewrites without project-identity grounding or proof are out of scope.
- Class: anti-feature
- Status: out-of-scope
- Description: Optimization theater: speculative rewrites without project-identity grounding or proof are out of scope.
- Why it matters: This prevents aggressive optimization from becoming churn that makes the project less understandable.
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Changes must tie back to project map, audit evidence, and verification.

### R093 — Speed changes that hide failures, remove diagnostics, leak secrets, or weaken security boundaries are out of scope.
- Class: constraint
- Status: out-of-scope
- Description: Speed changes that hide failures, remove diagnostics, leak secrets, or weaken security boundaries are out of scope.
- Why it matters: A local security triage app must remain trustworthy and diagnosable even when made faster.
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Optimization must preserve or improve error visibility and security posture.

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
| R008 | continuity | validated | M012/S01 | M012/S02 | S04 T01 produced 18-point wiring verification matrix (file:line evidence). allResults[] accumulation → export.ts via closure confirmed; filter.ts binds .verdict-kpi-card[data-verdict]; doSortCards() reads #ioc-cards-grid → .ioc-card[data-verdict]; #enrich-progress-fill/#enrich-progress-text/#enrich-warning present in results.html; .copy-btn[data-value] in _ioc_card.html; injectDetailLink() called from markEnrichmentComplete() with idempotency guard. 91/91 E2E at S04 close; 99/99 at S05 close. |
| R009 | compliance/security | validated | M012/S01 | M012/S02, M012/S03, M012/S04 | S04 T02 six grep-based audit checks confirm zero violations. CSP header at app/__init__.py:71 (script-src 'self'). CSRFProtect initialized and csrf.init_app(app) called; <meta name="csrf-token"> in base.html. innerHTML occurrences are JSDoc comment lines only. document.write/eval() return zero matches (grep exit 1). row-factory.ts and enrichment.ts use createElement/createElementNS + textContent + setAttribute throughout. |
| R010 | quality-attribute | validated | M012/S01 | M012/S02 | S04 T03 production bundle 27,226 bytes (≤ 30KB gate). 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts. |
| R011 | quality-attribute | validated | M002/S05 | none | python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed (up from 91 baseline). ResultsPage page object expanded from 118 to 266 lines. 8 new tests added. No tests removed. |
| R012 | quality-attribute | validated | M003/S03 | none | S03 applied M002 design tokens to ioc_detail.html: stacked .detail-provider-card layout with --bg-secondary surfaces, --border dividers, --text-primary/--text-secondary typography, --font-mono for IOC code, verdict-badge--{verdict} as only color class. Inline <style> block removed. Graph labels untruncated (routes.py and graph.ts [:N] slices removed). 13 tests pass: test_detail_page_with_results asserts detail-provider-card, verdict-badge--malicious, and absence of <style>; test_detail_graph_labels_untruncated asserts "Shodan InternetDB" appears verbatim in data-graph-nodes. |
| R013 | quality-attribute | validated | M015/S01 | M015/S02, M015/S03, M015/S04 | M015/S01 delivered and verified the redesigned index command-card DOM/CSS foundation: `python3 -m pytest -q tests/test_index_intake_contract.py ...` passed 6 route/contract checks, `make build` passed, `npx tsc --noEmit` passed, and `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` passed 18 Playwright tests proving the visible command-card intake surface and offline paste-to-results path. |
| R014 | quality-attribute | validated | M012/S01 | none | S01 added per-provider semaphore dict in orchestrator._do_lookup(): VT gets Semaphore(4), zero-auth providers get Semaphore(8). Unit tests in tests/test_orchestrator.py assert VT calls are capped at 4 concurrent while zero-auth providers run freely. All 828 unit tests + 99 E2E tests passing at M003 close. |
| R015 | quality-attribute | validated | M012/S01 | none | S01 added 429-aware backoff retry in orchestrator._do_lookup_inner(): exponential backoff with jitter using _BACKOFF_BASE and _MAX_RATE_LIMIT_RETRIES constants. Unit tests assert time.sleep is called with delay >= _BACKOFF_BASE on 429 response. All 828 unit tests + 99 E2E tests passing at M003 close. |
| R016 | core-capability | validated | M003/S02 | none | S02 added IOCType.EMAIL to models.py, email regex classifier in classifier.py at precedence position 8 (before Domain), OTX adapter explicit frozenset excluding EMAIL. CSS badge (.ioc-type-badge--email) in input.css and dist/style.css. Filter pill (.filter-pill--email.filter-pill--active) in both CSS files. 6 E2E tests added to test_results_page.py confirming: email cards render, EMAIL filter pill appears, filtering shows only email cards, active state works, All Types resets, badge is visible. 105/105 E2E passing, 828/828 unit tests passing. Fully-defanged form user[@]evil[.]com is a known limitation (iocsearcher doesn't extract it; domain is extracted instead). |
| R017 | quality-attribute | validated | M003/S04 | none | S04 applied summaryTimers debounce map in enrichment.ts: declaration + debouncedUpdateSummaryRow() wrapper + replaced direct updateSummaryRow() call. grep -c 'summaryTimers' enrichment.ts → 4. make typecheck → exit 0. bundle 26,783 bytes ≤ 30KB. 828 unit tests + 99 E2E tests all passing. |
| R018 | quality-attribute | validated | M012/S01 | none | S01 fixed all three concurrency invariants: (1) semaphore released before time.sleep() backoff via _single_attempt() + explicit sem.acquire()/release() in _do_lookup(); (2) get_status() returns list() snapshot not live reference; (3) _cached_markers reads/writes protected by _lock. Three dedicated unit tests prove each invariant independently. All 944 tests passing. |
| R019 | quality-attribute | validated | M012/S01 | none | S02/T01: enrichment_status() reads ?since= param (default 0), returns results[since:] and next_since: len(results). enrichment.ts replaced rendered dedup map with since counter — polls with ?since=${since}, updates since=data.next_since. 4 new unit tests (since=2 returns slice, since=0 full, no param full, since=99 empty) + E2E mock includes next_since. 6/6 enrichment_status tests pass. grep -c 'rendered' enrichment.ts returns 0. |
| R020 | quality-attribute | validated | M012/S01 | none | S02/T02: All 12 adapters have self._session = requests.Session() in __init__. 7 API-key adapters moved auth headers to session-level. grep -rn 'requests\.get\|requests\.post' adapters/*.py returns 0 code hits. grep -rl 'self._session' adapters/*.py returns 12. All 12 test files mock adapter._session directly. 839 unit tests pass. |
| R021 | compliance/security | validated | M004/S02 | none | S02/T03: ip_api.py rewritten for https://ipinfo.io/{ip}/json. IPINFO_BASE uses https://. grep 'http://' ip_api.py returns 0. ALLOWED_API_HOSTS: ipinfo.io added, ip-api.com removed. 404-based private IP handling. _parse_response() maps ipinfo.io fields (country→country_code, org→ASN+ISP, hostname→reverse). 50/50 test_ip_api.py tests pass with ipinfo.io fixtures. |
| R022 | quality-attribute | validated | M012/S04 | M012/S01 | S02/T04: CacheStore.__init__ executes PRAGMA journal_mode=WAL (L51 of store.py) and keeps persistent self._conn. purge_expired(ttl_seconds) method exists at L155 and deletes entries older than TTL, returning row count. 34/34 cache+config tests pass. All 944 tests pass. |
| R023 | quality-attribute | validated | M004/S03 | none | S03 applied all 5 R023 patterns: (1) findCopyButtonForIoc() uses querySelector attribute selector with CSS.escape() — grep confirms no querySelectorAll copy-btn. (2) updateDashboardCounts() + sortCardsBySeverity() moved outside per-result loop, called once per poll tick guarded by results.length > 0. (3) applyFilter() debounced at 100ms on search input with clearTimeout/setTimeout pattern — click handlers remain synchronous. (4) verdictSeverityIndex() uses SEVERITY_MAP (ReadonlyMap built at module load) — no indexOf in ioc.ts. (5) graph.ts builds nodeIndexMap before edge loop, replaces .find()/.indexOf() with Map.get(). npx tsc --noEmit clean. 105 E2E tests pass. 944 total tests pass. |
| R024 | quality-attribute | validated | M004/S04 | none | S04/T02: `tsconfig.json` has `"incremental": true` in compilerOptions — confirmed via grep. `tailwind.config.js` safelist includes `ioc-type-badge--email` and `filter-pill--email` — confirmed via grep. `npx tsc --noEmit` exits 0 (clean). 944 tests pass. |
| R025 | compliance/security | validated | M004/S04 | none | S04/T03: CSP header expanded to 7 directives (default-src, script-src, style-src, connect-src, img-src, font-src, object-src 'none') — confirmed via grep and live HTTP response test. SECRET_KEY startup warning implemented — confirmed fires at WARNING level when env var unset, silent when set. Rate limiter exception: kept as memory:// because the `limits` library has no filesystem backend (only Redis/Memcached/MongoDB); adding external services inappropriate for single-process local tool (D037/D038). 944 tests pass. |
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
| R040 | continuity | validated | M012/S03 | M012/S01, M012/S02, M012/S04 | `Makefile` lines 82-95 define `verify-fast` (non-E2E pytest + Vitest + `npx tsc --noEmit` + `make build`), `verify-deep` (pytest `tests/e2e`), and composite `verify`. `README.md` documents when to use each lane. Fresh M012 closeout evidence on 2026-04-23: `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q` → `266 passed in 0.96s`; `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` → `73 passed in 1.75s`; `make verify-fast` → `955 passed, 113 deselected`, Vitest `78 passed`, clean `npx tsc --noEmit`, and successful production build with only the pre-existing non-blocking Browserslist warning. |
| R041 | quality-attribute | validated | M009/S01 | M009/S02 | BaseHTTPAdapter exists in app/enrichment/adapters/base.py with full template-method skeleton. 12 HTTP adapters subclass it. 21 base class tests + 947 full suite tests pass. Verified by grep: 13 files contain 'class.*BaseHTTPAdapter' (12 adapters + 1 base definition). |
| R042 | quality-attribute | validated | M009/S02 | M009/S01 | All 12 HTTP adapters (abuseipdb, crtsh, greynoise, hashlookup, ip_api, malwarebazaar, otx, shodan, threatfox, threatminer, urlhaus, virustotal) subclass BaseHTTPAdapter. Verified by grep: 12 non-base adapter files contain 'class.*BaseHTTPAdapter'. 983 tests pass. |
| R043 | constraint | validated | M009/S02 | none | grep -c 'BaseHTTPAdapter' on dns_lookup.py, asn_cymru.py, whois_lookup.py all return 0. These three non-HTTP adapters remain standalone implementations. |
| R044 | quality-attribute | validated | M009/S03 | none | 172 parametrized tests in test_adapter_contract.py cover all 15 adapters across 12 contract dimensions. All pass. |
| R045 | quality-attribute | validated | M009/S03 | none | All 15 per-adapter test files contain only verdict/parsing/provider-specific tests. 208 contract tests removed, zero contract patterns remain. |
| R046 | quality-attribute | validated | M009/S04 | none | CSS audit sampled 10/10 selectors — all referenced. No dead CSS found. |
| R047 | quality-attribute | validated | M009/S04 | none | 4 functions extracted to shared-rendering.ts; zero private copies remain in enrichment.ts/history.ts; 84-line net reduction; make typecheck && make js pass. |
| R048 | continuity | validated | M009/all | none | 947 tests pass, 0 failures. Count decreased from 1,075 to 947 only from consolidation (208 duplicates removed, 172 parametrized replacements added). Zero behavior changes — same verdicts, same HTTP calls, same error handling. |
| R049 | quality-attribute | validated | M009/all | none | Net -1,143 LOC across 38 files (1,669 added, 2,812 deleted). Reduction in both app/ (adapter consolidation -112 LOC, TS dedup -84 LOC) and tests/ (contract test consolidation, bulk of remaining reduction). |
| R050 | quality-attribute | validated | M010/S01 | none | S01: _setup_orchestrator() in _helpers.py; zero inline EnrichmentOrchestrator( in analysis.py/api.py. 1061 tests pass. |
| R051 | quality-attribute | validated | M010/S01 | none | S01: _get_enrichment_status() in _helpers.py; enrichment.py and api.py delegate as one-liners. 1061 tests pass. |
| R052 | quality-attribute | validated | M010/S01 | none | S01: No uuid/json/ConfigStore imports in cleaned modules; export keyword removed from ResultDisplay. make typecheck passes. |
| R053 | core-capability | validated | M010/S02 | none | S02: No 'Recent Analyses' in index.html; no list_recent call in analysis.py; no initRecentAnalysesToggle in ui.ts. GET / returns paste form only. |
| R054 | core-capability | validated | M010/S02 | none | S02: history_list() route in history.py; history.html template; clock nav icon in base.html; links to /history/<id> detail pages. GET /history returns 200. |
| R055 | continuity | validated | M010/all | none | 1061 tests passed (up from 1060 baseline — 1 error-propagation test added, 0 removed). Zero behavior changes confirmed. |
| R056 | quality-attribute | validated | M011/S01 | none | 15 non-base adapter files trimmed to 1,597 lines (down from 2,659). One-liner module+class docstrings. Only _normalise_datetime retains a method docstring. All 1,012 tests pass unchanged. |
| R057 | quality-attribute | validated | M011/S02 | none | 49 standalone per-field tests removed across 8 adapter test files + test_provider_protocol.py. Assertions folded into response-shape tests with descriptive messages. Net -431 lines. 899 unit tests pass. |
| R058 | quality-attribute | validated | M011/S03 | none | CSS audit verified all 207 classes in input.css are referenced. 3 dynamic classes confirmed via string concatenation in row-factory.ts:336, row-factory.ts:309/416, cards.ts:60. Zero dead CSS found. |
| R059 | quality-attribute | validated | M011/S03 | none | 7 orchestrator tests rewritten with threading.Barrier/Event primitives. Suite runs in 0.09s (target <1s, was 6.2s). 27 orchestrator tests pass. |
| R060 | continuity | validated | M011/all | none | unmapped |
| R061 | continuity | validated | M014/S01 | M014/S02, M014/S04 | Validated in M014/S01 by passing `make verify-runtime-boundary` after the verifier was narrowed to fail on blocker classes only. Focused temp-repo Git fixtures prove tracked transient `.gsd/audit/events.jsonl` conflicts are surfaced as `tracked-transient`, ignored/untracked `.gsd/state-manifest.json` and `.gsd/event-log.jsonl` no longer wedge checkout flows, and the live repo audit reports zero blocker-class findings. |
| R062 | constraint | validated | M014/S01 | M014/S02 | Validated in M014/S01 by the checked-in classifier/audit seam in `tools/runtime_state_boundary.py`, focused classifier+Git regression tests, and the supported `make verify-runtime-boundary` lane. The repo now distinguishes durable `.gsd/milestones/**` and canonical ledgers from transient `.gsd`/`.bg-shell` runtime state, while `.planning/**` remains explicit `manual-review` instead of being auto-cleaned. |
| R063 | operability | validated | M014/S02 | M014/S01, M014/S04 | Validated in M014/S02 by shipping `tools/runtime_state_repair.py` plus `make repair-runtime-state` as the single repo-native recovery entrypoint. Fresh proof on 2026-04-25: `python3 -m pytest -q tests/test_runtime_state_repair.py` (7 passed), `python3 -m pytest -q tests/test_runtime_state_repair_git.py` (3 passed), `make repair-runtime-state` (apply-mode no-op on live repo with 0 actionable repairs, 237 visible `.planning/**` manual-review findings, 0 failures), `make verify-runtime-boundary` (focused boundary/Git lanes green; live audit clean of tracked/unignored/conflicting/unknown blockers), and `python3 tools/runtime_state_repair.py --format json` (machine-readable repair summary/report contract). |
| R064 | operability | validated | M014/S03 | M014/S02, M014/S04 | M014/S03 slice verification passed on 2026-04-25: `python3 -m pytest -q tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` (36 passed), `make verify-runtime-boundary`, and `make verify-fast` all exited 0; live repo-native lifecycle proof also confirmed start → /api/health healthy → crash detection → restart recovery → stop using `tools/dev_server.py` / `make dev-server-stop`. |
| R065 | continuity | validated | M014/S04 | M014/S01, M014/S02, M014/S03 | Validated in M014/S04 on 2026-04-26. Fresh slice-close proof passed after the final seam state: `python3 -m pytest -q tests/test_runtime_state_boundary.py tests/test_runtime_state_boundary_git.py tests/test_runtime_state_repair.py tests/test_runtime_state_repair_git.py tests/test_api.py tests/test_dev_server.py tests/test_dev_server_process.py` (57 passed), `make repair-runtime-state` (0 actionable repairs; `.planning/**` remained report-only/manual-review), `make verify-runtime-boundary` (blocker classes stayed at zero), live `tools/dev_server.py` start -> healthy -> forced crash -> crashed -> restart -> stop proof captured in `.gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json`, and `make verify` passed end to end (`1018` non-E2E pytest passes, `81` Vitest passes, clean TypeScript/build, `113` E2E passes). |
| R066 | operability | deferred | none | none | unmapped |
| R067 | constraint | deferred | none | none | unmapped |
| R068 | anti-feature | out-of-scope | none | none | n/a |
| R069 | quality-attribute | validated | M014/S04 | M014/S01, M014/S02, M014/S03 | Validated in M014/S04 on 2026-04-26. `.gsd/milestones/M014/slices/S04/S04-REVIEW.md` records an explicit seam-by-seam review of `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, focused tests, Make/docs, and the relevant ADRs. The review separated `refactor-now` from `leave-alone`, landed the minimal `app/health_contract.py` single-source refactor for `/api/health`, and explicitly preserved classifier-owned repair policy, report-only `.planning/**`, thin Make wrappers, and the single local dev-server lifecycle surface. |
| R070 | primary-user-loop | validated | M015/S01 | M015/S04 | M015/S04 final integrated proof validated the home page as a fast analyst intake workbench: route contract passed 27 checks, focused Playwright assembly passed 34 tests, `make verify-fast` passed 1026 pytest + 87 Vitest + TypeScript + build, and full E2E passed 125 tests. Proof covers stable paste form, clarified mode state, submit enablement, secondary Recent Analyses rail, no preview surfaces, and fail-open history behavior. |
| R071 | continuity | validated | M015/S01 | M015/S02, M015/S04 | M015/S04 re-proved the primary paste → default Offline mode → Extract → results flow in the final assembled command-card plus recent-rail layout. Fresh verification passed the focused homepage/UI/offline lane (34 tests), `make verify-fast`, and full Playwright E2E (125 tests), including an assertion that Offline extraction reaches `.page-results` without enrichment polling. |
| R072 | quality-attribute | validated | M015/S02 | M015/S04 | M015/S02 delivered and verified the clarified Offline/Online mode UI while preserving hidden `#mode-input name="mode"` submit semantics: `python3 -m pytest -q tests/test_index_intake_contract.py ...` passed 4 contract/route checks, `npx vitest run app/static/src/ts/modules/form.test.ts` passed 6 form-module tests, `npx tsc --noEmit` exited 0, `make build` regenerated assets successfully, and focused Playwright checks passed 16/16 across mode UI controls, default offline behavior, offline extraction, and online mode indication. |
| R073 | primary-user-loop | validated | M015/S03 | M015/S04 | M015/S03 delivered the compact server-rendered Recent Analyses rail on `/`: GET `/` performs one bounded `HistoryStore.list_recent(limit=4)` read, renders linked `.recent-analysis-row` entries with `url_for('main.history_detail', analysis_id=...)`, keeps the rail visually secondary on desktop and stacked below the command card on mobile, and passed fresh slice proof (`make build`, `npx tsc --noEmit`, route/history/security tests: 18 passed, and focused E2E homepage/extraction tests: 22 passed). |
| R074 | failure-visibility | validated | M015/S03 | M015/S04 | M015/S03 proved history listing is fail-open: route tests cover `list_recent` exceptions with sanitized warning logging, preserved status 200, preserved CSRF and stable paste form selectors, quiet unavailable state, and offline no-HTTP behavior; browser tests cover empty/unavailable states with form visibility and submit enablement. Fresh slice verification passed (`make build`, `npx tsc --noEmit`, route/history/security tests: 18 passed, focused E2E homepage/extraction tests: 22 passed). |
| R075 | quality-attribute | validated | M015/S01 | M015/S03, M015/S04 | M015/S04 validated desktop and mobile command-card plus compact recent rail behavior. Playwright assertions prove the command card remains visually dominant on desktop, the populated recent rail stays secondary, mobile stacks the rail below the command card, and the page has no horizontal overflow at 390px; all focused and full browser lanes passed. |
| R076 | continuity | validated | M015/S04 | M015/S01, M015/S02, M015/S03 | M015/S04 final regression proof passed after the intake redesign: route/security/history command passed 27 tests, focused browser assembly passed 34 tests, `make verify-fast` passed 1026 non-E2E pytest tests, 87 Vitest tests, TypeScript, and generated asset build, and the full E2E suite passed 125 tests. Fresh milestone-close verification re-ran `make verify-fast` successfully with 1026 pytest + 87 Vitest + TypeScript + build. Coverage preserved extraction, offline no-HTTP behavior, online no-provider guard, history reload/resume, CSRF/security headers, TypeScript/build, generated assets, and E2E behavior. |
| R077 | deferred | deferred | none | none | unmapped |
| R078 | deferred | deferred | none | none | unmapped |
| R079 | deferred | deferred | none | none | unmapped |
| R080 | anti-feature | out-of-scope | none | none | n/a |
| R081 | anti-feature | out-of-scope | none | none | n/a |
| R082 | anti-feature | out-of-scope | none | none | n/a |
| R083 | operability | validated | TBD | none | M018 delivered the diagnostic export contract, bounded/redacted assembler, Flask download route, deterministic E2E proof, and analyst guide. Fresh closeout verification for S04 ran `python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'` (3 passed), guide existence/section-count check (`GUIDE PASS`), and the full diagnostic export suite across primitives, contract, sources, assembler, integration, route, and E2E proof files (`39 passed`; `FULL DIAGNOSTIC SUITE PASS`). The proof downloads the ZIP through `/diagnostics/export`, validates manifest/archive consistency, verifies raw ZIP bytes exclude configured secret values, and checks download headers. |
| R084 | core-capability | active | M017/S01 | M017/S02, M017/S05 | mapped |
| R085 | quality-attribute | active | M017/S02 | M017/S03, M017/S04 | mapped |
| R086 | core-capability | active | M017/S03 | M017/S04 | mapped |
| R087 | quality-attribute | active | M017/S02 | M017/S03, M017/S04, M017/S05 | mapped |
| R088 | continuity | active | M017/S03 | M017/S04, M017/S05 | mapped |
| R089 | operability | active | M017/S05 | none | mapped |
| R090 | constraint | deferred | none | none | unmapped |
| R091 | constraint | deferred | none | none | unmapped |
| R092 | anti-feature | out-of-scope | none | none | n/a |
| R093 | constraint | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 6
- Mapped to slices: 6
- Validated: 73 (R001, R002, R003, R004, R005, R006, R007, R008, R009, R010, R011, R012, R013, R014, R015, R016, R017, R018, R019, R020, R021, R022, R023, R024, R025, R026, R027, R028, R029, R030, R031, R032, R033, R035, R036, R037, R038, R039, R040, R041, R042, R043, R044, R045, R046, R047, R048, R049, R050, R051, R052, R053, R054, R055, R056, R057, R058, R059, R060, R061, R062, R063, R064, R065, R069, R070, R071, R072, R073, R074, R075, R076, R083)
- Unmapped active requirements: 0
