# S01 Research: safe_request() Consolidation

## Summary

This is straightforward consolidation work — extracting a repeated ~25-line HTTP+exception pattern from 12 adapters into a single `safe_request()` function in `http_safety.py`. The API shape is already decided (D039, D040, D041). The pattern is identical across all 12 adapters with minor variations. All 1043 existing tests mock `adapter._session` directly and will continue to work because safe_request() uses `session.get()`/`session.post()` via `getattr` dispatch (KNOWLEDGE.md constraint).

## Recommendation

Implement safe_request() in `http_safety.py`, then migrate all 12 HTTP adapters in batches. The function signature, exception chain, and test strategy are fully specified by prior decisions. Risk is low — the exception chain is identical across all 12 adapters, and existing tests provide full regression coverage.

## Implementation Landscape

### Target file: `app/enrichment/http_safety.py` (65 lines)

Currently contains:
- `TIMEOUT = (5, 30)` — SEC-04
- `MAX_RESPONSE_BYTES = 1MB` — SEC-05
- `validate_endpoint()` — SEC-16 SSRF check
- `read_limited()` — SEC-05 byte-capped streaming JSON reader

`safe_request()` goes here, composing these existing primitives.

### safe_request() API shape (from D040)

```python
def safe_request(
    session: requests.Session,
    url: str,
    allowed_hosts: list[str],
    ioc: IOC,
    provider: str,
    *,
    method: str = "GET",
    data: dict | None = None,        # form-encoded POST body
    json_payload: dict | None = None, # JSON POST body (named to avoid shadowing json module)
    pre_raise_hook: Callable[[requests.Response], EnrichmentResult | EnrichmentError | None] | None = None,
) -> dict | EnrichmentError:
```

**Returns:** parsed dict body on success, or `EnrichmentError` on any failure.

**Internal flow:**
1. `validate_endpoint(url, allowed_hosts)` — SSRF check
2. `getattr(session, method.lower())(url, timeout=TIMEOUT, allow_redirects=False, stream=True, data=data, json=json_payload)` — dispatch
3. If `pre_raise_hook` is provided, call it with the response; if it returns non-None, return that value immediately
4. `resp.raise_for_status()`
5. `body = read_limited(resp)` — byte-capped read
6. Return `body`

**Exception chain (from KNOWLEDGE.md — ordering is a correctness constraint):**
`Timeout` → `HTTPError` → `SSLError` → `ConnectionError` → `Exception`

SSLError MUST appear before ConnectionError (SSLError is a subclass of ConnectionError).

### 12 HTTP adapters — variation catalog

| Adapter | Method | Pre-raise checks | Per-request headers | Session auth headers |
|---------|--------|-------------------|--------------------|--------------------|
| abuseipdb | GET | 429→EnrichmentError | Yes (redundant copy of session) | Key, Accept |
| crtsh | GET | none | none | none (no auth) |
| greynoise | GET | 404→no_data | Yes (redundant copy of session) | key |
| hashlookup | GET | 404→no_data | none | none (no auth) |
| ip_api | GET | 404→no_data | none | none (no auth) |
| malwarebazaar | POST (data=) | none | none | Auth-Key, Accept |
| otx | GET | 404→no_data | none | X-OTX-API-KEY |
| shodan | GET | 404→no_data | none | none (no auth) |
| threatfox | POST (json=) | none | none | Auth-Key |
| threatminer | GET | none | none | none (no auth) |
| urlhaus | POST (data=) | none | none | Auth-Key |
| virustotal | GET | 404→no_data | none | x-apikey, Accept |

**Key finding:** AbuseIPDB and GreyNoise pass per-request headers that are identical copies of their session headers. After migration, these can be dropped entirely — safe_request() relies on session-level headers only. No `headers=` parameter needed.

### Pre-raise hook patterns

6 adapters check 404 before raise_for_status() and return an `EnrichmentResult(verdict="no_data")`. These will pass a `pre_raise_hook` lambda to safe_request().

1 adapter (AbuseIPDB) checks 429 and returns a specific error message. This also goes through `pre_raise_hook`.

VT has a `_map_http_error()` for 429/401/403 — this stays in the VT adapter, called from the HTTPError except block. Actually, since safe_request() handles the exception chain, VT's custom HTTPError handling needs special consideration: VT wants specific messages for 429 ("Rate limit exceeded"), 401/403 ("Authentication error"). 

**Resolution:** safe_request() returns a generic `EnrichmentError(error=f"HTTP {code}")` for HTTPError. VT's `_map_http_error()` can be dropped — the orchestrator already handles 429 retries. The generic message is sufficient. If VT needs custom messages, it can use `pre_raise_hook` to check 429/401/403 before raise_for_status().

### Lines saved per adapter

Each adapter loses ~25 lines of HTTP boilerplate (the try/except block). The `validate_endpoint` call + try/except wrapper is replaced by a single `safe_request()` call + result check. Net savings: ~20 lines per adapter × 12 = ~240 lines.

### Test strategy (D041)

- **Existing adapter tests stay unchanged.** They mock `adapter._session.get`/`.post` directly. Since safe_request() calls `session.get()`/`session.post()` via `getattr`, these mocks intercept the call as before.
- **New tests for safe_request() itself** in a new `tests/test_http_safety.py` file. Test: SSRF rejection, timeout handling, each exception type, pre_raise_hook short-circuit, byte-cap enforcement, GET dispatch, POST dispatch.

### Natural task decomposition

1. **T01: Implement safe_request() in http_safety.py + tests** — the foundation. ~50 lines of implementation, ~80 lines of tests. Unblocks everything else.

2. **T02: Migrate GET adapters (no pre-raise hooks)** — crtsh, threatminer (2 adapters). Simplest case: just replace the try/except block with `result = safe_request(self._session, url, self._allowed_hosts, ioc, self.name)`.

3. **T03: Migrate GET adapters with 404 pre-raise hook** — shodan, hashlookup, ip_api, greynoise, otx, virustotal (6 adapters). Same pattern but pass a `pre_raise_hook` lambda for the 404 check. AbuseIPDB's 429 pre-check also uses this mechanism.

4. **T04: Migrate POST adapters** — malwarebazaar (data=), urlhaus (data=), threatfox (json=). Add `method="POST"` and `data=` or `json_payload=`.

5. **T05: Remove redundant per-request headers from AbuseIPDB and GreyNoise, run full test suite, verify grep checks** — cleanup and final verification.

Alternative: T02-T04 could be a single task (all 12 adapters in one pass) since the pattern is mechanical. The planner should decide based on context window budget.

### Verification commands

```bash
# All tests pass
python3 -m pytest -x -q

# No inline HTTP boilerplate in adapters
grep -c 'validate_endpoint\|read_limited\|requests.exceptions' app/enrichment/adapters/*.py

# safe_request exists
grep -c 'def safe_request' app/enrichment/http_safety.py

# No per-request headers= in adapter lookup() calls
grep -c 'headers={' app/enrichment/adapters/*.py
```

### Constraints from KNOWLEDGE.md

- safe_request() must use `session.get()`/`session.post()` via `getattr(session, method.lower())`, NOT `session.request()` — existing test mocks depend on this
- SSLError handler must appear before ConnectionError (subclass relationship)
- `json_payload=` parameter name (not `json=`) to avoid shadowing Python's json module
- Per-request headers are redundant — all auth is on session level already
