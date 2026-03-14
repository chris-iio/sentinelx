# Feature Research

**Domain:** Threat intelligence enrichment — DNSBL, public threat feeds, RDAP, ASN/BGP
**Milestone:** v7.0 Free Intel
**Researched:** 2026-03-15
**Confidence:** HIGH (DNSBL mechanism, RDAP protocol status); MEDIUM (specific provider choices, rate limits)

---

## Context: This Is a Subsequent Milestone

The app already has 13 providers, per-IOC detail pages, export, bulk input, SQLite cache, and filter bar.
This research covers ONLY the four new capabilities and the one removal task for v7.0.

Existing zero-auth providers (already shipping): Shodan InternetDB, CIRCL Hashlookup, ip-api.com,
DNS Records, crt.sh, ThreatMiner. The new providers follow the same Provider Protocol pattern:
one adapter file + one `registry.register()` call in `setup.py`. No orchestrator changes required.

---

## How Each Feature Domain Works

### DNSBL Reputation Checks

**Mechanism:** Pure DNS. Reverse the IP octets, append the blacklist zone, query for an A record.
Example: for IP `1.2.3.4`, query `4.3.2.1.zen.spamhaus.org`. If the DNS response returns any A
record, the IP is listed. NXDOMAIN means not listed. No HTTP calls — uses dnspython, which is
already installed and used by the existing DnsAdapter.

**For domains (DBL):** Prepend the domain to the zone: `example.com.dbl.spamhaus.org`.

**Return data:** Which list(s) hit, return code meaning (spam source vs botnet vs policy block),
and an overall "listed on N of N checked" summary. There is no confidence score — it is binary
listed/not-listed per zone.

**Key lists — free, no auth, actively maintained:**

| List | Zone | Covers | IOC Types |
|------|------|--------|-----------|
| Spamhaus ZEN | `zen.spamhaus.org` | SBL + CSS + XBL + PBL combined (spam + botnet + exploited hosts + policy) | IPv4 |
| Spamhaus DBL | `dbl.spamhaus.org` | Spam/phishing/malware domains | Domain |
| SURBL multi | `multi.surbl.org` | Malicious URLs/domains across multiple feeds | Domain |
| Barracuda | `b.barracudacentral.org` | Spam source IPs | IPv4 |
| SpamCop | `bl.spamcop.net` | Spam source IPs (user-reported) | IPv4 |

**Rate limits:** Spamhaus free public mirrors enforce fair-use for low-volume non-commercial use.
A local analyst triage tool running a few checks per session is well within limits. Commercial
email filtering requires a paid DQS subscription — not applicable here.

**Important:** Do NOT use public DNS resolvers (8.8.8.8, 1.1.1.1) for DNSBL queries. Some public
resolvers hijack NXDOMAIN responses (return synthetic A records), which breaks DNSBL negative
results — a listed IP could appear not listed. Use `dns.resolver.Resolver(configure=True)` to
rely on the system resolver, matching the existing DnsAdapter pattern.

**Verdict mapping:**
- Any hit → `malicious` — DNSBL listing is an explicit flagging action by list operators
- No hits across all checked zones → `clean` — affirmative signal: checked N lists, found on none
- DNS error / timeout → `error`

This contrasts with providers like ip-api.com that return `no_data`. DNSBL is a reputation signal
with a binary outcome, warranting real verdicts.

---

### Public Threat Feed Lookups

**Mechanism:** HTTP to abuse.ch endpoints. Check whether a specific IP appears in known-bad C2
infrastructure databases.

**Key providers (free):**

| Provider | Endpoint | Covers | Auth |
|----------|----------|--------|------|
| Feodo Tracker | `feodotracker.abuse.ch` | Botnet C2 IPs: Dridex, Emotet, TrickBot, QakBot, BazarLoader | None — public JSON blocklist |
| ThreatFox | `threatfox-api.abuse.ch` | IP:port, domain, URL, hash IOCs with malware family | Requires free abuse.ch Auth-Key |

**Feodo Tracker detail:** Publishes a bulk JSON blocklist refreshed every 5 minutes. No per-IP
lookup API exists — the integration is to fetch the full JSON blocklist and check in-memory or
cache in SQLite. Fields include: `ip_address`, `port`, `status`, `last_online`, `malware`,
`country`, `as_number`, `as_name`, `abuse_contact_email`. The full list is approximately 200KB
JSON — small enough to hold in memory or in the existing SQLite cache with TTL.

**ThreatFox detail:** Has a per-IOC search API (`search_ioc` POST method). Requires a free
Auth-Key from the abuse.ch Authentication Portal — same portal as existing MalwareBazaar and
URLhaus keys. Returns: IOC type, malware family, threat type (botnet_cc, payload_delivery, etc.),
confidence level, first/last seen timestamps, reporter, tags, associated samples (with hashes).
Supports IP:port, domain, URL, MD5, SHA256.

**ThreatFox vs existing ThreatFox provider:** The existing ThreatFox adapter (TFAdapter) already
queries ThreatFox. Check whether the existing adapter already covers the needed query types before
creating a new Feodo-specific adapter. Feodo Tracker is additive: it covers C2 IPs specifically,
which ThreatFox also covers — but Feodo's dedicated blocklist is authoritative for the specific
botnet families it tracks.

**Note on PhishTank:** New user registration disabled since 2020. Cannot obtain API key. Not viable.

**Note on URLhaus:** Already a provider (v4.0, free abuse.ch key). Covers malware distribution
URLs/domains/hashes/IPs. Feodo Tracker adds dedicated C2 IP coverage that URLhaus does not
emphasize. Do not duplicate URLhaus functionality.

**Verdict mapping:**
- Found in feed → `malicious` with malware family name in attribution fields
- Not found → `clean` (checked, not present — affirmative negative)

---

### RDAP Registration Data

**Mechanism:** HTTPS REST. IANA maintains bootstrap files mapping TLDs to authoritative RDAP
servers. The `rdap.org` proxy handles bootstrap discovery automatically — query
`https://rdap.org/domain/example.com` and it issues a 302 redirect to the authoritative registry
RDAP endpoint, returning the registry's response transparently. For IPs,
`https://rdap.org/ip/1.2.3.4` routes to the correct RIR (ARIN, RIPE, APNIC, LACNIC, AfriNIC).

**2025 RDAP status:** As of January 28, 2025, ICANN officially sunsetted WHOIS for all gTLD
registries. RDAP is now the definitive and authoritative source for domain registration data.
RDAP returns structured JSON per RFC 9083 — machine-readable, standardized, no text parsing needed.

**For domains — high-value fields:**

| Field | JSON path | Triage value |
|-------|-----------|--------------|
| Creation date | `events[?eventAction=="registration"].eventDate` | Domain age — "registered 3 days ago" is a major red flag |
| Expiration date | `events[?eventAction=="expiration"].eventDate` | Short-TTL domains common in malware campaigns |
| Registrar name | `entities[?roles contains "registrar"].vcard` | Some registrars have known abuse patterns |
| Nameservers | `nameservers[*].ldhName` | Fast-flux NS patterns reveal bulletproof hosting |
| Status | `status[]` | clientTransferProhibited, pendingDelete, etc. |

**For IPs — high-value fields:**

| Field | JSON path | Triage value |
|-------|-----------|--------------|
| Network name | `name` | e.g., "HETZNER-CLOUD" — immediately identifies hosting provider |
| CIDR block | `startAddress` + `endAddress` | Subnet ownership context |
| Organization | `entities[?roles contains "registrant"].vcard` | Who officially owns this network |
| Abuse contact | `entities[?roles contains "abuse"].vcard` | For incident reporting |
| Allocation date | `events[?eventAction=="registration"].eventDate` | Network block age |

**GDPR / privacy caveat:** Registrant contact info is heavily GDPR-redacted for European
registrars and many privacy-shield registrations. Do not surface registrant contact — it will be
"REDACTED FOR PRIVACY" for the majority of domains. The high-value fields (creation date,
registrar, nameservers) survive GDPR redaction and remain useful.

**Domain age calculation:** `created N days ago` is the highest-value output. Adversaries
rapidly register and abandon domains. A domain under 30 days old warrants immediate escalation.
Display as both the exact ISO date and a human-readable "X days ago" label.

**Verdict mapping:** `no_data` — registration data is context, not a threat verdict. This matches
the existing pattern for ip-api.com, DNS Records, crt.sh. The analyst sees creation date and draws
their own conclusion.

**rdap.org redirect behavior:** Querying `rdap.org` results in a 302 redirect to the authoritative
server. This adapter must use `allow_redirects=True`, which is a deliberate exception to the
existing `allow_redirects=False` convention used by all other HTTP adapters. This exception must
be documented explicitly in the adapter docstring.

**Python library vs plain requests:** `whoisit` (PyPI) and `whodap` (PyPI) are both available.
Recommendation: use plain `requests` to `rdap.org` — already a dependency, straightforward JSON
parsing, avoids adding a new library for a REST call. The RFC 9083 JSON structure is documented
and stable.

---

### ASN/BGP Intelligence

**What ip-api.com already provides:** The existing IPApiAdapter already returns ASN data. The `as`
field contains `"AS24940 Hetzner Online GmbH"` and `asname` contains `"HETZNER-ONLINE"`. This is
already formatted into the `geo` display string as `"CC · City · AS12345 (ISP Name)"`.

**What is missing:** ASN type classification (hosting vs ISP vs residential vs datacenter), the
CIDR prefix, RIR allocation, and allocation date. These are the differentiating fields that make
ASN data actionable for network-level pivoting.

**Team Cymru DNS-based ASN lookup (zero-auth):**

Query `{reversed_ip}.origin.asn.cymru.com` as a TXT record via dnspython.
Response format: `"15169 | 8.8.8.0/24 | US | arin | 1992-12-01"`
Fields: ASN number, CIDR prefix, country code, RIR, allocation date.

This is zero-auth, DNS-based (uses dnspython which is already installed), adds no new HTTP
dependency, and requires no account or API key. Rate limit caveat: the Cymru whois server blocks
abusive bulk usage patterns (large batches of individual queries instead of bulk mode). Single
per-IOC lookups as part of analyst triage sessions are fine.

**ipinfo.io Lite (alternative):** Provides ASN + org name + domain in JSON response. Requires a
free token (no credit card, unlimited requests on Lite tier). Adds a new account dependency.
Given Team Cymru provides equivalent data via DNS with zero auth, ipinfo.io Lite adds marginal
value and is not recommended for MVP.

**Recommended approach for v7.0:** Extend coverage with a dedicated ASN/BGP adapter using Team
Cymru DNS. This adds CIDR prefix + RIR + allocation date on top of what ip-api.com already shows.
Single adapter, DNS-based, zero new dependencies, zero new accounts.

**Verdict mapping:** `no_data` — network ownership is context, not a verdict. Hosting provider
classification is informational (legitimate cloud infrastructure hosts malicious payloads routinely).

---

## Feature Landscape

### Table Stakes (Analysts Expect These)

Features an analyst expects from a tool claiming "DNSBL + threat feed + RDAP + ASN" capability.
Missing these makes the feature feel incomplete or underbaked.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| DNSBL check for IPs against Spamhaus ZEN | Spamhaus ZEN is the industry-standard first check; every IP reputation tool includes it | LOW | Pure DNS via dnspython, reverse IP + A record query; already-available library |
| DNSBL check for domains against Spamhaus DBL | Domain blocklist complement to IP checks; email security staple | LOW | Prepend domain to DBL zone, same dnspython pattern as IP |
| DNSBL result names which list(s) hit, not just "listed" | Analysts need to know if SBL (spam source) vs XBL (botnet/exploited) vs PBL (policy block) | LOW | Return code decoding table mapped to human-readable names |
| "Not listed on any DNSBL" shown explicitly as CLEAN | Absence of listing is a positive signal; must not silently show as NO RECORD | LOW | Verdict = `clean` when all checked zones return NXDOMAIN |
| RDAP creation date for domains | Domain age is the primary triage signal; "registered 3 days ago" is immediately actionable | LOW | RDAP `events[registration].eventDate`, format as "X days ago" |
| RDAP registrar name for domains | Registrar context (pattern recognition across incidents) | LOW | `entities` array, role = "registrar" |
| RDAP nameservers for domains | Nameserver patterns reveal bulletproof hosting, fast-flux | LOW | `nameservers` array in RDAP response |
| RDAP network block name + org for IPs | Who owns this IP block — direct answer to "whose infrastructure is this?" | LOW | `name` + registrant entity in IP RDAP response |
| ASN number and CIDR prefix for IPs | ASN is standard; CIDR prefix enables subnet-level pivoting | LOW | ip-api.com already returns ASN; Team Cymru DNS adds prefix |
| Feodo Tracker C2 check for IPs | Well-known C2 list; zero-auth; direct threat signal for botnet infrastructure | MEDIUM | Bulk JSON download + in-memory or SQLite-cached check |
| Remove annotations (notes + tags) | Scope reduction per v7.0 plan — removes complexity, not a user-facing feature loss for triage | MEDIUM | Touches routes, TS modules, templates, SQLite store |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Domain age displayed as "registered N days ago" with visual age indicator | "Registered 2 days ago" is instant analyst signal; ISO date requires mental arithmetic | LOW | Client-side formatting from RDAP creation timestamp; color-code: red if < 30 days |
| DNSBL shows count summary "Listed on 2/5 checked" in summary badge | Triage at a glance without expanding detail rows | LOW | Aggregate in adapter, surface in summary row detection_count / total_engines fields |
| RDAP covers both domains AND IPs (single unified adapter) | Other tools split domain WHOIS and IP WHOIS into separate workflows | MEDIUM | Single adapter routes by IOC type: DOMAIN → rdap.org/domain/, IPv4/IPv6 → rdap.org/ip/ |
| DNSBL queries multiple lists in parallel | dnspython resolves each zone in ~50ms; 5 parallel queries < 500ms total | LOW | Loop of DNS resolver calls; no async required — each resolves quickly and sequentially is fine for 5-6 zones |
| Team Cymru CIDR prefix + RIR via DNS (zero new dependency) | Subnet ownership enables "is this the same /24 as other malicious IPs?" | LOW | TXT record query to origin.asn.cymru.com; uses existing dnspython |
| Feodo Tracker malware family attribution | Returns botnet family name alongside "malicious" verdict — high analyst value for family tracking | MEDIUM | `malware` field from Feodo JSON; map to canonical family names |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Check 50+ DNSBL zones | More lists = more coverage | Beyond 5-6 high-quality zones, lists have poor maintenance, high false positives, and DNS latency multiplies; checking 50 lists takes 5-10x longer for marginal signal gain | Check 5-6 actively maintained high-quality lists; show count clearly |
| WHOIS instead of RDAP | Familiar to analysts; widely referenced | ICANN sunsetted WHOIS for gTLDs January 2025; plain-text format is inconsistent across registrars; requires custom parsers per registrar; GDPR-redacted to near-uselessness | Use RDAP — machine-readable JSON, authoritative, standardized; already the successor |
| Registrant contact info from RDAP | "Who owns this domain?" is a natural question | GDPR redaction returns "REDACTED FOR PRIVACY" for the vast majority of European-registered domains; surfaces noise, not signal | Show registrar + nameservers + creation date; skip registrant contact entirely |
| BGP path visualization / AS path graph | Visual BGP routing looks impressive in demos | BGP routing paths change dynamically; a static snapshot is misleading; rendering AS path graphs requires significant frontend work for low triage value | Show ASN number, org, prefix, RIR as structured text fields |
| PhishTank phishing URL lookup | Well-known phishing database | New user registration closed since 2020; cannot obtain API key for new integrations | URLhaus already integrated for malware distribution URLs; ThreatFox covers phishing C2 |
| DNSBL via public resolvers (8.8.8.8, 1.1.1.1) | Easy to configure well-known public DNS | Some public resolvers use NXDOMAIN hijacking (returning synthetic A records for negative queries), which corrupts DNSBL results — listed IPs appear clean | Use `dns.resolver.Resolver(configure=True)` (system resolver); matches existing DnsAdapter pattern |
| Keep annotations (notes + tags) | Analysts want to mark IOCs for case management | Couples triage tool to case management workflow — better done in a dedicated TIP/SIEM; adds UI and backend complexity; conflicts with v7.0 simplification goal | Remove entirely; direct analysts to their TIP for case notes |
| ipinfo.io Lite for ASN | More ASN fields (ASN type classification) | Requires new account signup and token management; marginal value over Team Cymru + ip-api.com combined | Team Cymru DNS provides CIDR + RIR for free with zero auth |

---

## Feature Dependencies

```
DNSBL Provider (IP)
    requires──> dnspython (already installed — DnsAdapter uses it)
    requires──> Provider Protocol adapter pattern (in place)
    uses pattern──> same as existing DnsAdapter (no new library)

DNSBL Provider (Domain)
    requires──> dnspython (already installed)
    shares pattern──> DNSBL Provider (IP) — same adapter or sibling adapter

RDAP Provider
    requires──> requests (already installed)
    requires──> rdap.org added to SSRF allowlist in config.py
    requires──> allow_redirects=True (documented exception to project convention)
    covers──> DOMAIN + IPv4 + IPv6 (single adapter, routes by ioc.type)

ASN/BGP Provider (Team Cymru)
    requires──> dnspython (already installed)
    extends──> ip-api.com context (already returns ASN; this adds CIDR + RIR)
    covers──> IPv4 + IPv6

Feodo Tracker Provider
    requires──> requests (already installed)
    requires──> feodotracker.abuse.ch added to SSRF allowlist in config.py
    requires──> bulk-list caching strategy (SQLite with TTL or in-memory)
    covers──> IPv4 only

Annotations Removal
    removes──> app/annotations/__init__.py and store.py
    removes──> /api/annotations/* routes from app/routes.py
    removes──> AnnotationStore initialization from app/__init__.py
    removes──> annotations.ts TypeScript module
    removes──> annotation UI from app/templates/detail.html
    removes──> tag filter chip UI from app/templates/results.html
    removes──> tag nodes from graph.ts (or simplify graph without tags)
    removes──> annotation unit tests and E2E scenarios
    is independent of──> new providers (can be phased separately)
    should happen before──> new provider development (cleaner test surface)
```

### Dependency Notes

- **DNSBL requires dnspython** which is already present. The DnsAdapter (dns_lookup.py) uses it
  for A/MX/NS/TXT resolution. The DNSBL adapter uses the same library for A record queries to
  DNSBL zones. Zero new dependencies.

- **RDAP requires `rdap.org` in the SSRF allowlist.** The rdap.org proxy transparently returns
  the authoritative RIR or registry response, so only one allowlist entry is needed rather than
  entries for all RIRs (rdap.arin.net, rdap.db.ripe.net, rdap.apnic.net, etc.). The adapter must
  use `allow_redirects=True` — document this as an intentional deviation from the project default.

- **Feodo Tracker uses a bulk-list pattern** unlike all other providers. All existing adapters
  make per-IOC HTTP calls. Feodo requires a different pattern: fetch the full blocklist, cache it,
  then check membership. Two options: (1) in-memory set populated once at adapter construction
  time and refreshed on TTL, or (2) SQLite cache row per IP with a timestamp. Option 1 is simpler
  for a single-user app; option 2 aligns with existing CacheStore patterns and survives restarts.

- **Annotations removal is independent** of the new providers. It can be its own phase,
  completed first. This reduces test noise throughout the rest of the milestone.

- **DNSBL and ASN/BGP both use DNS (dnspython) not HTTP.** They do not require SSRF allowlist
  entries. DNS uses port 53 directly, same as the existing DnsAdapter.

---

## MVP Definition (v7.0)

### Launch With

These are the four specified feature areas plus the one removal. All are required for v7.0.

- [ ] Remove annotations entirely — notes, tags, AnnotationStore, tag filter UI, annotations.ts,
  tag nodes in graph.ts, /api/annotations routes, annotations.db documentation for users
- [ ] DNSBL provider for IPs — Spamhaus ZEN + Barracuda + SpamCop (3 zones minimum); dnspython
  A record queries; verdict `malicious` on any hit with hit list names, `clean` when all NXDOMAIN
- [ ] DNSBL provider for domains — Spamhaus DBL + SURBL multi (2 zones minimum); same DNS pattern
- [ ] RDAP provider — domains (creation date, registrar, nameservers) and IPs (org, network block,
  country) via rdap.org; verdict `no_data`; creation date formatted as human-readable age
- [ ] ASN/BGP provider for IPs — Team Cymru DNS TXT query for CIDR prefix + RIR + allocation date;
  verdict `no_data`; supplements existing ip-api.com ASN field
- [ ] Feodo Tracker provider for IPs — fetch and cache JSON blocklist; verdict `malicious` on hit
  with malware family; verdict `clean` when not found
- [ ] SSRF allowlist updates — add `rdap.org` and `feodotracker.abuse.ch` to ALLOWED_API_HOSTS

### Add After Validation (v7.x)

- [ ] SORBS DNSBL as additional IP zone — if analysts request more coverage
- [ ] DNSBL listed-count in summary badge "Listed 2/5" — once baseline DNSBL is working
- [ ] ThreatFox IOC search for domains/URLs/hashes — if analysts want malware family attribution
  beyond Feodo Tracker IPs (requires same free abuse.ch Auth-Key as existing MalwareBazaar key)

### Future Consideration (v8+)

- [ ] RDAP abuse contact email extraction for IPs — useful for incident reporting but requires
  complex entity traversal in RDAP response
- [ ] DNSBL for IPv6 — technically supported by most zones but IPv6 IOCs are rare in triage;
  IPv6 reversal uses nibble notation (32 hex chars reversed), more complex than IPv4
- [ ] Additional threat feeds (Abuse.ch SSL blacklist) — diminishing returns beyond core set

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Remove annotations | HIGH (simplifies app, aligns v7.0 goal) | MEDIUM (routes, TS, templates, SQLite) | P1 |
| DNSBL for IPs (Spamhaus ZEN et al.) | HIGH (direct reputation signal, zero-auth) | LOW (dnspython DNS queries, no new libs) | P1 |
| RDAP domain (creation date + registrar + NS) | HIGH (domain age is top triage signal, WHOIS sunset means RDAP is now the standard) | LOW (requests to rdap.org, JSON parsing) | P1 |
| Feodo Tracker C2 feed for IPs | HIGH (zero-auth, active C2 botnet list, direct malicious verdict) | MEDIUM (bulk list caching, not per-IP API) | P1 |
| RDAP IP (network block + org) | MEDIUM (supplements ip-api.com context) | LOW (same RDAP adapter, different path) | P2 |
| DNSBL for domains (DBL + SURBL) | MEDIUM (useful for email-origin domains; IP DNSBL is higher priority) | LOW (same DNS pattern as IP) | P2 |
| ASN/BGP via Team Cymru (CIDR + RIR) | MEDIUM (CIDR prefix adds analyst value for subnet pivoting) | LOW (dnspython TXT record, zero new deps) | P2 |
| DNSBL listed-count summary badge | LOW (nice-to-have UX polish) | LOW | P3 |

**Priority key:**
- P1: Must have for v7.0 launch
- P2: Should have, include in v7.0 if schedule permits
- P3: Nice to have, v7.x

---

## IOC Type Coverage by New Provider

| Provider | IPv4 | IPv6 | Domain | URL | Hash | CVE |
|----------|------|------|--------|-----|------|-----|
| DNSBL | YES | note | YES | — | — | — |
| RDAP | YES | YES | YES | — | — | — |
| Feodo Tracker | YES | — | — | — | — | — |
| ASN/BGP (Team Cymru) | YES | YES | — | — | — | — |

IPv6 DNSBL note: technically supported but requires nibble-format reversal (32 hex chars reversed
one at a time, dot-separated) rather than simple octet reversal. Omit from MVP — rare in triage.

---

## Implementation Notes (for Roadmap Phases)

### DNSBL Adapter Implementation Pattern

```python
# IP check: reverse octets, append zone, query A record
# 1.2.3.4 -> query 4.3.2.1.zen.spamhaus.org
# Hit = any A record returned; NXDOMAIN = not listed
reversed_ip = ".".join(reversed(ip.split(".")))
query = f"{reversed_ip}.{zone}"

# Domain check: prepend domain to zone
# example.com -> query example.com.dbl.spamhaus.org
query = f"{domain}.{zone}"
```

Both patterns use `dns.resolver.Resolver(configure=True)` from dnspython — identical to
DnsAdapter. The DNSBL adapter loops over a configured list of zones; each zone produces a
hit/miss result. Aggregate results feed detection_count (hits) and total_engines (zones checked).

### RDAP Adapter Implementation Pattern

```python
# Use rdap.org as bootstrap proxy
# Domains: GET https://rdap.org/domain/example.com
# IPs:     GET https://rdap.org/ip/1.2.3.4
# rdap.org issues 302 -> follow to authoritative registry/RIR
# allow_redirects=True is REQUIRED here (intentional exception to project default)
```

Parse RFC 9083 JSON. Extract events for creation date, nameservers array, entities for registrar.
For IPs: extract name, startAddress, endAddress, country from top-level fields.

### Feodo Tracker Integration Pattern

```python
# Bulk fetch: GET https://feodotracker.abuse.ch/downloads/ipblocklist.json
# Returns list of objects with ip_address, port, malware, status fields
# Cache strategy options:
#   A) In-memory set at adapter construction, TTL-refresh on lookup miss
#   B) SQLite rows in existing cache DB with timestamp, refresh on TTL expiry
# Option B recommended: survives restarts, consistent with CacheStore
```

### Annotations Removal Scope

Files to remove or modify:

| File | Action |
|------|--------|
| `app/annotations/__init__.py` | Delete |
| `app/annotations/store.py` | Delete |
| `app/routes.py` | Remove `/api/annotations/*` routes |
| `app/__init__.py` | Remove AnnotationStore import + initialization |
| `app/static/src/ts/annotations.ts` | Delete |
| `app/static/src/ts/detail.ts` | Remove annotation UI calls |
| `app/templates/detail.html` | Remove annotation form and display sections |
| `app/templates/results.html` | Remove tag filter chip UI |
| `app/static/src/ts/graph.ts` | Remove tag nodes (or simplify; graph stays for IOC-provider edges) |
| `tests/unit/test_annotations*.py` | Delete |
| `tests/e2e/` | Remove annotation E2E scenarios |

`~/.sentinelx/annotations.db` is a user file — the app should not delete it; release notes should
document that users can remove it manually after upgrading to v7.0.

---

## Sources

- [Spamhaus ZEN Blocklist](https://www.spamhaus.org/blocklists/zen-blocklist/) — DNSBL zone, return codes, usage
- [Spamhaus DBL](https://www.spamhaus.org/blocklists/domain-blocklist/) — Domain DNSBL zone and query format
- [Spamhaus Fair Use Policy](https://www.spamhaus.org/blocklists/dnsbl-fair-use-policy/) — Rate limits for non-commercial use
- [ICANN RDAP announcement January 2025](https://www.icann.org/en/announcements/details/icann-update-launching-rdap-sunsetting-whois-27-01-2025-en) — WHOIS sunset, RDAP now definitive
- [rdap.org developer guide](https://about.rdap.org/) — Bootstrap proxy usage, redirect behavior
- [RFC 9083 RDAP JSON](https://datatracker.ietf.org/doc/rfc9083/) — Response fields specification
- [IANA RDAP Bootstrap Registry](https://data.iana.org/rdap) — Authoritative RIR bootstrap files
- [Feodo Tracker](https://feodotracker.abuse.ch/) — C2 blocklist format, content, update frequency
- [ThreatFox API](https://threatfox.abuse.ch/api/) — IOC search methods, auth requirements, IOC types
- [Team Cymru IP to ASN](https://www.team-cymru.com/ip-asn-mapping) — DNS-based ASN lookup, TXT record format
- [ipinfo.io Lite API](https://ipinfo.io/developers/lite-api) — Free ASN fields (token required)
- [pydnsbl PyPI](https://pypi.org/project/pydnsbl/) — Python DNSBL reference implementation (not used directly)
- [ARIN RDAP](https://www.arin.net/resources/registry/whois/rdap/) — IP RDAP RIR reference

---

*Feature research for: SentinelX v7.0 Free Intel milestone*
*Researched: 2026-03-15*
