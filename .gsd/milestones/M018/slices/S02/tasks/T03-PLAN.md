---
estimated_steps: 34
estimated_files: 2
skills_used: []
---

# T03: Prove assembled runtime bundle integration and route boundary

Expected executor `skills_used`: `tdd`, `verify-before-complete`, `security-review`, `write-docs`.

Why: S02 closes only when the T01 assembler and T02 runtime source composition work together as a deterministic backend bundle, with no premature app route and no secret leakage. This task should add the integration proof and update the contract document for S03/S04 handoff.

Files: create `tests/test_diagnostic_export_bundle_integration.py`, update `docs/diagnostic-export-contract.md`.

Do:
1. Write an integration test that builds tmp_path-backed ConfigStore/CacheStore/HistoryStore fixtures with representative cache/history/settings data and configured provider secrets, composes runtime sources from T02, assembles them with T01 using a fixed `generated_at`, opens the archive bytes, and inspects `manifest.json` plus payload entries.
2. Assert deterministic output: assembling the same source set twice with the same timestamp produces byte-identical archive bytes and manifest JSON; manifest sources are sorted and counts match included/truncated/omitted/error outcomes.
3. Assert secret absence across every archive member and the serialized manifest for configured provider keys plus common runtime patterns (`Authorization: Bearer ...`, `x-api-key`, query `token=`/`api_key=`) while safe labels/provider names remain visible.
4. Assert bounds/failure behavior by including at least one oversized/truncated source and one intentionally failing source in the composed set; the archive must still be produced with explicit `truncated` and `error` records.
5. Keep S03 boundary intact: assert `/diagnostics/export` and `/api/diagnostics/export` remain unregistered/404 exactly as S01 did, or move the S01 route-absence assertion into this integration test if the old primitive test needs refactoring.
6. Update `docs/diagnostic-export-contract.md` with an S02 backend assembler section: archive shape, manifest/payload naming, included runtime source classes, bounds/error semantics, redaction order, non-goals, and what S03 must add for HTTP download behavior.
7. Run focused diagnostic tests plus related ConfigStore/settings regressions to prove R009/R011 remain intact.

Must-haves:
- The integration test exercises the real backend assembler entrypoint and real runtime source composition helpers, not ad hoc hand-built records only.
- Tests never read `.gsd/`, `.planning/`, `.audits/`, `.git/`, user home config, or external provider APIs.
- Documentation reflects the actual S02 artifact shape and explicitly states that S02 still has no route/UI affordance.

Failure Modes (Q5): composed source failure should not prevent archive generation; route absence assertion catches accidental surface exposure; docs should state how S03 route errors should map from backend assembly failures.

Load Profile (Q6): integration proof should assert bounded source limits and recent-history limits so a future 10x analysis history does not imply full DB export.

Negative Tests (Q7): assembled archive with failing source, oversized source, configured secrets, common auth patterns, empty/omitted optional job context, and absent route paths.

Verification:
- `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py`
- `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py`

Observability Impact: Establishes the full backend artifact inspection path: open archive, read `manifest.json`, find source records by `source_id`, and inspect bounded payload entries while using manifest errors to localize failed collectors.

Inputs:
- `app/diagnostics/assembler.py` — Backend bundle entrypoint from T01.
- `app/diagnostics/sources.py` — Runtime source composition from T02.
- `app/diagnostics/contract.py` — Manifest serialization contract.
- `app/diagnostics/redaction.py` — Redaction primitives and labels.
- `docs/diagnostic-export-contract.md` — Existing S01 contract documentation to extend.
- `tests/test_diagnostic_export_primitives.py` — S01 composition/route-boundary expectations to preserve.
- `tests/test_config_store.py` — Existing ConfigStore regression suite.
- `tests/test_settings.py` — Existing settings secret-display regression suite.

Expected Output:
- `tests/test_diagnostic_export_bundle_integration.py` — End-to-end backend assembly proof with deterministic archive and secret absence checks.
- `docs/diagnostic-export-contract.md` — Updated S02 backend assembler contract and S03 handoff notes.

## Inputs

- `app/diagnostics/assembler.py`
- `app/diagnostics/sources.py`
- `app/diagnostics/contract.py`
- `app/diagnostics/redaction.py`
- `docs/diagnostic-export-contract.md`
- `tests/test_diagnostic_export_primitives.py`
- `tests/test_config_store.py`
- `tests/test_settings.py`

## Expected Output

- `tests/test_diagnostic_export_bundle_integration.py`
- `docs/diagnostic-export-contract.md`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py && python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py

## Observability Impact

Proves the assembled archive is the backend diagnostic inspection surface and documents how future agents/S03 route code should localize source failures.
