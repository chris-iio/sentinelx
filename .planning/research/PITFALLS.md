# Pitfalls Research

**Domain:** Threat intelligence enrichment — adding DNSBL, public threat feeds, RDAP, and ASN/BGP to existing Python/Flask SOC tool; removing annotations feature
**Researched:** 2026-03-15
**Confidence:** HIGH — codebase reviewed directly for integration points; external findings verified against Spamhaus official docs, RFC 9224, RDAP.org, and ipinfo.io documentation

---

## Context: What This Research Covers

SentinelX v6.0 is a working, security-first, 13-provider enrichment tool with a strict security posture:
SSRF hostname allowlist (`ALLOWED_API_HOSTS` in `app/config.py`), SEC-06 (`allow_redirects=False`),
SEC-08 (no `innerHTML`), and a Provider Protocol (`typing.Protocol`) governing all adapters.

v7.0 adds DNSBL reputation checks, public threat feed lookups, RDAP registration data, and ASN/BGP
intelligence while removing the annotations feature (notes, tags, `AnnotationStore`).

The pitfalls below are calibrated for this exact system and these exact features.

---

## Critical Pitfalls

### Pitfall 1: New Provider Hostname Not Added to SSRF Allowlist

**What goes wrong:**
Every new HTTP-based provider adapter (ipinfo.io for ASN, rdap.org or an authoritative RIR for RDAP,
feodotracker.abuse.ch or other feed endpoints) must have its hostname added to `ALLOWED_API_HOSTS`
in `app/config.py`. If the hostname is absent, `http_safety.validate_endpoint()` raises `ValueError`
at runtime. Every lookup for that provider silently returns `EnrichmentError`. Tests pass because
they mock `requests.get` — the SSRF guard is bypassed by mocking and the failure is invisible until
the app is run live.

**Why it happens:**
Developers write the adapter, wire it into `setup.py`, write tests that mock the HTTP layer, see
green — and ship. The SSRF allowlist in `config.py` is a separate config file that is not part of
the adapter pattern itself. Nothing in the code scaffolding forces you to remember it.

**How to avoid:**
Add the provider hostname to `ALLOWED_API_HOSTS` as the very first step before writing any adapter
code. Include at least one unit test that calls `validate_endpoint()` directly (without mocking it)
to confirm the hostname passes. Better: write an integration test that makes a real request to the
provider endpoint in a CI environment.

**Warning signs:**
- Provider always returns `EnrichmentError` in production but passes all tests
- Error message contains "not in allowed_hosts" or "SSRF allowlist SEC-16"
- Provider row shows "Error" in UI with no matching exception in Flask logs

**Phase to address:**
Every new provider phase — add hostname to `ALLOWED_API_HOSTS` first, before the adapter.

---

### Pitfall 2: DNSBL Queries Via Public Resolvers Return False Positives (`127.255.255.254` Sentinel)

**What goes wrong:**
DNSBL lookups use `dnspython` with `configure=True`, which reads the system resolver
(`/etc/resolv.conf`). On analyst workstations and corporate jump boxes, the system resolver is
commonly Cloudflare (1.1.1.1), Google (8.8.8.8), or another public recursive resolver. Spamhaus
actively blocks queries originating from these resolvers and returns `127.255.255.254` as a sentinel
error code. An adapter that treats any `127.0.0.x` response as "listed" will interpret this sentinel
as a positive blacklist hit — meaning every IP appears to be on the Spamhaus blacklist regardless of
whether it actually is.

**Why it happens:**
DNSBL response interpretation is non-obvious. The DNSBL protocol is historically email-centric;
most documentation describes it from a mail server perspective, not from an analyst tool perspective.
The `127.255.255.254` sentinel is documented in Spamhaus FAQs but not prominently in general DNS
programming resources. Developers test DNSBL logic from a development machine where the system
resolver may be a local caching resolver that is not blocked.

**How to avoid:**
Always check for `127.255.255.254` in DNSBL response A records before interpreting a response as a
listing. Map it to `EnrichmentError("DNSBL queries blocked — public resolver in use; configure a
local resolver")` or a `no_data` result with an explanatory note. Do not surface this as a positive
listing to the analyst. Document the resolver requirement: Spamhaus DNSBL requires queries to
originate from a resolver with attributable rDNS (your own resolver on your own network). As an
alternative, use the Spamhaus Data Query Service (DQS) HTTP API which is not resolver-dependent.

**Warning signs:**
- Every IP returns a DNSBL hit regardless of reputation
- DNSBL A record is `127.255.255.254` in debug output
- Results differ dramatically between development machine and analyst workstation

**Phase to address:**
DNSBL provider implementation phase — the sentinel check is part of the response parser, not a
post-hoc fix.

---

### Pitfall 3: DNSBL IPv4 Octet Reversal Missing — All IPs Appear Clean (Silent Failure)

**What goes wrong:**
DNSBL queries for IPv4 require reversing the octets before appending the DNSBL zone. For IP
`1.2.3.4`, the DNS query must be `4.3.2.1.zen.spamhaus.org`. Querying `1.2.3.4.zen.spamhaus.org`
always returns NXDOMAIN (domain not found), which is indistinguishable from a clean IP response.
The adapter appears to work correctly — it returns "not listed" for every IP. But it is wrong for
every IP.

**Why it happens:**
DNSBL is an email filtering protocol pattern. Developers coming from REST API backgrounds implement
it as "append the IP to the zone name" without realizing the reversal is required. The failure mode
is a false negative (clean) rather than an error, so it passes tests and does not crash.

**How to avoid:**
Implement a test fixture using `127.0.0.2` — Spamhaus's canonical test IP that always returns listed
on `zen.spamhaus.org`. If the test IP returns NXDOMAIN, the reversal is missing. Use
`".".join(reversed(ip.split(".")))` for IPv4. The `pydnsbl` library handles reversal automatically.
Never test DNSBL logic only against IPs expected to be clean.

**Warning signs:**
- No test against a known-listed IP or test fixture address
- DNSBL consistently returns "not listed" for all IPs including obvious threat actors
- `127.0.0.2` lookup returns NXDOMAIN instead of `127.0.0.2`

**Phase to address:**
DNSBL provider implementation phase — write the `127.0.0.2` test first (TDD red).

---

### Pitfall 4: Domain DNSBL Reversal Applied Incorrectly (SURBL/URIBL Format)

**What goes wrong:**
For domain DNSBL checks (SURBL, URIBL), the query format is `example.com.multi.surbl.org` — the
domain name is prepended to the DNSBL zone without octet reversal. Developers who implement IP DNSBL
first and build a shared query constructor may apply the same reversal logic to domains, producing
queries like `com.example.multi.surbl.org`. This always returns NXDOMAIN; all domains appear clean.

**Why it happens:**
IP DNSBL reversal (required for IPv4) and domain DNSBL non-reversal (domain prepended as-is) are
easy to conflate when building a unified DNSBL checking function. The formats look similar at a
glance but have opposite logic.

**How to avoid:**
Separate the query construction logic into distinct code paths for `IOCType.IPV4` (reverse octets)
and `IOCType.DOMAIN` (prepend as-is). Test each with official test fixtures: `127.0.0.2` for
Spamhaus, `test.surbl.org` for SURBL (always returns listed).

**Warning signs:**
- All domain DNSBL results are "not listed" regardless of domain reputation
- `test.surbl.org` returns NXDOMAIN

**Phase to address:**
DNSBL provider implementation phase — separate IP and domain query construction from the start.

---

### Pitfall 5: RDAP Returns Mostly "REDACTED FOR PRIVACY" for Malicious Domains

**What goes wrong:**
RDAP was previously listed as "Out of Scope" in `PROJECT.md` specifically because of GDPR redaction.
As of January 2024, 58.2% of gTLD domains use proxy-protection services, and only 10.8% of domain
records identify the actual registrant (per Interisle Consulting data). Malicious domains — the ones
analysts care most about — almost universally use privacy protection. An RDAP adapter that surfaces
registrant name, email, phone, and address will show "REDACTED FOR PRIVACY" for the majority of
interesting IOCs. RFC 9537 (March 2024) formalizes this redaction pattern. WHOIS was sunsetted on
January 28, 2025; RDAP is now the sole protocol and inherits all the same GDPR constraints.

**Why it happens:**
RDAP looks more promising than WHOIS in documentation because it offers structured JSON and is
designed to replace WHOIS. The redaction reality is buried in privacy/GDPR discussions rather than
in the RDAP technical spec. Developers build an adapter, test it against a few domains, see some
data for non-privacy-protected domains, and conclude it works — not realizing that production usage
on threat intelligence IOCs will almost exclusively hit redacted records.

**How to avoid:**
Scope the RDAP adapter to fields that are NOT redacted under GDPR: `registration creation date`,
`expiry date`, `last updated date`, `registrar name`, `nameservers`, and `domain status codes`
(e.g., `clientHold`, `serverDeleteProhibited`). These fields are reliably populated and provide
genuine triage signal (newly registered = higher suspicion, registrar identity, NS provider for
infrastructure correlation). Never extract or display contact entity blocks (registrant, admin,
tech contacts). The adapter data model must be scoped to structural/temporal fields before
implementation begins.

**Warning signs:**
- RDAP result rows show "REDACTED FOR PRIVACY" for most domains during testing
- Adapter extracts `registrant`, `email`, `phone`, `address` fields
- Feature designed after testing with a domain that happens to have unredacted WHOIS data

**Phase to address:**
RDAP design phase — define the data model (structural/temporal fields only) before writing any code.

---

### Pitfall 6: RDAP Redirect Following Conflicts With SEC-06 (`allow_redirects=False`)

**What goes wrong:**
RDAP requires following HTTP redirects to work correctly. When querying an authoritative RIR (ARIN,
RIPE, APNIC, LACNIC, AFRINIC) for an IP block, or when using `rdap.org` as a proxy, the server
returns HTTP 301 or 302 pointing to the authoritative registry. The current project security policy
(SEC-06) sets `allow_redirects=False` on all `requests` calls. With redirects disabled, RDAP
lookups always fail silently — the 301/302 response has no body to parse, and the adapter may
misinterpret the status code as an error.

**Why it happens:**
SEC-06 was established as a blanket rule to prevent redirect-based SSRF attacks. RDAP is the first
protocol in the project that legitimately requires redirect following. The conflict is not obvious
until the adapter is tested against a live RDAP endpoint and returns empty results.

**How to avoid:**
Two valid approaches: (1) Use a Python RDAP library (`rdap` or `python-rdap` on PyPI) that handles
bootstrap and redirects internally, allowing the adapter to avoid raw redirect logic entirely.
(2) Implement manual redirect following with strict target hostname validation — after receiving a
301/302, extract the `Location` header, verify the redirect target hostname against a curated list
of known RDAP servers (IANA bootstrap list), then make the redirected request. Never follow an
open redirect. Document the SEC-06 exception clearly in the adapter.

**Warning signs:**
- RDAP lookups return empty results for most domains and all IPs
- HTTP 301 or 302 responses in debug output with no follow-through
- Adapter appears to work against `rdap.org` in testing (it returns 302, not the data)

**Phase to address:**
RDAP implementation phase — resolve the SEC-06 conflict in the design doc before writing code.

---

### Pitfall 7: Annotations Removal Leaves Orphaned Imports and Crashes App at Startup

**What goes wrong:**
`AnnotationStore` is currently imported and used in `app/routes.py`. `app/templates/ioc_detail.html`
and `app/templates/partials/_ioc_card.html` reference annotation template variables. The TypeScript
module `annotations.ts` is compiled into the IIFE bundle. `annotations.db` is initialized somewhere
in `app/__init__.py` or app setup. Removing only the `app/annotations/` directory without updating
all reference sites causes `ModuleNotFoundError: No module named 'app.annotations'` at Flask startup
— every page crashes.

**Why it happens:**
Annotations are woven through four layers (Python, templates, TypeScript, SQLite init). The feature
feels like a single unit but its dependencies are spread across independent files. Removing the
obvious entry point (the `annotations/` directory) does not remove the import in `routes.py` or the
template variables in `ioc_detail.html`.

**How to avoid:**
Before touching any files, run a full grep audit:
```
grep -rn "annotation\|AnnotationStore\|annotations_db" app/ --include="*.py"
grep -rn "annotation" app/templates/ --include="*.html"
grep -rn "annotation" app/static/src/ts/ --include="*.ts"
```
Remove in dependency order: TypeScript module first (remove from esbuild entry points in Makefile),
then template references, then `routes.py` imports and usages, then the `app/annotations/` package,
then `annotations.db` initialization. Run `flask --debug run` after each layer removal to catch
import errors early. Run the full test suite after the complete removal.

**Warning signs:**
- `ModuleNotFoundError` at Flask startup
- Jinja `UndefinedError` for template variables
- TypeScript build error after removing `annotations.ts` if other modules still reference it
- E2E tests failing on annotation UI elements that no longer exist

**Phase to address:**
Annotations removal phase (Phase 1 of v7.0) — must be a standalone phase with full test run before
adding any new provider features.

---

### Pitfall 8: RDAP Bootstrap Fetched on Every Lookup (Performance and Reliability)

**What goes wrong:**
Proper RDAP requires consulting the IANA bootstrap registry to find the authoritative RDAP server
for a given TLD or IP prefix. The IANA bootstrap files are JSON documents served at well-known URLs
(`https://data.iana.org/rdap/dns.json`, `asn.json`, `ipv4.json`, `ipv6.json`). An implementation
that fetches the bootstrap file on every `lookup()` call adds one extra HTTP round-trip per IOC,
doubles latency, and risks rate-limiting on IANA's infrastructure. RFC 9224 explicitly states that
clients SHOULD cache the bootstrap registry and SHOULD NOT fetch it on every request.

**Why it happens:**
Developers implement the simplest path first: fetch bootstrap, find server URL, query server. The
caching requirement is in the RFC spec, not in the library README. Under single-IOC testing, the
extra 100-200ms is not noticeable. Under bulk IOC submission (50+ IOCs), the bootstrap fetches
compound and the IANA endpoint may 429.

**How to avoid:**
Use a Python RDAP library that handles bootstrap caching internally (e.g., `rdap` package on PyPI).
If implementing directly, store the bootstrap data in a module-level dict with an `expires_at`
timestamp, refresh only when expired (the IANA files include HTTP `Expires` headers indicating
roughly 24-hour cache lifetime), and share the cached bootstrap across all `lookup()` calls.

**Warning signs:**
- RDAP lookup time consistently 2x or more longer than other HTTP providers
- IANA bootstrap URL appearing in request logs on every enrichment job
- HTTP 429 from IANA infrastructure under bulk IOC submission

**Phase to address:**
RDAP implementation phase — bootstrap caching is part of the initial design, not a later
optimization.

---

### Pitfall 9: Serial DNSBL Zone Queries Multiply Lookup Time by Number of Lists

**What goes wrong:**
A naive DNSBL implementation queries each zone serially: query `zen.spamhaus.org`, wait for
response, query `dbl.spamhaus.org`, wait, query `multi.surbl.org`, wait. Each zone adds up to
3-5 seconds of timeout surface. With 5 DNSBL zones, worst-case lookup time per IP is 15-25 seconds.
The analyst UI shows the enrichment spinner for an unacceptable duration. The existing
`EnrichmentOrchestrator` uses `ThreadPoolExecutor` for parallel HTTP providers; DNSBL adapter
running serially within its `lookup()` call blocks one thread for the entire duration.

**Why it happens:**
`lookup()` is a synchronous function in the Provider Protocol. DNS queries are naturally sequential
when using `resolver.resolve()` in a loop. Developers write the simplest implementation (for-loop
over zones) and do not profile multi-zone latency under adversarial conditions.

**How to avoid:**
Use `concurrent.futures.ThreadPoolExecutor` within the `lookup()` call to query DNSBL zones in
parallel, or use `pydnsbl` (async/aiodns-based DNSBL library) that handles parallel queries
natively. Set a short per-query timeout (`resolver.lifetime = 3.0`) so each zone contributes at
most 3 seconds to the total. Target total DNSBL lookup time under 5 seconds for 5+ zones.

**Warning signs:**
- DNSBL lookup time scales linearly with the number of zones checked
- Single-IOC enrichment takes over 10 seconds when any DNSBL zone is slow
- Performance degrades noticeably under bulk IOC submission

**Phase to address:**
DNSBL implementation phase — design for parallel zone queries before writing the lookup loop.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `rdap.org` as universal RDAP proxy | No bootstrap implementation needed | Rate-limited at 10 req/10 sec (Cloudflare 429); single point of failure | Never — use library with bootstrap caching |
| Querying DNSBL zones serially in a loop | Simple implementation, easy to read | Total lookup time = N * timeout per zone; blocks enrichment thread | Never for user-facing tool — parallelize zone queries |
| Treating any `127.0.0.x` DNSBL response as "listed" | Simple: any A record = listed | `127.255.255.254` means "resolver blocked"; causes universal false positives | Never — always check for sentinel values |
| Keeping `AnnotationStore` import during incremental removal | Avoids crash mid-refactor | Dead code, stale test fixtures, confusing codebase state | Only as a single-commit transition |
| Querying DNSBL from Cloudflare/Google DNS (system resolver) | No infrastructure needed | Spamhaus blocks these resolvers; results are unreliable | Only for DNSBL lists that do not enforce resolver attribution |
| Extracting RDAP contact/registrant fields | More data visible | Returns "REDACTED FOR PRIVACY" for majority of malicious domains; analyst noise | Never — scope to structural/temporal fields only |
| Fetching IANA RDAP bootstrap on every lookup | Simpler code; no cache management | Extra round-trip per IOC; IANA 429 under bulk submission; violates RFC 9224 | Never in production path |
| Building RDAP without addressing SEC-06 (`allow_redirects=False`) | Works in limited testing | All RDAP lookups silently fail in production when redirects required | Never — resolve SEC-06 conflict before shipping |

---

## Integration Gotchas

Common mistakes when connecting to these specific services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Spamhaus DNSBL (`zen.spamhaus.org`) | Querying via Cloudflare/Google DNS | Use system resolver with attributable rDNS, or switch to Spamhaus DQS HTTP API |
| DNSBL (any) | Not checking for `127.255.255.254` sentinel | Always check: if A record is `127.255.255.254`, emit `EnrichmentError("resolver blocked")` not a listing |
| DNSBL IPv4 | Missing octet reversal | `".".join(reversed(ip.split(".")))` before appending zone; test with `127.0.0.2` |
| DNSBL domain (SURBL/URIBL) | Applying IP octet reversal to domain names | Domains prepend directly: `example.com` → `example.com.multi.surbl.org`, no reversal |
| RDAP | Using `allow_redirects=False` (SEC-06) with raw requests | Either use a RDAP library that handles redirects internally, or validate redirect targets against IANA bootstrap list |
| RDAP | Querying `rdap.org` without 429 handling | `rdap.org` rate-limits at 10 req/10 sec via Cloudflare; add retry-on-429 with backoff |
| RDAP | Extracting contact/registrant fields | 58%+ of gTLD domains have privacy protection; contact fields return "REDACTED FOR PRIVACY" — skip them |
| ipinfo.io (ASN) | No API token (unauthenticated) | Unauthenticated: 1000 req/day limit shared by IP. Register free token for 50k/month. Handle 429 as `EnrichmentError`. |
| BGPView (any) | Using as ASN data source | BGPView shut down November 26, 2025 — do not use. ipinfo.io or Team Cymru are current alternatives. |
| ip-api.com (existing) | Adding separate ASN provider for data already available | `ip-api.com` already returns `as` and `asname` fields in existing `IPApiAdapter`; extend it rather than adding a new provider for duplicate data |
| Public threat feeds (Feodo Tracker, etc.) | Fetching full blocklist on every IOC lookup | Use point-query APIs where available; if downloading lists, cache with TTL — never fetch MB-scale files per IOC |

---

## Performance Traps

Patterns that work at small scale but fail under realistic analyst usage.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Serial DNSBL zone queries | Lookup takes 5-30 seconds per IP with 5+ zones | Use `ThreadPoolExecutor` within `lookup()` or `pydnsbl` for parallel zone queries | From first IOC — each zone adds full timeout overhead |
| Uncached IANA RDAP bootstrap | RDAP lookup time 2x other providers; IANA 429 under bulk submission | Cache bootstrap JSON in-memory, respect `Expires` header (~24h refresh) | First bulk IOC submission (10+ IOCs) |
| New `dns.resolver.Resolver` created per DNSBL zone per query | CPU overhead from repeated configuration; inconsistent lifetime enforcement | Create one `Resolver` per `lookup()` call, reuse across all DNSBL zones for that IOC | At scale with bulk IOC inputs |
| RDAP applied to hash and CVE IOC types | Lookups return immediate errors for every hash/CVE | Set `supported_types = frozenset({IOCType.DOMAIN, IOCType.IPV4})` | First hash or CVE submission |
| No DNSBL result caching | Same IP queried multiple times in one session hits DNSBL N times | Existing `CacheStore` (SQLite) should apply to DNSBL results at the same TTL as other providers | Any re-submission of the same IOC |
| Parallel enrichment saturated by slow RDAP bootstrap | Other providers complete but overall job waits on RDAP | Bootstrap caching ensures RDAP latency matches other HTTP providers | Any bulk submission without cached bootstrap |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| New provider hostname missing from `ALLOWED_API_HOSTS` | SSRF allowlist enforcement bypassed; any future code that constructs URLs from input could call arbitrary hosts | Add hostname to `app/config.py` as first step; test `validate_endpoint()` without mocking |
| RDAP open redirect following | RDAP 301/302 could point to internal services if redirect target not validated | Never follow redirects without validating target hostname against IANA bootstrap allowlist |
| Rendering raw RDAP `remarks` or `notices` fields via `innerHTML` | RDAP JSON can contain arbitrary text in free-form fields; XSS if rendered unsafely | All RDAP fields go through `createElement + textContent` — existing SEC-08 pattern; never `innerHTML` |
| DNS-based DNSBL bypassing the HTTP SSRF allowlist | DNSBL uses port 53 DNS, not HTTP; `validate_endpoint()` does not cover DNS | Acceptable — DNS queries go to system resolver, not to analyst-controlled hosts; no SSRF surface from DNS queries |
| ASN lookup revealing analyst investigation focus to third-party | `ipinfo.io` receives and logs the IP being queried | Document this; it applies equally to all 13 existing providers; analysts should be aware external enrichment logs IOC values |
| Annotating the SQLite `annotations.db` path in logs during removal | File path visible in logs could assist local privilege escalation on shared jump box | Remove all annotation-related log statements before removing the feature; ensure no `annotations.db` path leaks |

---

## UX Pitfalls

Common user experience mistakes when adding these features.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing "REDACTED FOR PRIVACY" RDAP fields prominently | Analyst questions why the feature exists; trust in tool decreases | Only surface creation date, registrar, nameservers, status codes — omit contact blocks entirely |
| Displaying DNSBL "listed" without naming the zone | Analyst cannot act on "listed on a blocklist" — needs to know which list and why | Include DNSBL zone name (e.g., `zen.spamhaus.org`) and a human-readable description of that list |
| Treating DNSBL `no_data` (NXDOMAIN) as the same as CLEAN | NXDOMAIN = not listed, but DNSBL is spam-focused; "not on spam list" is not "known clean" | Use `no_data` verdict for NXDOMAIN (correct); never surface it as "CLEAN" |
| Showing raw DNSBL return codes like `127.0.0.2` to analysts | Meaningless without explanation ("what is 127.0.0.2?") | Map return codes to human-readable descriptions per zone (e.g., `127.0.0.2` on Spamhaus SBL = "Spamhaus Block List") |
| Adding DNSBL/RDAP/ASN rows for hash and CVE IOC types | Empty rows add visual noise for every hash lookup | `supported_types` restrictions must prevent providers from appearing for irrelevant IOC types |
| ASN shown as duplicate of existing ip-api.com output | Analyst sees same AS number twice from two providers | Either extend `IPApiAdapter` with richer ASN fields or deduplicate at the orchestrator level |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **DNSBL provider:** Verify `127.0.0.2` (Spamhaus test address) returns "listed" — confirms IPv4 octet reversal works
- [ ] **DNSBL provider:** Verify `test.surbl.org` returns "listed" on SURBL — confirms domain query format works
- [ ] **DNSBL provider:** Verify `127.255.255.254` response is mapped to `EnrichmentError` (resolver blocked), not a listing
- [ ] **DNSBL provider:** Hostname added to `ALLOWED_API_HOSTS` if using HTTP-based DNSBL (e.g., DQS); DNS path confirmed exempt from SSRF guard
- [ ] **RDAP adapter:** Bootstrap caching verified — two sequential lookups for different domains fetch bootstrap exactly once
- [ ] **RDAP adapter:** Only non-GDPR-redacted fields in data model (creation date, registrar, nameservers, status) — no contact entity fields
- [ ] **RDAP adapter:** Redirect handling tested with a live RDAP endpoint; SEC-06 conflict documented and resolved
- [ ] **ASN provider (if separate):** Hostname added to `ALLOWED_API_HOSTS`; 429 returns `EnrichmentError` not a crash; not duplicating ip-api.com output
- [ ] **Annotations removal:** `grep -rn "AnnotationStore\|annotation" app/` returns zero results
- [ ] **Annotations removal:** `annotations.ts` removed from esbuild Makefile entry points
- [ ] **Annotations removal:** `annotations.db` initialization removed from `app/__init__.py` or app setup
- [ ] **Annotations removal:** All E2E tests referencing annotation UI elements removed or replaced
- [ ] **DNSBL + RDAP combined:** Single IP enrichment (all providers) completes in under 10 seconds
- [ ] **Public threat feeds:** Point-query APIs used (not full blocklist downloads) — no megabyte-scale responses per IOC
- [ ] **RDAP:** `supported_types` restricted to `{IOCType.DOMAIN, IOCType.IPV4}` — no hashes, CVEs, or URLs

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SSRF allowlist missing for new provider | LOW | Add hostname to `ALLOWED_API_HOSTS` in `config.py`; restart Flask; no code change to adapter needed |
| Spamhaus resolver block (`127.255.255.254`) returning false positives | MEDIUM | Add sentinel check to DNSBL response parser; re-run tests; no DB migration needed |
| RDAP returning mostly redacted data | LOW | Narrow `raw_stats` keys in adapter to structural fields only; update frontend template; no schema change |
| RDAP bootstrap re-fetched on every lookup | LOW | Add module-level cache dict with expiry timestamp; single-file change to adapter |
| Annotations removal crashes app at startup | MEDIUM | Temporarily restore import; work through grep-audit checklist layer by layer; test after each layer |
| DNSBL octet reversal missing (all IPs appear clean) | LOW | Fix reversal in query builder; add `127.0.0.2` fixture test; no data migration needed |
| Domain DNSBL reversal applied (all domains appear clean) | LOW | Remove reversal from domain code path; add `test.surbl.org` fixture test |
| BGPView included as ASN source | LOW | BGPView shut down November 2025; replace with ipinfo.io or Team Cymru; one adapter file change |
| RDAP SEC-06 conflict found after implementation | MEDIUM | Switch to RDAP library that handles redirects internally; or implement manual redirect with target validation |
| Serial DNSBL queries too slow for analyst | MEDIUM | Refactor `lookup()` to use `ThreadPoolExecutor` for parallel zone queries; add timing test |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SSRF allowlist not extended (Pitfall 1) | Every new provider phase — hostname added first | Unit test that calls `validate_endpoint()` without mocking |
| Spamhaus resolver block false positive (Pitfall 2) | DNSBL implementation phase | Mock DNS response `127.255.255.254`; assert `EnrichmentError` returned, not a listing |
| DNSBL IPv4 octet reversal missing (Pitfall 3) | DNSBL implementation phase | Unit test with `127.0.0.2`; assert listed result; this is the first test written (TDD red) |
| Domain DNSBL reversal applied incorrectly (Pitfall 4) | DNSBL implementation phase | Unit test with `test.surbl.org`; assert listed result |
| RDAP GDPR redaction noise (Pitfall 5) | RDAP design phase (before implementation) | Data model review: no contact/email/phone/address fields present |
| RDAP redirect vs. SEC-06 conflict (Pitfall 6) | RDAP design phase | Decision documented before writing adapter; integration test against live endpoint |
| Annotations removal incomplete (Pitfall 7) | Phase 1: Annotations removal | `grep -rn "AnnotationStore\|annotation" app/` returns zero; full test suite passes |
| RDAP bootstrap uncached (Pitfall 8) | RDAP implementation phase | Two sequential lookups; verify bootstrap fetched exactly once |
| Serial DNSBL query latency (Pitfall 9) | DNSBL implementation phase | Timing test: 5 DNSBL zones for one IP completes in under 5 seconds total |

---

## Sources

- Spamhaus DNSBL FAQ and open resolver blocking: https://www.spamhaus.org/faqs/dnsbl-usage/
- Spamhaus Cloudflare resolver advisory (127.255.255.254 sentinel): https://www.spamhaus.com/resource-center/successfully-accessing-spamhauss-free-block-lists-using-a-public-dns/
- Spamhaus Microsoft resolver advisory: https://www.spamhaus.com/resource-center/query-the-spamhaus-projects-legacy-dnsbls-via-microsoft/
- RDAP.org rate limiting (Cloudflare 429 at 10 req/10 sec): https://about.rdap.org/
- RFC 9224 — RDAP bootstrap registry and caching requirement (SHOULD NOT fetch on every request): https://datatracker.ietf.org/doc/html/rfc9224
- RDAP redirect server behavior (301 to authoritative RIR): https://rdap.rcode3.com/server_implementations/redirect.html
- RDAP GDPR redaction statistics (10.8% registrant visibility, 58.2% proxy protection as of Jan 2024): https://domaindetails.com/kb/security-privacy/whois-privacy-after-gdpr
- RFC 9537 — RDAP Redacted Fields specification (March 2024): https://datatracker.ietf.org/doc/rfc9537/
- WHOIS sunset date (January 28, 2025): https://domaindetails.com/kb/technical-guides/rdap-explained
- BGPView shutdown (November 26, 2025): confirmed via pfBlockerNG community migration reports
- ipinfo.io free tier limits (50k/month with token, 1k/day unauthenticated): https://ipinfo.io/faq/article/61-usage-limit-free-plan
- DNSBL octet reversal and response codes: https://en.wikipedia.org/wiki/Domain_Name_System_blocklist
- pydnsbl async DNSBL library (parallel zone queries with aiodns): https://pypi.org/project/pydnsbl/
- RFC 6471 — DNSBL operational best practices: https://datatracker.ietf.org/doc/html/rfc6471
- DNS rebinding SSRF bypass patterns: https://ghostsecurity.com/blog/how-to-prevent-ssrf-attacks-in-2025
- SentinelX codebase: `app/config.py` (ALLOWED_API_HOSTS), `app/enrichment/http_safety.py` (SEC-04 through SEC-07), `app/enrichment/adapters/dns_lookup.py` (existing DNS pattern), `app/enrichment/adapters/ip_api.py` (existing ASN fields in ip-api.com response), `app/routes.py` (AnnotationStore import location)

---

*Pitfalls research for: SentinelX v7.0 Free Intel — DNSBL, public threat feeds, RDAP, ASN/BGP, annotations removal*
*Researched: 2026-03-15*
