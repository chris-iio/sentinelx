---
estimated_steps: 19
estimated_files: 3
skills_used: []
---

# T02: Implement ConfigStore-backed redaction primitives

Expected executor `skills_used`: `tdd`, `security-review`, `verify-before-complete`.

Why: R083 cannot progress to bundle assembly until provider credentials and common auth material are proven absent from any diagnostic payload.

Files: create `app/diagnostics/redaction.py`, update `app/diagnostics/__init__.py` if useful, create `tests/test_diagnostic_redaction.py`.

Do:
1. Add redaction primitives that operate on plain text and JSON-like nested data (`dict`, `list`, scalar values) without requiring Flask request/app context.
2. Add a ConfigStore secret inventory helper that reads `ConfigStore.get_vt_api_key()` and `ConfigStore.all_provider_keys()`; include configured provider names only as safe labels, never raw values.
3. Redact exact configured secrets before any export serialization. Ignore `None`, empty strings, and very short values that would over-redact benign content, but still redact credential-looking auth/query patterns.
4. Cover common auth material in logs/errors/URLs/headers: `Authorization: Bearer ...`, `X-Api-Key`, `Auth-Key`, EmailRep `Key`, `api_key=...`, `apikey=...`, `token=...`, `secret=...`, and JSON-ish `api_key`/`token`/`secret` fields.
5. Preserve diagnostic usefulness: do not remove IOC values, provider names, verdicts, counts, timestamps, or non-sensitive context unless they exactly match a configured secret or credential pattern.
6. Return redaction metadata suitable for future manifests, such as a redaction count and safe rule labels; never include raw secret fragments in metadata.
7. Add tests with a tmp `ConfigStore` containing VT, GreyNoise/AbuseIPDB/EmailRep-style provider keys. Assert that raw configured keys and common credential pattern values do not appear in `json.dumps(redacted_payload)`, while benign IOCs/provider names remain.

Must-haves:
- Exact configured provider secrets are redacted in text, nested mappings, nested lists, URL query strings, and error strings.
- Pattern redaction is case-insensitive where headers/field names are case-insensitive.
- Redaction is deterministic and does not mutate caller-owned input objects.
- Tests prove negative cases: short benign words are not globally redacted; IOC values are preserved; malformed/non-string scalar values are handled safely.

Failure Modes (Q5): ConfigStore read failures should degrade to pattern-only redaction with safe metadata rather than throwing secrets into output; malformed nested payloads should be represented safely or left as non-secret scalars; regex errors must not bypass exact-secret redaction.

Load Profile (Q6): redaction is per-source O(serialized text size + number of collected secrets). Avoid unbounded recursion; enforce a practical recursion/depth guard or cycle protection for nested objects.

Negative Tests (Q7): missing config file, empty provider section, short configured values, mixed-case auth headers, repeated secret occurrences, nested list/dict payloads, cyclic or non-JSON-like object if the implementation supports defensive traversal.

## Inputs

- `app/diagnostics/__init__.py`
- `app/diagnostics/contract.py`
- `app/enrichment/config_store.py`
- `app/enrichment/adapters/base.py`
- `tests/test_config_store.py`
- `tests/test_settings.py`

## Expected Output

- `app/diagnostics/__init__.py`
- `app/diagnostics/redaction.py`
- `tests/test_diagnostic_redaction.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py

## Observability Impact

Adds safe redaction metadata for future diagnostic manifests: rule labels and counts only. It must never expose raw configured secret values, suffixes, or unredacted auth tokens.
