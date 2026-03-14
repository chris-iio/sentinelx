# Project Research Summary

**Project:** SentinelX v7.0 Free Intel
**Domain:** Threat intelligence enrichment — DNSBL reputation, public threat feeds, RDAP registration data, ASN/BGP intelligence; annotations removal
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

SentinelX v7.0 adds four zero-auth enrichment capabilities to a mature 13-provider threat intelligence platform: DNSBL reputation checks, Feodo Tracker C2 feed lookups, RDAP domain/IP registration data, and Team Cymru ASN/BGP intelligence. It simultaneously removes the annotations feature (notes, tags, AnnotationStore) to simplify the codebase. All four new capabilities integrate directly into the existing Provider Protocol — each is one new adapter file plus one `registry.register()` call — with no orchestrator, route, or TypeScript rendering changes required. The stack addition is minimal: only `whoisit==4.0.0` (plus its `python-dateutil` transitive dependency) is new. DNSBL and ASN/BGP both run over DNS via the already-installed `dnspython`, and Feodo Tracker uses the already-installed `requests`.

The recommended implementation order is: annotations removal first (eliminates ~500 LOC and three API routes before adding new code), then DNS-native providers (ASNAdapter via Team Cymru, DNSBLAdapter via Spamhaus/SURBL — zero new dependencies), then HTTP providers (ThreatFeedAdapter for Feodo C2 bulk-list, RDAPAdapter for registration data). This order minimizes risk at every stage: the destructive removal is contained and verified before new code is introduced, the DNS providers validate the Provider Protocol extension flow with no SSRF surface changes, and the HTTP providers with their allowlist updates come last. P1 features for v7.0 are: annotations removal, DNSBL for IPs, RDAP domain creation date/registrar/nameservers, and Feodo Tracker. P2 features are RDAP for IPs, DNSBL for domains, and Team Cymru ASN/BGP.

The primary risks are specific and well-understood. Spamhaus blocks queries from public DNS resolvers (Cloudflare/Google) and returns a `127.255.255.254` sentinel that must not be interpreted as a positive listing. RDAP's SEC-06 conflict (`allow_redirects=False`) means the adapter design must resolve redirect behavior before a line of code is written — `rdap.org` redirect-vs-proxy behavior is the one unconfirmed item in the research and needs empirical validation during Phase 5. The annotations removal spans four layers (Python, templates, TypeScript, SQLite init) and must be completed atomically with a full test run before any new provider work begins. All other aspects of the milestone have HIGH confidence grounded in direct codebase inspection and verified external documentation.

## Key Findings

### Recommended Stack

The v7.0 stack addition is as lean as possible: two new pip packages. `whoisit==4.0.0` handles RDAP bootstrapping (finding the correct RIR/registry RDAP server for any TLD or IP prefix) using only `requests` and `python-dateutil`. All other new capabilities reuse the existing `dnspython==2.8.0` (for DNSBL and Team Cymru ASN) and `requests==2.32.5` (for Feodo Tracker). `pydnsbl` was explicitly rejected for its async/aiodns dependency conflicting with Flask's synchronous pipeline. BGPView was rejected because it shut down November 2025. `pyasn` was rejected for requiring 100+ MB offline BGP dump files. See STACK.md for full alternatives analysis.

**Core technologies:**
- `dnspython==2.8.0` (existing): DNSBL A-record queries + Team Cymru TXT-record ASN lookups — no new library needed for either capability
- `requests==2.32.5` (existing): Feodo Tracker bulk JSON download — no new library needed
- `whoisit==4.0.0` (NEW): RDAP registration data for domains and IPs — handles IANA bootstrap automatically, synchronous, pure Python
- `python-dateutil==2.9.x` (NEW, transitive via whoisit): Date parsing — no conflicts with existing stack

**SSRF allowlist additions required:** `feodotracker.abuse.ch` and `rdap.org` (or individual RIR hostnames if rdap.org issues redirects rather than proxying). DNSBL and ASN providers use DNS (port 53) and have no SSRF surface — same as the existing `DnsAdapter`.

### Expected Features

The v7.0 milestone has one removal and four new provider capabilities. Every feature has been prioritized against analyst triage value and implementation cost.

**Must have (P1 — required for v7.0 launch):**
- Remove annotations entirely (notes, tags, AnnotationStore, tag filter UI, annotations.ts, /api/annotations routes) — simplifies the tool, eliminates case-management scope creep
- DNSBL for IPs: Spamhaus ZEN + Barracuda + SpamCop; verdict `malicious` on any hit naming which zones, `clean` when all NXDOMAIN
- RDAP for domains: creation date formatted as "registered N days ago", registrar name, nameservers; verdict `no_data`
- Feodo Tracker C2 feed for IPs: bulk JSON download with SQLite-cached result; verdict `malicious` with malware family on hit, `clean` when confirmed absent

**Should have (P2 — include in v7.0 if schedule allows):**
- RDAP for IPs: network block name, org, CIDR, country from IP RDAP response
- DNSBL for domains: Spamhaus DBL + SURBL multi; same DNS pattern as IP DNSBL
- ASN/BGP via Team Cymru: CIDR prefix, RIR, allocation date via DNS TXT query; supplements existing ip-api.com ASN field without duplicating it

**Defer (v7.x / v8+):**
- DNSBL listed-count summary badge "Listed 2/5" (UX polish, low complexity)
- IPv6 DNSBL (nibble reversal required; IPv6 IOCs rare in analyst triage)
- RDAP abuse contact email extraction (complex entity traversal in RFC 9083)
- Additional threat feeds beyond Feodo (diminishing returns over existing URLhaus, MalwareBazaar, ThreatFox coverage)

**Explicit anti-features (do not build):**
- WHOIS in any form — sunsetted by ICANN January 2025; RDAP is the sole standard
- RDAP registrant contact fields — 58%+ of malicious domains return "REDACTED FOR PRIVACY"; surfaces noise not signal
- BGP path visualization — dynamic data misleading as static snapshot; high frontend cost for low triage value
- PhishTank — new user registration closed since 2020; cannot obtain API key

### Architecture Approach

All four new providers conform to the existing `typing.Protocol` Provider contract: one file in `app/enrichment/adapters/`, one `register()` call in `app/enrichment/setup.py`, `requires_api_key = False`, `is_configured()` always returns `True`. The ProviderRegistry grows from 13 to 17 providers. No orchestrator, route, or TypeScript rendering changes are needed — the existing `createContextRow()` and `computeWorstVerdict()` functions already handle arbitrary new providers. Verdict-producing providers (DNSBL, ThreatFeed) participate in consensus automatically; context-only providers (RDAP, ASN) need their names added to the `CONTEXT_PROVIDERS` set.

**Major new components:**
1. `DNSBLAdapter` (`dnsbl.py`) — pure DNS, mirrors `DnsAdapter` pattern, parallel zone queries via `ThreadPoolExecutor`, IOCType.IPV4 + IOCType.DOMAIN
2. `ThreatFeedAdapter` (`threat_feed.py`) — HTTP bulk-feed pattern, downloads Feodo JSON, per-IP dict lookup, relies on `CacheStore` TTL, IOCType.IPV4 only
3. `RDAPAdapter` (`rdap.py`) — HTTP REST via rdap.org or whoisit library, parses RFC 9083 JSON, must resolve SEC-06 redirect conflict in design before implementation, IOCType.DOMAIN + IOCType.IPV4 + IOCType.IPV6
4. `ASNAdapter` (`asn.py`) — pure DNS TXT record to Team Cymru `origin.asn.cymru.com`, mirrors `DnsAdapter` pattern, IOCType.IPV4 + IOCType.IPV6
5. Annotations removal — deletes `app/annotations/` module, 3 API routes from routes.py, `annotations.ts`, annotation sections from `results.html` and `ioc_detail.html`, all annotation tests; 14 TS modules → 13

### Critical Pitfalls

1. **SSRF allowlist missing for new HTTP providers** — add `feodotracker.abuse.ch` and `rdap.org` to `ALLOWED_API_HOSTS` in `config.py` as the very first step of each respective provider phase; include a unit test calling `validate_endpoint()` without mocking to confirm the hostname passes; this failure mode is invisible in tests that mock `requests.get` and only manifests in live runs

2. **Spamhaus `127.255.255.254` sentinel misread as a positive listing** — Spamhaus returns this sentinel when queries arrive from public resolvers (Cloudflare 1.1.1.1, Google 8.8.8.8); the DNSBL response parser must check for this value and emit `EnrichmentError("resolver blocked")` not a malicious verdict; test with a mocked `127.255.255.254` DNS response to verify correct handling

3. **DNSBL IPv4 octet reversal absent — silent clean failure** — querying `1.2.3.4.zen.spamhaus.org` instead of `4.3.2.1.zen.spamhaus.org` always returns NXDOMAIN, making every IP appear clean; write the `127.0.0.2` test (Spamhaus canonical test address, always listed) first as TDD red; the failure mode produces no errors, only wrong results

4. **RDAP redirect vs. SEC-06 conflict** — the project security policy (`allow_redirects=False`) and RDAP's requirement to follow HTTP 302 redirects are in direct conflict; this must be resolved in the adapter design before writing code: either confirm empirically that `rdap.org` proxies responses (preferred), or use `whoisit` which handles bootstrapping internally and bypasses `validate_endpoint()` entirely (document the exception)

5. **Annotations removal crashes app at startup if incomplete** — `AnnotationStore` is imported in `routes.py`; template variables are referenced in `ioc_detail.html` and `results.html`; `annotations.ts` is compiled into the esbuild bundle; run `grep -rn "AnnotationStore\|annotation" app/` to audit all touchpoints before touching any file, remove in dependency order (TS → templates → routes → module directory), verify `flask --debug run` succeeds after each layer

## Implications for Roadmap

Based on combined research, the milestone maps to 5 phases driven by dependency order and risk profile. The Provider Protocol makes phases 2-5 largely independent of each other once phase 1 is complete.

### Phase 1: Annotations Removal

**Rationale:** Purely destructive — eliminates dead code before adding new code. Completing this first means the test suite baseline is accurate for all subsequent provider work. If done last, failing annotation tests would obscure new provider test failures.
**Delivers:** Clean codebase with no annotation-related Python, TypeScript, routes, or templates. App startup and full test suite pass cleanly. A fresh baseline for v7.0 development.
**Addresses:** FEATURES.md "remove annotations" (P1); reduces test surface noise for all subsequent phases
**Avoids:** Pitfall 7 (orphaned imports crashing app at startup) — mitigated by grep-audit-first approach before touching any file

### Phase 2: ASNAdapter (Team Cymru DNS)

**Rationale:** Zero new dependencies (dnspython already present), zero SSRF allowlist changes (DNS port 53, not HTTP), direct precedent in existing `DnsAdapter`. Lowest-risk new provider — validates the Provider Protocol extension flow in isolation before any HTTP complexity is introduced.
**Delivers:** Per-IP CIDR prefix, RIR, allocation date, ASN number and org name via DNS TXT query to Team Cymru `origin.asn.cymru.com`. Supplements existing ip-api.com ASN field with BGP-precision data (CIDR prefix, RIR, allocation date) without duplicating what ip-api.com already shows.
**Uses:** `dnspython==2.8.0` (existing), `typing.Protocol` adapter pattern (existing)
**Implements:** ASNAdapter — IOCType.IPV4 + IOCType.IPV6, verdict `no_data`, added to CONTEXT_PROVIDERS

### Phase 3: DNSBLAdapter

**Rationale:** Also DNS-native (no new deps, no SSRF changes), but more complex than ASNAdapter: two IOC types with different query construction (IP octet reversal vs. domain prepend-as-is), multiple zones queried in parallel, and three response categories (listed, clean, sentinel error). The first verdict-producing zero-auth provider — high analyst value for direct reputation signal.
**Delivers:** IP reputation against Spamhaus ZEN + Barracuda + SpamCop; domain reputation against Spamhaus DBL + SURBL multi. Verdict `malicious` on any zone hit (naming the zones), `clean` on all NXDOMAIN, `EnrichmentError` on `127.255.255.254` sentinel.
**Uses:** `dnspython==2.8.0` (existing), `ThreadPoolExecutor` within `lookup()` for parallel zone queries (target: 5 zones in under 5 seconds)
**Implements:** DNSBLAdapter — IOCType.IPV4 + IOCType.DOMAIN; IPv6 DNSBL deferred to v7.x (nibble reversal complexity, rare in triage)
**Avoids:** Pitfalls 2 (sentinel check), 3 (IPv4 reversal), 4 (domain format), 9 (serial zone latency)

### Phase 4: ThreatFeedAdapter (Feodo Tracker)

**Rationale:** First HTTP provider in the milestone — introduces SSRF allowlist change (`feodotracker.abuse.ch`) and the new bulk-feed download pattern (download full JSON, dict lookup, rely on CacheStore TTL). Simpler JSON structure than RDAP (flat list, not deeply nested RFC 9083). Natural second verdict-producing provider, complementing DNSBL with botnet C2 family attribution.
**Delivers:** Per-IP C2 reputation from Feodo Tracker botnet blocklist. Verdict `malicious` with malware family (Dridex, Emotet, QakBot, etc.) on hit; `clean` when confirmed absent. Note: feed is currently sparse due to law enforcement takedowns — `clean` verdicts are correct and informative, not a bug.
**Uses:** `requests==2.32.5` (existing), `CacheStore` (existing) for feed TTL
**Implements:** ThreatFeedAdapter — IOCType.IPV4 only; HTTP bulk-feed pattern; feed parsed into `dict[str, dict]` for O(1) IP lookup after download
**Avoids:** Anti-Pattern 1 (per-IOC full download) — CacheStore 24h TTL handles refresh; Anti-Pattern 5 (module-level mutable feed state — keep adapters stateless)

### Phase 5: RDAPAdapter

**Rationale:** Last because it has the most uncertainty: `rdap.org` redirect-vs-proxy behavior must be confirmed empirically before the design is finalized, RFC 9083 JSON requires defensive parsing at every nested level, and the SEC-06 conflict (`allow_redirects=False`) must be explicitly resolved in a design decision before implementation begins. Highest analyst value of the context providers — domain age ("registered 2 days ago") is the single most actionable triage signal for newly-registered malicious domains.
**Delivers:** Domain registration data (creation date as "registered N days ago", registrar, nameservers, status codes) and IP registration data (network block name, org, CIDR, country). Verdict `no_data` — registration context is informational.
**Uses:** `whoisit==4.0.0` (NEW) — preferred if rdap.org issues redirects; `requests` to rdap.org — preferred if rdap.org proxies; `python-dateutil==2.9.x` (NEW transitive)
**Implements:** RDAPAdapter — IOCType.DOMAIN + IOCType.IPV4 + IOCType.IPV6; GDPR-scoped data model (no registrant contact fields)
**Avoids:** Pitfall 5 (GDPR noise — contact fields excluded from data model before coding), Pitfall 6 (SEC-06 conflict — resolved in design doc first), Pitfall 8 (bootstrap uncached — whoisit handles per-process caching internally)

### Phase Ordering Rationale

- Phase 1 before all others: destructive removal creates a clean test baseline; annotation test failures would mask provider failures in later phases
- Phases 2-3 before 4-5: DNS-native providers validate the Provider Protocol extension flow with zero SSRF risk; HTTP providers with allowlist changes come after the DNS pattern is proven
- Phase 3 (DNSBL) before Phase 4 (ThreatFeed): both are verdict-producing, but DNSBL is DNS-native and has no HTTP complexity; building DNSBL first ensures the verdict-producing path is working before introducing HTTP bulk-feed pattern
- Phase 5 (RDAP) last: most uncertain phase benefits from having all other providers working as reference implementations; also contains the one design decision (redirect vs. proxy) that cannot be resolved from research alone

### Research Flags

Phases needing implementation-time validation before writing adapter code:

- **Phase 5 (RDAP):** Confirm empirically whether `rdap.org` proxies responses (returns 200 with the authoritative registry's data) or issues 302 redirects to authoritative servers. Test: `GET https://rdap.org/domain/google.com` with `allow_redirects=False`, inspect response status. If 200: single allowlist entry, standard SEC-06 behavior preserved. If 302: use `whoisit` library (handles bootstrapping internally, bypasses `validate_endpoint()` — document this exception) or implement manual redirect following limited to known IANA-blessed RDAP hostnames.

Phases with standard well-understood patterns (no additional research needed):

- **Phase 1 (Annotations Removal):** All touchpoints fully mapped in ARCHITECTURE.md. The grep-audit checklist is complete. No unknowns.
- **Phase 2 (ASNAdapter):** Team Cymru DNS TXT format verified, stable, free forever. Direct precedent in existing `DnsAdapter`. No unknowns.
- **Phase 3 (DNSBLAdapter):** DNS A-record DNSBL mechanism fully documented. Test fixtures (`127.0.0.2` for IPs, `test.surbl.org` for domains) are official and stable. Spamhaus sentinel behavior confirmed from primary Spamhaus advisory documents. No unknowns beyond runtime resolver configuration (handled by sentinel check).
- **Phase 4 (ThreatFeedAdapter):** Feodo Tracker URL and JSON schema stable and verified. Bulk-feed caching pattern is simple. Feed sparseness (law enforcement takedowns) is a known condition, not a code concern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified against PyPI and official docs; version compatibility confirmed; alternatives analyzed and rejected with documented rationale; only 2 net-new packages |
| Features | HIGH | P1/P2/P3 prioritization grounded in analyst triage workflow; anti-features documented with concrete technical reasons; MVP scope is tight and well-bounded |
| Architecture | HIGH (DNS + ThreatFeed + annotations removal), MEDIUM (RDAP) | DNSBL, ASN, ThreatFeed, and annotations removal fully mapped; RDAP has one open design question (redirect vs. proxy) requiring empirical validation |
| Pitfalls | HIGH | 9 pitfalls identified from direct codebase inspection + verified primary sources; Spamhaus sentinel, DNSBL reversal patterns, annotations removal scope, RDAP redirect conflict are all confirmed real failure modes with recovery paths |

**Overall confidence:** HIGH with one known gap (RDAP redirect behavior at rdap.org)

### Gaps to Address

- **`rdap.org` redirect vs. proxy behavior (Phase 5):** Research produced conflicting signals — rdap.org documentation implies proxying, but rdap.net and similar services confirm redirect behavior. During Phase 5, this must be resolved empirically before the adapter design is committed. Decision tree is clear: proxy → use `requests` + standard allowlist; redirect → use `whoisit` library with documented SEC-06 exception. This is the only unresolved item.

- **Feodo Tracker feed sparseness (Phase 4):** The feed is currently nearly empty (law enforcement takedowns of Emotet 2021, Operation Endgame 2024). ThreatFeedAdapter will typically return `clean` verdicts. This is technically correct but may cause analysts to question the provider's value. Consider adding a `last_updated` timestamp from the feed JSON to `raw_stats` so analysts can see the feed was recently checked. This is a UX enhancement, not a correctness issue.

- **System resolver on analyst workstations (Phase 3):** SentinelX uses `dns.resolver.Resolver(configure=True)` which reads the system resolver. On a cloud jump box configured with Cloudflare/Google DNS, Spamhaus returns `127.255.255.254`. The sentinel check handles this gracefully (surfaces as "resolver blocked" note, not a false positive), but analysts running from cloud hosts lose Spamhaus DNSBL signal. Document this limitation in the UI help text and release notes.

## Sources

### Primary (HIGH confidence)
- Spamhaus DNSBL zones and fair-use policy — zone names, return codes, `127.255.255.254` sentinel rollout confirmed from official Spamhaus advisories
- Team Cymru IP-to-ASN DNS service — query format (`origin.asn.cymru.com` TXT), response format, free-forever policy verified
- ICANN RDAP announcement January 2025 — WHOIS sunset confirmed; RDAP now the sole authoritative protocol for gTLD registrations
- RFC 9083 (RDAP JSON responses) — response field structure, events array, entities array format
- RFC 9224 (RDAP bootstrap registry) — caching requirement (SHOULD NOT fetch on every request) confirmed
- RFC 9537 (RDAP Redacted Fields) — GDPR redaction formalization March 2024; explains why registrant contact fields return "REDACTED FOR PRIVACY"
- Feodo Tracker blocklist — URL, JSON schema, CC0 license, zero-auth confirmed; feed activity MEDIUM (sparse due to takedowns)
- `whoisit` v4.0.0 on PyPI — pure Python, synchronous, only `requests` + `python-dateutil` dependencies confirmed
- BGPView shutdown November 2025 — confirmed; do not use in new code
- SentinelX codebase direct inspection — `app/config.py`, `app/enrichment/http_safety.py`, `app/enrichment/adapters/dns_lookup.py`, `app/enrichment/adapters/ip_api.py`, `app/routes.py` all reviewed for integration points

### Secondary (MEDIUM confidence)
- `rdap.org` rate limiting (10 req/10 sec via Cloudflare 429) — documented at about.rdap.org; redirect vs. proxy behavior requires empirical validation
- SURBL `multi.surbl.org` public resolver safety — no explicit restriction documented in primary sources
- `combined.abuse.ch` DNSBL — no public resolver restriction documented
- RDAP GDPR redaction statistics (58.2% proxy protection, 10.8% registrant visibility as of January 2024) — Interisle Consulting data via domain privacy research sources

### Tertiary (LOW confidence)
- Spamhaus fair-use policy page content — page failed to load during research; sentinel behavior is HIGH confidence from primary Spamhaus advisories; fair-use rate limit policy stated from secondary sources only

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
