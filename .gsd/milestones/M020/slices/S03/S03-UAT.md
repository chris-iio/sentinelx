# S03: S03 — UAT

**Milestone:** M020
**Written:** 2026-05-16T08:53:38.706Z

## UAT Type

Automated backend/regression UAT. No human browser session is required for this slice because the changed contract is diagnostic policy centralization, generated audit documentation, and failure/redaction behavior.

## Preconditions

- Work from the repository root `/home/chris/projects/sentinelx`.
- The M020 S03 task work has been applied.
- Python test dependencies and local frontend build tooling are available.

## Steps

1. Run `make audit-m020`.
2. Confirm `.gsd/milestones/M020/M020-AUDIT.md` includes the S03 diagnostics policy outcome, names the diagnostics modules/policy seam, and records the focused diagnostics pytest lane plus failure-visibility and redaction guardrails.
3. Run `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py`.
4. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
5. Run `make verify-fast`.

## Expected Outcomes

- The audit command regenerates the M020 audit without hiding capture failures.
- The generated audit records S03 as a shipped diagnostics policy centralization keep-decision, not stale hand-written prose.
- Diagnostic archive assembly rejects forbidden or malformed paths and preserves manifest failure visibility.
- Runtime diagnostic source sanitization truncates/omits oversized, nested, circular, or unsafe payloads according to shared policy caps.
- Redaction remains longest-first for exact secrets, bounds labels, and reports config read failures as secret-free metadata.
- The optimization audit tests and fast verification lane pass.

## Edge Cases Covered

- Forbidden archive paths including `.gsd`, `.planning`, `.audits`, and `.git`.
- Duplicate/unsafe generated filenames and filename bounds.
- Oversized strings, lists, dictionaries, nested payloads, and circular diagnostic payloads.
- Diagnostic source errors, omitted/truncated states, and archive validation errors.
- Secret-containing error text, provider keys, bearer tokens, and redaction label bounds.
- Stale audit prose or missing S03 proof/failure/redaction language.

## Not Proven By This UAT

- Browser-visible analyst workflow behavior for intake, enrichment, filtering, copy, or export; that remains for S04/S05.
- Live provider enrichment performance or network behavior.
- Final full `make verify`; S03 proves the focused diagnostics/audit lanes and `make verify-fast` only.
