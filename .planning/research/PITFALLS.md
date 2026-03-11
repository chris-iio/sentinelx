# Pitfalls Research

**Domain:** Expanding a local IOC enrichment tool into a deeper analyst experience platform (zero-auth sources, bundled databases, open feeds)
**Researched:** 2026-03-11
**Confidence:** HIGH — sourced from MaxMind official docs, dnspython official docs, verified GitHub issues, community post-mortems, and direct codebase audit of SentinelX v5.0

---

## Context: What This Research Covers

SentinelX v5.0 is a working, security-first, 8-provider enrichment tool running on Python 3.10 + Flask 3.1.
The v6.0 expansion adds **zero-auth enrichment** (DNS, GeoIP, WHOIS, ASN, certificate transparency),
**bundled databases** (GeoLite2/ASN MMDB files), and **richer results UX**. The existing system has
strict security posture: SSRF allowlist, CSP, CSRF, no subprocess, no innerHTML, and a Provider Protocol
(`typing.Protocol`) that governs all adapters.

The pitfalls below are calibrated for this exact context — not a generic enrichment tool.

---

## Critical Pitfalls

### Pitfall 1: GeoLite2 License Requires Free-But-Not-Anonymous Signup

**What goes wrong:**
Developers assume "free database" means "download and ship it." GeoLite2 databases are free but
require a MaxMind account and license key to download since December 30, 2019. Users who try to
bundle a pre-downloaded MMDB in the repo will violate the license if they do not personally own
the file. Users who discover the download requires a MaxMind account at install time feel misled
by documentation that said "zero-auth."

**Why it happens:**
The `maxminddb-geolite2` Python convenience package on PyPI was once a widely-cited workaround —
it bundled the database directly. That package now has **inactive maintenance status** and the bundled
database is severely stale (Snyk Advisory). Developers find it in blog posts from before 2019 and
treat it as current best practice.

**How to avoid:**
- Do NOT bundle the MMDB files in the repository
- Do NOT use `maxminddb-geolite2` from PyPI — it is unmaintained and stale
- Use the official `geoip2` library + MaxMind's `geoipupdate` tool for database management
- Document that GeoIP/ASN features require a (free) MaxMind account during first-run setup
- Present GeoIP features as "optional enhanced enrichment — requires one-time MaxMind signup"
  rather than "zero-auth" to avoid user frustration
- Store MMDB path in `~/.sentinelx/config.ini` under `[local_databases]` — same pattern as API keys

**Warning signs:**
- Any reference to `maxminddb-geolite2` as the installation path
- MMDB files appearing in `.gitignore` exemption or tracked in the repo
- Documentation that says "no signup needed" for GeoIP features

**Phase to address:**
GeoIP/ASN phase — document the MaxMind signup requirement explicitly in the feature plan and
in any first-run setup message. Treat this as a soft dependency with graceful degradation.

---

### Pitfall 2: Bundled MMDB Files Become Stale — Lookups Return Wrong Country/ASN Data

**What goes wrong:**
MaxMind updates GeoLite2 databases weekly (every Tuesday). IP allocations change as ISPs acquire,
reassign, or return CIDR blocks. A bundled MMDB that is 3+ months old can misidentify the country
or ASN for a significant fraction of IP addresses. An analyst sees "Germany" for a Russian IP and
draws a wrong conclusion. Worse, the tool shows confident geolocation with no indication the data
is stale — the analyst trusts it.

**Why it happens:**
The database is included once at development time and never updated. There is no automatic
refresh mechanism. The developer tests with one or two IPs they know and the results look correct
(because common major-provider IPs rarely change registrations).

**How to avoid:**
- Never commit MMDB files to the repository — document the required path and update cadence
- Check MMDB file modification time at startup; warn if the file is older than 30 days
- Display data age next to every GeoIP result: "GeoIP data from [file date]"
- Document in setup instructions: "Run `geoipupdate` weekly or set a cron job"
- Use `mmdb_file_path` in config; if absent, skip GeoIP enrichment with a clear "not configured"
  status rather than using a stale bundled file
- MaxMind's EULA actually **requires** deletion of databases older than 30 days after a new
  release — violating this is a license compliance issue, not just an accuracy concern

**Warning signs:**
- GeoIP results are shown without a "data as of" date
- MMDB file is present in the repo, not in `.gitignore`
- No check for file modification time before use

**Phase to address:**
GeoIP/ASN phase — implement a freshness check at adapter initialization time. If file is older
than 30 days, log a warning and surface it in the UI alongside results.

---

### Pitfall 3: DNS Lookups Block the ThreadPoolExecutor — Silent Performance Cliff

**What goes wrong:**
The existing `EnrichmentOrchestrator` uses `ThreadPoolExecutor(max_workers=4)`. Adding DNS lookups
via `dnspython` or Python's `socket.getaddrinfo()` to the same pool means DNS resolution competes
with HTTP provider calls for the 4 worker slots. A single slow DNS server (timeout: 5+ seconds) or
DNS NXDOMAIN for a domain with many NS records can stall the entire pool. The analyst sees the
progress bar freeze, not time out — there is no per-DNS-query timeout visible to the orchestrator.

Python's `socket.getaddrinfo()` (used by default DNS resolution) is **not thread-safe** and has
no reliable per-call timeout. The `dnspython` library IS thread-safe for `resolve()` calls on a
shared `Resolver` instance, but the default `lifetime` parameter (the total time allowed across
all DNS servers for a single query) defaults to a generous value.

**Why it happens:**
DNS lookups feel like cheap, fast operations in development (local resolver responds in <10ms).
Under production conditions — split-brain DNS, corporate resolvers with SERVFAIL cascades, or
resolving malicious domains that have intentionally flaky authoritative servers — DNS can take
30+ seconds per query before the resolver gives up.

**How to avoid:**
- Use `dnspython` (`dns.resolver`), NOT `socket.getaddrinfo()` for all DNS enrichment — it
  supports per-resolver timeout configuration
- Create a module-level shared `dns.resolver.Resolver` instance — it is safe for concurrent
  `resolve()` calls from multiple threads
- Set `resolver.lifetime = 5.0` (seconds) — this is the total per-query budget across all
  nameservers; default is much higher
- Set `resolver.timeout = 2.0` (seconds) — per-nameserver attempt timeout
- Wrap all DNS exceptions explicitly:
  ```python
  except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):   # legitimate no-data
      verdict = "no_data"
  except dns.exception.Timeout:                             # slow/unresponsive NS
      return EnrichmentError(...)
  except dns.resolver.NoNameservers:                        # all NS unreachable
      return EnrichmentError(...)
  ```
- Consider a separate, higher `max_workers` value for DNS-only lookups since they are I/O-bound
  and fast when they succeed — or implement a DNS-specific timeout wrapper
- Add a hardened `supported_types` set: a DNS adapter should only accept `domain` IOC types to
  avoid unexpected lookup attempts on IPs or hashes

**Warning signs:**
- DNS lookup uses `socket.getaddrinfo()` instead of `dnspython`
- No `lifetime` or `timeout` set on the `dns.resolver.Resolver` instance
- DNS lookups share the same `max_workers=4` pool as HTTP provider calls without consideration
- No explicit `except dns.exception.Timeout` in the adapter

**Phase to address:**
DNS enrichment phase — implement timeout guards before wiring into the orchestrator. Add a
unit test that simulates DNS timeout by mocking `dns.resolver.Resolver.resolve` to raise
`dns.exception.Timeout` and verifies the adapter returns `EnrichmentError`, not a hang.

---

### Pitfall 4: WHOIS Returns "REDACTED FOR PRIVACY" — Parsed as Empty, Treated as Error

**What goes wrong:**
Since GDPR enforcement (2018), the majority of WHOIS records for gTLDs return PII fields with
literal text like `"REDACTED FOR PRIVACY"`, `"DATA REDACTED"`, or entirely empty fields. The
`python-whois` library parses these as legitimate registrant/email values — so `result.registrant_email`
returns `"REDACTED FOR PRIVACY"` as a string, not `None`. Code that checks `if result.registrant_email:`
treats this as success and shows "REDACTED FOR PRIVACY" as the registrant email in the analyst UI.
This is technically correct but confusing — it looks like a bug.

Worse: many WHOIS servers rate-limit aggressively. `python-whois` can **hang indefinitely** on
rate-limited connections (no timeout by default). A domain whose WHOIS server is rate-limiting
will silently stall the lookup thread until the connection eventually fails.

**Why it happens:**
WHOIS was designed before GDPR. The `python-whois` library does not normalize privacy strings.
Developers test with a few hand-picked domains during development and never see a rate-limited
or fully-redacted response.

**How to avoid:**
- Use `python-whois` with explicit socket timeout: wrap the lookup in a thread with a timeout,
  or patch the socket timeout before calling — `python-whois` does not expose a timeout parameter
  directly; use `socket.setdefaulttimeout(10)` before the call and restore it after
- Alternatively, use `whoisit` (RDAP-based, `pip install whoisit`) which provides structured JSON
  via IANA's RDAP service — rate limits are less severe and data is machine-readable
- Normalize privacy strings: if a field value contains "REDACTED", "PRIVACY", or "WITHHELD",
  treat it as `None` and display "Redacted (GDPR)" in the UI
- WHOIS enrichment is explicitly listed as "Out of Scope" in `PROJECT.md` for v6.0 — if
  reconsidering, treat it as a high-risk feature requiring its own research phase
- Display WHOIS fields with a "data quality" indicator: "Registration date", "Registrar",
  and "Domain age" are reliably available; registrant contact fields are frequently redacted

**Warning signs:**
- WHOIS lookup has no timeout
- `result.registrant_email` displayed directly without privacy-string normalization
- WHOIS included in the main enrichment pool (it should be a separate, optional call due to
  rate limit risk)

**Phase to address:**
If WHOIS is added: implement it as a **separate, isolated lookup** — not wired into the main
`EnrichmentOrchestrator` pool. Timeout wrapper is mandatory. Privacy normalization is mandatory.
Given the "Out of Scope" note in `PROJECT.md`, treat this as a Phase N+ feature, not v6.0.

---

### Pitfall 5: Certificate Transparency Lookup Returns Hundreds of Subdomain Records — UI Overload

**What goes wrong:**
`crt.sh` is the canonical CT log search API. A query for a domain like `google.com` returns
thousands of certificate records — wildcard certs, expired certs, subdomains at every level.
An adapter that naively presents "certificates found" as a count and a list will overwhelm the
analyst with hundreds of rows in an already-dense results UI.

The `crt.sh` HTTP JSON API (via `https://crt.sh/?q=domain&output=json`) is public and zero-auth
but **has no documented rate limit** — it silently starts returning 504 Gateway Timeout errors
under heavy load. The direct PostgreSQL access (`psql -h crt.sh -p 5432`) provides more
flexibility but has strict session idle timeout (connection drops quickly) and is not appropriate
for a production Flask route.

**Why it happens:**
CT data is inherently wide — certificates exist for every subdomain. Developers test with a
private or small domain that has only 3-4 certificates and design the UI for that scale.

**How to avoid:**
- Aggregate CT results, not list them: show "X unique subdomains, Y certificates found,
  oldest [date], newest [date]" rather than individual certificate rows
- Limit API response processing: cap at 50 or 100 records for display purposes; show "X+ more"
- Wrap crt.sh HTTP call with a strict timeout (8-10 seconds) and treat 504 as a soft failure
  (`verdict="no_data"` with error note "CT log temporarily unavailable")
- Use `https://crt.sh/?q=%.domain.tld&output=json` (leading `%` for subdomain wildcard) — note
  that the bare `q=domain.tld` also returns certs for parent domains which may not be wanted
- Only support `domain` IOC type — CT lookups make no sense for IPs or hashes
- Show CT data as "passive DNS / subdomain intelligence" rather than a verdict

**Warning signs:**
- CT adapter returns raw list of certificate objects to the UI
- No response size cap on the crt.sh API call (SEC-05 `read_limited` pattern must apply)
- CT lookup included for all IOC types rather than domain-only

**Phase to address:**
CT log phase — design the UI aggregation layer before writing the adapter. The data shape
drives the adapter output schema; do not write the adapter first and retrofit the UI.

---

### Pitfall 6: Zero-Auth Provider That Always Returns `is_configured() = True` Becomes Noise

**What goes wrong:**
Zero-auth providers (DNS, GeoIP, Shodan InternetDB) implement `is_configured()` returning `True`
always. This works correctly for Shodan InternetDB because the API is unconditionally available.
But for GeoIP/ASN (requires local MMDB file) or DNS (requires `dnspython` installed), returning
`True` when the underlying resource is missing means the adapter runs, fails with an unexpected
error, and returns `EnrichmentError("MMDB file not found")` — which appears in the UI alongside
real results.

The existing `setup.py` registers all configured providers. If a zero-auth provider is always
registered and never checks its actual preconditions, it adds noise to every result set regardless
of whether the analyst expected it.

**Why it happens:**
The SentinelX Provider Protocol's `is_configured()` contract was designed for API-key providers:
"True if you have a key, False if you don't." Zero-auth providers inherit this design but have
different readiness conditions (file exists, library installed, etc.).

**How to avoid:**
- For MMDB-based providers (GeoIP, ASN): `is_configured()` should check that the configured
  MMDB path exists and is readable, not just that the path is non-empty in config:
  ```python
  def is_configured(self) -> bool:
      path = self._mmdb_path
      return bool(path) and os.path.isfile(path)
  ```
- For DNS: `is_configured()` should verify `dnspython` is importable (it is an optional dep)
- The orchestrator already gates on `is_configured()` before dispatch — this pattern is correct;
  the adapter must be honest about its readiness
- Distinguish between "not configured" (user hasn't set it up) and "configured but file missing"
  in error messages — they require different user actions

**Warning signs:**
- Zero-auth adapter `is_configured()` returns `True` unconditionally
- `EnrichmentError("MMDB file not found")` appearing in normal result sets
- No MMDB path validation at adapter initialization or at `is_configured()` time

**Phase to address:**
Each local-database adapter phase — establish the `is_configured()` contract for file-backed
providers before wiring into the registry.

---

### Pitfall 7: DNS Rebinding Attack Against the SSRF Allowlist

**What goes wrong:**
The existing SSRF allowlist (`http_safety.py`) validates hostnames against `ALLOWED_API_HOSTS`
before every network call. A DNS-based enrichment adapter introduces a new attack surface:
**DNS rebinding**. The attack flow: malicious IOC `evil.attacker.com` resolves to a public IP
(passes the `is_safe_url()` check), but the attacker's DNS server then returns `127.0.0.1`
for the second resolution (the actual HTTP connection). This bypasses hostname-based allowlists.

This attack is most relevant if SentinelX ever accepts IOC values from untrusted sources and
makes outbound HTTP calls to domains derived from those values. For the DNS enrichment adapter
itself (which looks up analyst-provided domains), the risk is lower — but the existing SSRF
allowlist pattern assumes HTTP calls, not DNS lookups.

**Why it happens:**
The SSRF protection in `http_safety.py` validates the URL before the HTTP call. DNS rebinding
exploits the time gap between validation and connection. This is a Time-Of-Check/Time-Of-Use
(TOCTOU) vulnerability pattern.

**How to avoid:**
- DNS enrichment adapters do DNS **lookups** of IOC values — they do not make HTTP calls to
  those domains; the DNS lookup itself is safe (it calls the configured resolver, not the target)
- Ensure DNS adapters never use the resolved IP to make subsequent HTTP connections — lookups
  should terminate at the DNS response
- For any feature that resolves a domain and then connects to the resolved IP (e.g., banner
  grabbing, HTTP header checks), implement a double-resolution check:
  1. Resolve the domain before connection attempt
  2. Verify the resolved IP is not in RFC1918/loopback/link-local space
  3. Make the connection to the explicit IP (not the hostname) to prevent re-resolution
- Add RFC1918 + loopback IP check to `http_safety.py` for any IPs derived from DNS resolution

**Warning signs:**
- Any adapter that resolves a domain and then makes an HTTP call to that domain
- HTTP calls to analyst-provided URLs without IP-level validation
- Feature involving "fetch HTTP headers" or "check HTTP response" for IOC domains

**Phase to address:**
Any network-enrichment phase that touches analyst-provided domain values — add IP validation
to `http_safety.py` as a shared utility before building features that depend on it.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Bundle GeoLite2 MMDB in repo | Simple install, no setup friction | License violation, stale data, large repo size | Never — document the download path instead |
| Use `maxminddb-geolite2` PyPI package | One-line install, no signup | Unmaintained, database is 1+ year stale | Never — use official `geoip2` + `geoipupdate` |
| Use `socket.getaddrinfo()` for DNS | Standard library, no extra deps | No per-call timeout, not thread-safe, no fine-grained error handling | Never for production enrichment paths |
| Share a single `requests.Session` across DNS+HTTP adapters | Slightly lower overhead | Connection pool pollution, session state leaks between adapter types | Never — DNS adapters don't use HTTP sessions anyway |
| Show all CT certificate records raw | Simple implementation | Hundreds of rows in UI, analyst cognitive overload | Never — aggregate before display |
| Register zero-auth providers unconditionally | Simple setup.py | Errors in results when MMDB missing, no graceful degradation | Never — `is_configured()` must check actual readiness |
| Add WHOIS in main enrichment pool | Feature completeness | Rate limit hangs stall all other results | Never — WHOIS must be isolated if added at all |
| Accept `any` IOC type in DNS/GeoIP adapters | Broader coverage appearance | Silent errors for hash/URL/CVE types that can't be DNS-queried | Never — `supported_types` must be precise |

---

## Integration Gotchas

Common mistakes when connecting zero-auth and local enrichment sources.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MaxMind GeoLite2 | Use `maxminddb-geolite2` package or bundle MMDB in repo | Use official `geoip2` library; store MMDB at `~/.sentinelx/GeoLite2-*.mmdb`; check file freshness |
| `dnspython` resolver | Create a new `Resolver()` per lookup call | Create one module-level `Resolver` with `lifetime=5.0` and `timeout=2.0`; it is thread-safe for `resolve()` |
| `dnspython` NXDOMAIN | Treat `NXDOMAIN` as an error → `EnrichmentError` | `NXDOMAIN` is a valid DNS response meaning "no record" → `verdict="no_data"` |
| `dnspython` NoAnswer | Treat `NoAnswer` as error | `NoAnswer` means the record type doesn't exist for that domain → `verdict="no_data"` |
| crt.sh API | Query `q=domain.tld` and display all results | Query `q=%.domain.tld`, cap at 100 results, aggregate into subdomain count + date range |
| crt.sh 504 | Propagate as HTTP error to analyst | Treat as soft failure: `verdict="no_data"`, note "CT log temporarily unavailable" |
| pyasn / BGPView | Use BGPView REST API for ASN lookups | BGPView blocks user agents and rate-limits aggressively; use `pyasn` with local BGP dump or ipwhois RDAP for ASN data |
| WHOIS timeout | Call `python-whois` directly in enrichment thread | Use `socket.setdefaulttimeout(10)` wrapper or isolate in a separate timed thread; never block enrichment pool |
| Provider Protocol with MMDB | `is_configured()` returns `True` if config key exists | `is_configured()` must verify `os.path.isfile(configured_path)` — config key presence is not sufficient |

---

## Performance Traps

Patterns that work fine for 1-2 IOCs but degrade with realistic analyst workloads (10-50 IOCs).

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| DNS lookup per IOC on main pool (max_workers=4) | Progress stalls when any DNS server is slow; HTTP providers queued behind DNS | Increase `max_workers` for DNS-heavy workloads, or give DNS adapters a dedicated executor | 5+ domains with at least one slow nameserver |
| Opening MMDB file on every `lookup()` call | GeoIP lookups are slow, CPU spikes | Open `maxminddb.open_database()` once at adapter init; store as `self._reader` | Every lookup call |
| WHOIS in main enrichment pool | One rate-limited WHOIS hangs entire job | Isolate WHOIS calls with per-call timeout; run after primary enrichment completes | First rate-limited domain (~5% of queries) |
| CT log query blocking on crt.sh unavailability | All domain lookups stall for 8-10 seconds while CT times out | Wrap with strict timeout; treat 504 as immediate soft failure | crt.sh intermittent outages (happens monthly) |
| Loading GeoIP + ASN MMDB readers from disk on every request | Slow first lookup, high I/O | Initialize readers at Flask app startup or adapter singleton init | Concurrent requests |
| No caching for DNS results | Same domain looked up 8x (once per provider) and also via DNS adapter | DNS results are cacheable — the existing `CacheStore` (SQLite) should apply | Any IOC list with repeated domains |

---

## Security Mistakes

Domain-specific security issues beyond general web security, specific to zero-auth enrichment expansion.

| Mistake | Risk | Prevention |
|---------|------|------------|
| DNS rebinding via resolved-then-HTTP pattern | SSRF bypass to internal services | Never make HTTP connections to domains derived from analyst IOC values without IP validation; DNS lookups (not HTTP) are safe |
| Displaying raw MMDB data without sanitization | GeoIP city/org names in MMDB can contain arbitrary Unicode/HTML-like strings | All MMDB string fields go through `textContent` (never `innerHTML`) — existing SEC-08 pattern |
| Logging IOC values from failed DNS lookups | Analyst IPs and internal hostnames appear in server logs | Log only error type and provider name, never IOC value in error logs |
| Using `subprocess` to call `whois` binary | Violates PROJECT.md constraint (no subprocess); potential injection if IOC value reaches shell | Never use subprocess; use `python-whois` (pure Python) or `whoisit` (HTTP/RDAP) |
| Bundling MMDB with insecure permissions | MMDB file readable by other local users on shared jump box | Document that MMDB files should be stored with 600 permissions in `~/.sentinelx/` |
| ipwhois/python-whois making outbound connections to IOC nameservers | DNS provider could log the query, revealing analyst investigation focus | Acceptable risk for a SOC tool; document this in threat model; ensure analyst awareness |

---

## UX Pitfalls

Common user experience mistakes when expanding from "simple results" to "deep analysis."

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Adding GeoIP/ASN/DNS columns to existing result cards | Cards become wide tables; analyst loses the "at a glance" verdict clarity established in v4.0 | Add enrichment data as a new expandable section within existing card — preserve summary row |
| Showing "no data" for every zero-auth source on every IOC | Result grid fills with grey "no data" badges for GeoIP on hash IOCs, DNS on IP IOCs | Suppress zero-auth providers from result display when `supported_types` makes them irrelevant (e.g., GeoIP on hashes) |
| Treating GeoIP country as a verdict | Analyst may misinterpret "Russia" as "malicious" | GeoIP is context, not verdict — display as metadata, never as a colored verdict badge |
| CT "found X certificates" displayed prominently | Suggests the domain is suspicious due to having certificates (all HTTPS sites do) | Label CT data as "certificate history" — normalize it as neutral context |
| DNS resolution showing "resolved" as green/clean | Successful DNS resolution is not a positive indicator | DNS resolution is infrastructure data, not threat intel — use neutral grey display |
| New enrichment sources showing "Loading..." indefinitely | Analyst confusion when MMDB is not configured or dnspython not installed | Show "Not configured" state clearly for each optional source; link to setup instructions |
| Info-dumping: showing all enrichment sections expanded by default | Analyst cognitive overload — they came to triage, not read a thesis | New enrichment sections start collapsed; only expand automatically for suspicious/malicious findings |

---

## "Looks Done But Isn't" Checklist

- [ ] **GeoIP adapter:** `is_configured()` returns True — but verify it calls `os.path.isfile(path)` not just `bool(path)`
- [ ] **GeoIP freshness:** Results are displaying — but verify file modification time is checked and surfaced in the UI
- [ ] **DNS adapter:** Lookups succeed in dev — but verify `lifetime` and `timeout` are set on the Resolver and tested with a simulated timeout
- [ ] **DNS adapter:** NXDOMAIN returns no data — but verify it returns `EnrichmentResult(verdict="no_data")` not `EnrichmentError`
- [ ] **CT log adapter:** Domain returns results — but test with a major domain (e.g., `microsoft.com`) to verify response capping at 100 records
- [ ] **CT log adapter:** Results display — but verify the `read_limited()` SEC-05 pattern is applied (crt.sh responses can be very large)
- [ ] **Zero-auth providers:** All pass unit tests — but test the "MMDB file missing" code path to verify clean degradation
- [ ] **maxminddb reader:** GeoIP lookups are fast — but verify the `maxminddb.open_database()` call happens once at init, not on every `lookup()` call
- [ ] **ThreadPool:** All providers complete — but verify DNS lookups do not stall the pool by timing a 50-domain batch
- [ ] **Results UX:** New sections added — but verify they are collapsed by default and do not break existing verdict/filter summary row layout

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Stale bundled MMDB discovered | MEDIUM | Remove from repo, add to .gitignore, document download path, add freshness check to adapter |
| DNS pool starvation stalling other providers | MEDIUM | Increase `max_workers` or add separate DNS executor; add `lifetime` timeout; re-test with 50-domain batch |
| WHOIS hanging enrichment pool | HIGH | Remove WHOIS from main pool, implement isolated timeout wrapper, redeploy — stale in-flight jobs must time out |
| CT results overwhelming analyst (thousands of rows) | LOW | Add server-side cap to 100 results + aggregation; no UX re-architecture needed |
| `maxminddb-geolite2` stale data discovered | LOW | Replace with official `geoip2` library + fresh MMDB download; update config |
| Zero-auth provider showing spurious errors | LOW | Fix `is_configured()` to check actual readiness; errors disappear from results |
| GeoIP/ASN reader opened per-call (slow) | LOW | Move `maxminddb.open_database()` to adapter `__init__`; restart Flask |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| GeoLite2 license/signup requirement (Pitfall 1) | GeoIP/ASN phase planning | Setup docs state MaxMind account is required; no MMDB in repo |
| Stale bundled MMDB (Pitfall 2) | GeoIP adapter implementation | File freshness check exists; `.gitignore` includes `*.mmdb`; UI shows data age |
| DNS blocking thread pool (Pitfall 3) | DNS enrichment phase | `Resolver.lifetime=5.0` set; unit test for timeout behavior; 50-domain batch completes in <30s |
| WHOIS privacy/hang (Pitfall 4) | Defer to post-v6.0 | WHOIS remains "Out of Scope" in v6.0; revisit only with dedicated research |
| CT log UI overload (Pitfall 5) | CT log phase | Adapter caps at 100 records; test with `microsoft.com`; SEC-05 applied |
| Zero-auth always-True is_configured (Pitfall 6) | Each local-DB adapter phase | `is_configured()` verifies `os.path.isfile()`; test missing-file code path |
| DNS rebinding / SSRF expansion (Pitfall 7) | Any network-enrichment phase | No adapter makes HTTP calls to IOC-derived hostnames; IP validation added to `http_safety.py` if needed |

---

## Sources

- MaxMind GeoLite2 licensing changes (December 2019, account required): https://blog.maxmind.com/2019/12/significant-changes-to-accessing-and-using-geolite2-databases/
- MaxMind GeoLite2 EULA (30-day deletion requirement): https://www.maxmind.com/en/geolite2/eula
- MaxMind GeoLite2 developer docs (update frequency, download): https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/
- maxminddb-geolite2 PyPI inactive maintenance status: https://snyk.io/advisor/python/maxminddb-geolite2
- dnspython thread safety docs: https://dnspython.readthedocs.io/en/latest/threads.html
- dnspython resolver class (lifetime, timeout parameters): https://dnspython.readthedocs.io/en/latest/resolver-class.html
- dnspython exceptions reference: https://dnspython.readthedocs.io/en/latest/exceptions.html
- python-whois "not found" parsing issues: https://github.com/DannyCork/python-whois/issues/89
- python-whois rate limit behavior: https://github.com/DannyCork/python-whois/issues/167
- whoisit RDAP library (structured alternative to python-whois): https://github.com/meeb/whoisit
- WHOIS GDPR redaction impact on cybersecurity: https://main.whoisxmlapi.com/privacy-or-accountability-what-the-redaction-of-whois-data-means-for-cybersecurity
- crt.sh architecture and HTTP API availability: https://www.lukeshu.com/blog/crt-sh-architecture.html
- BGPView rate limiting and user-agent blocking: community reports + https://bgpview.docs.apiary.io/
- pyasn local lookup approach: https://github.com/hadiasghari/pyasn
- DNS rebinding SSRF bypass pattern: https://www.clear-gate.com/blog/ssrf-with-dns-rebinding-2/
- OWASP SSRF prevention (allow-lists over deny-lists): https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- SentinelX codebase: `app/enrichment/provider.py` (Provider Protocol — `is_configured()` contract)
- SentinelX codebase: `app/enrichment/http_safety.py` (SSRF allowlist, SEC-04 through SEC-07 patterns)
- SentinelX codebase: `app/enrichment/adapters/shodan.py` (zero-auth adapter reference implementation)
- SentinelX codebase: `.planning/PROJECT.md` (WHOIS "Out of Scope" note; no-subprocess constraint)

---

*Pitfalls research for: v6.0 analyst experience expansion — zero-auth enrichment, bundled databases, open feeds*
*Researched: 2026-03-11*
