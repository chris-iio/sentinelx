# Phase 01: Zero-Auth IP Intelligence + Known-Good — Research

**Researched:** 2026-03-12
**Domain:** Zero-auth HTTP adapter implementation, new verdict type, IP geolocation API, rDNS, proxy flag detection, NSRL hash lookup, Shodan card UI completion
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Known-Good Verdict Design**
- New verdict value: `known_good` with blue badge color — outside the red/amber/green threat spectrum entirely
- Badge text: "KNOWN GOOD" (matches requirements language)
- Override behavior: If CIRCL hashlookup confirms NSRL match, summary verdict becomes KNOWN GOOD regardless of other provider verdicts (e.g., VT false positives on calc.exe get overridden)
- Detail rows still show individual provider verdicts normally — override is summary-level only
- Add "Known Good" as a filter chip in the verdict filter bar (between Clean and No Data)

**IP Enrichment Display**
- Single combined "IP Context" row — GeoIP + rDNS + proxy flags together in one row, not separate provider rows
- Context-only, no verdict badge — IP Context is factual metadata, not a threat assessment
- First in detail row order — appears above all provider detail rows (VT, Shodan, GreyNoise, etc.)
- Compact inline geo format: `DE · Frankfurt · AS24940 (Hetzner Online GmbH)` — country code + city + ASN with ISP name in one line
- rDNS on its own line: `PTR: tor-exit.example.com`
- Flags on their own line as tags: `[hosting] [tor-exit]`

**Proxy Flag Presentation**
- Neutral tags — same visual styling as Shodan ports/vulns context tags. No color-coding by risk category
- Only show true flags — if proxy/VPN/hosting/mobile are false, that flag is not rendered. Clean residential IPs show no flags line at all
- Purely informational — IP Context never participates in summary verdict calculation
- Keep separate from Shodan tags — ip-api.com flags and Shodan tags stay in their own provider rows

**Shodan Card Completeness**
- Add CPEs and tags to the existing Shodan InternetDB context fields (both already fetched in raw_stats, just not rendered)
- CPEs render as tags (same as ports/vulns/hostnames)
- Shodan tags render as tags (same styling)

### Claude's Discretion
- Exact CSS/Tailwind classes for the blue KNOWN GOOD badge
- rDNS lookup implementation approach (built into ip-api.com adapter or separate)
- CIRCL hashlookup adapter internals (API endpoint, response parsing, error handling)
- CPE string truncation or formatting in Shodan card (if needed for readability)
- How to handle ip-api.com rate limits or failures gracefully
- Whether IP Context row has a subtle visual separator from provider rows

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IPINT-01 | User can see country, city, and ASN for any IP IOC without configuring an API key | ip-api.com adapter returning `countryCode`, `city`, `as`/`asname` fields; rendered as compact inline text |
| IPINT-02 | User can see reverse DNS (PTR) hostname for any IP IOC without an API key | ip-api.com includes `reverse` field in same request — no separate rDNS call needed |
| IPINT-03 | User can see proxy/VPN/hosting detection flags for any IP IOC without an API key | ip-api.com `proxy`, `hosting`, `mobile` boolean fields; rendered as neutral tags only when true |
| HINT-01 | User can see whether a file hash is a known-good (NSRL) file via CIRCL hashlookup without an API key | CIRCL hashlookup `GET /lookup/{type}/{hash}` — 200=found, 404=not found; no auth required |
| HINT-02 | Known-good verdict is visually distinct from malicious/clean/unknown in summary rows and filter bar | New `known_good` VerdictKey + blue CSS token triple + filter chip + dashboard KPI card |
| EPROV-01 | User can see ports, CVEs, hostnames, and CPEs in Shodan InternetDB result cards | `cpes` and `tags` already in `raw_stats`; add two entries to `PROVIDER_CONTEXT_FIELDS["Shodan InternetDB"]` |
</phase_requirements>

---

## Summary

This phase adds three zero-auth data sources and one UI completion. The work splits cleanly into backend adapter work (two new Python adapters), frontend display work (new verdict type system-wide, IP Context detail row, Shodan field additions), and the verdict override logic that links CIRCL hashlookup to the summary row.

The existing `ShodanAdapter` in `app/enrichment/adapters/shodan.py` is the canonical reference for all new adapters. Every pattern needed — Protocol conformance, HTTP safety controls, raw_stats dict, SSRF allowlist validation — is already embodied there. The new adapters are straightforward copies with different URLs, field names, and verdict logic.

The most architecturally interesting piece is the "IP Context" row. Unlike every other provider, it carries no verdict badge — it is purely informational metadata. The planner must ensure the frontend renders this row differently: no badge, no stat text, just a special layout. The `createDetailRow()` function in `enrichment.ts` currently always renders a badge, so it needs a non-badge path, or IP Context must be rendered by a separate function.

The `known_good` verdict override requires changes in six places: `VerdictKey` type (TypeScript), `VERDICT_LABELS`, `VERDICT_SEVERITY` array, `computeWorstVerdict()` logic, CSS tokens, and the filter bar/dashboard HTML. The override semantics (known_good beats everything at the summary level) mean `known_good` must sit at a higher severity index than `malicious` in `VERDICT_SEVERITY`, or `computeWorstVerdict()` must use special-case logic. The latter is safer and avoids the conceptual confusion of "known good" being "more severe" than "malicious."

**Primary recommendation:** Implement in task order — (1) Shodan EPROV-01 frontend-only first as a warm-up with zero risk, (2) CIRCL hashlookup adapter + verdict system, (3) ip-api.com adapter + IP Context row.

---

## Standard Stack

### Core (all existing — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | project-pinned | HTTP calls in all adapters | Already used by every adapter |
| `pytest` | project-pinned | Unit test framework | 565 tests already in place |
| Python `unittest.mock` | stdlib | Mock `requests.get` in tests | Pattern used in every adapter test |

### External APIs (zero-auth, no installation)
| API | Base URL | Purpose | Rate Limit |
|-----|----------|---------|------------|
| ip-api.com | `http://ip-api.com/json/{ip}` | GeoIP + rDNS + proxy flags | 45 req/min (free tier) |
| CIRCL hashlookup | `https://hashlookup.circl.lu` | NSRL known-good hash lookup | Best-effort, no hard limit documented |

**Note on ip-api.com protocol:** The free tier uses HTTP (not HTTPS). HTTPS requires a paid pro plan. The existing `validate_endpoint()` in `http_safety.py` parses the URL hostname — it does not enforce HTTPS, so HTTP is compatible with SEC-16. However, using plain HTTP for a metadata-only, non-secret endpoint is acceptable; no API keys or credentials are transmitted.

**Note on ip-api.com `proxy` field semantics:** The `proxy` field covers proxy, VPN, and Tor exit addresses as a single boolean. There is no separate "VPN" flag at the free tier. The CONTEXT.md decision to show a `[proxy]` tag maps directly to this field name.

**Installation:**
```bash
# No new Python packages — requests already installed
# No new npm packages — no frontend dependency changes
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)
```
app/enrichment/adapters/
├── ip_api.py                  # NEW: ip-api.com GeoIP + rDNS + proxy flags
└── hashlookup.py              # NEW: CIRCL hashlookup NSRL known-good

tests/
├── test_ip_api.py             # NEW: unit tests for IPApiAdapter
└── test_hashlookup.py         # NEW: unit tests for HashlookupAdapter
```

### Modified files
```
app/config.py                          # Add ip-api.com and hashlookup.circl.lu to ALLOWED_API_HOSTS
app/enrichment/setup.py                # Register two new adapters; update test count assertions
app/static/src/ts/types/ioc.ts         # Add known_good to VerdictKey, VERDICT_LABELS, VERDICT_SEVERITY
app/static/src/ts/modules/enrichment.ts# known_good override in computeWorstVerdict(); IP Context row rendering
app/static/src/ts/modules/cards.ts     # Add known_good to updateDashboardCounts() counts dict and verdicts array
app/static/src/input.css               # New CSS token triple for known_good; .verdict-known_good; filter/dashboard classes
app/templates/partials/_filter_bar.html    # Add "Known Good" filter button
app/templates/partials/_verdict_dashboard.html  # Add known_good KPI card
```

### Pattern 1: Zero-Auth Adapter (canonical from ShodanAdapter)
**What:** Structural Protocol conformance with `requires_api_key = False`, `is_configured()` always returns `True`, HTTP safety controls on every call.

**When to use:** Any new zero-auth provider.

**Example (from existing `shodan.py`):**
```python
# Source: app/enrichment/adapters/shodan.py

class ShodanAdapter:
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "Shodan InternetDB"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        return True  # Always True — zero-auth

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unsupported type")
        url = f"{BASE_URL}/{ioc.value}"
        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))
        try:
            resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True)
            if resp.status_code == 404:
                return EnrichmentResult(ioc=ioc, provider=self.name, verdict="no_data", ...)
            resp.raise_for_status()
            body = read_limited(resp)
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
        except Exception:
            logger.exception("Unexpected error during lookup for %s", ioc.value)
            return EnrichmentError(ioc=ioc, provider=self.name, error="Unexpected error during lookup")
```

### Pattern 2: ip-api.com Adapter
**What:** GET `http://ip-api.com/json/{ip}?fields=status,message,countryCode,city,as,asname,reverse,proxy,hosting,mobile`

**Key behaviors:**
- `status` field: `"success"` or `"fail"` (with `message` explaining failure)
- `fail` response is NOT an HTTP error — must check `status` before `raise_for_status`
- All requested fields present on success; use `.get()` with defaults
- Returns `EnrichmentResult` with `verdict="no_data"` always — IP Context is purely informational, no threat verdict
- `raw_stats` contains all geo/proxy fields for frontend rendering

**Response shape (success):**
```json
{
  "status": "success",
  "countryCode": "DE",
  "city": "Frankfurt am Main",
  "as": "AS24940 Hetzner Online GmbH",
  "asname": "HETZNER-AS",
  "reverse": "static.24.116.230.95.clients.your-server.de",
  "proxy": false,
  "hosting": true,
  "mobile": false
}
```

**Response shape (failure — private IP, reserved range):**
```json
{
  "status": "fail",
  "message": "private range"
}
```

**Fields to request:** `status,message,countryCode,city,as,asname,reverse,proxy,hosting,mobile`

The `as` field returns the full ASN string like `"AS24940 Hetzner Online GmbH"`. Split on first space to separate number from name, or pass whole string and let frontend format. Using `asname` for just the org name is also available.

### Pattern 3: CIRCL Hashlookup Adapter
**What:** GET `https://hashlookup.circl.lu/lookup/{type}/{hash}`

**Key behaviors:**
- `type` is `md5`, `sha1`, or `sha256` (lowercase)
- 200 = hash found in NSRL → verdict `"known_good"`
- 404 = hash not in database → verdict `"no_data"` (NOT an error — same as Shodan 404 pattern)
- 400 = malformed hash → `EnrichmentError`
- Supports MD5, SHA1, SHA256 IOC types; not IP/domain/URL
- No API key, no auth headers

**Positive response fields (partial — only need to confirm NSRL hit):**
```json
{
  "FileName": "calc.exe",
  "FileSize": "114688",
  "MD5": "EBB33B09B966B01F5EA82B47B09B8E12",
  "SHA-1": "A5C0C...",
  "db": "nsrl_modern_rds",
  "source": "NSRL",
  "hashlookup:trust": 75
}
```

For the adapter, the meaningful signal is simply "200 = found = known_good". Optionally surface `FileName` and `source` in `raw_stats` for the frontend to display.

### Pattern 4: IP Context Row — No-Verdict Special Row
**What:** The IP Context row in `enrichment.ts` cannot use `createDetailRow()` as-is because that function always renders a verdict badge. IP Context must be rendered without a badge.

**Options (Claude's discretion):**
1. Add an optional `noBadge: boolean` parameter to `createDetailRow()` — minimal change, badge skipped when true
2. Create a separate `createContextRow()` function — cleaner separation, no parameter flag pollution

Option 2 is recommended for clarity: the IP Context row is semantically different enough (no verdict participation) to warrant its own function.

**The "first in order" constraint:** IP Context must appear above all other detail rows. The `sortDetailRows()` debounce function reorders rows by verdict severity. IP Context has no `data-verdict` attribute (or uses a special sentinel), so the sort either places it last or ignores it. The simplest solution: give IP Context a `data-verdict="context"` or no `data-verdict` attribute, and modify `sortDetailRows()` to pin rows without a recognized verdict to the top (or always prepend the IP Context row before calling sort, using DOM order rather than sort).

### Pattern 5: known_good Verdict Override Logic
**What:** `computeWorstVerdict()` currently finds the highest-severity verdict across all providers. `known_good` must override all other verdicts at the summary level — even if VT says "malicious", KNOWN GOOD wins.

**Current severity order (VERDICT_SEVERITY):**
```
["error", "no_data", "clean", "suspicious", "malicious"]
```

**Approach — special-case override (recommended over adding known_good to the severity array):**
```typescript
// Source: enrichment.ts computeWorstVerdict() — to be modified
function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  // known_good from any provider overrides everything at summary level
  if (entries.some((e) => e.verdict === "known_good")) {
    return "known_good";
  }
  const worst = findWorstEntry(entries);
  return worst ? worst.verdict : "no_data";
}
```

This keeps `VERDICT_SEVERITY` clean (known_good not in the severity array), and `verdictSeverityIndex("known_good")` returning -1 is fine because IP Context rows are excluded from severity sorting.

**Why not add known_good to VERDICT_SEVERITY?** Adding it above `malicious` (index 5) would make `sortDetailRows()` put CIRCL hashlookup rows at the top, above malicious rows. That's confusing. The detail row sort should remain threat-severity-based.

### Anti-Patterns to Avoid

- **Registering IP Context as a verdict-bearing provider:** IP Context must never participate in `computeConsensus()`, `computeAttribution()`, or `sortDetailRows()` by verdict. It is purely metadata.
- **Making a separate rDNS call:** ip-api.com returns `reverse` (PTR) in the same response. Never add a separate DNS lookup; that would add latency and another outbound host.
- **Using ip-api.com HTTPS without a paid key:** The free tier is HTTP-only. Do not add `https://ip-api.com` to ALLOWED_API_HOSTS — use `ip-api.com` (the library does HTTP).
- **Showing all proxy flags even when false:** Only render flags that are `true`. A residential IP with no flags should show nothing in the flags line.
- **Merging IP Context flags with Shodan tags:** These must stay in separate rows with separate source attribution.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IP geolocation | Custom MaxMind GeoLite2 local DB | ip-api.com JSON API | Already decided in STATE.md; GeoLite2 requires local DB setup, licensing, periodic updates |
| rDNS lookup | Custom DNS resolver via `socket.getfqdn()` | ip-api.com `reverse` field | Same request, zero extra latency, no additional outbound host |
| NSRL hash DB | Local DB download | CIRCL hashlookup API | NSRL is 3+ GB; API is maintained and zero-auth |
| Proxy/VPN detection | IP reputation scoring | ip-api.com `proxy`/`hosting`/`mobile` | Maintained commercial-quality detection, zero-auth |

**Key insight:** Both external APIs do the hard work (maintaining up-to-date datasets) for free. The adapter code is thin wrappers around HTTP calls — no domain logic required beyond parsing the response.

---

## Common Pitfalls

### Pitfall 1: ip-api.com `status: "fail"` Not Checked Before raise_for_status
**What goes wrong:** The API returns HTTP 200 for private IPs and reserved ranges but with `{"status": "fail", "message": "private range"}`. If the adapter only checks HTTP status, it will try to parse a fail response as a success and render empty fields.
**Why it happens:** Follows the "HTTP 200 = success" assumption. ip-api.com breaks this.
**How to avoid:** Check `body["status"] == "success"` after parsing. Return `EnrichmentResult(verdict="no_data", raw_stats={})` for `status == "fail"`.
**Warning signs:** Empty IP Context rows for RFC 1918 addresses (10.x.x.x, 192.168.x.x, etc.).

### Pitfall 2: CIRCL Hashlookup 404 Treated as Error
**What goes wrong:** 404 means "not in NSRL" — it is the expected negative case, not a failure. If treated as an error, every unknown hash produces an error result.
**Why it happens:** Standard HTTP client behavior — `raise_for_status()` raises on 404.
**How to avoid:** Check `resp.status_code == 404` BEFORE `raise_for_status()`. Return `EnrichmentResult(verdict="no_data")` for 404. This is the same pattern as ShodanAdapter.
**Warning signs:** `EnrichmentError` objects appearing for common software hashes.

### Pitfall 3: known_good Verdict in Severity Sort
**What goes wrong:** Adding `known_good` to `VERDICT_SEVERITY` above `malicious` causes CIRCL hashlookup detail rows to sort above malicious rows, making the threat-severity sort misleading.
**Why it happens:** Naive inclusion of new verdict in the severity array.
**How to avoid:** Keep `known_good` out of `VERDICT_SEVERITY`. Use the special-case override in `computeWorstVerdict()` only. Detail rows for CIRCL hashlookup use `"no_data"` severity for sort ordering (or a sentinel that sorts last).
**Warning signs:** CIRCL hashlookup row appearing at top of detail list above Shodan malicious rows.

### Pitfall 4: IP Context Verdict Participating in Consensus/Attribution
**What goes wrong:** IP Context (provider name "IP Context") gets included in `computeConsensus()` and `computeAttribution()`. Consensus count becomes 0/1 (instead of 0/0 when no real providers voted). Attribution may show "IP Context" as the attributing provider.
**Why it happens:** All VerdictEntry objects pushed to `iocVerdicts[ioc_value]` — IP Context would be one of them.
**How to avoid:** Do NOT push IP Context into `iocVerdicts`. The IP Context row is rendered directly into the details container without going through the `VerdictEntry` accumulation pipeline. The backend adapter returns `EnrichmentResult(verdict="no_data")` but the frontend special-cases the "IP Context" provider name to render a context row rather than a verdict row.
**Warning signs:** Consensus badge shows `[0/1]` instead of `[0/0]` on IP-only queries. Attribution shows "IP Context: Not in database".

### Pitfall 5: test_registry_setup.py Provider Count Assertion
**What goes wrong:** `test_registry_has_eight_providers` asserts `len(registry.all()) == 8`. Adding two new adapters breaks this test.
**Why it happens:** The count assertion is exact.
**How to avoid:** Update the test to assert `len(registry.all()) == 10` when the new adapters are registered. Also add `test_registry_contains_ip_context` and `test_registry_contains_hashlookup` tests.
**Warning signs:** `AssertionError: 8 != 10` in CI.

### Pitfall 6: ip-api.com Rate Limit (45 req/min)
**What goes wrong:** Bulk analysis with many IP IOCs hits the 45/min limit. ip-api.com returns HTTP 429 with `X-Rl: 0` and `X-Ttl: N` headers.
**Why it happens:** No rate limiting in the adapter.
**How to avoid:** Treat HTTP 429 as a graceful `EnrichmentError("HTTP 429")` — same as other adapters. The warning banner system in `enrichment.ts` already handles 429 errors and shows a rate-limit banner to the user. No throttling needed in the adapter itself.
**Warning signs:** Rate-limit warning banner appearing for ip-api.com lookups.

### Pitfall 7: Shodan `tags` Field Collision with IP Context Flags
**What goes wrong:** Shodan returns its own `tags` field (e.g., `["cdn", "self-signed"]`). IP Context has proxy/hosting/mobile flags. If these are merged into a single display row, source attribution is lost.
**Why it happens:** Both are "tag-like" boolean/string lists.
**How to avoid:** Keep them in separate rows. Shodan tags go in the `PROVIDER_CONTEXT_FIELDS["Shodan InternetDB"]` entry. IP Context flags go in the `PROVIDER_CONTEXT_FIELDS["IP Context"]` entry. Never merge.

---

## Code Examples

### ip-api.com Adapter Fields Parameter
```python
# Source: ip-api.com docs (https://ip-api.com/docs/api:json)
# Request only the fields we need — saves bandwidth and avoids unused data
IP_API_BASE = "http://ip-api.com/json"
IP_API_FIELDS = "status,message,countryCode,city,as,asname,reverse,proxy,hosting,mobile"

url = f"{IP_API_BASE}/{ioc.value}?fields={IP_API_FIELDS}"
```

### ip-api.com Response Parsing
```python
# status must be checked before treating the body as success data
body = read_limited(resp)  # returns parsed dict

if body.get("status") != "success":
    # Private range, reserved, invalid IP, etc.
    return EnrichmentResult(
        ioc=ioc, provider=self.name, verdict="no_data",
        detection_count=0, total_engines=0, scan_date=None, raw_stats={}
    )

return EnrichmentResult(
    ioc=ioc, provider=self.name, verdict="no_data",
    detection_count=0, total_engines=0, scan_date=None,
    raw_stats={
        "country_code": body.get("countryCode", ""),
        "city":         body.get("city", ""),
        "as":           body.get("as", ""),          # e.g. "AS24940 Hetzner Online GmbH"
        "asname":       body.get("asname", ""),
        "reverse":      body.get("reverse", ""),      # PTR hostname, empty string if none
        "proxy":        body.get("proxy", False),
        "hosting":      body.get("hosting", False),
        "mobile":       body.get("mobile", False),
    }
)
```

### CIRCL Hashlookup Adapter
```python
# Source: https://hashlookup.circl.lu/swagger.json
HASHLOOKUP_BASE = "https://hashlookup.circl.lu"

# Map IOCType to API path segment
_TYPE_MAP = {
    IOCType.MD5:    "md5",
    IOCType.SHA1:   "sha1",
    IOCType.SHA256: "sha256",
}

url = f"{HASHLOOKUP_BASE}/lookup/{_TYPE_MAP[ioc.type]}/{ioc.value}"

# 200 = found in NSRL -> known_good
# 404 = not in database -> no_data (not an error)
if resp.status_code == 404:
    return EnrichmentResult(ioc=ioc, provider=self.name, verdict="no_data",
                            detection_count=0, total_engines=0, scan_date=None, raw_stats={})
resp.raise_for_status()
body = read_limited(resp)
# Surface minimal metadata for the frontend
return EnrichmentResult(
    ioc=ioc, provider=self.name, verdict="known_good",
    detection_count=1, total_engines=1, scan_date=None,
    raw_stats={
        "file_name": body.get("FileName", ""),
        "source":    body.get("source", "NSRL"),
        "db":        body.get("db", ""),
    }
)
```

### Shodan PROVIDER_CONTEXT_FIELDS Addition (frontend-only, EPROV-01)
```typescript
// Source: app/static/src/ts/modules/enrichment.ts lines 248-252
// Current Shodan entry — add cpes and tags:
"Shodan InternetDB": [
  { key: "ports",     label: "Ports",     type: "tags" },
  { key: "vulns",     label: "Vulns",     type: "tags" },
  { key: "hostnames", label: "Hostnames", type: "tags" },
  { key: "cpes",      label: "CPEs",      type: "tags" },  // ADD
  { key: "tags",      label: "Tags",      type: "tags" },  // ADD
],
```

### known_good VerdictKey Addition
```typescript
// Source: app/static/src/ts/types/ioc.ts
// Add known_good to VerdictKey union
export type VerdictKey =
  | "error"
  | "no_data"
  | "clean"
  | "suspicious"
  | "malicious"
  | "known_good";   // NEW

// Add label
export const VERDICT_LABELS: Record<VerdictKey, string> = {
  malicious:   "MALICIOUS",
  suspicious:  "SUSPICIOUS",
  clean:       "CLEAN",
  no_data:     "NO DATA",
  error:       "ERROR",
  known_good:  "KNOWN GOOD",   // NEW
} as const;

// VERDICT_SEVERITY does NOT include known_good (see anti-pattern)
// verdictSeverityIndex("known_good") returns -1, which is acceptable
```

### known_good CSS Token Triple
```css
/* Source: app/static/src/input.css — add to :root block */
/* Using blue-500/blue-950/blue-400 — outside the red/amber/green threat spectrum */
--verdict-known-good-text:   #60a5fa;   /* blue-400 */
--verdict-known-good-bg:     #172554;   /* blue-950 */
--verdict-known-good-border: #3b82f6;   /* blue-500 */

/* Verdict badge class */
.verdict-known_good {
    background-color: var(--verdict-known-good-bg);
    color: var(--verdict-known-good-text);
    border-color: var(--verdict-known-good-border);
}

/* IOC card left border */
.ioc-card[data-verdict="known_good"] { border-left-color: var(--verdict-known-good-border); }

/* Verdict label on card header */
.verdict-label--known_good {
    background-color: var(--verdict-known-good-bg);
    color: var(--verdict-known-good-text);
    border: 1px solid var(--verdict-known-good-border);
}

/* KPI card top border */
.verdict-kpi-card--known_good { border-top-color: var(--verdict-known-good-border); }

/* Filter button */
.filter-btn--known_good {
    border-color: var(--verdict-known-good-border);
    color: var(--verdict-known-good-text);
    background-color: var(--verdict-known-good-bg);
}
```

### IP Context PROVIDER_CONTEXT_FIELDS Entry
```typescript
// Provider name must match adapter's `name` attribute exactly
"IP Context": [
  { key: "geo",     label: "Location", type: "text" },   // formatted by frontend: "DE · Frankfurt · AS24940 (Hetzner)"
  { key: "reverse", label: "PTR",      type: "text" },
  { key: "flags",   label: "Flags",    type: "tags" },   // array of true-flag strings e.g. ["hosting"]
],
```

**Note:** The adapter can build the `geo` formatted string in Python (simpler) or pass raw fields and let the frontend format (more flexible). Recommend building in Python — the compact format `"DE · Frankfurt · AS24940 (Hetzner Online GmbH)"` is a display concern that doesn't vary per user.

**Alternative for flags:** Pass `proxy`, `hosting`, `mobile` as individual booleans and let frontend filter for true values, or pass them as a pre-filtered list of tag strings. The latter is simpler for the frontend `type: "tags"` renderer which already handles string arrays.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MaxMind GeoLite2 local DB | ip-api.com JSON API | STATE.md decision (2026-03-12) | No DB download, no licensing, always current |
| No hash known-good detection | CIRCL hashlookup NSRL | Phase 01 | Reduces false positives on common OS files |
| Shodan CPEs/tags fetched but hidden | All Shodan fields rendered | Phase 01 (EPROV-01) | Two-line change in PROVIDER_CONTEXT_FIELDS |

**Deprecated/outdated:**
- VERDICT_SEVERITY without known_good: must be updated, but known_good is NOT added to the array (override logic instead)
- `test_registry_has_eight_providers`: count becomes 10 after this phase

---

## Open Questions

1. **IP Context row rendering path (verdict-entry vs. separate path)**
   - What we know: `createDetailRow()` always renders a verdict badge; IP Context must not have one
   - What's unclear: Whether to add a `noBadge` parameter flag or a separate `createContextRow()` function
   - Recommendation: Separate function — IP Context is semantically different enough

2. **IP Context row position during sort**
   - What we know: `sortDetailRows()` reorders by `data-verdict` severity; rows without a recognized verdict get `verdictSeverityIndex(-1)` = sorted last
   - What's unclear: Best sentinel value so IP Context stays first (not last)
   - Recommendation: Give IP Context row `data-verdict="context"` which returns -1 from `verdictSeverityIndex`. Modify `sortDetailRows()` to handle "context" verdict as "pin to top" (or simply prepend IP Context row after sort).

3. **ip-api.com for IPv6**
   - What we know: ip-api.com accepts IPv6 addresses in the URL path
   - What's unclear: Whether all geo/proxy fields are populated for IPv6 addresses
   - Recommendation: Support both IPV4 and IPV6 in `supported_types`. Return graceful `no_data` if fields are empty (private range pattern handles this).

4. **IP Context row in `iocVerdicts` accumulation**
   - What we know: VerdictEntry accumulation drives consensus and attribution; IP Context must not participate
   - What's unclear: Whether to filter by provider name in `renderEnrichmentResult()` or handle at a higher level
   - Recommendation: In `renderEnrichmentResult()`, check `if result.provider === "IP Context"` and branch to a separate rendering path that skips VerdictEntry accumulation and calls `createContextRow()` instead of `createDetailRow()`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (stdlib + unittest.mock) |
| Config file | `pyproject.toml` or `pytest.ini` (check project root) |
| Quick run command | `python3 -m pytest tests/test_ip_api.py tests/test_hashlookup.py -x -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IPINT-01 | IPApiAdapter returns country/city/ASN in raw_stats | unit | `python3 -m pytest tests/test_ip_api.py -x -q` | Wave 0 |
| IPINT-02 | IPApiAdapter returns reverse PTR in raw_stats | unit | `python3 -m pytest tests/test_ip_api.py::TestLookupFound::test_reverse_dns -x` | Wave 0 |
| IPINT-03 | IPApiAdapter returns proxy/hosting/mobile flags; only-true flags rendered | unit | `python3 -m pytest tests/test_ip_api.py::TestProxyFlags -x` | Wave 0 |
| IPINT-01/02/03 | ip-api.com hostname in ALLOWED_API_HOSTS | unit | `python3 -m pytest tests/test_ip_api.py::TestAllowedHostsIntegration -x` | Wave 0 |
| HINT-01 | HashlookupAdapter returns known_good verdict for 200 response | unit | `python3 -m pytest tests/test_hashlookup.py::TestLookupFound -x` | Wave 0 |
| HINT-01 | HashlookupAdapter returns no_data for 404 (not error) | unit | `python3 -m pytest tests/test_hashlookup.py::TestLookupNotFound -x` | Wave 0 |
| HINT-02 | known_good in VerdictKey type, VERDICT_LABELS, CSS (TypeScript compile + CSS) | type-check | `make typecheck` | ❌ code change |
| EPROV-01 | Shodan raw_stats already has cpes/tags; frontend renders them | unit (existing) | `python3 -m pytest tests/test_shodan.py::TestLookupFound::test_raw_stats_contains_ports_vulns_tags -x` | ✅ |
| EPROV-01 | PROVIDER_CONTEXT_FIELDS has cpes+tags entries for Shodan | manual/visual | Browser smoke test | ❌ visual only |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_ip_api.py tests/test_hashlookup.py tests/test_shodan.py tests/test_registry_setup.py -x -q`
- **Per wave merge:** `python3 -m pytest -q`
- **Phase gate:** Full suite green (565 + new tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ip_api.py` — covers IPINT-01, IPINT-02, IPINT-03 (must be written before adapter implementation per TDD)
- [ ] `tests/test_hashlookup.py` — covers HINT-01 (must be written before adapter implementation per TDD)
- [ ] Update `tests/test_registry_setup.py` — `test_registry_has_eight_providers` count assertion fails after adding 2 new adapters; update to 10 + add provider-name tests

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/enrichment/adapters/shodan.py`, `app/enrichment/setup.py`, `app/config.py`, `app/enrichment/http_safety.py`, `app/enrichment/provider.py`, `app/enrichment/models.py` — all patterns confirmed by reading source
- Direct codebase inspection: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/types/ioc.ts`, `app/static/src/ts/modules/cards.ts`, `app/static/src/ts/modules/filter.ts` — all frontend patterns confirmed
- Direct codebase inspection: `app/static/src/input.css` — all verdict CSS patterns confirmed
- Direct codebase inspection: All template files — HTML structure confirmed

### Secondary (MEDIUM confidence)
- [ip-api.com JSON API docs](https://ip-api.com/docs/api:json) — WebFetch verified; confirmed `proxy`, `hosting`, `mobile` field names, `reverse` for PTR, rate limit of 45/min, free tier HTTP-only
- [CIRCL hashlookup service page](https://www.circl.lu/services/hashlookup/) — WebFetch verified; confirmed endpoints `/lookup/md5/{hash}`, `/lookup/sha1/{hash}`, `/lookup/sha256/{hash}`, 404=not found, 200=found, no auth required
- [hashlookup swagger.json](https://hashlookup.circl.lu/swagger.json) — WebFetch verified endpoint structure

### Tertiary (LOW confidence)
- [hashlookup gist examples](https://gist.github.com/adulau/4191d44e30fc01df38f1d5fe605fa920) — exact positive response JSON shape (FileName, FileSize, MD5, SHA-1, db, source fields); not independently verified but consistent with swagger.json structure

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; external APIs confirmed via official docs
- Architecture: HIGH — all patterns read directly from existing codebase; no guesswork
- Pitfalls: HIGH — derived from direct code analysis of the exact functions that will be modified

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (ip-api.com free tier terms are stable; CIRCL hashlookup endpoint is long-lived)
