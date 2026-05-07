---
estimated_steps: 8
estimated_files: 3
skills_used: []
---

# T03: Add EmailRep to shared adapter contract coverage

Why: Prove the new adapter obeys the same shared adapter invariants as existing HTTP adapters before downstream slices register it.

Do:
1. Add a `make_email_ioc()` helper if needed, following existing helper style.
2. Extend `tests/test_adapter_contract.py` with an EmailRep `AdapterEntry` using allowed host `emailrep.io`, `api_key="test-key"`, `requires_api_key=True`, supported type `IOCType.EMAIL`, and HTTP method `get`.
3. Ensure contract tests prove unsupported-type handling for all non-email IOC types and configured/unconfigured key behavior.
4. Do not add EmailRep to `app/enrichment/setup.py` or settings metadata yet.
5. Update any adapter-count wording in the contract-test module if it becomes stale.

Done when: Dedicated EmailRep tests and the shared adapter contract suite pass together.

## Inputs

- `app/enrichment/adapters/emailrep.py`
- `tests/test_adapter_contract.py`
- `tests/helpers.py`

## Expected Output

- `tests/test_adapter_contract.py`
- `tests/helpers.py`

## Verification

python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q

## Observability Impact

No runtime signal change; contract tests become the inspection surface proving the adapter remains compatible with shared HTTP safety invariants.
