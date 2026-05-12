# S02: Backend export assembler — UAT

**Milestone:** M018
**Written:** 2026-05-12T08:41:17.038Z

# S02 UAT — Backend export assembler

## Scope

Backend-only proof; no browser route or UI is expected in this slice.

## Acceptance checks

1. Assemble default runtime diagnostic sources with injected config/cache/history/job diagnostics and inspect the returned ZIP.
2. Confirm `manifest.json` is present and source payload paths are stable under `runtime/`.
3. Confirm every considered source has an explicit status and byte bounds.
4. Confirm configured provider secret values and bearer-token prose are absent from archive bytes.
5. Confirm missing or failing runtime dependencies become `omitted` or `error` manifest records without aborting unrelated sources.
6. Confirm `/diagnostics/export` and `/api/diagnostics/export` are not registered until S03.

## Evidence

- `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py` passed 20 tests.
- `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py` passed 51 tests.

