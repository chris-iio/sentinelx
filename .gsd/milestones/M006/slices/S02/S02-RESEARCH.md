# S02: WHOIS Domain Enrichment — Research

**Depth:** Targeted  
**Rationale:** Known technology (python-whois), established adapter pattern (DnsAdapter), clear requirements. The main risk is python-whois API surface quirks, which are now explored.

## Summary

This slice adds a 15th enrichment provider — a `WhoisAdapter` that queries WHOIS data for domain IOCs and returns registrar, creation date, expiry date, and name servers in `raw_stats`. The pattern is fully established: `DnsAdapter` is the exact template (non-HTTP, zero-auth, port 43, no `http_safety.py` imports). Registration in `setup.py` is a single `register()` call. The frontend already renders `raw_stats` fields automatically via `PROVIDER_CONTEXT_FIELDS` in `row-factory.ts` and the detail page template iterates `raw_stats.items()`.

**Requirement coverage:** R032 (WHOIS enrichment for domains) — primary owner of this slice.

## Recommendation

Follow the DnsAdapter pattern exactly. Three independent work units:

1. **Adapter** (`app/enrichment/adapters/whois_lookup.py`) — the core deliverable
2. **Registration + dependency** (`app/enrichment/setup.py`, `requirements.txt`) — wiring
3. **Frontend context fields + tests** (`row-factory.ts`, test file) — display and verification

## Implementation Landscape

### python-whois Library API (v0.9.6)

**Import:** `import whois` (package installs as `python-whois`, import name is `whois`)

**Core call:**
```python
w = whois.whois(domain, timeout=10)
```

**Return type:** A dict-like object with attribute access. Key fields:
- `w.registrar` → `str | None` (e.g., `"MarkMonitor, Inc."`)
- `w.creation_date` → `datetime | list[datetime] | None` (**CRITICAL: can be a single datetime OR a list**)
- `w.expiration_date` → `datetime | list[datetime] | None` (same polymorphism)
- `w.name_servers` → `list[str] | None` (e.g., `["NS1.GOOGLE.COM", "NS2.GOOGLE.COM"]`)
- `w.registrar_url` → `str | None`
- `w.org` → `str | None`
- `w.country` → `str | None`
- `w.dnssec` → `str | None`
- `w.status` → `list[str] | None`

**Timeout parameter:** `timeout=10` (int, seconds) — passed directly to the underlying socket connection. Matches DnsAdapter's 5s lifetime. Suggest using 5s to match, since WHOIS can be slow (1-3s typical, registrar-dependent).

**Exception hierarchy (all under `whois.exceptions`):**
- `PywhoisError` — base
  - `WhoisError` — general WHOIS errors
    - `WhoisDomainNotFoundError` — domain not registered (analogous to DNS NXDOMAIN)
    - `WhoisCommandFailedError` — `whois` command failed (binary not found, network error)
    - `WhoisQuotaExceededError` — rate limited by registrar
    - `WhoisUnknownDateFormatError` — date parsing failed (common with exotic TLDs)
    - `FailedParsingWhoisOutputError` — parser couldn't make sense of output
    - `UnknownTldError` — TLD not recognized by the library

### Error Handling Strategy

| Exception | Mapping | Rationale |
|-----------|---------|-----------|
| `WhoisDomainNotFoundError` | `EnrichmentResult(verdict="no_data")` | Not registered = no data, not an error (mirrors DNS NXDOMAIN handling) |
| `WhoisQuotaExceededError` | `EnrichmentError(error="WHOIS rate limited")` | Let orchestrator retry with backoff |
| `WhoisCommandFailedError` | `EnrichmentError(error="WHOIS lookup failed")` | Network/command failure |
| `FailedParsingWhoisOutputError` | `EnrichmentResult(verdict="no_data", raw_stats={"parse_error": ...})` | Some data came back but couldn't be parsed — degrade gracefully |
| `UnknownTldError` | `EnrichmentResult(verdict="no_data")` | TLD not supported by library — no data, not a real error |
| `WhoisUnknownDateFormatError` | Should not occur if we handle dates carefully — but catch as fallback |
| `socket.timeout` / generic `Exception` | `EnrichmentError(error="WHOIS timeout/unexpected error")` | Catch-all |

### Datetime Polymorphism — Critical Gotcha

`creation_date` and `expiration_date` can be:
- A single `datetime` object (e.g., `example.com`)
- A `list[datetime]` (e.g., `google.com` — returns two dates from different WHOIS sources)
- `None` (no date available)

**Normalization pattern:**
```python
def _normalize_date(val) -> str | None:
    """Convert whois date field to ISO-8601 string, handling single/list/None."""
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]  # Take first (most authoritative)
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)  # Fallback for unexpected types
```

### Adapter Structure (following DnsAdapter exactly)

```
class WhoisAdapter:
    name = "WHOIS"
    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        pass  # API compat; WHOIS is port 43, no SSRF surface

    def is_configured(self) -> bool:
        return True  # No API key needed

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        ...
```

**Key design points:**
- `requires_api_key = False` → no semaphore gating in orchestrator (uncapped concurrency, same as DNS)
- No `http_safety.py` imports — WHOIS uses port 43 directly (same constraint as DnsAdapter)
- No `requests.Session` — not HTTP
- `verdict = "no_data"` always — WHOIS is informational context, not a threat signal (mirrors DNS)
- `raw_stats` keys: `registrar`, `creation_date`, `expiration_date`, `name_servers`, `org`, `registrar_url`, `lookup_errors`

### Registration in setup.py

Add to imports and the zero-auth section:
```python
from app.enrichment.adapters.whois_lookup import WhoisAdapter
# ...
registry.register(WhoisAdapter(allowed_hosts=allowed_hosts))
```

Provider count goes from 14 → 15. Tests in `test_registry_setup.py` that assert `len(registry.all()) == 14` must update to 15.

### Frontend: CONTEXT_PROVIDERS + PROVIDER_CONTEXT_FIELDS

**`row-factory.ts`** changes:

1. Add `"WHOIS"` to `CONTEXT_PROVIDERS` set (line 162) — this makes it render as a context row (no verdict badge, pinned to top alongside DNS Records, IP Context, etc.)

2. Add entry to `PROVIDER_CONTEXT_FIELDS`:
```ts
"WHOIS": [
  { key: "registrar",       label: "Registrar",  type: "text" },
  { key: "creation_date",   label: "Created",    type: "text" },
  { key: "expiration_date", label: "Expires",    type: "text" },
  { key: "name_servers",    label: "NS",         type: "tags" },
  { key: "org",             label: "Org",        type: "text" },
],
```

3. Optionally add WHOIS context upsert in the summary row context section (like DNS A records are shown inline). Candidate: show registrar or creation_date in summary for at-a-glance domain age detection.

### Detail Page

No template changes needed. `ioc_detail.html` already iterates `raw_stats.items()` for every provider card. WHOIS data will render automatically as key-value pairs in the Raw Stats section.

### Dependency Management

Add `python-whois==0.9.6` to `requirements.txt`. The library depends on `python-dateutil` (already pulled in transitively, but should be verified).

### Test File Structure

`tests/test_whois_lookup.py` — follow `tests/test_dns_lookup.py` pattern exactly:

1. **Class metadata** — name, supported_types (frozenset, DOMAIN only), requires_api_key=False, is_configured=True
2. **Protocol conformance** — `isinstance(adapter, Provider)` check
3. **Unsupported type** — IPV4 → EnrichmentError
4. **Successful lookup** — mock `whois.whois()` return, verify raw_stats keys, verdict="no_data"
5. **Domain not found** — `WhoisDomainNotFoundError` → EnrichmentResult(verdict="no_data")
6. **Timeout/error** — various exceptions → EnrichmentError
7. **Datetime normalization** — test single datetime, list of datetimes, None
8. **No HTTP safety imports** — verify module doesn't import http_safety symbols
9. **No requests import** — verify module doesn't import requests

**Mock pattern:** `with patch("whois.whois") as mock_whois:` — mock the `whois.whois()` function call. The return value should be a `MagicMock` with attribute access for `.registrar`, `.creation_date`, etc.

### Registry/Setup Test Updates

`test_registry_setup.py` needs:
- `test_registry_has_fourteen_providers` → change assertion from 14 to 15
- Add `test_registry_contains_whois` — assert `"WHOIS"` in names
- Add `test_whois_is_always_configured` — zero-auth verification
- `test_config_store_get_provider_key_called_for_each_new_provider` — still 6 calls (WHOIS has no API key)

### Verification Commands

```bash
# Unit tests for the adapter
python -m pytest tests/test_whois_lookup.py -v

# Registry tests (updated count)
python -m pytest tests/test_registry_setup.py -v

# Protocol conformance
python -m pytest tests/test_provider_protocol.py -v

# Full test suite (960+ existing tests must still pass)
python -m pytest --tb=short -q

# TypeScript typecheck (after row-factory.ts changes)
make typecheck

# Verify no http_safety imports in adapter
grep -c "http_safety\|validate_endpoint\|safe_request" app/enrichment/adapters/whois_lookup.py
# Expected: 0

# Verify adapter satisfies Provider protocol
python -c "from app.enrichment.adapters.whois_lookup import WhoisAdapter; from app.enrichment.provider import Provider; assert isinstance(WhoisAdapter(allowed_hosts=[]), Provider)"
```

### Natural Task Boundaries

| Task | Scope | Dependencies |
|------|-------|-------------|
| T01: WhoisAdapter + unit tests | `whois_lookup.py`, `test_whois_lookup.py` | None — can be built and tested in isolation |
| T02: Registration + setup tests | `setup.py`, `requirements.txt`, `test_registry_setup.py` | T01 (adapter must exist to import) |
| T03: Frontend context fields | `row-factory.ts`, `make typecheck` | T01 (provider name must match) |

T01 is the bulk of the work (~70%). T02 and T03 are mechanical wiring (~15% each).

### What Could Go Wrong

1. **`whois` binary not available in worktree environment** — python-whois shells out to the system `whois` command. If it's not installed, `WhoisCommandFailedError` will be raised. The adapter handles this gracefully. Tests mock `whois.whois()` so they don't need the binary.
2. **Datetime can be a `str` in some edge cases** — some TLDs return dates that python-whois can't parse into datetime objects, leaving them as strings. The normalizer must handle `str` as a fallback.
3. **`name_servers` can be `None`** — not all domains have name servers in WHOIS (rare but possible). Must default to empty list.
