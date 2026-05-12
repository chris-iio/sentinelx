---
id: T02
parent: S01
milestone: M018
key_files:
  - app/diagnostics/redaction.py
  - app/diagnostics/__init__.py
  - tests/test_diagnostic_redaction.py
key_decisions:
  - Public diagnostic inventory metadata exposes only safe labels and configured provider names; raw ConfigStore values are retained only in private exact-match redaction candidates.
  - Exact configured-secret redaction runs before case-insensitive pattern redaction to prevent regex mismatches from bypassing known secrets.
  - Nested payload redaction defensively copies caller-owned objects and uses cycle/depth/unserializable guards rather than mutating or trusting arbitrary repr output.
duration: 
verification_result: passed
completed_at: 2026-05-12T05:29:42.225Z
blocker_discovered: false
---

# T02: Added ConfigStore-backed diagnostic redaction primitives for text and JSON-like payloads with safe metadata only.

**Added ConfigStore-backed diagnostic redaction primitives for text and JSON-like payloads with safe metadata only.**

## What Happened

Created `app/diagnostics/redaction.py` with backend-only redaction functions that do not depend on Flask app/request context. The module collects configured VirusTotal and provider-key redaction candidates from `ConfigStore`, exposes only safe inventory labels/provider names publicly, redacts exact configured secrets before serialization, and applies case-insensitive pattern rules for Authorization Bearer, X-Api-Key, Auth-Key, EmailRep-style Key headers, query credentials, and JSON-like api_key/token/secret fields. Nested dict/list/tuple traversal copies caller-owned objects, preserves benign diagnostic context such as IOCs/provider names/verdicts/timestamps/counts, handles missing/failing config as pattern-only redaction with safe metadata, and includes cycle/depth/unserializable-object guards. Exported the public primitives from `app/diagnostics/__init__.py` for future diagnostic bundle assembly.

## Verification

Added `tests/test_diagnostic_redaction.py` covering configured VT/GreyNoise/AbuseIPDB/EmailRep-style secrets, nested mappings/lists, URL query strings, error strings, mixed-case auth names, short configured-value negative cases, missing/failing config fallback, deterministic non-mutating traversal, repeated occurrence counts, cycles, and malformed scalars. Ran the focused redaction tests and the task verification command with existing ConfigStore/settings coverage; both passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_redaction.py` | 0 | ✅ pass — 8 passed | 290ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py` | 0 | ✅ pass — 51 passed | 676ms |

## Deviations

Hardened the public inventory helper beyond the initial test draft so it exposes only secret labels/provider labels, keeping raw configured values private to in-process redaction candidates.

## Known Issues

None.

## Files Created/Modified

- `app/diagnostics/redaction.py`
- `app/diagnostics/__init__.py`
- `tests/test_diagnostic_redaction.py`
