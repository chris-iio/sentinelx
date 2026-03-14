# Phase 02: ASN Intelligence - Research

**Researched:** 2026-03-15
**Domain:** Team Cymru DNS-based IP-to-ASN mapping, SentinelX provider adapter pattern
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ASN-01 | User sees ASN/BGP context (CIDR prefix, RIR, allocation date) for IP IOCs via Team Cymru DNS | Team Cymru DNS protocol fully documented; dnspython already a project dependency; adapter pattern is well-established in the codebase |
</phase_requirements>

---

## Summary

Phase 02 adds ASN/BGP intelligence for IP IOCs by querying the Team Cymru IP-to-ASN DNS mapping service. The service works by constructing a DNS TXT query using the reversed octets of the IP address and a well-known zone suffix (`origin.asn.cymru.com` for IPv4, `origin6.asn.cymru.com` for IPv6). The TXT response is a pipe-delimited string containing ASN, CIDR prefix, country code, RIR, and allocation date. No API key, no HTTP, no new Python dependencies — dnspython is already installed and in use by the existing `DnsAdapter`.

The implementation follows the same structural pattern as `DnsAdapter` (port 53 DNS, no `http_safety.py`, `allowed_hosts` accepted but unused, `is_configured()` always returns `True`). The new adapter lives at `app/enrichment/adapters/asn_cymru.py` and is registered unconditionally in `setup.py` alongside the other zero-auth providers. The frontend `enrichment.ts` needs one new entry in `PROVIDER_CONTEXT_FIELDS` and one addition to `CONTEXT_PROVIDERS`.

**Primary recommendation:** Use `ipaddress.ip_address(value).reverse_pointer` to compute the reversed query name, replace the `.in-addr.arpa` / `.ip6.arpa` suffix with the Cymru zone, then resolve with `dns.resolver.Resolver` — identical mechanics to `DnsAdapter`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dnspython | Already installed (see `dns_lookup.py`) | TXT record resolution via `dns.resolver.Resolver` | Already the project DNS library; no new dependency |
| Python `ipaddress` stdlib | stdlib | Construct reversed query name via `ip.reverse_pointer` | Zero-dependency, correct for both IPv4 and IPv6 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `app.enrichment.models` | internal | `EnrichmentResult`, `EnrichmentError` | Return types for `lookup()` |
| `app.pipeline.models` | internal | `IOC`, `IOCType` | Input type for `lookup()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Team Cymru DNS | BGPView HTTP API | BGPView shut down November 2025 — not viable |
| Team Cymru DNS | RIPE Stat HTTP API | Would add HTTP dependency, SSRF surface, and rate-limit concerns; DNS is zero-auth, cacheable, no new hosts |
| `ip.reverse_pointer` | Manual string manipulation | `reverse_pointer` is stdlib, handles both IPv4 and IPv6 correctly — no hand-rolling needed |

**Installation:** No new packages needed.

---

## Team Cymru DNS Protocol

### IPv4 Query Construction
```
IP: 216.90.108.31
Reversed octets: 31.108.90.216
Query name: 31.108.90.216.origin.asn.cymru.com
```

Using Python stdlib:
```python
import ipaddress
ip = ipaddress.ip_address("216.90.108.31")
# ip.reverse_pointer == "31.108.90.216.in-addr.arpa"
query = ip.reverse_pointer.replace(".in-addr.arpa", ".origin.asn.cymru.com")
# query == "31.108.90.216.origin.asn.cymru.com"
```

### IPv6 Query Construction
```
IP: 2001:4860:4860::8888
Query zone: origin6.asn.cymru.com
```

```python
ip = ipaddress.ip_address("2001:4860:4860::8888")
# ip.reverse_pointer == "8.8.8.8.0.0.0.0....1.0.0.2.ip6.arpa"
query = ip.reverse_pointer.replace(".ip6.arpa", ".origin6.asn.cymru.com")
```

### TXT Response Format
```
"23028 | 216.90.108.0/24 | US | arin | 1998-09-25"
```

Field order (pipe-delimited, spaces around pipes):
1. ASN number (e.g., `23028`)
2. CIDR prefix (e.g., `216.90.108.0/24`)
3. Country code (e.g., `US`) — RIR assignment region, not geolocation
4. Registry/RIR (e.g., `arin`, `ripe`, `apnic`, `lacnic`, `afrinic`)
5. Allocation date (e.g., `1998-09-25`) — when prefix was allocated

**Parsing:**
```python
parts = [p.strip() for p in txt_record.split("|")]
asn    = parts[0] if len(parts) > 0 else ""
prefix = parts[1] if len(parts) > 1 else ""
rir    = parts[3] if len(parts) > 3 else ""
allocated = parts[4] if len(parts) > 4 else ""
```

### NXDOMAIN Behavior
Private/RFC-1918 IPs and unrouted space return NXDOMAIN. This is the expected "no BGP entry" outcome — not an error. Return `EnrichmentResult(verdict="no_data", raw_stats={})` for NXDOMAIN, mirroring how `IPApiAdapter` handles private IPs.

### Rate Limits
No explicit rate limit stated. Team Cymru recommends keeping bulk runs to a few thousand addresses. For per-IOC interactive use this is not a concern.

Source (HIGH): [Team Cymru IP-to-ASN Mapping](https://www.team-cymru.com/ip-asn-mapping)

---

## Architecture Patterns

### Recommended Project Structure

New file only:
```
app/enrichment/adapters/asn_cymru.py    # New adapter (CymruASNAdapter)
tests/test_asn_cymru.py                  # New test file
```

Modified files:
```
app/enrichment/setup.py                  # +1 register() call, +1 import
app/config.py                            # No change needed (DNS has no HTTP host)
app/static/src/ts/modules/enrichment.ts  # +1 PROVIDER_CONTEXT_FIELDS entry, +1 CONTEXT_PROVIDERS entry
tests/test_registry_setup.py             # +3 tests (registered, always configured, count 14)
```

### Pattern 1: Zero-Auth DNS Adapter (mirrors DnsAdapter exactly)

```python
# Source: app/enrichment/adapters/dns_lookup.py pattern
class CymruASNAdapter:
    name = "ASN Intel"
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        pass  # DNS is port 53 — no HTTP, no SSRF surface

    def is_configured(self) -> bool:
        return True  # Always True — no API key required
```

**Key design decisions carried over from DnsAdapter:**
- Do NOT import `http_safety.py` — DNS uses port 53 directly, not HTTP
- `allowed_hosts` accepted for API compatibility but intentionally unused
- `resolver.lifetime = 5.0` (float, not the HTTP `(connect, read)` tuple)
- NXDOMAIN is `EnrichmentResult(verdict="no_data")`, not `EnrichmentError`
- verdict is always `"no_data"` — ASN context is informational, not a threat signal

### Pattern 2: Frontend Context Provider Registration

The adapter is a "context provider" — purely informational, no verdict badge, pinned to top of detail rows. Two additions required in `enrichment.ts`:

```typescript
// In PROVIDER_CONTEXT_FIELDS:
"ASN Intel": [
  { key: "asn",       label: "ASN",       type: "text" },
  { key: "prefix",    label: "Prefix",    type: "text" },
  { key: "rir",       label: "RIR",       type: "text" },
  { key: "allocated", label: "Allocated", type: "text" },
],

// In CONTEXT_PROVIDERS:
const CONTEXT_PROVIDERS = new Set(["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]);
```

This routes results through `createContextRow()` (no verdict badge, prepended to details) rather than `createDetailRow()`.

### Pattern 3: setup.py Registration

```python
# Zero-auth providers — no key needed, always configured
registry.register(CymruASNAdapter(allowed_hosts=allowed_hosts))
```

No ConfigStore interaction. No ALLOWED_API_HOSTS entry — Team Cymru is DNS, not HTTP.

### Anti-Patterns to Avoid
- **Importing http_safety.py**: DNS adapters must never import `validate_endpoint`, `TIMEOUT`, or `read_limited` — these are HTTP-only controls
- **Returning EnrichmentError for NXDOMAIN**: Private IPs return NXDOMAIN — this is expected, return `no_data` result
- **Adding Team Cymru to ALLOWED_API_HOSTS**: This list is for HTTP hosts only; DNS has no SSRF surface
- **Creating a new dns.resolver.Resolver instance as a class attribute**: Create fresh per `lookup()` call for thread safety (same as DnsAdapter)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IP reversal for DNS query | Manual string splitting and reversing octets | `ipaddress.ip_address(value).reverse_pointer` | Handles both IPv4 and IPv6 correctly, stdlib, no bugs |
| TXT record parsing | Regex-based parser | Simple `str.split("|")` + `strip()` | Format is fixed and stable; pipe-delimited with no escaping |
| DNS resolution | Raw socket calls | `dns.resolver.Resolver` (already imported) | Already the project standard; handles NXDOMAIN, NoAnswer, timeouts |

**Key insight:** Every non-trivial piece of this implementation is already solved by stdlib or existing project dependencies.

---

## Common Pitfalls

### Pitfall 1: NXDOMAIN for Private/RFC-1918 IPs
**What goes wrong:** Private IPs (10.x.x.x, 192.168.x.x, 172.16-31.x.x) have no BGP route and return NXDOMAIN. If treated as an error, the adapter returns `EnrichmentError` and the UI shows a failure icon.
**Why it happens:** Conflating "record not found" with "lookup failed."
**How to avoid:** Catch `dns.resolver.NXDOMAIN` and return `EnrichmentResult(verdict="no_data", raw_stats={})`.
**Warning signs:** Test for a private IP and see `EnrichmentError` instead of `EnrichmentResult`.

### Pitfall 2: Multiple ASN Records in One TXT Answer
**What goes wrong:** When an IP prefix is announced by multiple ASNs, the TXT record may contain multiple ASN numbers separated by spaces before the first pipe: `"23028 1234 | 216.90.108.0/24 | US | arin | 1998-09-25"`.
**Why it happens:** BGP multi-origin announcements.
**How to avoid:** Use `parts[0].strip()` which may contain multiple ASNs as space-separated — store as-is or take the first. Document this behavior.
**Warning signs:** Parsed ASN contains a space.

### Pitfall 3: importing http_safety in a DNS Adapter
**What goes wrong:** `validate_endpoint()` and `TIMEOUT` only apply to HTTP traffic. The test `test_dns_adapter_does_not_import_http_safety` in `test_dns_lookup.py` enforces this for DnsAdapter. The same test pattern will be needed for `CymruASNAdapter`.
**Why it happens:** Cargo-culting from HTTP adapters.
**How to avoid:** Explicitly do not import from `app.enrichment.http_safety`.
**Warning signs:** Module-level `from app.enrichment.http_safety import ...` in `asn_cymru.py`.

### Pitfall 4: Provider Count Mismatch in Tests
**What goes wrong:** `test_registry_has_thirteen_providers` in `test_registry_setup.py` asserts exactly 13. Adding a 14th provider breaks this test.
**Why it happens:** The count assertion is a guard against accidental double-registration.
**How to avoid:** Update the count assertion to 14 as part of this phase.
**Warning signs:** `test_registry_has_thirteen_providers` fails after adding the new adapter.

### Pitfall 5: CONTEXT_PROVIDERS set not updated in enrichment.ts
**What goes wrong:** Without adding "ASN Intel" to `CONTEXT_PROVIDERS`, the result is routed through the verdict/consensus path. It gets a verdict badge (always "no_data"), participates in the consensus calculation, and does NOT get pinned to the top of the detail rows.
**Why it happens:** The provider name check in `renderEnrichmentResult()` gates the two rendering paths.
**How to avoid:** Add "ASN Intel" to both `PROVIDER_CONTEXT_FIELDS` and `CONTEXT_PROVIDERS` in the same PR.
**Warning signs:** ASN provider shows "No Data" badge and participates in consensus count.

---

## Code Examples

### Adapter Skeleton (complete, verified against DnsAdapter pattern)
```python
# Source: app/enrichment/adapters/dns_lookup.py (structural model)
import ipaddress
import logging

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

_RESOLVER_LIFETIME: float = 5.0
_IPV4_SUFFIX = ".in-addr.arpa"
_IPV6_SUFFIX = ".ip6.arpa"
_CYMRU_ZONE_V4 = ".origin.asn.cymru.com"
_CYMRU_ZONE_V6 = ".origin6.asn.cymru.com"


class CymruASNAdapter:
    name = "ASN Intel"
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        pass  # DNS is port 53 — no HTTP, no SSRF surface, allowed_hosts unused

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")

        try:
            ip = ipaddress.ip_address(ioc.value)
        except ValueError:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Invalid IP address")

        if ip.version == 4:
            query = ip.reverse_pointer.replace(_IPV4_SUFFIX, _CYMRU_ZONE_V4)
        else:
            query = ip.reverse_pointer.replace(_IPV6_SUFFIX, _CYMRU_ZONE_V6)

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = _RESOLVER_LIFETIME

        try:
            answers = resolver.resolve(query, "TXT")
            txt = b"".join(list(answers)[0].strings).decode("utf-8", errors="replace")
            return _parse_response(ioc, txt, self.name)
        except dns.resolver.NXDOMAIN:
            return EnrichmentResult(
                ioc=ioc, provider=self.name, verdict="no_data",
                detection_count=0, total_engines=0, scan_date=None, raw_stats={},
            )
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
            return EnrichmentResult(
                ioc=ioc, provider=self.name, verdict="no_data",
                detection_count=0, total_engines=0, scan_date=None, raw_stats={},
            )
        except Exception:
            logger.exception("Unexpected error during Cymru ASN lookup for %s", ioc.value)
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unexpected error")


def _parse_response(ioc: IOC, txt: str, provider_name: str) -> EnrichmentResult:
    parts = [p.strip() for p in txt.split("|")]
    raw_stats = {
        "asn":       parts[0] if len(parts) > 0 else "",
        "prefix":    parts[1] if len(parts) > 1 else "",
        "rir":       parts[3] if len(parts) > 3 else "",
        "allocated": parts[4] if len(parts) > 4 else "",
    }
    return EnrichmentResult(
        ioc=ioc, provider=provider_name, verdict="no_data",
        detection_count=0, total_engines=0, scan_date=None, raw_stats=raw_stats,
    )
```

### setup.py Registration (diff)
```python
from app.enrichment.adapters.asn_cymru import CymruASNAdapter

# In build_registry(), with other zero-auth providers:
registry.register(CymruASNAdapter(allowed_hosts=allowed_hosts))
```

### enrichment.ts additions
```typescript
// PROVIDER_CONTEXT_FIELDS addition:
"ASN Intel": [
  { key: "asn",       label: "ASN",       type: "text" },
  { key: "prefix",    label: "Prefix",    type: "text" },
  { key: "rir",       label: "RIR",       type: "text" },
  { key: "allocated", label: "Allocated", type: "text" },
],

// CONTEXT_PROVIDERS update:
const CONTEXT_PROVIDERS = new Set([
  "IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"
]);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BGPView HTTP API | Team Cymru DNS | Nov 2025 (BGPView shutdown) | BGPView is gone; DNS is the correct path |
| WHOIS-based ASN lookup | RDAP / DNS | ~2025 (WHOIS sunset) | WHOIS is EOL; REQUIREMENTS.md explicitly excludes it |

**Deprecated/outdated:**
- BGPView: Service shut down November 2025 — listed in Out of Scope table in REQUIREMENTS.md
- WHOIS: Sunsetted by ICANN January 2025 — listed in Out of Scope table in REQUIREMENTS.md

---

## Open Questions

1. **Provider name: "ASN Intel" vs. "BGP Intel" vs. "ASN/BGP"**
   - What we know: The requirement says "ASN/BGP context"; the success criterion says "ASN context row"
   - What's unclear: Exact display name is not specified
   - Recommendation: Use "ASN Intel" — short, accurate, matches UI aesthetic of other providers ("IP Context", "Cert History", "DNS Records")

2. **What to display when NXDOMAIN (private IP)?**
   - What we know: Private IPs have no BGP route; `raw_stats={}` means the context row renders with no fields
   - What's unclear: Whether the context row should be suppressed entirely or shown empty
   - Recommendation: Return `raw_stats={}` and let the frontend's `createContextFields()` return `null` (no fields rendered); the row name still appears, indicating the lookup ran. This is consistent with how IPApiAdapter handles private IPs.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_asn_cymru.py -x` |
| Full suite command | `pytest tests/ -m 'not e2e'` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASN-01 | IPv4 lookup returns asn/prefix/rir/allocated in raw_stats | unit | `pytest tests/test_asn_cymru.py -x` | No — Wave 0 |
| ASN-01 | IPv6 lookup constructs correct origin6 query | unit | `pytest tests/test_asn_cymru.py -x` | No — Wave 0 |
| ASN-01 | NXDOMAIN returns no_data result, not EnrichmentError | unit | `pytest tests/test_asn_cymru.py -x` | No — Wave 0 |
| ASN-01 | Provider has requires_api_key=False, is_configured()=True | unit | `pytest tests/test_asn_cymru.py -x` | No — Wave 0 |
| ASN-01 | Provider registered in build_registry() (count 14) | unit | `pytest tests/test_registry_setup.py -x` | Partial — needs update |
| ASN-01 | Provider appears as zero-auth in provider count dashboard | integration | `pytest tests/test_routes.py -x` | Partial — needs update |

### Sampling Rate
- **Per task commit:** `pytest tests/test_asn_cymru.py -x`
- **Per wave merge:** `pytest tests/ -m 'not e2e'`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_asn_cymru.py` — covers ASN-01 (adapter unit tests)
- [ ] Update `tests/test_registry_setup.py` — change count from 13 to 14, add "ASN Intel" presence test, add always-configured test
- [ ] Update `tests/test_routes.py` if it asserts provider counts

---

## Sources

### Primary (HIGH confidence)
- [Team Cymru IP-to-ASN Mapping](https://www.team-cymru.com/ip-asn-mapping) — DNS query format, TXT response format, IPv4/IPv6 zones, NXDOMAIN behavior, bulk query guidance
- `app/enrichment/adapters/dns_lookup.py` — structural model for DNS adapter pattern
- `app/enrichment/adapters/ip_api.py` — model for zero-auth, always-configured adapter pattern
- `app/enrichment/setup.py` — registration pattern and `allowed_hosts` convention
- `app/config.py` — ALLOWED_API_HOSTS structure (DNS adapters are NOT added here)
- `app/static/src/ts/modules/enrichment.ts` — PROVIDER_CONTEXT_FIELDS and CONTEXT_PROVIDERS integration points
- Python 3.10 stdlib `ipaddress` module — `ip_address().reverse_pointer` confirmed working for IPv4 and IPv6

### Secondary (MEDIUM confidence)
- `tests/test_dns_lookup.py` — test pattern for DNS adapter (mock strategy, exception coverage, no-http-safety assertion)
- `tests/test_registry_setup.py` — test pattern for registry integration

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — dnspython already installed; stdlib ipaddress confirmed working
- Architecture: HIGH — mirrors existing DnsAdapter pattern exactly; no new patterns needed
- Protocol: HIGH — Team Cymru docs verified against official source; query format confirmed with live Python testing
- Pitfalls: HIGH — derived from direct codebase inspection of existing patterns and test enforcement
- Frontend integration: HIGH — PROVIDER_CONTEXT_FIELDS and CONTEXT_PROVIDERS patterns fully understood from enrichment.ts

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (Team Cymru DNS is stable infrastructure; no expiry risk)
