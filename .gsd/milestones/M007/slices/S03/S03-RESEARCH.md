# S03 Research: Test DRY-up

**Depth:** Light — mechanical refactoring using established patterns already in the codebase.

## Summary

All 12 HTTP adapter test files already import `make_mock_response` from `tests/helpers.py` but none import the IOC factory functions (`make_ipv4_ioc`, `make_domain_ioc`, etc.) that also live there. Instead, they construct `IOC(type=IOCType.IPV4, value="x", raw_match="x")` inline — 219+ occurrences of `IOCType.IPV4` alone across test files. The `adapter._session = MagicMock(); adapter._session.get.return_value = mock_resp` two-line block repeats 268+ times across 12 files. The work is: add missing IOC factories, add a session-mock helper, then update each test file to use them.

## Requirement Coverage

- **R039** — Test DRY-up with shared helpers (primary owner)
- **R040** — All tests pass, zero behavior changes (supporting)

## Implementation Landscape

### Current `tests/helpers.py` (67 lines)

Has:
- `make_mock_response(status_code, body)` — used by all 12 adapter test files
- `make_ioc(ioc_type, value)` — generic factory
- `make_ipv4_ioc`, `make_ipv6_ioc`, `make_domain_ioc`, `make_sha256_ioc`, `make_md5_ioc`, `make_url_ioc`

Missing (needed by tests):
- `make_sha1_ioc` — used inline in test_hashlookup, test_malwarebazaar, test_otx, test_threatminer, test_urlhaus, test_vt_adapter
- `make_cve_ioc` — used inline in test_enrichment_models, test_otx, test_threatfox, test_threatminer, test_urlhaus, test_vt_adapter
- `make_email_ioc` — not currently used inline in adapter tests

### Repetition Pattern: Inline IOC Construction

Every adapter test file creates IOCs inline: `IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")`. Counts by type:
- IPV4: 219, MD5: 60, DOMAIN: 56, URL: 43, SHA256: 41, IPV6: 36, SHA1: 27, CVE: 25

Replacement: import `make_ipv4_ioc` etc. from `tests.helpers` and call `make_ipv4_ioc("8.8.8.8")`.

### Repetition Pattern: `adapter._session = MagicMock()`

Every test that exercises adapter.lookup() does:
```python
adapter = _make_adapter()
adapter._session = MagicMock()
adapter._session.get.return_value = mock_resp  # or .post, or .side_effect
result = adapter.lookup(ioc)
```

This 2-3 line mock setup block appears 268+ times across 12 files. A helper can collapse this:
```python
def mock_adapter_session(adapter, *, method="get", response=None, side_effect=None):
    adapter._session = MagicMock()
    target = getattr(adapter._session, method)
    if side_effect is not None:
        target.side_effect = side_effect
    elif response is not None:
        target.return_value = response
    return adapter
```

### Local Duplicates to Remove

- `test_threatminer.py` — 5 local `_make_*_ioc()` functions (`_make_ioc`, `_make_ip_ioc`, `_make_domain_ioc`, `_make_sha256_ioc`, `_make_md5_ioc`) that duplicate `tests/helpers.py`
- `test_crtsh.py` — local `_make_domain_ioc()` duplicates helpers (different default value "example.com" vs "evil.com" — tests pass the value explicitly so the default doesn't matter)

### What Should Stay Local

- `_make_adapter()` in each test file — these create different adapter classes with different constructor args (api_key, allowed_hosts). NOT duplication.
- `_make_response_body()` in test_abuseipdb.py — adapter-specific JSON builder
- `_mock_get_returning()` in test_threatminer.py — thin wrapper around `make_mock_response`, can stay or be inlined

### Files In-Scope (12 HTTP adapter test files)

| File | Lines | `adapter._session = MagicMock()` count | Inline IOC() count |
|------|-------|---------------------------------------|---------------------|
| test_threatminer.py | 1002 | 55 | 4 (uses local factories) |
| test_ip_api.py | 731 | 37 | 39 |
| test_crtsh.py | 574 | 29 | 2 (uses local factory) |
| test_otx.py | 623 | 26 | 24 |
| test_hashlookup.py | 483 | 21 | 23 |
| test_abuseipdb.py | 502 | 18 | 20 |
| test_shodan.py | 387 | 14 | 16 |
| test_urlhaus.py | 473 | 16 | 10 |
| test_vt_adapter.py | 344 | 16 | 17 |
| test_greynoise.py | 434 | 15 | 17 |
| test_threatfox.py | 361 | 13 | 14 |
| test_malwarebazaar.py | 225 | 8 | 9 |

### Files Out-of-Scope

Non-HTTP adapter tests (test_asn_cymru, test_dns_lookup, test_whois_lookup) use different mock patterns (dns.resolver, whois module). The route tests (test_routes, test_history_routes, test_ioc_detail_routes) use Flask test client patterns. These should not be touched.

## Recommendation

### Task decomposition by natural seams:

1. **Extend `tests/helpers.py`** — add `make_sha1_ioc`, `make_cve_ioc`, `mock_adapter_session`. ~15 lines. Verify existing tests still pass.

2. **Migrate adapter test files (batch 1: smaller files)** — test_malwarebazaar, test_threatfox, test_vt_adapter, test_shodan, test_greynoise, test_hashlookup. Replace inline `IOC()` calls with `make_*_ioc()` imports, replace `adapter._session = MagicMock()` blocks with `mock_adapter_session()`. ~6 files.

3. **Migrate adapter test files (batch 2: larger files)** — test_abuseipdb, test_urlhaus, test_otx, test_crtsh, test_ip_api, test_threatminer. Same pattern. test_threatminer additionally removes 5 local `_make_*_ioc` functions; test_crtsh removes 1 local `_make_domain_ioc`. ~6 files.

Each batch can be verified independently with `python3 -m pytest -x -q`.

### Verification commands:
```bash
# All 1057 tests pass
python3 -m pytest -x -q

# No adapter test file creates IOC() inline (except unsupported-type tests with exotic values)
grep -c 'IOC(type=IOCType' tests/test_shodan.py tests/test_ip_api.py tests/test_crtsh.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_otx.py tests/test_hashlookup.py tests/test_threatminer.py tests/test_vt_adapter.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py
# Target: 0 for all files (or near-zero — some edge-case IOCs with unique values may remain)

# No adapter test file has raw adapter._session = MagicMock()
grep -c 'adapter._session = MagicMock()' tests/test_shodan.py tests/test_ip_api.py tests/test_crtsh.py tests/test_abuseipdb.py tests/test_greynoise.py tests/test_otx.py tests/test_hashlookup.py tests/test_threatminer.py tests/test_vt_adapter.py tests/test_malwarebazaar.py tests/test_threatfox.py tests/test_urlhaus.py
# Target: 0 for all files

# No local _make_*_ioc duplicates remain
grep -c 'def _make_.*ioc' tests/test_threatminer.py tests/test_crtsh.py
# Target: 0
```

### Risk: Near-zero
- Pure mechanical replacement with 1057 tests as safety net
- No behavior changes — only import paths and constructor calls change
- Each file can be done independently and verified immediately
