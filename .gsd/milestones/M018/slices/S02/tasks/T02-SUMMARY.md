---
id: T02
parent: S02
milestone: M018
key_files:
  - app/diagnostics/sources.py
  - app/diagnostics/__init__.py
  - app/routes/_helpers.py
  - app/diagnostics/redaction.py
  - tests/test_diagnostic_export_sources.py
key_decisions:
  - Runtime source composition remains backend-only and dependency-injected; omitted/error descriptors make absent or failing optional sources visible in the manifest without route coupling.
  - Orchestration diagnostics are exposed through a narrow copied snapshot accessor rather than exporting registry objects or mutable internals.
  - Standalone bearer-token redaction belongs in shared diagnostic redaction primitives so both source payloads and manifest error summaries are protected.
duration: 
verification_result: passed
completed_at: 2026-05-12T08:13:04.858Z
blocker_discovered: false
---

# T02: Added backend-only runtime diagnostic source composition for safe config, cache, history, health, and optional orchestration snapshots.

**Added backend-only runtime diagnostic source composition for safe config, cache, history, health, and optional orchestration snapshots.**

## What Happened

Created `app/diagnostics/sources.py` with `build_default_diagnostic_sources(...)`, returning assembler-compatible `DiagnosticSource` descriptors without assembling bundles or registering routes. The helper uses explicit dependency injection for `ConfigStore`, cache, history, health checks, and optional job diagnostics so tests and future route wiring do not depend on Flask request context or local developer state. Missing runtime objects and absent job IDs are represented as omitted sources, while cache/history/config/health failures become per-source manifest errors through the T01 assembler rather than aborting the bundle.

Updated backend exports in `app/diagnostics/__init__.py` and added a narrow `get_orchestration_diagnostics_snapshot(job_id)` accessor in `app/routes/_helpers.py`. The accessor returns copied, bounded, JSON-safe status/diagnostic snapshots from the orchestrator registry or explicit not-found/evicted-style records, never live orchestrator objects or mutable internals.

Added `tests/test_diagnostic_export_sources.py` covering safe runtime snapshots, bounded history limits, secret inventory labels/counts only, missing optional runtime objects, failing fake dependencies, missing job IDs, and bearer-token redaction in runtime diagnostics/error strings. During verification, a shared redaction gap surfaced for prose like `Bearer token`; I strengthened `app/diagnostics/redaction.py` to redact standalone bearer tokens and tightened JSON-ish credential field matching so safe labels such as `configured_secret:virustotal` are not over-redacted.

## Verification

Ran the required focused verification for T02 and additional regression checks because the final fix touched shared diagnostic redaction primitives. `tests/test_diagnostic_export_sources.py` passed. `tests/test_diagnostic_redaction.py` passed. A final combined diagnostic export check passed 25 tests and confirmed no `/diagnostics/export` or `/api/diagnostics/export` route string exists under `app/`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_sources.py` | 0 | ✅ pass | 433ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_redaction.py` | 0 | ✅ pass | 364ms |
| 3 | `python3 -m pytest -q tests/test_diagnostic_export_sources.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_assembler.py && route absence check for /diagnostics/export and /api/diagnostics/export` | 0 | ✅ pass | 629ms |

## Deviations

Also updated `app/diagnostics/redaction.py` to safely redact standalone bearer tokens and preserve safe diagnostic labels after tests exposed shared redaction behavior needed by this task's negative cases.

## Known Issues

None.

## Files Created/Modified

- `app/diagnostics/sources.py`
- `app/diagnostics/__init__.py`
- `app/routes/_helpers.py`
- `app/diagnostics/redaction.py`
- `tests/test_diagnostic_export_sources.py`
