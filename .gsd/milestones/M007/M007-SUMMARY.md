---
id: M007
title: "Dead Code & Boilerplate Reduction"
status: complete
completed_at: 2026-03-28T03:12:00.085Z
key_decisions:
  - D047: Reattempt safe_request() consolidation from M005 — confirmed M005's code never materialized; work completed successfully in M007
  - getattr(session, method.lower()) dispatch in safe_request() preserves existing test mocks that patch session.get/session.post
  - SSLError → ConnectionError exception ordering enforced as correctness constraint (SSLError inherits from ConnectionError)
  - VT _map_http_error() removed — status code handling consolidated into pre_raise_hook closure pattern
  - SEC-control documentation lives once in http_safety.py — adapters reference with a single delegation line
  - mock_adapter_session() returns adapter for chaining and accepts method/response/side_effect kwargs
key_files:
  - app/enrichment/http_safety.py
  - tests/test_http_safety.py
  - tests/helpers.py
  - app/enrichment/adapters/virustotal.py
  - app/enrichment/adapters/abuseipdb.py
  - app/enrichment/adapters/greynoise.py
  - app/enrichment/adapters/crtsh.py
  - app/enrichment/adapters/threatminer.py
  - app/enrichment/adapters/shodan.py
  - app/enrichment/adapters/hashlookup.py
  - app/enrichment/adapters/ip_api.py
  - app/enrichment/adapters/otx.py
  - app/enrichment/adapters/malwarebazaar.py
  - app/enrichment/adapters/threatfox.py
  - app/enrichment/adapters/urlhaus.py
  - app/static/src/input.css
  - tests/test_routes.py
  - tests/test_history_routes.py
  - tests/test_ioc_detail_routes.py
lessons_learned:
  - Milestone closers must verify prior task code changes actually landed — M005 claimed safe_request() was done but the code never materialized. Always diff against known-good state.
  - When routes.py is refactored to use current_app attributes instead of module-level imports, test patches must switch from patch('app.routes.ClassName') to client.application.attr = mock — a pattern now documented in KNOWLEDGE.md.
  - Automated regex replacement works well for large-scale mechanical test migrations (181 session mocks, 99 inline IOCs) but requires 2-3 manual fix passes for edge cases (multiline constructors, function-call response values, multiline side_effect lists).
  - Pre-raise hook closures are a clean pattern for per-adapter HTTP status code handling — they compose well with safe_request() without needing per-adapter subclass overrides.
---

# M007: Dead Code & Boilerplate Reduction

**Consolidated all 12 HTTP adapters to use safe_request(), trimmed 77 lines of duplicated docstrings, removed dead CSS, and migrated all adapter tests to shared helpers — net -418 LOC, 1057 tests passing.**

## What Happened

M007 was a pure cleanup milestone with zero behavior changes, using the existing test suite as a safety net. It completed in three slices.

**S01 — safe_request() consolidation (medium risk).** Built `safe_request()` in `app/enrichment/http_safety.py` — a single function composing SSRF validation, HTTP dispatch via `getattr(session, method.lower())`, optional pre-raise hooks, raise_for_status, and byte-limited JSON read. All 12 HTTP adapters were migrated from ~25-line inline boilerplate blocks to a single `safe_request()` call each. VT's `_map_http_error()` was removed entirely — its logic became a pre-raise hook closure. 14 new unit tests cover the function. During closer verification, 18 stale test mocks across test_routes.py, test_history_routes.py, and test_ioc_detail_routes.py were discovered and fixed (they used `patch("app.routes.ClassName")` for names no longer imported after M005's routes refactoring).

**S02 — Docstring trimming & dead CSS (low risk).** Removed three categories of duplicated text from all 12 adapter files: SEC bullet lists (6 adapters had identical SEC-04/05/06/07/16 lists), module-level Thread safety paragraphs (all 12), and lookup() SSRF boilerplate (all 12). Each was replaced with a single delegation line pointing to http_safety.py. Also removed a stale `.chevron-toggle rules removed` comment from input.css. Net: 26 insertions, 103 deletions.

**S03 — Test DRY-up (low risk).** Added `make_sha1_ioc()`, `make_cve_ioc()`, `make_email_ioc()` factories and `mock_adapter_session()` helper to tests/helpers.py. Migrated all 12 adapter test files to use these shared helpers. The larger files (test_ip_api with 37 session mocks, test_threatminer with 55) used automated regex replacement with manual fix passes for edge cases. Removed 6 local `_make_*_ioc` factory functions.

This milestone also reattempted M005's safe_request() work (R026/R027), which had been claimed complete but never materialized in the codebase. The work landed successfully this time.

## Success Criteria Results

- **All 12 HTTP adapters use safe_request():** ✅ PASS — `grep -rl 'safe_request(' app/enrichment/adapters/` returns all 12 adapter files. Zero adapters import requests.exceptions. Zero adapters call validate_endpoint or read_limited directly.
- **http_safety.py has the single canonical HTTP+exception path:** ✅ PASS — `grep -c 'def safe_request' app/enrichment/http_safety.py` → 1. Function handles SSRF, dispatch, hooks, raise_for_status, and byte-limited read.
- **Adapter files are ~40% shorter (docstrings):** ✅ PASS — 77 lines of duplicated SEC-control docstrings, SSRF boilerplate, and Thread safety paragraphs removed. Each adapter's lookup() docstring is now one line.
- **SEC control docs live once in http_safety.py:** ✅ PASS — Zero SEC-04/05/06/07/16 references in any adapter file.
- **consensus-badge CSS gone:** ✅ PASS — Zero occurrences of consensus-badge in input.css. Stale chevron-toggle comment also removed.
- **Adapter test files use shared factories:** ✅ PASS — All 12 adapter test files have zero `IOC(type=IOCType` inline constructions, zero `adapter._session = MagicMock()` blocks, and zero local `_make_*_ioc` factory functions.
- **All tests pass:** ✅ PASS — 1057 passed, 0 failed (up from 1043 due to 14 new safe_request() tests).

## Definition of Done Results

- **All 3 slices complete:** ✅ S01 ✅, S02 ✅, S03 ✅ — all marked done in roadmap.
- **All slice summaries exist:** ✅ S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md all present on disk.
- **Cross-slice integration:** ✅ S03 consumed S01's safe_request() migration correctly — test files stable for refactoring after S01.
- **Zero behavior changes:** ✅ Test suite proves no functional regressions. Same HTTP calls, verdicts, error handling, and DOM output.
- **1057 tests pass:** ✅ `python3 -m pytest -x -q` → 1057 passed in 52.48s.

## Requirement Outcomes

| Req | Before | After | Evidence |
|-----|--------|-------|----------|
| R026 | active | validated | safe_request() exists in http_safety.py with 14 unit tests |
| R027 | active | validated | All 12 HTTP adapters call safe_request(); zero import requests.exceptions |
| R036 | active | validated | Same as R026 — safe_request() consolidates all HTTP boilerplate |
| R037 | active | validated | Zero SEC refs in adapters; 77 lines removed; lookup() docstrings replaced |
| R038 | active | validated | consensus-badge CSS absent; stale chevron-toggle comment removed |
| R039 | active | validated | All 12 test files use shared make_*_ioc() and mock_adapter_session() |
| R040 | active | validated | 1057 tests pass; zero behavior changes |

## Deviations

S01 required fixing 18 stale test mocks that were introduced by prior milestone refactoring but not caught at the time. S03 used automated regex replacement instead of manual edits for the larger test files. No functional deviations from plan.

## Follow-ups

None. All planned work completed. The row-factory.test.ts negative assertion for consensus-badge could be removed in a future cleanup but is harmless.
