# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.
**Current focus:** Phase 3 — Additional TI Providers

## Current Position

Phase: 3 of 4 (Additional TI Providers)
Plan: 1 of 4 in current phase (Plan 03-01 COMPLETE)
Status: Phase 3, Plan 1 complete — Multi-adapter orchestrator and MalwareBazaar adapter for hash IOC lookups
Last activity: 2026-02-21 — 03-01 complete: refactored orchestrator to accept adapters list, built MBAdapter querying abuse.ch, supported_types on VTAdapter, 218 tests passing, 100% coverage on new code

Progress: [████████░░] 82%

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 3.75 min
- Total execution time: 0.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-and-offline-pipeline | 4 | 14 min | 3.5 min |
| 02-core-enrichment | 4 | 15 min | 3.75 min |
| 03-additional-ti-providers | 1 | 4 min | 4 min |

**Recent Trend:**
- Last 5 plans: 02-02 (2 min), 02-03 (3 min), 02-04 (5 min), 03-01 (4 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-phase]: Python + Flask chosen for rapid development and rich parsing ecosystem
- [Pre-phase]: VirusTotal as primary enrichment API (universal SOC baseline)
- [Pre-phase]: No combined threat score — show raw per-provider verdicts only
- [Pre-phase]: Localhost-only binding; all security defenses built in Phase 1 before any network code
- [01-01]: Python 3.10 used instead of 3.12 — python3.12 not available in WSL; Flask 3.1 fully compatible with 3.10
- [01-01]: requests added as explicit requirement — iocextract 1.16.1 undeclared dependency
- [01-01]: flask-talisman excluded — manual after_request headers used per research recommendation
- [01-01]: app.debug = False applied twice in create_app to prevent accidental override via config_override
- [Phase 01-02]: Sequential regex in normalizer: all patterns applied left-to-right for compound defanging support
- [Phase 01-02]: ipaddress.ip_address() stdlib used for IP validation — handles edge cases like 999.999.999.999 rejection
- [Phase 01-02]: Exact hex-length anchored regex for hash classification prevents partial matches and cross-type collisions
- [Phase 01-03]: Module-level _searcher = Searcher() at import time per iocsearcher docs — Searcher is expensive to construct and should be reused
- [Phase 01-03]: Two-stage deduplication: extract_iocs deduplicates by raw string; run_pipeline deduplicates by (IOCType, normalized_value) — handles same IOC appearing defanged and fanged
- [Phase 01-03]: Exception handlers around each library call — defensive isolation so one library failure does not block the other
- [Phase 01-04]: ALLOWED_API_HOSTS exposed in app config (empty in Phase 1) — establishes SEC-16 SSRF prevention structure for Phase 2 enrichment calls
- [Phase 01-04]: <details>/<summary> accordion for IOC groups — no JavaScript needed, all sections open by default
- [Phase 01-04]: navigator.clipboard.writeText() with execCommand fallback — works in both HTTPS and HTTP (localhost) contexts
- [Phase 02-01]: Fresh requests.Session per lookup() call — avoids thread safety issues under ThreadPoolExecutor (Pitfall 3)
- [Phase 02-01]: raise_for_status() after 404 check — VT 404 is "no data" semantic; ordering prevents JSONDecodeError on error body parse
- [Phase 02-01]: ALLOWED_API_HOSTS passed to VTAdapter constructor — allows use outside Flask request context (background threads)
- [Phase 02-01]: ConfigStore accepts config_path param — test isolation via tmp_path without mocking filesystem
- [Phase 02-02]: max_workers=4 default respects VT free tier 4 req/min rate limit (Pitfall 7)
- [Phase 02-02]: max_jobs parameter on __init__ (not hardcoded) — enables test isolation without patching
- [Phase 02-02]: OrderedDict for LRU eviction — no external dependency, popitem(last=False) gives deterministic FIFO
- [Phase 02-02]: get_status() returns shallow copy — prevents external callers from mutating internal job state
- [Phase 02-core-enrichment]: Module-level _orchestrators dict stores job_id -> orchestrator for polling endpoint lookup without Flask app context
- [Phase 02-core-enrichment]: daemon=True on enrichment Thread prevents orphaned threads blocking process exit (Pitfall 4)
- [Phase 02-core-enrichment]: _mask_key() reveals only last 4 chars of stored VT API key for display in settings UI
- [Phase 02-04]: textContent only for all API-sourced dynamic content — no innerHTML to prevent XSS (SEC-08)
- [Phase 02-04]: setInterval at 750ms with a rendered-object prevents duplicate enrichment row rendering on repeated polls
- [Phase 02-04]: enrichable_count passed from route (excludes CVE types) — accurate progress denominator
- [Phase 03-01]: adapters list replaces single adapter in EnrichmentOrchestrator — each adapter declares supported_types set; orchestrator dispatches all matching (adapter, ioc) pairs
- [Phase 03-01]: total in job status reflects dispatched lookups (IOC x matching adapters), not just IOC count — enables accurate multi-provider progress tracking
- [Phase 03-01]: MBAdapter uses standalone requests.post per lookup (no shared Session) for thread safety — matches VTAdapter pattern
- [Phase 03-01]: MalwareBazaar presence-based semantics: found=verdict:malicious (confirmed sample), absent=verdict:no_data (not clean)
- [Phase 03-01]: No API key required for MalwareBazaar public hash queries
- [Phase 03-02]: CONFIDENCE_THRESHOLD=75: >=75 maps to malicious, <75 maps to suspicious for ThreatFox confidence-based verdict mapping
- [Phase 03-02]: suspicious verdict is a plain string in verdict: str field — no EnrichmentResult model changes needed
- [Phase 03-02]: ThreatFox POST API routing: search_hash for MD5/SHA1/SHA256, search_ioc for domain/IP/URL

### Pending Todos

None.

### Blockers/Concerns

- [Research]: MalwareBazaar and ThreatFox rate limits are "fair use" with no documented numeric limits — test against live APIs early in Phase 3
- [Resolved 01-01]: iocextract Flask 3.1 compatibility confirmed — iocextract is pure text processing, no Flask dependency; Python 3.10 compatible
- [Resolved 01-01]: flask-talisman concern resolved — excluded in favor of manual after_request headers

## Session Continuity

Last session: 2026-02-21
Stopped at: Phase 3, Plan 01 complete — Multi-adapter orchestrator with MBAdapter for hash lookups. 218 tests passing, 100% coverage on new code. Ready for Plan 03-02.
Resume file: None
