---
estimated_steps: 17
estimated_files: 2
skills_used: []
---

# T03: Prove contract and redaction compose without exposing a bundle route

Expected executor `skills_used`: `tdd`, `verify-before-complete`.

Why: The slice closes only when the contract primitives and redaction primitives work together in the shape S02 will consume, while confirming no premature public export path was introduced.

Files: create `tests/test_diagnostic_export_primitives.py`; update `docs/diagnostic-export-contract.md` with a short S01 primitive-composition proof note if the initial contract doc does not already include it.

Do:
1. Add an integration-style unit test that builds representative diagnostic source payloads in memory: orchestrator diagnostics-like dicts, history-save diagnostics-like dicts, settings/config excerpts, provider error strings, and oversized log text containing configured secrets.
2. Apply redaction first, then wrap the sanitized payloads in the T01 manifest/source contract. Assert deterministic serialization and source outcomes (`included`, `truncated`, `omitted`, `error`) remain visible after redaction.
3. Assert the serialized manifest/payload contains no raw configured VT/provider keys or auth-pattern values, but still includes useful non-secret debugging context such as provider names, dispatch/error counts, source ids, truncation flags, and safe error summaries.
4. Add a guard test that Flask does not expose the final download route yet. Use a clearly future route such as `/diagnostics/export` or `/api/diagnostics/export` and assert it is not available in S01; S03 will intentionally replace/update this guard when the supported local app path is added.
5. Update `docs/diagnostic-export-contract.md` to state that S01 proves primitive composition only and that the route absence guard is expected to be removed/replaced by S03 route tests.
6. Keep tests self-contained; do not read `.gsd/`, `.planning/`, `.audits/`, `.artifacts/`, or other gitignored paths.

Must-haves:
- Composition proof uses real `ConfigStore` APIs with a temp config path.
- Secret absence is asserted against serialized JSON/text, not just individual fields.
- The route absence guard prevents S01 from accidentally shipping a public export surface before S02/S03 safety work.

Failure Modes (Q5): If redaction returns malformed data, manifest wrapping should fail in tests rather than silently serializing unsafe state; if route registration drifts, the route guard should force planners/executors to move that work to S03 with full route tests.

Load Profile (Q6): The composition test should include at least one truncated source at the contract bound to prove large diagnostic text is bounded before later zip assembly.

Negative Tests (Q7): oversized source payload, source error record, omitted source record, and configured secrets embedded in both text and nested metadata.

## Inputs

- `app/diagnostics/contract.py`
- `app/diagnostics/redaction.py`
- `docs/diagnostic-export-contract.md`
- `app/__init__.py`
- `app/routes/__init__.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_diagnostic_export_primitives.py`
- `docs/diagnostic-export-contract.md`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py

## Observability Impact

Proves the future diagnostic observability contract can carry safe source status/truncation/error metadata after redaction, and proves there is still no analyst-visible runtime export endpoint in S01.
