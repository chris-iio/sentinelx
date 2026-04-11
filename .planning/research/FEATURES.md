# Feature Landscape: SSH Login Anomaly Detection

**Domain:** SSH auth.log parsing and behavioral anomaly detection for SOC analysts
**Milestone:** v1.2 SSH Login Anomaly Detection
**Researched:** 2026-04-12
**Confidence:** HIGH (auth.log formats from official docs + field inspection); HIGH (anomaly
detection patterns from production SIEM rules + Elastic security); MEDIUM (UX workflow
from SOC analyst guides)

---

## Context: What v1.2 Adds to SentinelX

SentinelX already ships: IOC extraction, 14 threat intel providers, verdict display, detail pages,
cache, export, bulk input. v1.2 adds a second entry point: upload an auth.log file, get structured
anomaly alerts with per-IP enrichment. The two features share the Flask shell and ipinfo.io adapter
but operate as a distinct workflow with distinct routes.

**New capability in scope for v1.2:**
- SSH auth.log parser (structured event extraction)
- Per-user behavioral anomaly detector (4 rule types)
- GeoIP lookup via existing ipinfo.io adapter (reused)
- Upload UI + alerts table + JSON API endpoint

**Out of scope for v1.2 (documented in PROJECT.md):**
- Other log types (nginx, syslog, Apache)
- Real-time log streaming
- ML/AI models
- SIEM integration / STIX output
- Multi-user baselines

---

## auth.log Format Reference

This section documents every format variant a parser must handle. Confidence is HIGH for
Ubuntu/Debian (directly verified); MEDIUM for RHEL/CentOS (consistent with docs).

### Log File Locations by Distro

| Distro | Log Path | Notes |
|--------|----------|-------|
| Ubuntu 22.04 and earlier | `/var/log/auth.log` | rsyslog, BSD timestamp |
| Ubuntu 24.04+ | `/var/log/auth.log` | rsyslog RFC3339 timestamp (breaking change) |
| Debian 10–12 | `/var/log/auth.log` | rsyslog, BSD timestamp by default; may vary |
| RHEL / CentOS / Rocky / Alma | `/var/log/secure` | Same line format, different path |
| Arch Linux | `/var/log/auth.log` | journald or rsyslog depending on install |
| macOS | `/var/log/system.log` | Different host/process format |
| systemd-only systems | `journalctl -u sshd` | No flat file; must export via `journalctl -o syslog` |

### Timestamp Format Variations (Critical Edge Case)

This is the single most important parsing edge case. Two incompatible formats exist in the wild.

**BSD syslog (RFC 3164) — Ubuntu ≤ 23.10, Debian, RHEL:**
```
Jan 30 12:45:23 server sshd[1234]: Accepted password for user1 from 192.168.1.100 port 54321 ssh2
```
- No year. Parsers must infer year from current date.
- Day is space-padded for single digits: `Jan  5` (two spaces) — regex must handle `\s+`.
- No timezone. Local time only.
- Year rollover edge case: a December log parsed in January must be assigned the prior year.

**RFC 3339 / ISO 8601 — Ubuntu 24.04+, systemd journal exports:**
```
2024-03-04T17:39:08.271714+01:00 hostname sshd[35883]: Accepted publickey for user from 192.168.1.5 port 57528 ssh2: ED25519 SHA256:xxxxxx
```
- Full year + timezone + microseconds present.
- Different field order: timestamp is first, hostname is second (same as BSD).
- CrowdSec and other log parsers had production breakage on Ubuntu 24.04 upgrade due to this change
  (confirmed bug report: https://github.com/crowdsecurity/crowdsec/issues/4199).

**Parser must detect format from the first token of the first line and apply consistently.**

### sshd Message Types (All Variants)

Every line the parser will encounter. Non-sshd lines (cron, sudo, pam_unix without sshd) must be
skipped. Only lines containing `sshd[` are in scope.

**Successful logins (events to track):**
```
Accepted password for alice from 192.168.1.10 port 54321 ssh2
Accepted publickey for alice from 192.168.1.10 port 54321 ssh2
Accepted publickey for alice from 192.168.1.10 port 54321 ssh2: RSA SHA256:abc123
Accepted publickey for alice from 192.168.1.10 port 54321 ssh2: ED25519 SHA256:abc123
Accepted keyboard-interactive/pam for alice from 192.168.1.10 port 54321 ssh2
```

**Failed logins (events to track for brute-force detection):**
```
Failed password for alice from 10.0.0.1 port 52772 ssh2
Failed password for invalid user admin from 10.0.0.1 port 52772 ssh2
Failed publickey for alice from 10.0.0.1 port 52772 ssh2
Failed publickey for invalid user git from 10.0.0.1 port 52772 ssh2: ED25519 SHA256:abc123
Invalid user admin from 10.0.0.1
Illegal user admin from 10.0.0.1
input_userauth_request: invalid user admin [preauth]
```

**Session lifecycle (parse but low priority for anomaly detection):**
```
Disconnected from user alice 192.168.1.10 port 54321
Disconnected from authenticating user alice 192.168.1.10 port 54321 [preauth]
Connection closed by 192.168.1.10 port 54321 [preauth]
Connection reset by 192.168.1.10 port 54321 [preauth]
pam_unix(sshd:session): session opened for user alice(uid=1000) by (uid=0)
pam_unix(sshd:session): session closed for user alice
```

**Noise lines (skip entirely):**
```
Did not receive identification string from 10.0.0.1 port 55123
error: accept: Software caused connection abort
Maximum authentication attempts exceeded for alice from 10.0.0.1 port 22 ssh2 [preauth]
Server listening on 0.0.0.0 port 22
Postponed publickey for alice from 10.0.0.1 port 54321 ssh2
```

### IPv6 in auth.log

sshd logs IPv6 addresses unbracketed and uncompressed in standard notation:
```
Accepted publickey for alice from 2001:db8:85a3::8a2e:370:7334 port 54321 ssh2
Failed password for alice from ::1 port 54321 ssh2
```

Compressed IPv6 (using `::`) is valid and must be handled. Link-local addresses with zone IDs
(`fe80::1%eth0`) are rare in auth.log context but can appear. The existing `IPApiAdapter` already
declares `IOCType.IPV6` support, so the GeoIP lookup path handles IPv6 natively. The parser regex
must use `IPORHOST` equivalent logic: match `[0-9a-fA-F:]+` for IPv6 and `[\d.]+` for IPv4,
preferably using Python's `ipaddress` module for validation rather than regex alone.

Private/loopback IPs (`127.0.0.1`, `::1`, RFC 1918 ranges) must be detected and skipped for GeoIP
lookup — the existing `_404_hook` in `IPApiAdapter` handles 404s from ipinfo.io for private IPs,
but callers should short-circuit before making network requests for obviously private addresses.

---

## Table Stakes

Features a SOC analyst expects from any SSH anomaly detection tool. Missing these makes the
tool feel incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Dependencies |
|---------|--------------|------------|--------------|
| auth.log file upload | Primary entry point — analyst uploads a log file collected from an endpoint | LOW | Flask `request.files`, `MAX_CONTENT_LENGTH` config |
| Parse Accepted/Failed events into structured records | Raw log → `{timestamp, user, ip, event_type, auth_method, port}` | MEDIUM | Dual timestamp format handling (BSD + RFC3339) |
| Per-IP GeoIP lookup (country, city, ASN) | Analysts need to know where login attempts came from, not just the raw IP | LOW | Reuse `IPApiAdapter` (already ships) |
| New IP alert per user | Flag when a user logs in from an IP they've never used in the uploaded log | LOW | Requires per-user historical IP set (derived from the uploaded log itself) |
| New country alert per user | Flag when country of login IP differs from all prior observed countries for that user in the log | MEDIUM | GeoIP lookup per IP + per-user country baseline |
| Brute-force detection | Flag N failed logins from same IP within time window (default: 10 failures in 5 minutes) | MEDIUM | Time-windowed failure count per source IP |
| Unusual hour login alert | Flag logins outside configurable normal window (default 06:00–22:00 local time) | LOW | Timestamp parsing + configurable window from config.ini |
| Alerts table with sortable columns | SOC analysts triage by severity; a flat unordered list is unusable at scale | MEDIUM | Frontend table with JS sort or server-side ordering |
| Per-alert severity level | CRITICAL / HIGH / MEDIUM / LOW — analyst must know which alerts to investigate first | LOW | Rule-specific severity assignment |
| IP enrichment link to existing SentinelX | When an alert surfaces an IP, the analyst should be able to click to the existing enrichment detail page | LOW | Link to `/ioc/ipv4/<ip>` — already exists |
| Parse failure summary | If 200 lines parsed and 18 failed, report that — don't silently drop bad lines | LOW | Track parse errors per line; summarize in response |
| JSON API endpoint | `POST /ssh/analyze` returning structured JSON alongside the HTML view — enables scripting and future integrations | LOW | Flask route with `request.accept_mimetypes` or separate `/api/ssh/analyze` |

---

## Differentiators

Features that elevate v1.2 beyond "grep for Accepted in auth.log." These are what make the tool
genuinely useful vs a shell script.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Impossible travel detection | Two logins for the same user from geographically distant locations within a time window too short for air travel (threshold: >1000 km/h implied speed) | HIGH | GeoIP for each unique IP + per-user ordered login timeline + haversine distance calculation |
| Per-user login summary | "alice: 14 logins from 3 IPs across 2 countries, 0 anomalies" — aggregate view before anomaly drill-down | MEDIUM | Accumulate per-user stats during parse pass |
| Configurable normal-hours window | `[ssh_detection] normal_hours_start = 6` / `normal_hours_end = 22` in config.ini — deployable without per-user learning | LOW | ConfigStore integration (already ships for API keys) |
| Alert deduplication | If the same IP triggers 500 failed logins, emit one brute-force alert, not 500 — alert count vs line count | MEDIUM | Group-and-deduplicate step between detection and output |
| Alert explanation fields | Each alert includes a human-readable `reason` field: "First seen IP for user alice. Previous IPs: 10.0.0.1, 10.0.0.2" — tells analyst why the alert fired | LOW | Embed context in the alert struct at detection time |
| Attack pattern classification | After detecting brute-force, classify: did any failure-source IP later succeed? ("Brute Force Success") or only fail ("Brute Force Attempt") — high-value MITRE T1110 signal | MEDIUM | Cross-reference failed IP set against successful IP set per log |
| Summary statistics header | Total lines parsed, successful logins, failed attempts, unique IPs, unique users, time range of log — gives analyst an orientation before diving into alerts | LOW | Accumulate during parse pass |
| "First login" flag | When a user's very first appearance in the log is a successful login from a foreign country, flag it distinctly vs a user with 50 prior logins — no baseline in the log means no comparison is possible | MEDIUM | Detect single-occurrence users and annotate alerts accordingly |

---

## Anti-Features

Features that are commonly requested or seem obviously useful but create more problems than they solve
for a local, upload-based, single-analyst tool.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| ML/AI anomaly models | Requires training data, model maintenance, false-positive tuning, Python ML dependency stack (scikit-learn, pandas) — massive surface area for a rule-based detection feature | 4 explicit rule types with configurable thresholds; explain exactly why each alert fired |
| "Known good" IP whitelist stored across sessions | Seems useful, but introduces persistent state management complexity; whitelist goes stale; analysts forget what's in it; creates false sense of security for whitelisted IPs that later get compromised | Surface GeoIP + ASN in every alert; let analyst make the judgment call |
| Real-time log streaming / tailing | Requires WebSocket or SSE, background thread, file handle management, log rotation awareness — architecturally complex for a batch triage tool | Upload-based batch analysis; analyst collects log from endpoint and uploads. PROJECT.md explicitly deferred this. |
| Other log types (nginx, syslog, Apache) | Each format requires its own parser, its own anomaly rules, its own output format — scope explosion | SSH auth.log only for v1.2. Other log types deferred explicitly in PROJECT.md. |
| SIEM / STIX / CEF export | Complex format with schema maintenance; low value for a local triage tool used by one analyst | JSON API endpoint covers the scripting case; STIX deferred in PROJECT.md |
| Per-user baseline database (persisted across uploads) | Would enable "this IP is new for alice historically" beyond the current file — but introduces a database with grow-forever behavior, schema migration, user management | Per-log baseline only: "new in this file." Document the limitation clearly in the UI. |
| Composite risk score per user | "alice's risk score is 73/100" — sounds useful, invites gaming and false confidence | Explicit alert list with severity per alert; follows SentinelX's "never invent scores" design principle |
| Automatic IP blocking or firewall rules | Some tools offer to emit iptables rules — dangerous for a triage tool | Read-only. Never emit actions. Users follow up in their own tooling. |
| Reverse DNS lookups for every IP | Seems like useful enrichment — but 1,000-line auth.log with 300 unique IPs means 300 DNS queries; adds latency, may be rate-limited | Show reverse DNS only on the detail page (already available via IPApiAdapter `hostname` field) |

---

## Feature Dependencies

```
File Upload
    enables──> Auth Log Parser

Auth Log Parser
    produces──> LoginEvent list (timestamp, user, ip, event_type, auth_method)
    produces──> ParseSummary (line count, error count, time range)
    feeds──> All anomaly detectors
    feeds──> Per-user login summary

GeoIP Lookup (per unique IP)
    requires──> Auth Log Parser (needs IP list)
    reuses──> IPApiAdapter (already ships; ipinfo.io, zero-auth)
    requires──> private IP short-circuit (skip 127.x, 10.x, 172.16-31.x, 192.168.x, ::1)
    feeds──> New Country detector
    feeds──> Impossible Travel detector
    feeds──> Alert enrichment (country/city/ASN in every alert)

New IP Alert
    requires──> Auth Log Parser
    requires──> per-user IP set (derived from log — no external state needed)
    complexity: LOW — set membership check

New Country Alert
    requires──> GeoIP Lookup
    requires──> per-user country set
    complexity: MEDIUM — GeoIP must complete before rule runs

Brute-Force Detection
    requires──> Auth Log Parser (Failed events)
    requires──> time-windowed failure count per source IP
    complexity: MEDIUM — sliding window or bucket-based counting
    enhances──> Attack Pattern Classification (did any brute-force IP later succeed?)

Unusual Hour Alert
    requires──> Auth Log Parser (Accepted events)
    requires──> ConfigStore normal_hours_start / normal_hours_end
    complexity: LOW — hour extraction from parsed timestamp

Impossible Travel Detection
    requires──> GeoIP Lookup (lat/lon for each IP)
    requires──> per-user ordered login timeline
    requires──> haversine distance calculation between consecutive logins
    requires──> speed threshold comparison (default 1000 km/h = commercial aviation)
    complexity: HIGH — most complex rule; needs ipinfo.io to return lat/lon (it does)

Alert Deduplication
    requires──> raw alert list from all detectors
    produces──> deduplicated alert list
    complexity: MEDIUM — group by (user, ip, rule_type) and merge

Alert Enrichment Link
    requires──> existing /ioc/ipv4/<ip> route (already ships)
    complexity: LOW — URL construction in template

JSON API Endpoint
    requires──> alert list (same data as HTML view)
    complexity: LOW — return JSON from same route based on Accept header or /api/ prefix
```

### Critical Dependency: GeoIP Rate Limit

ipinfo.io free tier: unlimited requests (no documented rate limit on the free tier, unlike ip-api.com
which caps at 45/min). However, a large auth.log may contain hundreds of unique IPs. Deduplicate IPs
before lookups (one request per unique IP, not one per log line). A 10,000-line brute-force log
might have 1 attacking IP — deduplicate first.

### Critical Dependency: Timestamp Parsing Must Precede All Detectors

Impossible travel, unusual hours, and brute-force time windows all require accurate timestamps.
BSD format lacks year and timezone — the parser must inject the inferred year before any detector
runs. Detector code must never do timestamp arithmetic directly on raw strings.

---

## MVP Definition (v1.2 Core)

Minimum feature set that delivers genuine analyst value.

**Must ship:**
- File upload (POST endpoint, `multipart/form-data`, `MAX_CONTENT_LENGTH` enforced)
- Auth log parser (BSD + RFC3339 timestamps, 8 message types, IPv4 + IPv6)
- GeoIP per unique IP (reuse `IPApiAdapter`, skip private ranges)
- New IP alert (LOW severity — informational)
- New country alert (MEDIUM severity)
- Brute-force detection: 10 failures/5-minute window (HIGH severity)
- Unusual hour login: outside 06:00–22:00 (MEDIUM severity, configurable)
- Alert table with per-alert severity, user, IP, country, reason text, link to enrichment
- Parse summary: lines parsed, events extracted, errors, time range
- JSON API response (`Accept: application/json` or `/api/ssh/analyze`)

**Add in v1.2 if time allows (not blocking):**
- Impossible travel detection (HIGH/CRITICAL severity) — high-value but depends on ipinfo.io lat/lon
  fields being present in response; needs haversine implementation
- Attack pattern classification (did brute-force IP later succeed?)
- Per-user login summary header

**Defer to v1.3+:**
- ConfigStore integration for `normal_hours_start` / `normal_hours_end` (hardcode defaults in v1.2)
- Alert export (JSON download) — JSON API covers the scripting case
- DNSBL lookup for source IPs (separate milestone per REQUIREMENTS.md)

---

## Alert Format: What Makes an Alert Actionable

Based on SOC triage workflow research, each alert must contain:

| Field | Purpose | Example |
|-------|---------|---------|
| `severity` | CRITICAL / HIGH / MEDIUM / LOW | HIGH |
| `rule` | Machine-readable rule ID | `new_country` |
| `user` | SSH username affected | `alice` |
| `source_ip` | IP that triggered the alert | `185.220.101.5` |
| `country` | Country from GeoIP | `RU` |
| `city` | City from GeoIP | `Moscow` |
| `asn` | ASN org from GeoIP | `AS204428 (SSAB)` |
| `timestamp` | Login event time (ISO 8601) | `2024-01-30T14:23:00` |
| `reason` | Human-readable explanation | `First login from country RU for user alice. Prior countries: US` |
| `enrichment_url` | Link to SentinelX detail page | `/ioc/ipv4/185.220.101.5` |
| `auth_method` | password / publickey | `password` |

What makes alerts actionable vs noisy:

- **Reason field is mandatory.** "New IP for alice" with no context is noise. "New IP for alice —
  previous IPs: 10.0.0.1, 10.0.0.2 (all US/Hetzner). New IP geolocates to RU/Moscow" is a lead.
- **Deduplication is mandatory.** 8,114 failed login lines from one IP = one brute-force alert.
  Without deduplication, the analyst sees 8,000 rows and learns nothing.
- **Severity differentiation is mandatory.** If everything is HIGH, nothing is HIGH. Assign LOW to
  "new IP from same country, same ASN as previous" and HIGH to "new IP from a sanctioned country."
- **Enrichment link is mandatory.** The analyst's next step after seeing an alert is to check the
  IP in threat intel — provide the one-click path to the existing SentinelX enrichment page.

What creates noise that analysts ignore:

- Alerting on every RFC 1918 (private) IP login — these are normal jump-box patterns
- Alerting on logins from the same subnet as prior logins with no context
- Impossible travel from VPN/proxy IPs (no device fingerprinting available; accept as limitation,
  note it in the UI)
- Alerting on the first login of a user with no baseline (flag as "no baseline" not as "anomalous")

---

## Distro-Specific Notes for the Parser

| Distro / Scenario | Parser Concern | Mitigation |
|-------------------|---------------|------------|
| Ubuntu 24.04 | RFC3339 timestamp with microseconds and timezone | Detect by checking if first token matches `\d{4}-\d{2}-\d{2}T` |
| Ubuntu ≤ 23.10 / Debian / RHEL | BSD timestamp, no year, space-padded day | Parse with `strptime("%b %d %H:%M:%S")`; inject current year; handle Dec→Jan rollover |
| RHEL / Rocky / Alma | Log in `/var/log/secure` | Parser is path-agnostic (accepts uploaded bytes); document both paths in UI |
| systemd journal export | `journalctl -o syslog` exports BSD format; `journalctl -o json` is incompatible | Accept syslog-format output; document `journalctl -o syslog -u sshd` in UI help text |
| Logs with hostname variations | Some hosts log FQDN (`server.internal.corp`), some log short name | Hostname is field 2 — parse it but do not use it for anomaly detection (not reliable) |
| Mixed distro logs (forwarded syslog) | Multiple hosts' logs concatenated — different timestamps per section | Detect timestamp format per line, not per file |
| High-verbosity sshd (LogLevel DEBUG) | Extra `debug1:`, `debug2:` lines appear before/after auth lines | These do not start with `sshd[<pid>]: Accepted/Failed` — the standard filter skips them |
| `UseDNS yes` in sshd_config | Hostnames appear instead of IPs in log lines: `from server.example.com` | The IP field may be a hostname; use `socket.getaddrinfo()` to resolve, or skip GeoIP for hostnames |

---

## Sources

- [Elastic Blog: Grokking Linux Authorization Logs](https://www.elastic.co/blog/grokking-the-linux-authorization-logs)
  — Grok patterns for all sshd message variants, IPORHOST pattern (HIGH confidence)
- [OSSEC Log Samples: sshd](https://www.ossec.net/docs/log_samples/auth/sshd.html)
  — Comprehensive sshd message corpus including edge cases (HIGH confidence)
- [CrowdSec Issue #4199: Ubuntu 24.04 RFC3339 breakage](https://github.com/crowdsecurity/crowdsec/issues/4199)
  — Production evidence of the BSD → RFC3339 breaking change (HIGH confidence)
- [Elastic Security Rule: Successful SSH Auth from Unusual IP](https://detection.fyi/elastic/detection-rules/linux/initial_access_successful_ssh_authentication_by_unusual_ip/)
  — Production rule logic, risk score 21, 5-day lookback window, false-positive taxonomy (HIGH confidence)
- [WorkOS: Impossible Travel](https://workos.com/blog/impossible-travel)
  — Speed threshold rationale (≥900 km/h = commercial aviation), VPN false-positive patterns (MEDIUM confidence)
- [Huntress: Time Travelers Busted](https://www.huntress.com/blog/time-travelers-busted-how-to-detect-impossible-travel-)
  — Real-world impossible travel detection implementation notes (MEDIUM confidence)
- [Fingerprint.com: Impossible Travel Detection](https://fingerprint.com/blog/impossible-travel-detection/)
  — Device fingerprint suppression, layered context to reduce false positives (MEDIUM confidence)
- [rsyslog Syslog Parsing Documentation](https://www.rsyslog.com/doc/whitepapers/syslog_parsing.html)
  — RFC 3164 vs RFC 5424 timestamp differences, partial-match handling (HIGH confidence)
- [ipinfo.io API — IP Context Adapter](../app/enrichment/adapters/ip_api.py)
  — Actual adapter uses ipinfo.io (not ip-api.com); returns country, city, org/ASN, hostname; handles
  private IP 404s; supports IPv4 and IPv6 (HIGH confidence — source code)
- [LevelBlue: SSH Brute Force Authentication Attempt](https://levelblue.com/blogs/security-essentials/stories-from-the-soc-ssh-brute-force-authentication-attempt-tactic)
  — Real SOC triage workflow for SSH brute force, 8,114 attempts/minute observed in production (MEDIUM confidence)

---

*Feature research for: SentinelX v1.2 SSH Login Anomaly Detection*
*Researched: 2026-04-12*
