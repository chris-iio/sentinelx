---
phase: 01-foundation-and-offline-pipeline
plan: 02
subsystem: pipeline
tags: [python, regex, ioc, normalizer, classifier, defanging, tdd]

# Dependency graph
requires:
  - phase: 01-01
    provides: IOCType enum and IOC frozen dataclass from app.pipeline.models
provides:
  - normalize() pure function: defangs IOC strings to canonical form (20 patterns)
  - classify() pure function: deterministic 8-type IOC classification with strict precedence
  - 35 normalizer tests covering all defanging variants
  - 45 classifier tests covering all 8 types, precedence, and edge cases
affects:
  - 01-03 (extractor calls normalize + classify on each extracted match)
  - 01-04 (UI routes receive IOC dataclasses from classifier)
  - all pipeline plans (normalizer/classifier are core pipeline utilities)

# Tech tracking
tech-stack:
  added:
    - pytest-cov 7.0.0 (coverage reporting, installed during verification)
  patterns:
    - Sequential regex pipeline: _DEFANG_PATTERNS list iterated left-to-right for compound defanging
    - Strict precedence classification: ordered conditional chain prevents ambiguous type matches
    - ipaddress module for IP validation: stdlib rejects invalid octets and partial addresses
    - Exact hex-length matching: 64/40/32 char counts distinguish SHA256/SHA1/MD5 unambiguously

key-files:
  created:
    - app/pipeline/normalizer.py (normalize() with 20-pattern DEFANG_PATTERNS list)
    - app/pipeline/classifier.py (classify() with CVE>SHA256>SHA1>MD5>URL>IPv6>IPv4>Domain precedence)
    - tests/test_normalizer.py (35 tests: scheme, dot, at-sign, combined, edge cases)
    - tests/test_classifier.py (45 tests: all 8 types + precedence + None cases)
  modified: []

key-decisions:
  - "Sequential regex application in normalizer: all patterns applied left-to-right rather than first-match-wins, enabling compound defanging (e.g., hxxps[://]evil[.]example[.]com)"
  - "ipaddress.ip_address() used for IP validation instead of custom regex: stdlib handles all edge cases including 999.999.999.999 rejection and IPv6 validity"
  - "Exact hex char count for hash classification (no prefix/suffix matching): ^[hex]{N}$ anchors prevent partial matches"
  - "Domain blacklist for localhost rejection: regex alone cannot distinguish localhost from valid single-label domains"

patterns-established:
  - "Sequential defang pattern: compile regex at module level, iterate patterns in normalize(), apply re.sub on each step"
  - "Precedence classification: ordered if-elif chain in classify() guarantees unambiguous type assignment"
  - "Pure pipeline functions: normalizer and classifier import no Flask modules, make no network calls, have no side effects"

requirements-completed: [EXTR-03, EXTR-04]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 1 Plan 02: IOC Normalizer and Classifier Summary

**Sequential-regex defanging normalizer (20 patterns) and deterministic 8-type classifier with CVE>SHA256>SHA1>MD5>URL>IPv6>IPv4>Domain precedence — 80 tests at 95% pipeline coverage**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T08:29:10Z
- **Completed:** 2026-02-21T08:32:01Z
- **Tasks:** 4 (2 TDD RED + 2 TDD GREEN)
- **Files modified:** 4

## Accomplishments

- Normalizer handles all 20 documented defanging patterns including compound variants (hxxps[://] + [.]) in a single pass
- Classifier provides unambiguous deterministic type assignment for all 8 IOC types using strict precedence order
- 100% branch coverage on both normalizer.py and classifier.py; 95% overall pipeline coverage
- TDD process: wrote 35 normalizer tests (RED), implemented, then 45 classifier tests (GREEN against pre-existing implementation)

## Task Commits

1. **TDD RED — Normalizer tests** - `b3c4aca` (test)
2. **TDD GREEN — Normalizer implementation** - `51b120b` (feat)
3. **TDD GREEN — Classifier tests** - `c8f040f` (test)
4. **TDD GREEN — Classifier implementation** - `17d53a1` (feat)

## Files Created/Modified

- `app/pipeline/normalizer.py` - normalize() with 20-entry _DEFANG_PATTERNS list; handles hxxp/hxxps schemes, [.] (.) {.} [dot] (dot) {dot} _dot_ dots, [@] (@) [at] at-signs
- `app/pipeline/classifier.py` - classify() returns IOC dataclass or None; precedence: CVE > SHA256 > SHA1 > MD5 > URL > IPv6 > IPv4 > Domain; uses ipaddress stdlib for IP validation
- `tests/test_normalizer.py` - 35 tests across 5 classes: scheme, dot, at-sign, combined patterns, edge cases
- `tests/test_classifier.py` - 45 tests across 8 type classes + precedence class + None class

## Decisions Made

- Used sequential pattern application (not first-match-wins) in normalizer so compound defanging like `hxxps[://]evil[.]example[.]com` resolves correctly in one normalize() call.
- ipaddress.ip_address() from stdlib handles IP validation — rejects 999.999.999.999 (ValueError), partial addresses like 192.168.1 (ValueError), and validates all IPv6 forms including compressed notation.
- Hash classification uses anchored exact-length regex (^[hex]{N}$) to prevent partial matches or cross-type collisions.
- Domain classifier uses a small blacklist (_DOMAIN_BLACKLIST = {"localhost"}) because the hostname regex alone cannot distinguish "localhost" from a valid label.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Classifier was pre-created but uncommitted from prior session**
- **Found during:** Classifier TDD RED phase (all tests passed immediately on import)
- **Issue:** app/pipeline/classifier.py existed on disk but had never been committed to git (untracked file from previous plan 01-01 session)
- **Fix:** Verified the implementation was correct against the plan spec, ran all 45 tests to confirm GREEN state, then committed as TDD GREEN step
- **Files modified:** app/pipeline/classifier.py
- **Verification:** All 45 classifier tests pass; 100% coverage on classifier.py
- **Committed in:** 17d53a1 (Classifier implementation commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The pre-existing classifier.py was functionally correct and matched the plan spec exactly. No code changes required. Committed cleanly as TDD GREEN step.

## Issues Encountered

- pytest-cov was not installed (not in requirements.txt). Installed during verification step with `.venv/bin/pip install pytest-cov`. This is a dev dependency and does not affect the production codebase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- normalize() and classify() are ready for Plan 03 (extractor) to call on each extracted IOC match
- Both functions are pure — no Flask context needed, safe to call from any module
- IOC frozen dataclass flows from classifier → extractor → routes → template rendering unchanged
- 95% pipeline coverage provides confidence baseline before extractor adds extraction logic

No blockers.

## Self-Check: PASSED

All created files verified present. All task commits verified in git history.

---
*Phase: 01-foundation-and-offline-pipeline*
*Completed: 2026-02-21*
