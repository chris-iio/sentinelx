---
estimated_steps: 20
estimated_files: 2
skills_used: []
---

# T01: Delete test_provider_protocol.py and relocate 2 negative tests to test_adapter_contract.py

## Description

`test_provider_protocol.py` contains 17 tests: 15 positive protocol/attribute tests (isinstance, name, requires_api_key, is_configured) for VT/MB/TF adapters, plus 2 negative tests (`test_non_conforming_class_fails_isinstance`, `test_non_conforming_class_missing_lookup_fails`) that verify the Protocol runtime check rejects non-conforming classes.

All 15 positive tests are parametrically covered by `test_adapter_contract.py` across all 15 adapters (test_isinstance_provider, test_name_matches, test_requires_api_key_matches, test_configured_when_key_provided_or_not_needed, test_not_configured_when_key_missing). The 2 negative tests are unique — they test Protocol rejection, not any specific adapter — and must be relocated to `test_adapter_contract.py`.

## Steps

1. Read `tests/test_provider_protocol.py` — identify the 2 negative test methods and their imports (IOCType, Provider).
2. Read `tests/test_adapter_contract.py` — find the appropriate insertion point (near the existing `test_isinstance_provider` test or at the end of the protocol section).
3. Add a new test class `TestProtocolNegative` (or individual test functions) to `test_adapter_contract.py` containing the 2 negative tests. Ensure the IOCType and Provider imports already exist (they should — verify).
4. Delete `tests/test_provider_protocol.py` entirely.
5. Run `python3 -m pytest tests/test_adapter_contract.py -v --tb=short` — all existing + 2 new tests pass.
6. Run `python3 -c "import tests.test_provider_protocol"` — confirm ImportError (file deleted).
7. Run `python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short` — full suite still passes.

## Must-Haves

- [ ] Both negative Protocol tests exist in `test_adapter_contract.py` and pass
- [ ] `tests/test_provider_protocol.py` is deleted
- [ ] Full unit test suite passes with 0 failures
- [ ] Net test count change: -15 (17 removed from old file, 2 added to new file)

## Verification

- `python3 -m pytest tests/test_adapter_contract.py -v --tb=short` — all tests pass including 2 new negative tests
- `python3 -c "import tests.test_provider_protocol" 2>&1 | grep -q ModuleNotFoundError && echo PASS` — file is deleted
- `python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short` — full suite passes

## Inputs

- ``tests/test_provider_protocol.py` — source of 2 negative tests to relocate`
- ``tests/test_adapter_contract.py` — destination for relocated tests`

## Expected Output

- ``tests/test_adapter_contract.py` — updated with 2 relocated negative Protocol tests`
- ``tests/test_provider_protocol.py` — deleted`

## Verification

python3 -m pytest tests/test_adapter_contract.py -v --tb=short && python3 -m pytest tests/ --ignore=tests/e2e -q --tb=short
