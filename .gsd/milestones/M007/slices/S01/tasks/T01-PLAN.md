---
estimated_steps: 55
estimated_files: 2
skills_used: []
---

# T01: Implement safe_request() in http_safety.py with unit tests

Build the shared safe_request() function that all 12 HTTP adapters will delegate to, plus comprehensive unit tests. This is the foundation — T02 and T03 depend on it.

## Steps

1. Read `app/enrichment/http_safety.py` to understand existing primitives (validate_endpoint, read_limited, TIMEOUT, MAX_RESPONSE_BYTES).
2. Add `safe_request()` to `http_safety.py` with the exact signature from D040:
   - `session`, `url`, `allowed_hosts`, `ioc`, `provider` positional args
   - `method='GET'`, `data=None`, `json_payload=None`, `pre_raise_hook=None` keyword args
   - Returns `dict | EnrichmentError`
3. Implementation flow inside safe_request():
   a. Call `validate_endpoint(url, allowed_hosts)` — raises ValueError on SSRF
   b. HTTP dispatch via `getattr(session, method.lower())(url, timeout=TIMEOUT, allow_redirects=False, stream=True, data=data, json=json_payload)` — MUST use getattr dispatch, NOT session.request() (KNOWLEDGE.md constraint: existing test mocks depend on session.get/session.post)
   c. If `pre_raise_hook` provided, call it with response; if non-None return, return that value
   d. `resp.raise_for_status()`
   e. `body = read_limited(resp)` — byte-capped JSON read
   f. Return body
4. Exception chain (ordering is a correctness constraint per KNOWLEDGE.md):
   - `requests.exceptions.Timeout` → EnrichmentError(error='Request timed out')
   - `requests.exceptions.HTTPError` → EnrichmentError(error=f'HTTP {resp.status_code}')
   - `requests.exceptions.SSLError` → EnrichmentError(error='SSL/TLS error')  ← MUST be before ConnectionError
   - `requests.exceptions.ConnectionError` → EnrichmentError(error='Connection failed')
   - `ValueError` (from validate_endpoint SSRF rejection) → EnrichmentError(error='Endpoint validation failed')
   - `Exception` → EnrichmentError(error=str(e))
5. Create `tests/test_http_safety.py` with tests:
   - test_safe_request_get_success — mock session.get returns valid JSON via iter_content
   - test_safe_request_post_json — method='POST', json_payload={...}, verify session.post called
   - test_safe_request_post_data — method='POST', data={...}, verify session.post called with data=
   - test_safe_request_ssrf_rejection — url with disallowed host → EnrichmentError
   - test_safe_request_timeout → EnrichmentError with 'timed out'
   - test_safe_request_http_error → EnrichmentError with 'HTTP 500'
   - test_safe_request_ssl_error → EnrichmentError with 'SSL/TLS'
   - test_safe_request_connection_error → EnrichmentError with 'Connection failed'
   - test_safe_request_pre_raise_hook_returns_result — hook returns EnrichmentResult → short-circuit
   - test_safe_request_pre_raise_hook_returns_none — hook returns None → continues to raise_for_status
   - test_safe_request_stream_true — verify stream=True and allow_redirects=False passed
6. Run tests: `python3 -m pytest tests/test_http_safety.py -v` — all pass.
7. Run full suite: `python3 -m pytest -x -q` — 1043+ pass, 0 fail.

## Must-Haves

- [ ] safe_request() exists with correct signature matching D040
- [ ] Exception chain ordering: SSLError before ConnectionError
- [ ] Uses getattr dispatch (session.get/session.post), NOT session.request()
- [ ] All safe_request tests pass
- [ ] Full test suite still passes (1043+ tests)

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| validate_endpoint() | ValueError caught → EnrichmentError | N/A (sync check) | N/A |
| read_limited() | JSONDecodeError → caught by Exception handler | Bounded by TIMEOUT | Returns error via Exception handler |
| session.get/post | Each exception type has dedicated handler | Timeout handler | HTTPError handler |

## Negative Tests

- SSRF: url pointing to disallowed host → EnrichmentError, not a network call
- Each exception type: Timeout, HTTPError (various codes), SSLError, ConnectionError
- pre_raise_hook returning non-None → short-circuit before raise_for_status

## Verification

- `python3 -m pytest tests/test_http_safety.py -v` — all tests pass
- `python3 -m pytest -x -q` — 1043+ pass, 0 fail
- `grep -c 'def safe_request' app/enrichment/http_safety.py` returns 1

## Inputs

- ``app/enrichment/http_safety.py` — existing primitives (validate_endpoint, read_limited, TIMEOUT, MAX_RESPONSE_BYTES)`
- ``app/enrichment/models.py` — IOC, EnrichmentResult, EnrichmentError types`
- ``tests/helpers.py` — make_mock_response helper pattern`

## Expected Output

- ``app/enrichment/http_safety.py` — safe_request() function added`
- ``tests/test_http_safety.py` — new test file with 11+ tests covering all safe_request paths`

## Verification

python3 -m pytest tests/test_http_safety.py -v && python3 -m pytest -x -q
