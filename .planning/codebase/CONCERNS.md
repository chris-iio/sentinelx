# Codebase Concerns

**Analysis Date:** 2026-04-06

## Tech Debt

**Monolithic enrichment.ts module:**
- Issue: 450 LOC in `app/static/src/ts/modules/enrichment.ts` with interleaved polling logic, verdict computation, and DOM rendering. Makes visual changes to row factory require touching a large, interleaved file.
- Files: `app/static/src/ts/modules/enrichment.ts`
- Impact: Increases risk of regressions when updating row visuals; harder to test verdict computation in isolation; module extraction is prerequisite for v1.1 visual redesign.
- Fix approach: Extract verdict computation to `verdict-compute.ts` (~80 LOC pure functions), row creation to `row-factory.ts` (~150 LOC DOM-only), leaving enrichment.ts as polling orchestrator (~300 LOC). Already planned for v1.1 Phase 2; implementation in place.

**Broad exception handling in adapters:**
- Issue: Multiple adapters (whois_lookup.py, asn_cymru.py, dns_lookup.py, pipeline/extractor.py) catch generic `except Exception:` with logging but no structured error propagation. Makes debugging adapter failures harder.
- Files: `app/enrichment/adapters/whois_lookup.py` (5 bare Exception catches), `app/enrichment/adapters/asn_cymru.py`, `app/enrichment/adapters/dns_lookup.py`, `app/pipeline/extractor.py`
- Impact: Exceptions get logged but not differentiated by type; observers of enrichment results can't distinguish between timeout, parse error, and unexpected failure.
- Fix approach: Define specific exception types for adapter failures (TimeoutError, ParseError, QuotaError) and catch those explicitly. http_safety.py already does this correctly; apply same pattern to remaining adapters.

**E2E selector brittleness:**
- Issue: 20+ hard-coded CSS selectors in `tests/e2e/pages/results_page.py` (e.g., `.ioc-card`, `.ioc-summary-row`, `.enrichment-details`, `.verdict-label`). Any class rename breaks tests.
- Files: `tests/e2e/pages/results_page.py`
- Impact: v1.1 visual redesign risk — phase 3 CSS refactor requires updating all POM selectors in sync; class name typo in template cascades to test failures.
- Fix approach: Phase 1 of v1.1 already catalogued CSS selectors and added "do not rename" guardrails (see `.planning/ROADMAP.md` Phase 1 success criteria). Enforce via pre-commit hook or linter rule to prevent accidental renames.

**CONTEXT_PROVIDERS set coupling:**
- Issue: `CONTEXT_PROVIDERS` set lives in `enrichment.ts` (module-scope) and is referenced in `row-factory.ts` import to determine rendering category. Tightly coupled; moving or renaming the set is a multi-file change.
- Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`
- Impact: Adds friction to extracting verdict computation; CONTEXT_PROVIDERS should live in row-factory since that's where it's used.
- Fix approach: Move CONTEXT_PROVIDERS to row-factory.ts during Phase 2 extraction. Already identified in `.planning/ROADMAP.md` Phase 2 success criteria.

## Known Bugs

**Cache key mutation in orchestrator:**
- Symptoms: `cached_at` key is mutated from the cached dict during retrieval, potentially affecting concurrent access patterns.
- Files: `app/enrichment/orchestrator.py` line 290 (`cached.pop("cached_at", "")`)
- Trigger: High concurrency with cache hits on the same IOC across multiple worker threads.
- Workaround: Cache dict is never re-used after this pop, but pattern is fragile if code changes. No observed runtime impact.
- Fix approach: Use `get()` instead of `pop()` to avoid mutation, or document explicitly that cached dict is disposable. Change line 290 from `cached.pop("cached_at", "")` to `cached.get("cached_at", "")`.

## Security Considerations

**Broad exception handling in safe_request:**
- Risk: Final `except Exception:` at line 155 in `app/enrichment/http_safety.py` catches all exceptions and returns a generic EnrichmentError. Could mask security-relevant exceptions (e.g., unexpected SSL error, DNS hijacking attempts).
- Files: `app/enrichment/http_safety.py` lines 155–160
- Current mitigation: Specific exception types (Timeout, HTTPError, SSLError, ConnectionError, ValueError) are caught first; the final catch is a fallback for defensive programming. Warning is logged with full traceback via `exc_info=True`.
- Recommendations: Document the intent of the final catch (prevent adapter crashes from cascading to the orchestrator). Consider logging the exception type in the error message returned to the user for debugging.

**DNS resolver configuration in dns_lookup.py:**
- Risk: `dns.resolver.Resolver(configure=True)` auto-discovers system resolver configuration. On a compromised system with malicious /etc/resolv.conf, could leak queries to attacker-controlled DNS server.
- Files: `app/enrichment/adapters/dns_lookup.py` line 48
- Current mitigation: Localhost binding and analyst-controlled environment (jump box / analyst workstation) — not exposed to internet.
- Recommendations: Document that this tool assumes a trusted, isolated environment. Consider accepting explicit resolver configuration as an option (e.g., 8.8.8.8 or system default) in ConfigStore.

**Whois lookup blocks indefinitely:**
- Risk: `whois.whois()` call on line 60 in `app/enrichment/adapters/whois_lookup.py` has no timeout parameter. Port 43 connection can hang indefinitely on network issues or malicious server.
- Files: `app/enrichment/adapters/whois_lookup.py` line 60
- Current mitigation: Orchestrator's per-provider semaphores limit concurrency; overall timeout from Flask request timeout (5 minute default).
- Recommendations: Pin `python-whois` to latest version and monitor for timeout parameter support. If unavailable, wrap call in a thread with timeout using threading.Timer or concurrent.futures.ThreadPoolExecutor with a 10-second timeout.

## Performance Bottlenecks

**SQLite WAL with many concurrent enrichment jobs:**
- Problem: CacheStore and HistoryStore both use WAL journal mode, which is efficient for concurrent readers but can cause write contention when multiple threads attempt simultaneous cache writes during enrichment (20 workers × 14 adapters = potential 280 concurrent writes).
- Files: `app/cache/store.py` lines 51–55, `app/enrichment/history_store.py` lines 87–91
- Cause: threading.Lock on write operations is per-store instance, not global. Multiple EnrichmentOrchestrator instances (one per enrichment job) could contend on the shared CacheStore singleton.
- Improvement path: Measure contention with `PRAGMA synchronous=EXTRA` temporarily; if needed, batch cache writes (flush every 50 results) or use a background writer thread to decouple worker threads from I/O latency.

**Semaphore contention for zero-auth adapters:**
- Problem: Zero-auth adapters (ip-api, DNS, WHOIS, shodan InternetDB, etc.) have no semaphore and can all execute concurrently in all 20 worker threads. If many of them are slow (e.g., DNS timeout), workers pile up waiting on I/O.
- Files: `app/enrichment/orchestrator.py` lines 94–99
- Cause: Design intentionally uncaps zero-auth to prevent rate limits from starving; correct for normal cases but doesn't account for slow adapters (DNS, WHOIS) holding threads.
- Improvement path: Profile with concurrent traces to find which adapter is slowest. Consider adding optional per-adapter timeouts or a global "slow adapter" semaphore cap (e.g., max 5 concurrent DNS queries). Document expected behavior under load.

**enrichment.ts render debounce at 100ms:**
- Problem: sortDetailRows and updateSummaryRow are both debounced at 100ms. During rapid result arrivals (streaming enrichment), each new result enqueues a 100ms delay before rendering. On slow systems or large IOC counts, visual feedback appears sluggish.
- Files: `app/static/src/ts/modules/enrichment.ts` lines 47–77
- Cause: Debounce prevents thrashing during batch result delivery, but 100ms is conservative.
- Improvement path: Reduce debounce to 50ms or replace with requestAnimationFrame for smoother incremental updates. Measure 99th percentile render time before/after to ensure no regression on lower-end hardware.

## Fragile Areas

**History and Cache stores share DB logic:**
- Files: `app/enrichment/history_store.py`, `app/cache/store.py`
- Why fragile: Both classes duplicate identical WAL/pragmas initialization, connection logic, and error handling. If a bug is found in one (e.g., busy_timeout too low), it must be fixed in both. Thread-safety pattern is identical but not shared.
- Safe modification: Extract base class `SqliteStore` with shared initialization; both HistoryStore and CacheStore inherit. Tests become simpler and bugs fix everywhere at once.
- Test coverage: Both have unit tests (test_history_store.py, test_cache_store.py), but integration tests don't verify concurrent access under contention.

**DNS and WHOIS adapters with exception loops:**
- Files: `app/enrichment/adapters/dns_lookup.py` lines 59–92, `app/enrichment/adapters/whois_lookup.py` lines 59–110
- Why fragile: Both loop through record types or parse steps, catching exceptions per iteration. If query succeeds for A records but fails for MX, raw_stats is partially filled with a mix of results and error entries. No validation that results are consistent.
- Safe modification: Define strict invariants (e.g., "all record types queried or all errored") and document in comments. Add debug logging of raw_stats structure before return to catch unexpected states early.
- Test coverage: Adapters have unit tests (test_dns_lookup, test_whois_lookup implicitly via test_adapter_contract.py), but no tests for mixed success/error scenarios (e.g., A record found but MX timeout).

**Extractor's independent try/except loops:**
- Files: `app/pipeline/extractor.py` lines 63–109
- Why fragile: Five independent try/except blocks for URL, IPv4, IPv6, MD5/SHA1/SHA256, CVE extraction. Each catches Exception broadly. If iocextract or iocsearcher changes behavior, one extraction path could silently fail while others succeed, leading to incomplete IOC lists.
- Safe modification: Consolidate extraction into a single function per library with documented failure modes. Add a "completeness check" function that warns if any extraction library failed.
- Test coverage: Extractor has unit tests (test_extractor.py) but they test happy-path and known-defang cases, not malformed input that would trigger broad exceptions.

## Scaling Limits

**ThreadPoolExecutor with 20 workers vs 14 adapters:**
- Current capacity: 20 threads × 14 adapters = potential 280 concurrent adapter calls. Actual bottleneck is per-provider semaphore (e.g., VirusTotal at 4).
- Limit: Memory per thread (~1 MB in CPython) means 20 threads ≈ 20 MB reserved. On a resource-constrained system (jump box), this is fine. Network I/O timeout (30s read) is the real bottleneck: 20 threads × 30s read = 10 minutes worst-case hung time for slow providers.
- Scaling path: If adding more adapters, monitor ThreadPoolExecutor queue depth via orchestrator status endpoint. If queue grows unbounded, lower max_workers to 10 or implement adaptive backpressure (reject new lookups when queue > 100).

**SQLite single-file concurrency:**
- Current capacity: WAL allows multiple readers; only one writer at a time. CacheStore and HistoryStore are separate files. Contention is unlikely unless hundreds of enrichments per second.
- Limit: SQLite journal disk I/O becomes bottleneck around 1000+ cache writes/second. No observed issue at current usage (analyst-driven, not high-frequency API).
- Scaling path: If SentinelX is deployed as a shared service, consider moving to PostgreSQL or Redis cache. For now, document as single-analyst tool only.

**Extractor library initialization:**
- Current capacity: Searcher created once at module level; iocextract is stateless. No pooling or limiting.
- Limit: Searcher holds in-memory regex state (~1 MB). No scaling issue for analyst-driven usage.
- Scaling path: If bulk file scanning is added, consider lazy-loading Searcher or using a process pool to isolate library state.

## Dependencies at Risk

**python-whois package maintenance:**
- Risk: python-whois has infrequent releases and is community-maintained. Port 43 WHOIS protocol is fragile (many registrars blocking or rate-limiting).
- Impact: WHOIS adapter could stop working if library has bugs or port 43 access is blocked. Alternative: use dnspython to query SOA records instead of WHOIS for domain metadata.
- Migration plan: Add DNSAdapter as alternative (already done). Document WHOIS as optional/low-reliability. If maintainability becomes an issue, disable WHOIS adapter by default and promote DNS Records adapter instead.

**iocextract library defanging edge cases:**
- Risk: iocextract handles defanging (e.g., `evil[.]com` → `evil.com`) but may not handle all analyst-invented obfuscation patterns.
- Impact: Some obfuscated IOCs may fail to extract, leading to incomplete results.
- Migration plan: Normalizer module already handles 20 defang patterns (see `app/pipeline/normalizer.py`). Extractor feeds both libraries (iocextract + normalizer) to maximize coverage. Document known limitations in UI.

**Requests library timeout behavior:**
- Risk: `requests.get(timeout=(5, 30))` uses (connect, read) tuple. Read timeout of 30 seconds is long; slow-responding APIs could delay enrichment significantly.
- Impact: A single slow provider can hold a worker thread for 30 seconds, starving other IOCs in the queue.
- Migration plan: Monitor adapter response times; reduce timeout to 15 seconds if data shows most providers respond faster. Use httpx for better timeout semantics if requests behavior becomes limiting.

## Missing Critical Features

**No adapter timeout enforcement at adapter level:**
- Problem: Individual adapters (WHOIS, DNS, some HTTP adapters) don't declare timeouts. http_safety.py enforces 5/30 but WHOIS/DNS/ASN use library defaults.
- Blocks: Impossible to guarantee orchestrator completes within predictable time frame; users see "enriching..." spinner for unpredictable durations.
- Recommendation: Define IOCAdapter timeout constraints in Provider Protocol. Each adapter must declare max_time_seconds; orchestrator validates against this before dispatch.

**No circuit breaker for consistently-failing providers:**
- Problem: If a provider is offline (e.g., VirusTotal API down), orchestrator still dispatches to it for every IOC, wasting thread time and bandwidth.
- Blocks: Enrichment jobs take longer than necessary when providers are degraded.
- Recommendation: Add circuit breaker pattern: if provider fails 5 times in 60 seconds, mark as "open" and skip dispatch for 5 minutes. Emit warning in UI. Close circuit after 1 successful response.

## Test Coverage Gaps

**No concurrent cache access tests:**
- What's not tested: CacheStore and HistoryStore have threading.Lock but no tests verify behavior under true concurrent access (multiple threads writing simultaneously).
- Files: `app/cache/store.py`, `app/enrichment/history_store.py`, tests are in `tests/test_*_store.py`
- Risk: Silent data corruption or race conditions could occur in production under high concurrency without being caught by tests.
- Priority: High — add race condition tests using threading.Thread to verify no data loss or corruption.

**No E2E tests for cache staleness:**
- What's not tested: Staleness badges (Phase 5 requirement) — E2E tests don't verify that cached results display age indicators or that cache expiration works end-to-end.
- Files: E2E tests in `tests/e2e/`; cache staleness logic in `enrichment.ts` and backend
- Risk: Staleness feature could ship broken (always showing "0m ago" or never expiring) without being caught.
- Priority: Medium — add E2E test that seeds cache with old data and verifies staleness badge displays correctly.

**No adapter error message consistency tests:**
- What's not tested: Adapters return error messages in different formats. test_adapter_contract.py verifies timeout/network errors contain "timeout" or "timed out" but doesn't test that all 14 adapters use consistent terminology for other errors.
- Files: `tests/test_adapter_contract.py`, `app/enrichment/adapters/*`
- Risk: Frontend filters or aggregates error messages; inconsistent messages could lead to incomplete filtering or confusing user-facing text.
- Priority: Medium — add test that verifies all adapters use consistent error message format (e.g., "HTTP 429", "Rate limit exceeded", "Connection failed").

**No E2E tests for filter interactions:**
- What's not tested: Filter bar (verdict filter, type filter, search) interactions with enrichment updates. E2E tests for filter exist but don't verify behavior when results arrive asynchronously during filtering.
- Files: `tests/e2e/test_results_page.py`, filter logic in `app/static/src/ts/modules/filter.ts`
- Risk: Race condition where filter hides IOCs but updates still render in hidden cards, or search query gets clobbered by async result arrival.
- Priority: Medium — add E2E test for concurrent filtering during enrichment progress.

---

*Concerns audit: 2026-04-06*
