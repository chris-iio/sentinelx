# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.
**Current focus:** Phase 2 — Core Enrichment

## Current Position

Phase: 2 of 4 (Core Enrichment)
Plan: 3 of 4 in current phase (Plan 02-03 COMPLETE)
Status: Phase 2, Plan 3 complete — Flask routes wired: settings page, online-mode /analyze, polling endpoint
Last activity: 2026-02-21 — 02-03 complete: settings page, online-mode /analyze with daemon Thread, /enrichment/status polling endpoint, 187 tests passing

Progress: [███████░░░] 65%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 3.7 min
- Total execution time: 0.37 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-and-offline-pipeline | 4 | 14 min | 3.5 min |
| 02-core-enrichment | 3 | 10 min | 3.3 min |

**Recent Trend:**
- Last 5 plans: 01-04 (3 min), 02-01 (5 min), 02-02 (2 min), 02-03 (3 min)
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

### Pending Todos

None.

### Blockers/Concerns

- [Research]: MalwareBazaar and ThreatFox rate limits are "fair use" with no documented numeric limits — test against live APIs early in Phase 3
- [Resolved 01-01]: iocextract Flask 3.1 compatibility confirmed — iocextract is pure text processing, no Flask dependency; Python 3.10 compatible
- [Resolved 01-01]: flask-talisman concern resolved — excluded in favor of manual after_request headers

## Session Continuity

Last session: 2026-02-21
Stopped at: Phase 2, Plan 03 complete — Flask routes wired: settings page, online-mode /analyze with background daemon Thread, /enrichment/status polling endpoint. Ready for Plan 04.
Resume file: None
