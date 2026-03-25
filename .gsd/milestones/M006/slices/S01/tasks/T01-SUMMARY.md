---
id: T01
parent: S01
milestone: M006
key_files:
  - app/enrichment/history_store.py
  - tests/test_history_store.py
key_decisions:
  - Used UUID4 hex (32-char) as row id rather than integer autoincrement — avoids leaking analysis count and supports potential future distributed use
  - top_verdict computed at save time and stored in the row — avoids re-parsing results_json on every list_recent() call
  - list_recent() truncates input_text to 120 chars in the query result — keeps the summary lightweight without a separate 'preview' column
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:05:35.746Z
blocker_discovered: false
---

# T01: Implement HistoryStore class with SQLite WAL-mode persistence and 20 comprehensive unit tests

**Implement HistoryStore class with SQLite WAL-mode persistence and 20 comprehensive unit tests**

## What Happened

Created `app/enrichment/history_store.py` following the CacheStore pattern: SQLite WAL-mode, threading.Lock on writes, constructor `db_path` override for test isolation, auto-creating parent directories.

The HistoryStore class provides three public methods:
- `save_analysis(input_text, mode, iocs, results)` — serializes IOCs/results to JSON, computes top_verdict from result verdicts (malicious > suspicious > no_data > clean > error), generates a UUID4 hex id, inserts row with UTC timestamp, returns the id.
- `list_recent(limit=20)` — returns lightweight summary dicts (no full results_json) ordered by created_at DESC, with input_text truncated to 120 chars for the home page list.
- `load_analysis(id)` — returns full row dict with deserialized iocs and results, or None for missing ids.

A helper `_compute_top_verdict()` derives the most severe verdict from serialized results, ignoring error entries (no verdict key). Empty or all-error results produce "error".

Wrote 20 unit tests in `tests/test_history_store.py` covering: roundtrip save/load, unique IDs, created_at population, list_recent ordering/limit/truncation/summary fields, top_verdict computation (mixed, all-clean, all-error, no_data-over-clean, empty), direct _compute_top_verdict unit tests, IOC serialization fidelity with special chars and nested dicts, concurrent writes from 5 threads × 10 operations, and DB directory auto-creation.

## Verification

Ran `python3 -m pytest tests/test_history_store.py -v` — all 20 tests passed in 0.69s. Ran full suite with `python3 -m pytest --tb=short -q -x --ignore=tests/test_playwright` — all 964 tests passed in 47.23s. No regressions introduced.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_history_store.py -v` | 0 | ✅ pass | 690ms |
| 2 | `python3 -m pytest --tb=short -q -x --ignore=tests/test_playwright` | 0 | ✅ pass | 47230ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/history_store.py`
- `tests/test_history_store.py`
