---
estimated_steps: 5
estimated_files: 2
---

# T02: Fix pre-existing test failures and verify all M003 gates

**Slice:** S04 — Frontend Render Efficiency & Integration Verification
**Milestone:** M003

## Description

S02 added `IOCType.EMAIL` as the 9th enum member, which broke two hardcoded test assertions. This task fixes both assertions and then runs all M003 gates to confirm the milestone is complete: typecheck clean, bundle ≤ 30KB, full test suite 0 failures, ≥ 99 E2E tests passing.

No production code changes — only test assertion fixes.

## Steps

1. **Fix `test_otx.py` — supported_types count.** In `tests/test_otx.py`, find the assertion around line 196–198:
   ```python
   """OTX supports all 8 IOC types — len(supported_types) == 8."""
   assert len(OTXAdapter.supported_types) == 8, (
       f"Expected 8 supported types, got {len(OTXAdapter.supported_types)}: {OTXAdapter.supported_types}"
   )
   ```
   Change `8` to `9` in the docstring, assertion, and error message. The OTX adapter uses `frozenset(IOCType)` which now includes `EMAIL` as the 9th member.

2. **Fix `test_routes.py` — dedup count threshold.** In `tests/test_routes.py`, find line 194:
   ```python
   assert count < 10  # Sanity: not repeated many times as separate rows
   ```
   Change `< 10` to `< 20`. The richer M002/M003 template (data attributes, detail sections, additional markup) now produces 12 occurrences of the canonical IP string in the HTML. The dedup guarantee is "not 3 separate IOC entries", not "fewer than 10 string occurrences in rendered HTML". Update the comment to reflect this.

3. **Run unit + integration tests:** `python3 -m pytest tests/ -q --ignore=tests/e2e` → expect 0 failures, ≥ 815 passing.

4. **Run E2E tests:** `python3 -m pytest tests/e2e/ -q` → expect ≥ 99 passing, 0 failures (current: 105).

5. **Run remaining gates:**
   - `make typecheck` → exit 0
   - `wc -c app/static/dist/main.js` → ≤ 30,000 bytes

## Must-Haves

- [ ] `test_otx.py` assertion updated from `== 8` to `== 9` (docstring + assert + error message)
- [ ] `test_routes.py` assertion updated from `< 10` to `< 20` with clarified comment
- [ ] `python3 -m pytest tests/ -q` → 0 failures
- [ ] `python3 -m pytest tests/e2e/ -q` → ≥ 99 passing, 0 failures
- [ ] `make typecheck` → exit 0
- [ ] `wc -c app/static/dist/main.js` → ≤ 30,000 bytes

## Verification

- `python3 -m pytest tests/test_otx.py::TestOTXProtocol::test_all_eight_ioc_types_supported -v` → PASSED (test name still says "eight" — that's fine, the docstring and assertion are what matter)
- `python3 -m pytest tests/test_routes.py::test_analyze_deduplicates -v` → PASSED
- `python3 -m pytest tests/ -q` → 0 failures, ≥ 920 passing
- `python3 -m pytest tests/e2e/ -q` → ≥ 99 passing, 0 failures
- `make typecheck` → exit 0
- `wc -c app/static/dist/main.js` → ≤ 30,000 bytes

## Inputs

- `tests/test_otx.py` — line 196–198: hardcoded `== 8` assertion on `OTXAdapter.supported_types`
- `tests/test_routes.py` — line 194: hardcoded `< 10` count threshold
- T01 must be complete (bundle rebuilt with debounce changes)

## Expected Output

- `tests/test_otx.py` — assertion updated to `== 9`
- `tests/test_routes.py` — threshold relaxed to `< 20`
- All 4 M003 gates verified passing (typecheck, bundle, unit tests, E2E tests)
