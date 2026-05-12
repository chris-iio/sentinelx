---
estimated_steps: 35
estimated_files: 4
skills_used: []
---

# T02: Compose safe runtime diagnostic sources

Expected executor `skills_used`: `api-design`, `tdd`, `observability`.

Why: The assembler must prove it can package real local app context, not only synthetic fixtures. This task should add the backend source composition layer that turns existing SentinelX runtime surfaces into safe diagnostic source descriptors without exposing a route.

Files: create `app/diagnostics/sources.py`, update `app/diagnostics/__init__.py`, add narrow diagnostic accessor(s) to `app/routes/_helpers.py`, create `tests/test_diagnostic_export_sources.py`.

Do:
1. Add a runtime composition helper such as `build_default_diagnostic_sources(...)` that returns source descriptors for the T01 assembler without assembling or sending a response itself.
2. Include safe, bounded JSON sources for: diagnostic export metadata, ConfigStore secret inventory labels/counts only, cache stats from `CacheStore.stats()`, recent history summaries from `HistoryStore.list_recent(limit=...)`, helper-level history save diagnostics from `get_history_save_diagnostics()`, and health/dependency checks using the same secret-free shape as `app/health_contract.py`.
3. Add a narrow accessor in `app/routes/_helpers.py` for optional job-specific orchestration diagnostics when a `job_id` is provided. It should return a safe snapshot from `EnrichmentOrchestrator.get_status()`/`get_diagnostics()` without exposing live objects, raw API keys, or mutable internals.
4. Represent absent optional runtime objects, missing job ids, empty stores, or unavailable checks as explicit omitted/error source descriptors so the manifest shows what happened.
5. Keep raw config files, raw provider secret values, full unbounded database dumps, filesystem traversal, and route registration out of scope. Do not read `.gsd/`, `.planning/`, `.audits/`, `.git/`, or any gitignored planning/runtime path.
6. Use dependency injection in tests: pass tmp_path-backed `ConfigStore`, `CacheStore`, and `HistoryStore` or lightweight fakes rather than reading the developer's real home config/databases.

Must-haves:
- Config-related sources expose only labels/counts/config errors from S01 inventory; raw keys and masked suffixes do not appear.
- Runtime source composition can be called from tests without Flask request context; if an app object is required, it must be explicit.
- Optional failing dependencies become safe source errors and do not prevent other sources from being assembled by T01.
- No public `/diagnostics/export` or `/api/diagnostics/export` route is added in this task.

Failure Modes (Q5): cache/history/config stats raise -> source error descriptor with class-name/bounded summary; job id missing/evicted -> omitted or error source with reason; malformed diagnostics snapshots -> coerce to safe bounded fields or rely on existing `get_diagnostics()` coercion.

Load Profile (Q6): history source should use a small configurable recent limit, cache source should call `stats()` only, health checks should be cheap, and no source should dump full SQLite tables by default.

Negative Tests (Q7): empty stores, failing fake cache/history/config, missing job id, configured secrets in store, and a runtime diagnostic/error string containing a bearer token.

Verification:
- `python3 -m pytest -q tests/test_diagnostic_export_sources.py`

Observability Impact: Adds backend source inventory for future agents: what local runtime context is considered, which optional contexts were unavailable, and how runtime dependency failures are represented in the manifest.

Inputs:
- `app/diagnostics/assembler.py` — Source descriptor/result API from T01.
- `app/diagnostics/redaction.py` — Safe config inventory and redaction metadata.
- `app/enrichment/config_store.py` — ConfigStore API and provider secret storage contract.
- `app/cache/store.py` — Cache statistics API.
- `app/enrichment/history_store.py` — Recent-history and full-history storage API; default source should use recent summaries only.
- `app/health_contract.py` — Secret-free health payload schema.
- `app/routes/_helpers.py` — Existing history-save diagnostics and orchestrator registry location.
- `app/enrichment/orchestrator.py` — Existing safe `get_status()`/`get_diagnostics()` snapshots.

Expected Output:
- `app/diagnostics/sources.py` — Runtime source composition helpers.
- `app/diagnostics/__init__.py` — Public backend-only exports for runtime source composition.
- `app/routes/_helpers.py` — Narrow safe diagnostic accessor for orchestrator job snapshots.
- `tests/test_diagnostic_export_sources.py` — Tests for safe runtime source descriptors and dependency failure handling.

## Inputs

- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/enrichment/config_store.py`
- `app/cache/store.py`
- `app/enrichment/history_store.py`
- `app/health_contract.py`
- `app/routes/_helpers.py`
- `app/enrichment/orchestrator.py`

## Expected Output

- `app/diagnostics/sources.py`
- `app/diagnostics/__init__.py`
- `app/routes/_helpers.py`
- `tests/test_diagnostic_export_sources.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_sources.py

## Observability Impact

Adds explicit backend runtime source inventory and safe dependency-failure descriptors for later route/download diagnostics.
