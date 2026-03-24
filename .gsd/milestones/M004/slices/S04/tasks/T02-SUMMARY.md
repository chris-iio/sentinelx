---
id: T02
parent: S04
milestone: M004
provides:
  - tsconfig.json incremental compilation enabled (R024)
  - Tailwind safelist includes email IOC type badge and filter pill classes (R024)
key_files:
  - tsconfig.json
  - tailwind.config.js
key_decisions: []
patterns_established:
  - When adding a new IOC type, its ioc-type-badge--{type} and filter-pill--{type} classes must be added to tailwind.config.js safelist
observability_surfaces:
  - "npx tsc --noEmit succeeds and generates .tsbuildinfo for incremental caching"
  - "grep email tailwind.config.js confirms safelist entries are present"
duration: 5m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T02: Frontend config fixes — tsconfig incremental + tailwind email safelist (R024)

**Added `incremental: true` to tsconfig.json and safelisted `ioc-type-badge--email` and `filter-pill--email` in tailwind.config.js to fix R024 frontend config gaps.**

## What Happened

Two config changes for R024 compliance:

1. **tsconfig.json** — Added `"incremental": true` to `compilerOptions`. This enables TypeScript's incremental build cache (`.tsbuildinfo`), avoiding full re-typechecks on `make typecheck`. Works with `noEmit` in TypeScript 5+.

2. **tailwind.config.js** — Added `"ioc-type-badge--email"` to the ioc-type-badge safelist block (after `--cve`) and `"filter-pill--email"` to the filter-pill safelist block (after `--cve`). These classes were introduced in M003/S02 for email IOC support but were never safelisted, meaning Tailwind's purge step would strip them from production builds.

## Verification

- `grep -q '"incremental": true' tsconfig.json` → OK
- `grep -q "ioc-type-badge--email" tailwind.config.js` → OK
- `grep -q "filter-pill--email" tailwind.config.js` → OK
- `npx tsc --noEmit` → exit 0 (clean typecheck)
- `python3 -m pytest tests/ -x -q` → 944 passed, 0 failures
- All T01 slice checks still pass (helpers imported by 10 files, no local mock factories)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q '"incremental": true' tsconfig.json` | 0 | ✅ pass | <1s |
| 2 | `grep -q "ioc-type-badge--email" tailwind.config.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "filter-pill--email" tailwind.config.js` | 0 | ✅ pass | <1s |
| 4 | `npx tsc --noEmit` | 0 | ✅ pass | 4.0s |
| 5 | `python3 -m pytest tests/ -x -q` | 0 | ✅ pass | 45.3s |
| 6 | `test $(grep -rl "from tests.helpers import" tests/test_*.py \| wc -l) -eq 10` | 0 | ✅ pass | <1s |
| 7 | `! grep -l "def _make_mock_.*response" tests/test_*.py` | 0 | ✅ pass | <1s |
| 8 | `grep -q "def make_mock_response" tests/helpers.py` | 0 | ✅ pass | <1s |
| 9 | `python3 -c "from tests.helpers import make_mock_response; ..."` | 0 | ✅ pass | <1s |
| 10 | `grep -q "style-src" app/__init__.py` | 1 | ⏳ pending T03 | <1s |
| 11 | `grep -q "object-src 'none'" app/__init__.py` | 1 | ⏳ pending T03 | <1s |

## Diagnostics

- **Incremental build cache**: After `npx tsc --noEmit`, a `.tsbuildinfo` file is created. If stale type errors appear after structural changes, delete this file and re-run.
- **Email safelist verification**: `grep "email" tailwind.config.js` shows both safelist entries. If email IOC badges or filter pills are missing from production CSS, this is the first place to check.

## Deviations

- First attempt to add `filter-pill--email` silently failed (edit matched `"filter-pill--cve",` but the replacement wasn't persisted to the line after it). Re-ran the edit with a larger context window including the closing `],` which succeeded. Root cause was ambiguity when editing the last item in an array — the edit tool needs enough surrounding context to anchor the replacement.

## Known Issues

None.

## Files Created/Modified

- `tsconfig.json` — added `"incremental": true` to compilerOptions
- `tailwind.config.js` — added `"ioc-type-badge--email"` and `"filter-pill--email"` to safelist
- `.gsd/milestones/M004/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M004/slices/S04/S04-PLAN.md` — marked T02 as done
