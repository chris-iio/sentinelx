---
estimated_steps: 5
estimated_files: 4
---

# T04: SQLite WAL + persistent connection + purge_expired, and config read caching

**Slice:** S02 — IO Performance & Polling Protocol
**Milestone:** M004

## Description

Two independent mechanical optimizations combined into one task because both are small and isolated:

1. **CacheStore** creates a new `sqlite3.Connection` for every `get()`, `put()`, `clear()`, `get_all_for_ioc()`, and `stats()` call — 200+ open/close cycles per enrichment batch. It also uses the default journal mode (DELETE), which serializes concurrent readers behind writers. This task switches to WAL mode, keeps a persistent connection, and adds a `purge_expired()` method for TTL-based cleanup. Covers requirement R022.

2. **ConfigStore._read_config()** re-reads and re-parses the INI file on every call. Since config is read during adapter initialization and on each settings page load, this is wasted IO. This task adds a simple in-memory cache with write-through invalidation.

## Steps

1. **CacheStore: persistent connection + WAL mode**
   - In `__init__`, instead of `conn = self._connect(); ... conn.close()`, store: `self._conn = self._connect()`
   - Immediately after opening: `self._conn.execute("PRAGMA journal_mode=WAL")`
   - Run `self._conn.execute(_CREATE_TABLE); self._conn.commit()`
   - Remove or keep `_connect()` as a private helper, but all methods must use `self._conn` instead of `self._connect()`

2. **CacheStore: update all methods to use `self._conn`**
   - `get()`: replace `with self._connect() as conn:` with direct use of `self._conn` (the `with` statement on sqlite3.Connection manages transactions, not the connection itself — but since we're only reading, we can just use `self._conn.execute(...)` directly)
   - `put()`: replace `with self._lock, self._connect() as conn:` with `with self._lock:` and use `self._conn.execute(...); self._conn.commit()`
   - `clear()`: same pattern as `put()`
   - `get_all_for_ioc()`: use `self._conn.execute(...)`
   - `stats()`: use `self._conn.execute(...)`

3. **CacheStore: add `purge_expired(ttl_seconds: int)` method**
   ```python
   def purge_expired(self, ttl_seconds: int) -> int:
       """Delete cache entries older than ttl_seconds.
       
       Returns:
           Number of rows deleted.
       """
       cutoff = (
           datetime.datetime.now(tz=datetime.timezone.utc)
           - datetime.timedelta(seconds=ttl_seconds)
       ).isoformat()
       with self._lock:
           cursor = self._conn.execute(
               "DELETE FROM enrichment_cache WHERE cached_at < ?",
               (cutoff,),
           )
           self._conn.commit()
           return cursor.rowcount
   ```

4. **Add purge_expired tests in `tests/test_cache_store.py`**
   - `test_purge_expired_deletes_old_entries`: insert 2 entries with different timestamps (one "old" by manipulating cached_at directly), call `purge_expired(3600)`, assert old entry deleted, new entry kept, return value is 1
   - `test_purge_expired_empty_db`: call on empty DB, assert returns 0, no error
   - `test_purge_expired_keeps_fresh_entries`: insert entries within TTL, call purge, assert all kept, returns 0

5. **ConfigStore: add `_cached_cfg` with write-through invalidation**
   - In `__init__`, add: `self._cached_cfg: configparser.ConfigParser | None = None`
   - In `_read_config()`, add at the start:
     ```python
     if self._cached_cfg is not None:
         return self._cached_cfg
     ```
   - Before returning the parsed `cfg`, add: `self._cached_cfg = cfg`
   - In `_save_config()`, add at the end: `self._cached_cfg = None`
   - This is transparent — existing tests pass without modification because they always call `set_*` before `get_*` (which invalidates and re-reads)

## Must-Haves

- [ ] `CacheStore.__init__` creates persistent `self._conn` and sets WAL mode
- [ ] All CacheStore methods use `self._conn` — no per-method `self._connect()` calls
- [ ] `purge_expired(ttl_seconds)` method exists and works correctly
- [ ] 3 new purge tests pass
- [ ] `ConfigStore._read_config()` returns cached parser when available
- [ ] `ConfigStore._save_config()` invalidates the cache
- [ ] All existing cache_store and config_store tests pass

## Verification

- `grep 'journal_mode' app/cache/store.py` — WAL pragma present
- `grep 'purge_expired' app/cache/store.py` — method exists
- `grep 'self._conn' app/cache/store.py` — persistent connection used (multiple hits)
- `grep -c 'self._connect()' app/cache/store.py` — should be ≤1 (only in `__init__` or helper, not in method bodies)
- `grep '_cached_cfg' app/enrichment/config_store.py` — cache variable present
- `python3 -m pytest tests/test_cache_store.py -v` — all existing + 3 new purge tests pass
- `python3 -m pytest tests/test_config_store.py -v` — all 16 tests pass
- `python3 -m pytest tests/ --ignore=tests/e2e -x -q` — ≥936 pass

## Inputs

- `app/cache/store.py` — current CacheStore with per-method `_connect()`, no WAL, no `purge_expired()`
- `tests/test_cache_store.py` — 15 existing tests using `tmp_path` fixtures
- `app/enrichment/config_store.py` — current ConfigStore with uncached `_read_config()`
- `tests/test_config_store.py` — 16 existing tests

## Expected Output

- `app/cache/store.py` — persistent `self._conn`, WAL mode, `purge_expired()` method, all methods use `self._conn`
- `tests/test_cache_store.py` — 3 new `purge_expired` tests added
- `app/enrichment/config_store.py` — `_cached_cfg` field, cached `_read_config()`, invalidation in `_save_config()`
- `tests/test_config_store.py` — unchanged (caching is transparent), all pass
