# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.
**Current focus:** Phase 1 — Foundation and Offline Pipeline

## Current Position

Phase: 1 of 4 (Foundation and Offline Pipeline)
Plan: 3 of TBD in current phase
Status: In progress
Last activity: 2026-02-21 — Completed 01-03: IOC extractor and pipeline integration

Progress: [███░░░░░░░] 30%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 3.7 min
- Total execution time: 0.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-and-offline-pipeline | 3 | 11 min | 3.7 min |

**Recent Trend:**
- Last 5 plans: 01-01 (4 min), 01-02 (3 min), 01-03 (4 min)
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

### Pending Todos

None.

### Blockers/Concerns

- [Research]: MalwareBazaar and ThreatFox rate limits are "fair use" with no documented numeric limits — test against live APIs early in Phase 3
- [Resolved 01-01]: iocextract Flask 3.1 compatibility confirmed — iocextract is pure text processing, no Flask dependency; Python 3.10 compatible
- [Resolved 01-01]: flask-talisman concern resolved — excluded in favor of manual after_request headers

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 01-03-PLAN.md (IOC extractor and pipeline integration)
Resume file: None
