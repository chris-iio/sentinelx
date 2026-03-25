---
estimated_steps: 2
estimated_files: 2
skills_used: []
---

# T01: Implement HistoryStore class with SQLite persistence and unit tests

Create the `HistoryStore` class following the CacheStore SQLite WAL-mode pattern. New file `app/enrichment/history_store.py` with schema for `analysis_history` table (id, input_text, mode, iocs_json, results_json, total_count, top_verdict, created_at). Methods: `save_analysis()` serializes IOCs/results to JSON and inserts row, `list_recent(limit=20)` returns recent analyses ordered by created_at DESC, `load_analysis(id)` returns full row dict or None. Uses `threading.Lock` on writes, `Path.home() / '.sentinelx' / 'history.db'` default path with constructor `db_path` override for test isolation.

Write comprehensive unit tests in `tests/test_history_store.py` following the `test_cache_store.py` structure: roundtrip save/load, list_recent ordering and limit, missing ID returns None, top_verdict computation at save time, IOC serialization/deserialization fidelity, concurrent write safety.

## Inputs

- ``app/cache/store.py` — CacheStore pattern to replicate (SQLite WAL-mode, threading.Lock, tmp_path injection)`
- ``app/pipeline/models.py` — IOC and IOCType dataclass/enum for serialization`
- ``app/routes.py` — `_serialize_result()` format (lines 73-97) defining the results JSON shape`

## Expected Output

- ``app/enrichment/history_store.py` — HistoryStore class with save_analysis(), list_recent(), load_analysis()`
- ``tests/test_history_store.py` — unit tests for HistoryStore (roundtrip, ordering, missing ID, top_verdict, concurrency)`

## Verification

python3 -m pytest tests/test_history_store.py -v && python3 -m pytest --tb=short -q 2>&1 | tail -3
