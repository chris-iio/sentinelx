# S01: Contract and redaction primitives — UAT

**Milestone:** M018
**Written:** 2026-05-12T05:38:30.251Z

## UAT Type

Contract/unit proof only. No human runtime, browser, or real provider account is required for S01.

## Preconditions

1. Project checkout is available at `/home/chris/projects/sentinelx`.
2. Python test dependencies used by the existing SentinelX test suite are installed.
3. No diagnostic export route or bundle assembler is expected to exist yet.

## Steps

1. Run `python3 -m pytest -q tests/test_diagnostic_export_contract.py`.
2. Confirm the manifest contract tests pass and cover deterministic serialization, allowed statuses/categories, duplicate source-id rejection, byte-bound/truncation metadata, omitted/error outcomes, bounded safe error summaries, and aggregate counts.
3. Run `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py`.
4. Confirm redaction tests pass and existing ConfigStore/settings secret-display regressions remain green.
5. Run `python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py`.
6. Inspect the primitive-composition proof expectations: configured and runtime secrets must be absent from serialized bundle-shaped output, useful non-secret debugging context must remain, oversized source text must be truncated with explicit metadata, and `/diagnostics/export` plus `/api/diagnostics/export` must still be absent.
7. Read `docs/diagnostic-export-contract.md` and confirm it names S01 non-goals and instructs later slices to replace the route-absence guard with positive route tests only when the supported download path is introduced.

## Expected Outcomes

- All three pytest commands exit 0.
- Every considered diagnostic source has an explicit `included`, `omitted`, `truncated`, or `error` outcome.
- Error summaries and source metadata are bounded and safe for serialization.
- Raw ConfigStore/provider secrets, common auth headers, query credentials, and nested token/API-key fields are redacted before manifest serialization.
- Public redaction metadata exposes labels/counts only, not secret values.
- No Flask route, UI download button, zip creation, filesystem traversal, or runtime bundle assembly is exposed by S01.

## Edge Cases Covered

- Malicious or malformed diagnostic strings containing auth headers, query credentials, and JSON-like secret fields.
- Oversized source payloads that must produce explicit truncation metadata.
- Omitted and error sources that must remain visible in the manifest instead of silently disappearing.
- Missing/failing config fallback to pattern-only redaction.
- Repeated secret occurrences, mixed-case auth names, short configured-value negative cases, nested mappings/lists/tuples, cycles, depth limits, and unserializable objects.

## Not Proven By This UAT

- Real runtime diagnostic source collection.
- Zip or tar bundle assembly.
- Download headers or browser/API route behavior.
- Analyst UI affordance for creating an export.
- End-to-end app proof of downloading and inspecting a bundle; that remains for S02-S04.
