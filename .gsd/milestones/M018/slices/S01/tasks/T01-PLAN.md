---
estimated_steps: 17
estimated_files: 4
skills_used: []
---

# T01: Define the diagnostic export contract and manifest schema

Expected executor `skills_used`: `api-design`, `tdd`, `write-docs`.

Why: S02 needs a precise, deterministic source/manifest contract before it can gather runtime files, orchestrator diagnostics, history/cache context, or per-source errors safely.

Files: create `app/diagnostics/__init__.py`, create `app/diagnostics/contract.py`, create `docs/diagnostic-export-contract.md`, create `tests/test_diagnostic_export_contract.py`.

Do:
1. Create a small backend-only `app/diagnostics` package; keep it independent of Flask routes and zip/bundle assembly.
2. In `contract.py`, define the exported schema/version constants and typed/frozen primitives for diagnostic bundle manifests and source records. The contract should make these states explicit: `included`, `omitted`, `truncated`, and `error`.
3. Include bounds-oriented fields that S02 can enforce: stable source id/name, category, relative/display path or logical source label, media/content type, original bytes, included bytes, max bytes, truncated boolean, omitted/error reason, safe error summary, and manifest-level omitted/truncated/source counts.
4. Provide deterministic serialization helpers for manifests/source records. Serialization should be JSON-safe, stable in key ordering, and should not require wall-clock time internally; callers may pass timestamps later.
5. Document the S01 contract in `docs/diagnostic-export-contract.md`, including in-scope source classes, manifest statuses, default bounds expectations, redaction-before-export rule, and explicit non-goals: no download route and no bundle assembly in S01.
6. Add focused tests in `tests/test_diagnostic_export_contract.py` that pin schema version, source status validation, deterministic ordering/serialization, bounded safe error summaries, and manifest aggregate counts.

Must-haves:
- The contract is usable by S02 without importing route handlers or touching `.gsd/`, `.planning/`, or other gitignored planning/runtime paths.
- The manifest records what was included, omitted, truncated, and errored; it must not silently drop a source outcome.
- Tests exercise malformed status/category values, oversized summaries, and deterministic serialization.

Failure Modes (Q5): malformed source descriptors should raise or coerce to an explicit error/omitted state, not create ambiguous manifests; future filesystem read failures should be representable as `error` source records with bounded summaries; missing optional fields should serialize to safe defaults.

Load Profile (Q6): per-source contract operations should be O(number of sources + metadata size), not dependent on raw bundle size. Default bounds should be constants for S02 to enforce before bytes enter a zip.

Negative Tests (Q7): invalid status, empty source id/name, oversized error strings, no sources, and mixed included/truncated/omitted/error source sets.

## Inputs

- `app/enrichment/orchestrator.py`
- `app/routes/_helpers.py`
- `app/health_contract.py`
- `Makefile`

## Expected Output

- `app/diagnostics/__init__.py`
- `app/diagnostics/contract.py`
- `docs/diagnostic-export-contract.md`
- `tests/test_diagnostic_export_contract.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_contract.py

## Observability Impact

Defines the future inspection vocabulary: manifest schema version, source statuses, byte counts, truncation flags, omitted/error reasons, and bounded safe summaries. No live runtime signal is emitted yet.
