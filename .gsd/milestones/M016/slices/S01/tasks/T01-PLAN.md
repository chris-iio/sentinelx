---
estimated_steps: 8
estimated_files: 3
skills_used: []
---

# T01: Pin the EmailRep adapter contract in tests

Why: Lock the EmailRep adapter contract before implementation so verdict thresholds and flattened raw_stats do not drift during coding.

Do:
1. Create `tests/test_emailrep.py` with representative EmailRep response fixtures for malicious, suspicious, clean, and no_data cases.
2. Assert the future `EmailRepAdapter` is key-gated, supports only `IOCType.EMAIL`, builds `https://emailrep.io/<encoded-email>`, and sets documented `Key` plus `User-Agent` headers.
3. Assert parsed results expose flattened `raw_stats` fields: `reputation`, `suspicious`, `references`, `risk_flags`, `domain_reputation`, and `profiles`.
4. Include negative tests for unsupported IOC type and malformed/thin response handling.
5. Keep registry/setup tests untouched in this task; S01 is adapter-local.

Done when: The new test file expresses the desired adapter contract and fails only because `app.enrichment.adapters.emailrep` does not exist yet.

## Inputs

- `.gsd/milestones/M016/M016-RESEARCH.md`
- `app/enrichment/adapters/base.py`
- `app/pipeline/models.py`
- `tests/helpers.py`

## Expected Output

- `tests/test_emailrep.py`

## Verification

python3 -m pytest tests/test_emailrep.py -q (expected red until T02 creates the adapter)

## Observability Impact

Defines failure-path expectations for unsupported types and malformed/thin upstream responses; no runtime instrumentation is added.
