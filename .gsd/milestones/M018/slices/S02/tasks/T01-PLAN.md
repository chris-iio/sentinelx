---
estimated_steps: 29
estimated_files: 3
skills_used: []
---

# T01: Implement deterministic bounded bundle assembly

Expected executor `skills_used`: `api-design`, `tdd`, `security-review`.

Why: S03 needs one backend service with stable archive semantics before a route can safely expose downloads. This task should implement the source-agnostic assembler and pin its behavior with tests before runtime collectors are added.

Files: create `app/diagnostics/assembler.py`, update `app/diagnostics/__init__.py`, create `tests/test_diagnostic_export_assembler.py`.

Do:
1. Define a small backend-only assembly API, e.g. `DiagnosticSource`, `DiagnosticBundle`, and `assemble_diagnostic_bundle(...)`, that accepts caller-supplied source descriptors/callables plus a caller-supplied `generated_at` timestamp.
2. Package output as deterministic archive bytes containing `manifest.json` plus sanitized payload entries under a stable prefix such as `sources/<source_id>.json` or caller-provided safe relative paths. Use fixed ZIP metadata/order/compression settings so identical inputs produce identical bytes.
3. Enforce path safety: reject or coerce unsafe payload paths that are absolute, contain `..`, target `.gsd/`, `.planning/`, `.audits/`, `.git/`, or collide with `manifest.json`; duplicate source ids/paths must fail fast with a clear `ValueError`.
4. For each source attempt: evaluate content lazily, redact with S01 primitives before serialization/encoding, measure original redacted bytes, enforce per-source `max_bytes`, include truncated content only up to the bound, and create a `DiagnosticSourceRecord` with status `included` or `truncated`.
5. Support intentional omissions (no content by design) and source exceptions. Omissions become `omitted` records with reasons; exceptions become `error` records with bounded, redacted `safe_error_summary`; neither should abort unrelated sources.
6. Return a result object exposing archive bytes, the `DiagnosticManifest`, and any helpful secret-free summary fields needed by tests/S03; export the public names from `app/diagnostics/__init__.py`.

Must-haves:
- Redaction happens before payload bytes are written to the archive or manifest error summaries.
- Manifest sources are sorted by `source_id` and archive entries are written in stable order.
- Every considered source produces exactly one manifest outcome unless input validation fails before assembly starts.
- The assembler stays independent of Flask routes and does not read filesystem paths directly.

Failure Modes (Q5): source callable raises -> per-source `error` record with bounded redacted summary; malformed/duplicate descriptor -> fail fast before bundle bytes are trusted; oversized source -> `truncated` record and bounded payload; unserializable object -> safe type-name representation via S01 payload redaction/JSON fallback.

Load Profile (Q6): per bundle cost is O(number of sources + bounded included bytes). The default source bound should come from `DEFAULT_SOURCE_MAX_BYTES`; archive construction must not keep unbounded source content beyond the source currently being processed.

Negative Tests (Q7): duplicate source ids, duplicate archive paths, traversal/absolute/gitignored paths, oversized source content, source exception containing a configured secret, and deterministic two-run archive equality.

Verification:
- `python3 -m pytest -q tests/test_diagnostic_export_assembler.py`

Observability Impact: Adds manifest/archive assembly summary and per-source failure/truncation/redaction records that future route code can surface safely.

Inputs:
- `app/diagnostics/contract.py` — S01 manifest/source-record vocabulary, bounds constants, deterministic JSON helpers.
- `app/diagnostics/redaction.py` — S01 ConfigStore-backed text/payload redaction primitives.
- `tests/test_diagnostic_export_primitives.py` — Composition patterns and secret fixtures to reuse conceptually without copying route behavior.

Expected Output:
- `app/diagnostics/assembler.py` — New source-agnostic deterministic bundle assembler.
- `app/diagnostics/__init__.py` — Public backend-only exports for the assembler API.
- `tests/test_diagnostic_export_assembler.py` — Focused assembler contract tests.

## Inputs

- `app/diagnostics/contract.py`
- `app/diagnostics/redaction.py`
- `tests/test_diagnostic_export_primitives.py`

## Expected Output

- `app/diagnostics/assembler.py`
- `app/diagnostics/__init__.py`
- `tests/test_diagnostic_export_assembler.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_assembler.py

## Observability Impact

Adds the backend diagnostic artifact structure itself: manifest, stable archive paths, byte counts, truncation/error outcomes, and redaction metadata.
