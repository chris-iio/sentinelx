---
phase: 06-models-parser-and-foundation
plan: "03"
subsystem: ssh-parser
tags: [ssh, parser, tdd, regex, datetime, ipaddress, frozen-dataclass]

dependency_graph:
  requires:
    - phase: 06-01
      provides: app/ssh/models.py::LoginEvent, app/ssh/models.py::ParseSummary
  provides:
    - app/ssh/parser.py::parse_auth_log
  affects:
    - Phase 7 GeoIP wrapper (consumes LoginEvent.source_ip)
    - Phase 8 detector (consumes list[LoginEvent] and ParseSummary)
    - Phase 9 routes/UI (calls parse_auth_log, renders LoginEvent fields)

tech-stack:
  added: []
  patterns:
    - "TDD red-green: failing tests committed first, then implementation"
    - "Dual-format regex: BSD syslog tried first, RFC 3339 second, partial-match sentinel third"
    - "BSD year rollover: dt > now + 24h => year - 1 heuristic"
    - "ipaddress.ip_address() for IP vs hostname classification (PARSE-03/04)"
    - "errors='replace' on BytesIO decode (T-06-09 mitigation)"

key-files:
  created:
    - app/ssh/parser.py
    - tests/test_ssh_parser.py
  modified: []

key-decisions:
  - "Dual-format regex order: BSD first (most common in Debian/Ubuntu), RFC3339 second (systemd journals)"
  - "Year rollover threshold: 24 hours future — large enough to avoid false positives from timezone skew, tight enough to catch Dec/Jan boundary"
  - "RFC3339 partial-match on fromisoformat failure: bad timestamp string in an otherwise matching line gets warning_count not skipped_count"
  - "Line-by-line via splitlines() not iter() — avoids partial-line buffering edge cases with BytesIO"

patterns-established:
  - "parse_auth_log signature: (stream, *, now) — keyword-only now= for safe test overrides"
  - "Private helpers prefixed with _ and tested indirectly through parse_auth_log"
  - "Partial-match via _PARTIAL_SSH_RE after both full regexes fail — no double-counting"

requirements-completed:
  - PARSE-01
  - PARSE-02
  - PARSE-03
  - PARSE-04

duration: 4min
completed: 2026-04-11
---

# Phase 6 Plan 03: SSH auth.log Parser Summary

**parse_auth_log() with BSD syslog + RFC 3339 dual-format parsing, Dec-to-Jan year rollover, IP/hostname classification, and 34 TDD tests.**

## Performance

- **Duration:** ~4 minutes
- **Started:** 2026-04-11T22:56:59Z
- **Completed:** 2026-04-11T23:00:09Z
- **Tasks:** 1 (TDD: RED commit + GREEN commit)
- **Files created:** 2

## Accomplishments

- `app/ssh/parser.py` — 255-line parser with dual-format regex, year-rollover heuristic, IP/hostname classifier, and D-06/D-07 error handling
- `tests/test_ssh_parser.py` — 500-line test file, 34 tests across 9 test classes covering all PARSE-01 through PARSE-04 requirements
- Full phase suite (SSH models + parser + config) passes: 72 tests
- No regressions: 928 non-e2e tests pass

## Task Commits

1. **RED — failing tests** - `697dab8` (test): 34 tests, all failing with ModuleNotFoundError
2. **GREEN — implementation** - `ee439d0` (feat): parser implemented, all 34 tests pass

## Files Created/Modified

- `app/ssh/parser.py` — `parse_auth_log()` function, `_classify_source()`, `_parse_bsd_timestamp()`, `_iter_lines()`, three compiled regexes
- `tests/test_ssh_parser.py` — TestParserAccepted, TestParseSummary, TestTimestampBSD, TestTimestampRFC3339, TestYearRollover, TestSourceExtraction, TestPartialMatch, TestSkippedLines, TestStreamTypes, TestD02Invariant

## Decisions Made

- **Dual-format regex order:** BSD syslog tried first (most common in Debian/Ubuntu `/var/log/auth.log`), RFC3339 second (systemd journal export). Order matters because both regexes can produce a match on some edge-case lines.
- **Year rollover threshold is 24 hours:** Gives a comfortable margin for timezone-skewed analysis without false positives. The previous-year assignment only fires when the inferred datetime is more than a day in the future relative to `now`.
- **RFC3339 bad timestamp → warning, not skip:** If the regex matches the RFC3339 shape but `fromisoformat()` rejects the timestamp string, it is a partial match (D-06), not an unrecognised line. Warning count captures it accurately.
- **splitlines() not line-by-line iteration:** Reads all content then splits. Avoids partial-line buffering edge cases inherent in iterating over a BytesIO with a trailing newline.

## Deviations from Plan

None — plan executed exactly as written. The `\S` escape warning in the module docstring was cleaned up as a minor refactor (no behaviour change).

## Known Stubs

None. `parse_auth_log()` is fully implemented and returns real LoginEvent records from real log content. No placeholder data or hardcoded returns.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. The parser operates on caller-supplied streams only. Threat mitigations T-06-06 through T-06-09 (as listed in the plan) are all implemented:

- T-06-06: Anchored regexes, no nested quantifiers, compiled once at module level
- T-06-07: raw_line/username/hostname stored as-is; SEC-08 obligation documented in module docstring
- T-06-08: Line-by-line processing (splitlines handles large files); MAX_CONTENT_LENGTH (Plan 02) bounds input before parser is called
- T-06-09: BytesIO decoded with `errors="replace"`

## Self-Check: PASSED

- `app/ssh/parser.py`: FOUND (255 lines, >= 100 minimum)
- `tests/test_ssh_parser.py`: FOUND (500 lines, >= 200 minimum)
- Commit `697dab8`: FOUND (test RED)
- Commit `ee439d0`: FOUND (feat GREEN)
- 34 parser tests pass: VERIFIED
- 72 phase tests pass: VERIFIED
- 928 non-e2e tests pass (no regressions): VERIFIED
- `from app.ssh.models import LoginEvent, ParseSummary` present in parser: VERIFIED
- `ipaddress.ip_address` present: VERIFIED
