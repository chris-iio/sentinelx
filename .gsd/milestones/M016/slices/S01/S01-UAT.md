# S01: EmailRep adapter contract — UAT

**Milestone:** M016
**Written:** 2026-05-09T15:25:22.267Z

## UAT Type

Automated adapter-contract acceptance for a backend provider seam. This UAT uses mocked HTTP responses and pytest unit/contract tests; it does not require or use a live EmailRep API key.

## Preconditions

- Python test dependencies are installed.
- No live third-party EmailRep API calls are allowed or required.
- The working tree contains `app/enrichment/adapters/emailrep.py`, `tests/test_emailrep.py`, and `tests/test_adapter_contract.py`.

## Test Case 1 — Malicious EmailRep response maps conservatively

1. Run `python3 -m pytest tests/test_emailrep.py -q`.
2. Inspect the malicious fixture case for `attacker@evil.com`.
3. Expected: the adapter returns provider `EmailRep`, verdict `malicious`, non-zero detection count from `references`, scan date from `details.last_seen`, and risk flags including blacklisted/malicious/credential/breach signals.

## Test Case 2 — Risky but unconfirmed response maps to suspicious

1. In the same pytest run, inspect the low-reputation/disposable fixture case.
2. Expected: the adapter returns verdict `suspicious`, not `malicious`, and flattened `risk_flags` include `new_domain`, `suspicious_tld`, `disposable`, `deliverable_false`, `valid_mx_false`, and `spoofable`.

## Test Case 3 — High reputation without risk flags maps to clean

1. In the same pytest run, inspect the high-reputation fixture case.
2. Expected: verdict is `clean`, detection count is `0`, `risk_flags` is empty, `profiles` is preserved as a compact list, and `domain_reputation` is `high`.

## Test Case 4 — Unknown/thin responses degrade to no_data

1. In the same pytest run, inspect the `reputation='none'` and thin JSON fixture cases.
2. Expected: verdict is `no_data`, detection count is `0`, missing nested `details` does not raise, and flattened defaults are safe (`reputation='none'`, `suspicious=False`, `references=0`, `risk_flags=[]`, `profiles=[]`).

## Test Case 5 — Email-only type guard prevents accidental non-email calls

1. In the same pytest run, inspect the unsupported-domain IOC case.
2. Expected: the adapter returns an `EnrichmentError` with `error == 'Unsupported type'` and the mocked HTTP session is not called.

## Test Case 6 — Request/auth contract matches EmailRep documentation

1. In the same pytest run, inspect key-gating, headers, and URL-encoding tests.
2. Expected: `is_configured()` is false without a key and true with a key; session headers include `Key: <api key>` and `User-Agent: SentinelX`; no `Authorization` header is used; `user+tag@example.com` is requested as `https://emailrep.io/user%2Btag%40example.com`.

## Test Case 7 — Shared adapter contract includes EmailRep

1. Run `python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q`.
2. Expected: the combined suite passes, including EmailRep inside shared adapter invariants for provider name, required key, supported/excluded IOC types, HTTP GET dispatch, allowlisted host coverage, status/error handling, and malformed response safety.

## Not Proven By This UAT

- Live EmailRep API availability, response drift, quota behavior, or real-key authentication.
- Online-mode provider registration/settings coverage and provider-count behavior; this belongs to S02.
- Result-row rendering of EmailRep compact context fields; this belongs to S03.
- Full mocked Online browser flow from submitted email IOC to rendered EmailRep verdict/context row; this belongs to S04.
- Performance under large email batches or live network latency.
