# Project Research Summary

**Project:** SentinelX v1.2 — SSH Login Anomaly Detection
**Domain:** SSH auth.log parsing and behavioral anomaly detection integrated into an existing Flask SOC triage tool
**Researched:** 2026-04-12
**Confidence:** HIGH

## Executive Summary

SentinelX v1.2 adds a second vertical to the existing Flask shell: upload an auth.log file, extract structured login events, apply four rule-based anomaly detectors, and surface prioritized alerts with GeoIP enrichment and one-click links to the existing SentinelX detail pages. The feature is architecturally additive — a new `app/ssh/` package running parallel to `app/enrichment/` with no changes to any existing enrichment code and only seven lines of modification to existing files across the entire codebase. The recommended approach uses zero new pip dependencies: all parsing, detection, and distance calculation use stdlib `re`, `datetime`, `math`, `collections`, and `ipaddress` already present in Python 3.10.

The most important integration decision is GeoIP provider alignment. PROJECT.md references ip-api.com but the existing adapter (`app/enrichment/adapters/ip_api.py`) actually calls ipinfo.io at `https://ipinfo.io/{ip}/json`. STACK.md, FEATURES.md, and ARCHITECTURE.md all confirm this; PITFALLS.md contained residual ip-api.com references from the project doc that do not reflect the live codebase. **ipinfo.io is the correct provider.** It is already in `ALLOWED_API_HOSTS`, already in the test suite, already returns `country` and `loc` (lat/lon) fields that the impossible travel detector needs. The SSH GeoIP module calls ipinfo.io directly through `http_safety.safe_request()` without routing through `IPApiAdapter`, avoiding a coupling mismatch between enrichment pipeline types and SSH-specific data shapes.

The key risks are: (1) auth.log timestamp format complexity — BSD syslog omits the year, single-digit days use leading spaces, and Ubuntu 24.04 switched to RFC3339, so the parser must detect format per-line and implement the standard year-rollover algorithm; (2) the existing `MAX_CONTENT_LENGTH` of 512 KB will reject real auth.log files — it must be raised to at least 5 MB; and (3) alert deduplication is table stakes — a brute-force log with 8,000 failed lines from one IP must produce one alert, not 8,000. Both timestamp handling and deduplication must be correct in Phase 1 before any anomaly detector is built.

## Key Findings

### Recommended Stack

Zero new pip dependencies. Every capability required for v1.2 exists in the Python 3.10 stdlib or existing requirements.txt. New code is five new Python modules (`app/ssh/models.py`, `parser.py`, `detector.py`, `geoip.py`, `routes/ssh.py`), two Jinja templates, and one TypeScript module. The existing `requests` library (via `http_safety.safe_request()`) handles ipinfo.io calls. The existing Flask blueprint pattern and `werkzeug.FileStorage` handle file upload.

**Core technologies:**
- `re` (stdlib): auth.log line parsing — 3-4 named-capture-group regexes cover all OpenSSH message variants; no log-parsing library needed
- `datetime` (stdlib): timestamp parsing for both BSD syslog (`strptime`) and ISO8601 (`fromisoformat`); year inference via the standard rollover algorithm
- `math` (stdlib): haversine distance formula for impossible travel (`math.sin`, `math.cos`, `math.atan2`)
- `collections.defaultdict` / `deque` (stdlib): per-user login history with `deque(maxlen=100)` to bound memory
- `ipaddress` (stdlib): RFC1918/loopback/reserved IP filtering before GeoIP lookup
- `requests` (existing, 2.32.5): ipinfo.io calls reusing `http_safety.safe_request()` SSRF guard
- Flask Blueprints (existing, 3.1.1): `Blueprint("ssh", __name__, url_prefix="/ssh")` — no name collision with existing `bp` or `bp_api`

**One configuration change required:** `MAX_CONTENT_LENGTH` raised from 512 KB to 5 MB in `app/config.py`. The 413 error handler already exists; update its text to mention both use cases.

**What NOT to add:** python-dateutil, GeoLite2/maxminddb, pytz, pandas, scikit-learn, ip-api.com (HTTPS unavailable on free tier, verified live), any ML library, any log-parsing library.

See `.planning/research/STACK.md` for full detail including verified regex patterns, dataclass definitions, and config.ini schema.

### Expected Features

The v1.2 feature set is a clean second entry point: upload auth.log → get structured anomaly alerts. The two workflows (IOC enrichment and SSH analysis) share the Flask shell and ipinfo.io adapter but operate independently with no shared routes, models, or state.

**Must have (table stakes for v1.2 MVP):**
- File upload endpoint (`POST /ssh/analyze`, `multipart/form-data`, CSRF required, `MAX_CONTENT_LENGTH` enforced)
- Auth log parser: BSD + RFC3339 timestamps, 8 OpenSSH message types, IPv4 + IPv6, parse error summary
- GeoIP per unique IP via ipinfo.io (skip private ranges; deduplicate before lookup)
- New IP alert (LOW severity — set membership check per user within this log)
- New country alert (MEDIUM severity — requires GeoIP to complete first)
- Brute-force detection: 10 failures/5-minute window from same IP (HIGH severity)
- Unusual hour login: outside 06:00–22:00 server local time (MEDIUM severity, configurable)
- Alert deduplication: one alert per (user, ip, rule_type) group — mandatory, not optional
- Alert table: severity, user, IP, country, reason text, link to `/ioc/ipv4/<ip>`
- Parse summary: lines parsed, events extracted, errors, time range
- JSON API response (`Accept: application/json` or `/api/ssh/analyze`)
- Per-alert `reason` field explaining exactly why the alert fired

**Should have (add if time allows in v1.2):**
- Impossible travel detection (HIGH/CRITICAL) — haversine + ipinfo.io `loc` field; 900 km/h threshold
- Attack pattern classification: did any brute-force IP later succeed? (MITRE T1110 signal)
- Per-user login summary header

**Defer to v1.3+:**
- ConfigStore UI for `normal_hours_start` / `normal_hours_end`
- Alert JSON export download
- DNSBL lookup for source IPs
- Other log types (nginx, Apache, syslog)
- Real-time log streaming

**Anti-features (do not implement):**
- ML/AI anomaly models — rule-based detection is the explicit design choice
- Persistent "known good" IP whitelist across sessions
- Composite risk scores per user — "never invent scores" principle
- Reverse DNS for every IP — use detail page instead
- Any automatic firewall rule emission — read-only tool

See `.planning/research/FEATURES.md` for full alert format specification, feature dependency DAG, and distro-specific parser notes.

### Architecture Approach

SSH detection is a second vertical inside the existing Flask shell. It shares UI chrome, security scaffolding, and GeoIP infrastructure but does not touch the IOC enrichment pipeline at all. The design principle is: new files are additive; existing files receive only surgical additions (7 lines across 3 files). This preserves the existing 757 unit + 91 E2E test suite without modification.

The detector is architected to be network-free: the route handler builds a `geo_map: dict[str, str | None]` by calling `geoip.lookup_country()` for each unique IP, then passes this dict to `detector.detect()`. The detector never makes HTTP calls. This means Phase 3 (detector) can be fully built and tested before Phase 2 (GeoIP) is complete.

**Major components:**
1. `app/ssh/models.py` — Frozen dataclasses: `LoginEvent`, `AnomalyAlert`; consistent with project-wide immutability pattern
2. `app/ssh/parser.py` — Regex-based: auth.log bytes → `list[LoginEvent]`; handles BSD + RFC3339 formats; implements year-rollover algorithm; returns parse error summary
3. `app/ssh/geoip.py` — Standalone `lookup_country(ip, allowed_hosts) -> GeoLocation | None`; imports only `http_safety` constants; zero enrichment pipeline coupling
4. `app/ssh/detector.py` — Pure function `detect(events, geo_map, config) -> list[AnomalyAlert]`; builds per-user history in one in-memory pass; applies 4 rules; deduplicates
5. `app/routes/ssh.py` — Flask Blueprint `"ssh"` at `/ssh/`; orchestrates modules 2-4; renders templates; applies rate limits
6. `templates/ssh/upload.html` + `results.html` — Extend `base.html`; CSRF token included on upload form
7. `app/static/src/ts/modules/ssh.ts` — File validation + alert table interactions; `createElement + textContent` only (SEC-08); no enrichment machinery

**Existing files modified (additions only):**

| File | Change |
|------|--------|
| `app/__init__.py` | +2 lines: import + register `bp_ssh` |
| `app/templates/base.html` | +3 lines: SSH nav link |
| `app/static/src/ts/main.ts` | +2 lines: import + `initSsh()` |

See `.planning/research/ARCHITECTURE.md` for full data flow diagram, build order DAG, security posture table, and exact code sketches for each module.

### Critical Pitfalls

1. **Year rollover bug in BSD syslog parsing** — BSD format omits the year; naive "assume current year" assigns 2026 to December logs analyzed in January, breaking chronological ordering and triggering false impossible-travel alerts. Prevention: implement `_infer_year()` using the Logstash algorithm (if inferred date is >24h in the future, use `year - 1`); inject a fixed `now` at parse time. Write a Dec 29 – Jan 03 fixture before anything else.

2. **ipinfo.io vs ip-api.com confusion** — PITFALLS.md contains residual ip-api.com references from PROJECT.md. The live adapter calls ipinfo.io. ip-api.com's free tier is HTTP-only (HTTPS returns 403, verified live). Use ipinfo.io; no allowlist changes needed; do not build an ip-api.com batch adapter.

3. **auth.log format silently drops valid events** — Naive parsers miss `Accepted publickey`, `Failed password for invalid user <name>` (username position shifts), single-digit day padding (`Jan  5`), and IPv6 addresses. Use named capture groups; write an 8-variant fixture before shipping.

4. **`MAX_CONTENT_LENGTH` 512 KB rejects all real auth.log files** — A 30-day server log reaches 2-10 MB. Flask rejects uploads before the route handler runs; the existing 413 message says "paste size" which confuses analysts. Raise to 5 MB and update the error message in Phase 1.

5. **Alert deduplication is mandatory** — A brute-force log with 8,114 failed lines from one IP must produce one alert. Implement `(username, source_ip, rule_type)` deduplication as part of the detector contract, not a post-processing step.

6. **XSS from attacker-controlled usernames** — SSH scanners inject `<script>` tags as attempted usernames. These appear verbatim in auth.log. `createElement + textContent` only in `ssh.ts`; verify Jinja autoescape is active; never pass log-derived content through `innerHTML`.

7. **Impossible travel timezone complexity** — BSD syslog timestamps are server local time with no timezone. Mixing them with GeoIP UTC offsets is unreliable for v1.2. Use server-local elapsed time for speed calculation; document the limitation with a UI note; defer true timezone correction.

See `.planning/research/PITFALLS.md` for all 16 pitfalls with phase mappings, code-level prevention strategies, and a security mistakes table.

## Implications for Roadmap

The dependency graph is a strict DAG. Parser correctness is the foundation for all detection; GeoIP must exist before country-based rules; detector must exist before routes can orchestrate it. The suggested phase structure maps directly to this DAG.

### Phase 1: Models, Parser, and Foundation Contracts

**Rationale:** Parser correctness is the precondition for all anomaly detection. Year-rollover correctness and format-variant coverage must be verified before any detection logic is written. Configuration changes (MAX_CONTENT_LENGTH, blueprint registration, CSRF) block all subsequent phases if deferred.

**Delivers:** `app/ssh/__init__.py`, `app/ssh/models.py` (frozen dataclasses), `app/ssh/parser.py` (BSD + RFC3339, all 8 message types, year rollover, parse error summary), `tests/unit/test_ssh_parser.py` (Dec-Jan rollover fixture + all message variants), `app/config.py` MAX_CONTENT_LENGTH raised to 5 MB, Blueprint "ssh" registered at `/ssh/`.

**Addresses:** File upload foundation, structured event extraction, parse summary
**Avoids:** Pitfalls 1 (year rollover), 3 (silent line drops), 4 (MAX_CONTENT_LENGTH), 7 (blueprint collision)
**Research flag:** None — standard stdlib patterns. Skip `/gsd:research-phase`.

---

### Phase 2: GeoIP Wrapper

**Rationale:** GeoIP must exist before new-country detection or impossible travel can be implemented. Small scope (one module, one test file) but blocks country-based rules in Phase 3.

**Delivers:** `app/ssh/geoip.py` (`lookup_country(ip) -> GeoLocation | None` via ipinfo.io using `http_safety` constants), IP deduplication, private IP short-circuit, `tests/unit/test_ssh_geoip.py` (mocked `requests.get`).

**Uses:** Existing `http_safety.validate_endpoint`, `TIMEOUT`, `MAX_RESPONSE_BYTES` — no new imports
**Addresses:** GeoIP per unique IP, private IP filtering
**Avoids:** Pitfall 2 (ipinfo.io confirmed; no allowlist changes needed), Pitfall 9 (private IPs)
**Research flag:** None — ipinfo.io integration verified against live codebase. Skip `/gsd:research-phase`.

---

### Phase 3: Anomaly Detector

**Rationale:** The detector is a pure function — no network, no Flask context. It can be fully tested with no mocking. Building it before routes isolates all rule logic to one testable unit.

**Delivers:** `app/ssh/detector.py` with all four rules (new_ip, new_country, unusual_hours, impossible_travel), alert deduplication by `(username, source_ip, rule_type)`, `deque(maxlen=100)` per-user history, haversine distance for impossible travel, configurable normal-hours window, `tests/unit/test_ssh_detector.py` (all rules, deduplication, edge cases, no network).

**Implements:** Per-user in-memory history, rule-based detection, deduplication
**Addresses:** All four anomaly rules, impossible travel (if time allows), alert deduplication
**Avoids:** Pitfall 5 (bounded deque history), Pitfall 4 (naive datetime — document timezone limitation), Pitfall 14 (country-level only, no intra-country haversine flagging)
**Research flag:** None — rule logic is fully specified. Skip `/gsd:research-phase`.

---

### Phase 4: Routes and Templates

**Rationale:** Routes orchestrate the three prior modules. All data shapes are now concrete. This phase carries the highest integration risk (file upload, new routes, template rendering) and is done after all underlying logic is verified.

**Delivers:** `app/routes/ssh.py` (upload form GET, analyze POST, rate-limited), `templates/ssh/upload.html` (CSRF token, file size guidance, distro path hints), `templates/ssh/results.html` (alert table with severity/user/IP/country/reason/enrichment link), `app/__init__.py` (+2 lines), `app/templates/base.html` (+3 lines nav link), `tests/unit/test_ssh_routes.py`, integration upload + analyze flow tests.

**Addresses:** Full MVP feature set, JSON API response, parse failure summary display, enrichment link to `/ioc/ipv4/<ip>`
**Avoids:** Pitfall 6 (XSS — Jinja autoescape + textContent), Pitfall 11 (CSRF on upload form), Pitfall 12 (in-memory processing, no disk write), Pitfall 13 (base.html name verification before extending)
**Research flag:** None — Flask blueprint pattern well-established in this codebase. Skip `/gsd:research-phase`.

---

### Phase 5: TypeScript Module

**Rationale:** TypeScript enhances the server-rendered templates but is not required for functional correctness. Building it last means DOM structure is stable and the module can be written against real markup.

**Delivers:** `app/static/src/ts/modules/ssh.ts` (file input validation, client-side size warning, alert table copy-to-clipboard, severity filter toggle), registered in `main.ts` (+2 lines), `make js-dev` build verified.

**Addresses:** Alert table UX, copy-to-clipboard (follows existing `clipboard.ts` pattern)
**Avoids:** Pitfall 6 (SEC-08 textContent-only enforced), Pitfall 13 (SSH page guard: `if (!document.querySelector('.page-ssh')) return`)
**Research flag:** None — follows established module init patterns. Skip `/gsd:research-phase`.

---

### Phase Ordering Rationale

- Phase 1 must be first: parser correctness and configuration preconditions (MAX_CONTENT_LENGTH, blueprint) block all subsequent phases.
- Phase 2 before Phases 3-4: GeoIP output shape must be concrete before the detector's `geo_map` parameter is finalized. Phase 3 can begin in parallel using mock geo_map dicts.
- Phase 3 before Phase 4: route handler must know what `detect()` returns before it can render templates.
- Phase 4 before Phase 5: TypeScript module targets real DOM markup; markup must be stable first.
- The Parser → GeoIP → Detector → Routes → TypeScript order is also the natural order for incremental integration testing.

### Research Flags

Phases needing deeper research during planning:
- **None.** All four research areas returned HIGH-confidence findings based on direct codebase inspection and verified API probes.

Phases with standard patterns (skip `/gsd:research-phase`):
- **All five phases** follow well-documented patterns: stdlib regex parsing, ipinfo.io HTTP wrapper, rule-based detection with in-memory state, Flask Blueprint registration, TypeScript module init.

One implementation-time verification (not a blocker):
- **Impossible travel `loc` field availability:** STACK.md confirms ipinfo.io returns `loc` as `"lat,lon"`. A quick integration test in Phase 2 will validate this concretely before Phase 3 commits to the haversine implementation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against running Python 3.10.12, live API probes (ip-api.com HTTPS 403 confirmed), direct source inspection of requirements.txt, config.py, ip_api.py, http_safety.py |
| Features | HIGH | auth.log format variants from official OpenSSH docs + production incident evidence (CrowdSec #4199); anomaly rules from production Elastic SIEM rules and real SOC triage workflows |
| Architecture | HIGH | Based entirely on direct codebase inspection of all affected files; 7-line modification footprint on existing files is mechanically verifiable |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls are verified structural facts. PITFALLS.md Pitfall 2 (ip-api.com batch) describes a scenario that does not apply — correct provider is ipinfo.io. Impossible travel timezone mitigation is a pragmatic judgment call, not a verified best practice. |

**Overall confidence:** HIGH

### Gaps to Address

- **PITFALLS.md ip-api.com references:** PITFALLS.md describes ip-api.com as the SSH GeoIP provider (Pitfall 2, integration risk table) with batch rate limit analysis and SSRF allowlist requirements. This is incorrect — the live adapter and all other research confirm ipinfo.io. During planning, treat all ip-api.com references in PITFALLS.md as documentation artifacts from an incorrect assumption in PROJECT.md; use STACK.md and ARCHITECTURE.md as authoritative on GeoIP provider.

- **Impossible travel scope decision:** Haversine + ipinfo.io `loc` field is well-specified but adds complexity to Phase 3. Research recommends implementing it as "add if time allows" rather than blocking the MVP. Confirm this scope decision during roadmap creation.

- **`enrichment.ts` init guard:** PITFALLS.md notes that `enrichment.ts:init()` may run on SSH pages and log errors. During Phase 5, verify whether a page-presence guard already exists or needs to be added (1-line fix, must not be forgotten).

## Sources

### Primary (HIGH confidence)
- SentinelX codebase direct inspection: `app/enrichment/adapters/ip_api.py` (confirmed ipinfo.io), `app/enrichment/http_safety.py`, `app/config.py`, `app/__init__.py`, `app/routes/__init__.py`, `app/routes/api.py`, `requirements.txt`
- Live API probe: `https://ip-api.com/json/8.8.8.8` returns HTTP 403 — confirms HTTPS unavailable on free tier
- Python 3.10.12 stdlib verification: all required modules confirmed available
- OpenSSH regex: all 4 message variants tested against sample lines in running Python interpreter
- [CrowdSec Issue #4199](https://github.com/crowdsecurity/crowdsec/issues/4199) — Ubuntu 24.04 RFC3339 timestamp breaking change, production evidence
- [Elastic: Grokking Linux Authorization Logs](https://www.elastic.co/blog/grokking-the-linux-authorization-logs) — Grok patterns for all sshd message variants
- [OSSEC Log Samples: sshd](https://www.ossec.net/docs/log_samples/auth/sshd.html) — comprehensive sshd message corpus

### Secondary (MEDIUM confidence)
- [WorkOS: Impossible Travel](https://workos.com/blog/impossible-travel) — speed threshold rationale (900 km/h), VPN false positive patterns
- [Elastic Security Detection Rule: SSH Authentication by Unusual IP](https://detection.fyi/elastic/detection-rules/linux/initial_access_successful_ssh_authentication_by_unusual_ip/) — production rule logic and false positive taxonomy
- [LevelBlue: SSH Brute Force SOC workflow](https://levelblue.com/blogs/security-essentials/stories-from-the-soc-ssh-brute-force-authentication-attempt-tactic) — 8,114 attempts in production; SOC triage workflow
- [Grafana Loki issue #692](https://github.com/grafana/loki/issues/692) — yearless syslog timestamp year=0 failure
- [Logstash date filter issue #46](https://github.com/logstash-plugins/logstash-filter-date/issues/46) — New Year rollover algorithm

---
*Research completed: 2026-04-12*
*Ready for roadmap: yes*
