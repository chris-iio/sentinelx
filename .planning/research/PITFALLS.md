# Pitfalls: SSH Login Anomaly Detection — SentinelX v1.2

**Domain:** Adding SSH auth.log parsing + behavioral anomaly detection to existing Flask security tool
**Researched:** 2026-04-12
**Confidence:** HIGH — based on direct codebase inspection (config.py, __init__.py, ip_api.py,
http_safety.py, routes/) combined with verified external sources.

---

## Context: What This Research Covers

SentinelX v1.2 adds SSH auth.log parsing, per-user behavioral anomaly detection, and GeoIP enrichment
(ip-api.com via batch API) to a working Flask 3.1 app. The pitfalls below are calibrated for:

- Parsing BSD syslog format (auth.log) in Python
- Rule-based anomaly detection: new IP, new country, impossible travel, unusual hours
- Reusing ip-api.com via a NEW batch endpoint (existing enrichment adapter calls the single-IP endpoint)
- Adding a Flask blueprint to an app already registering two blueprints (`bp`, `bp_api`)
- Security model: all input untrusted, textContent-only DOM (SEC-08), CSRF on all POST, 512 KB MAX_CONTENT_LENGTH

The existing ALLOWED_API_HOSTS allowlist in config.py does NOT include `ip-api.com` — only `ipinfo.io`
is listed. This is a required integration change.

---

## Critical Pitfalls

### Pitfall 1: Year Inference Bug Around December–January Rollover

**What goes wrong:**
BSD syslog format (auth.log on Ubuntu/Debian) omits the year from every timestamp:
```
Jan  5 03:22:11 hostname sshd[1234]: Accepted publickey for alice from 1.2.3.4 port 54321 ssh2
```
The naive fix — "assume current year" — produces wrong timestamps for logs that span a year boundary.
A log file captured 2025-12-28 through 2026-01-03, processed on 2026-01-10, will infer 2026 for the
December entries. Those December logins appear to be in the future relative to January logins, which
breaks chronological ordering and makes every December session appear to have traveled to the past.

The Grafana Loki team hit this identically: yearless syslog timestamps result in year=0 failures or
year=currentYear assignments that are provably wrong across rollovers. Logstash's canonical algorithm
is: assume current year; if parsed date is in the future (e.g., Dec 31 parsed in January), decrement
year by one.

**Why it happens:**
Developers test with a single log from the current month and never encounter a rollover. The code
ships correct for 11 months and silently breaks in January.

**Consequences:**
- Impossible travel alerts fire for sessions that are actually months apart
- "New IP" baseline lookups compare wrong historical windows
- Login timestamps rendered in the UI show the wrong year

**Prevention:**
Implement the standard rollover algorithm in the parser's `_infer_year()` helper:
```python
def _infer_year(parsed_date: datetime.date, now: datetime.date) -> int:
    candidate = parsed_date.replace(year=now.year)
    if candidate > now + datetime.timedelta(days=1):
        return now.year - 1
    return now.year
```
Process the log file in a single pass with a fixed `now` timestamp (inject at parse time, not
call time) so the year inference is consistent across the entire file.

**Detection:**
Write a unit test with a fixture spanning Dec 29 – Jan 03. Assert December events get last year,
January events get current year, and December comes before January in sorted order.

**Phase:** Parser module (Phase 1). Year inference must be correct before anomaly detection can work.

---

### Pitfall 2: ip-api.com Rate Limit — Batch Endpoint is 15 req/min, Not 45

**What goes wrong:**
The existing SentinelX ip-api.com adapter (`ip_api.py`) calls the single-IP ipinfo.io endpoint, not
ip-api.com. For SSH log analysis, ip-api.com's batch endpoint is the natural choice (batch up to 100
IPs per call). However: the batch endpoint is capped at **15 HTTP requests per minute** (not 45
like the single endpoint), and each batch may contain up to 100 IPs.

A large auth.log with 200 unique attacker IPs requires at least 2 batch calls. At 15 req/min that is
fine. But with 1500 unique IPs (a brute-force log), 15 batches * 60 seconds = 4 minutes of throttled
enrichment. Worse: exceeding the rate limit bans the IP for up to one hour.

**Additional constraint:** ip-api.com is NOT in the current ALLOWED_API_HOSTS allowlist in config.py.
The allowlist contains `ipinfo.io` but not `ip-api.com`. SSRF validation (SEC-16 in http_safety.py)
will reject all calls to ip-api.com with a ValueError until the allowlist is updated.

**Why it happens:**
Developers see "ip-api.com is already integrated" in PROJECT.md and assume the adapter is ready to
use for batch GeoIP. In fact, the existing adapter calls ipinfo.io (different host, different API,
no batch endpoint). The ip-api.com batch endpoint requires a new adapter and an allowlist addition.

**Consequences:**
- HTTP 429 errors with potential 1-hour IP ban if rate limit is exceeded
- ValueError from SSRF validation if `ip-api.com` is not added to ALLOWED_API_HOSTS
- Silent failures: if the code ignores EnrichmentError returns, all 1500 IPs show no country data

**Prevention:**
1. Add `ip-api.com` to `ALLOWED_API_HOSTS` in config.py (Phase 1, not an afterthought)
2. Use the batch endpoint (`POST http://ip-api.com/batch`) with up to 100 IPs per request
3. Deduplicate IPs before batching — a log with 5000 entries may have only 50 unique source IPs
4. Implement a rate-limit-aware sleep: check the `X-Rl` response header (remaining requests) and
   the `X-Ttl` header (seconds until reset) and sleep if `X-Rl == 0`
5. Return `no_data` (not an error) for private/reserved IPs — ip-api.com returns `{"status":"fail",
   "message":"private range"}` for RFC1918 addresses; treat this as expected, not a failure

**Detection:**
Unit test with a mock that returns HTTP 429 on the second batch call; assert the code backs off and
does not raise, and does not ban by retrying immediately.

**Phase:** Phase 1 (SSRF allowlist) + Phase 2 (batch adapter with rate handling).

---

### Pitfall 3: auth.log Format Variation Silently Drops Lines

**What goes wrong:**
auth.log contains many sshd message types. A naive "only parse Accepted/Failed password" regex will
silently drop valid successful logins using public key authentication and miss important context lines:

```
# Successful password auth:
Jan  5 03:22:11 sshd[1234]: Accepted password for alice from 1.2.3.4 port 54321 ssh2

# Successful pubkey auth (different keyword):
Jan  5 03:22:11 sshd[1234]: Accepted publickey for alice from 1.2.3.4 port 54321 ssh2: RSA SHA256:abc123

# PAM session open (same login, different line):
Jan  5 03:22:11 sshd[1234]: pam_unix(sshd:session): session opened for user alice by (uid=0)

# Failed with "invalid user" (username position shifts):
Jan  5 03:22:11 sshd[1234]: Failed password for invalid user hacker from 5.5.5.5 port 12345 ssh2

# Single-digit day (two spaces before day):
Jan  5 03:22:11 ...  (note: two spaces between "Jan" and "5")
Jan 15 03:22:11 ...  (note: one space between "Jan" and "15")
```

The "invalid user" variant has a different structure: `Failed password for invalid user {name} from
{ip}` vs `Failed password for {name} from {ip}`. Parsing with `split(" ")` at a fixed position
extracts the wrong field for invalid-user lines.

IPv6 source addresses further complicate regex-based IP extraction: `from 2001:db8::1 port` needs a
different pattern than `from 1.2.3.4 port`.

**Why it happens:**
Developers write the parser against a small sample log, which may not include all variants. The
parser appears to work on test data but silently skips real production entries.

**Consequences:**
- Successful publickey logins not counted in per-user history → "new login" false positives for
  users who exclusively use publickey auth and whose logins were never seen before
- "Invalid user" failed attempts counted against the wrong username (or skipped entirely)
- Baseline history is incomplete, making anomaly thresholds unreliable

**Prevention:**
Use named capture groups in regex, not positional splitting. Handle both auth methods:
```python
ACCEPTED_RE = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\S+)\s+\S+\s+"
    r"sshd\[\d+\]:\s+Accepted\s+(?:password|publickey)\s+for\s+(?P<user>\S+)"
    r"\s+from\s+(?P<ip>\S+)\s+port\s+\d+"
)
```
Write a fixture covering all known variants (password, publickey, invalid user, IPv6, single-digit
day). Assert parsed count matches expected count.

**Phase:** Phase 1 (parser). Correctness before anomaly logic.

---

### Pitfall 4: Impossible Travel Uses Naive Datetimes, Producing Wrong Speed Calculations

**What goes wrong:**
auth.log timestamps have no timezone information — they record local server time. ip-api.com returns
UTC offset for the IP's geolocation. If the parser creates `datetime.datetime` objects without a
timezone (naive datetimes), and the impossible travel detector subtracts them directly, the elapsed
time calculation is correct only if both logins are from the same timezone offset. For a user who
logs in from London (UTC+1) and then from New York (UTC-5), the raw timestamp difference is
calculated in server-local time with no adjustment for the fact that one IP resolves to a location
6 hours offset from the other.

This is not just a false positive risk — it is a false negative risk: the travel speed between two
logins that look 2 hours apart (server time) may actually be geographically impossible when the
correct UTC-adjusted timestamps are used.

**Why it happens:**
`datetime.datetime.strptime("Jan 5 03:22:11", "%b %d %H:%M:%S")` creates a naive datetime. All
arithmetic on naive datetimes assumes a single implicit timezone.

**Consequences:**
- Impossible travel alerts fire on impossible schedules (false positives)
- Real impossible travel is missed because the time delta looks plausible when it isn't (false negatives)
- Timezone-aware comparisons between server-local and GeoIP UTC offset are complex to get right

**Prevention:**
For v1.2 rule-based detection, the pragmatic safe approach is to treat all timestamps as being in
the server's local timezone and document this limitation clearly. Do NOT mix timezone-naive server
timestamps with timezone-offset data from GeoIP to compute "adjusted elapsed time" — the complexity
exceeds the signal quality for this use case. Instead:

1. Parse auth.log timestamps as naive datetimes representing server local time
2. Use only elapsed time (in seconds) between consecutive events for speed calculation
3. Accept that the speed threshold must be conservative (>= 900 km/h implied is flagged) and that
   VPN/proxy false positives are expected and documented for the analyst
4. Add a UI note on any impossible travel alert: "Timestamps are in server local time. VPN and
   proxy use may cause false positives."

If timezone correction is added later, use `datetime.timezone.utc` consistently for all stored events.

**Phase:** Phase 2 (anomaly detector). Document the limitation in code comments at the datetime
parsing site.

---

### Pitfall 5: Unbounded Per-User Login History Grows Without Limit

**What goes wrong:**
The anomaly detector must track per-user login history to evaluate "is this a new IP for this user?"
and "what was the last login location?". The straightforward implementation stores a list per user
in a dict:

```python
history: dict[str, list[LoginEvent]] = {}
```

A large auth.log containing 2 years of data and 500 users with 10,000 logins each will consume
significant memory. More practically, brute-force attack logs may contain millions of failed attempts
for "root" and "admin" under a single key. If failed attempts are stored in the history dict, the
"root" key alone can grow to hundreds of thousands of entries.

**Why it happens:**
The developer stores everything because "we might need it for analysis." The per-user history is
never bounded.

**Consequences:**
- Memory consumption proportional to log file size (could be gigabytes for old logs)
- For anomaly detection, the full history is not needed: only the N most recent confirmed logins per
  user matter for "new IP" and "last location" checks

**Prevention:**
1. Use `collections.deque(maxlen=N)` per user for confirmed successful logins, where N = 50 or 100.
   The deque automatically discards the oldest entry when full.
2. Do NOT store failed login attempts in per-user history — they are irrelevant to behavioral
   baselines and constitute the bulk of brute-force log volume
3. Deduplicate IP lookups before GeoIP enrichment: a log with 50,000 entries from the same 3 IPs
   requires only 3 GeoIP calls, not 50,000

```python
from collections import defaultdict, deque
MAX_HISTORY = 100
user_history: dict[str, deque[LoginEvent]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
```

**Phase:** Phase 1 (data model) and Phase 2 (anomaly detector implementation).

---

### Pitfall 6: File Upload XSS via Log Content Displayed Without textContent Enforcement

**What goes wrong:**
Auth.log lines contain attacker-controlled content: usernames attempted by SSH scanners. A line like:
```
Failed password for invalid user <script>alert(1)</script> from 1.2.3.4 port 22 ssh2
```
is a real-world injection attempt that SSH scanners use. If the parsed username is rendered in the
browser via `innerHTML`, template string interpolation, or Jinja without autoescaping, it executes
as JavaScript.

The project has a strict DOM safety requirement (SEC-08): all dynamic content via
`createElement + textContent`, never `innerHTML`. The existing enrichment UI follows this correctly.
The SSH results UI, being new code, is at risk of introducing innerHTML shortcuts during development.

Jinja2 autoescape protects server-rendered templates by default for `.html` files, but:
1. Any dynamic DOM construction in TypeScript for the SSH results page must use textContent, not innerHTML
2. Alert detail content (username strings, raw log lines) passed from Python to JSON API and
   rendered client-side bypasses Jinja autoescaping entirely
3. If alert data is written to a TypeScript object literal in a `<script>` block in a Jinja template,
   the escaping must use `tojson` filter, not raw variable interpolation

**Consequences:**
- Stored XSS: if the analyst uploads a crafted log, the injected script executes in their browser
- For a localhost-only tool, the impact is limited — but still violates the security model and
  could steal session cookies or CSRF tokens

**Prevention:**
1. Any TypeScript module rendering SSH alert data must use `createElement + textContent` exclusively
2. If Flask serves alert data as JSON (via the `/api/ssh/` endpoints), the TypeScript must use
   textContent when populating table cells, not innerHTML template strings
3. If Jinja templates render alert data (username, raw log line), verify autoescape is active —
   it is on by default for `.html` files but can be accidentally disabled
4. Add a grep guard to CI: `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` must
   return zero results (this guard already exists in project checklist)

**Phase:** Phase 2 (TypeScript SSH UI module). Enforce during code review before first E2E test run.

---

### Pitfall 7: Flask Blueprint Name or Route Collision With Existing Blueprints

**What goes wrong:**
The app already registers two blueprints: `bp` (main routes) and `bp_api` (JSON API routes).
Flask raises `AssertionError: "A name collision occurred between blueprints..."` if the new SSH
blueprint uses the same name as an existing one. More subtly, Flask does NOT report route collisions
between blueprints — the same URL path can be registered twice without warning, and the first
registered blueprint wins silently.

The existing route structure includes:
- `GET /` — main IOC input form
- `POST /analyze` — IOC enrichment
- `GET /ioc/<type>/<path:value>` — IOC detail page
- `GET/POST /settings` — provider API key management
- `GET /api/history` — enrichment history JSON

A new `/upload` route for SSH log upload could collide with a future route. More likely: if the SSH
blueprint is named `"main"` or `"api"` (same as existing), Flask raises at startup.

**Why it happens:**
Blueprint names are set as the first argument to `Blueprint(name, ...)`. Developers often copy an
existing blueprint definition and forget to change the name string.

**Consequences:**
- AssertionError at startup (caught immediately — not silent)
- Silent route shadowing if two blueprints define the same URL path — the SSH route may silently
  override an existing route or never be reachable

**Prevention:**
1. Name the SSH blueprint explicitly: `Blueprint("ssh", __name__, url_prefix="/ssh")`
2. Use a `/ssh/` URL prefix for all SSH routes to guarantee no path collisions:
   - `POST /ssh/upload` — log file upload
   - `GET /ssh/results/<session_id>` — display results
   - `GET /api/ssh/alerts` — JSON API
3. After registering, run `flask routes` to verify all expected routes appear with correct endpoints

**Phase:** Phase 1 (blueprint registration). Verify at startup before writing any route logic.

---

### Pitfall 8: MAX_CONTENT_LENGTH Rejects Auth.log Files Larger Than 512 KB

**What goes wrong:**
The existing `MAX_CONTENT_LENGTH` is hardcoded to 512 KB in config.py (SEC-12). A real-world
auth.log from a production server under brute-force attack can easily be 5–50 MB. Flask silently
rejects uploads exceeding MAX_CONTENT_LENGTH with HTTP 413. The existing 413 error handler returns
a plain-text error message: "Input too large. Maximum paste size is 512 KB."

For SSH log upload, 512 KB is too restrictive. An auth.log covering 30 days of moderate SSH activity
on a cloud instance typically reaches 2–10 MB. An analyst uploading a log to investigate suspicious
activity will hit this limit without understanding why.

**Why it happens:**
The 512 KB limit was designed for the IOC text paste input (pasting threat intel reports). Auth.log
files are fundamentally different — they are structured binary-ish text files that need to be
substantially larger to be useful.

**Consequences:**
- Analysts cannot upload real auth.log files
- HTTP 413 response with a message saying "paste size" which is confusing for a file upload

**Prevention:**
1. Raise MAX_CONTENT_LENGTH to at least 10 MB for the upload endpoint, or handle it per-route
2. Add a dedicated 413 handler or route-level check with a message specific to log file upload:
   "Log file too large. Maximum size is 10 MB. Consider trimming to recent entries."
3. Independently validate file size in the upload route handler (not just relying on Flask's global
   limit) to provide a cleaner error message
4. Add a hard upper bound on lines processed (e.g., 500,000 lines) to prevent memory issues from
   enormous files regardless of file size

**Phase:** Phase 1 (config + route setup). The 413 handler must be updated before upload testing.

---

## Moderate Pitfalls

### Pitfall 9: Private and Reserved IPs Sent to ip-api.com Cause Noise

**What goes wrong:**
Auth.log from a server with local network access may contain logins from RFC1918 addresses
(10.x.x.x, 192.168.x.x, 172.16-31.x.x), localhost (127.0.0.1), and IPv6 link-local addresses
(fe80::). Sending these to ip-api.com returns `{"status":"fail","message":"private range"}`, which
is not an error but must be handled as "no GeoIP data available."

If private IPs are passed to the impossible travel detector without a country code, and the detector
compares `None` country to a previous country, it may raise TypeError or produce a spurious "new
country" alert.

**Prevention:**
Filter private IP ranges before batching for GeoIP:
```python
import ipaddress
def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local)
    except ValueError:
        return False
```
Logins from private IPs: include in behavioral history (they happened) but skip GeoIP enrichment
and skip all geo-based anomaly checks (country, impossible travel). Only flag for "unusual hours."

**Phase:** Phase 2 (anomaly detector + GeoIP enrichment).

---

### Pitfall 10: False Positives From VPN, Cloud Shell, and SSH Tunnels

**What goes wrong:**
The "new country" and "impossible travel" detectors have inherent false positive sources that are
architectural, not bugs:

1. **VPN users:** A user in Berlin connecting through a VPN exit node in Singapore will show
   a Singapore source IP. Their next login without VPN shows Berlin. Detection sees Berlin→Singapore
   or Singapore→Berlin as a new country every time.

2. **Cloud shell / web-based SSH:** Google Cloud Shell, AWS CloudShell, and similar services
   originate from data center IPs that geolocate to US East/West coast even when the analyst is
   in Europe. These create persistent "new country" alerts for analysts using cloud shell regularly.

3. **SSH tunnels:** A user may forward ports through a bastion host, making all their logins
   appear from the bastion's IP rather than their actual location.

4. **IPv6 Privacy Addresses:** Modern Linux/macOS clients use IPv6 Privacy Extensions (RFC 4941)
   which rotate the interface ID every 24 hours. Each rotation produces a new IP, triggering
   "new IP" alerts even for logins from the same physical machine on the same network.

**Prevention:**
Design alerts as informational, not blocking. The UI must clearly label these as "requires analyst
judgment" rather than "confirmed threat." Include the alert reason in the output ("New country:
Singapore (previously: Germany)") so the analyst can immediately evaluate whether VPN explains it.

Add a configurable IP allowlist to suppress false positives: if `known_good_ips` is defined in
config, suppress "new IP" alerts for those IPs. Do not suppress "unusual hours" for known IPs —
that signal is independent of location.

**Phase:** Phase 3 (UI + alert presentation). Frame alerts correctly from the start.

---

### Pitfall 11: CSRF Token Missing on File Upload POST

**What goes wrong:**
All POST endpoints in SentinelX require a CSRF token (`WTF_CSRF_ENABLED = True`). The existing
`/analyze` form includes the CSRF token via `{{ form.hidden_tag() }}` or the meta tag approach.
A new SSH upload form that forgets to include the CSRF token will return HTTP 400 on POST with
no useful error message for the analyst. The 400 is from Flask-WTF's CSRF protection, not from
form validation — it can look like a server error.

The API blueprint (`bp_api`) is CSRF-exempt (`csrf.exempt(bp_api)`). The SSH blueprint must NOT
be CSRF-exempt since it processes file uploads from the browser.

**Prevention:**
Include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` in the upload form,
or use `{{ form.hidden_tag() }}` if using Flask-WTF form class. Test the upload endpoint with
CSRF disabled in the test config (`WTF_CSRF_ENABLED: False`) and verify CSRF is enforced in
integration tests with CSRF enabled.

**Phase:** Phase 1 (form template). Verify before first manual upload test.

---

### Pitfall 12: werkzeug.secure_filename Strips All Non-ASCII Characters

**What goes wrong:**
`werkzeug.secure_filename("auth.log")` returns `"auth.log"` — fine. But:
- `secure_filename("../../etc/passwd")` returns `"etc_passwd"` — path traversal prevented
- `secure_filename("")` returns `""` — an empty string, which then causes a downstream error
- `secure_filename("日本語.log")` returns `".log"` — all non-ASCII stripped, leaving just extension

For a localhost tool where the uploaded file is processed in-memory (never saved to disk), the
filename is only needed for display and for basic validation. Using it as a filename hint for
`open()` is unnecessary.

**Prevention:**
Process uploaded auth.log files entirely in-memory using `file.read()` (with size check first).
Do not write to disk. Use `secure_filename` only for display in the UI. Validate the content
type is `text/plain` or has a `.log` extension before reading. Never `open(secure_filename(...))`.

If a temp file is genuinely needed (e.g., for very large files), use `tempfile.NamedTemporaryFile`
with an explicit directory under `/tmp`, not user-provided filename.

**Phase:** Phase 1 (upload route). Decision: in-memory processing vs disk.

---

### Pitfall 13: Jinja Template Inheritance Breaks if SSH Templates Use Wrong Base

**What goes wrong:**
SentinelX uses a base template (`base.html` or `layout.html`) that includes the navigation, CSS,
and JavaScript bundle. If SSH result templates use `{% extends "base.html" %}` but the actual base
template has a different name, the template fails with `TemplateNotFound`. More subtly: if the SSH
templates include the `enrichment.ts`-driven JavaScript bundle but do not define the data attributes
that `enrichment.ts:init()` expects (like `data-job-id` on `.page-results`), the JavaScript will
log errors in the console or silently fail to initialize.

The SSH results page does not need IOC enrichment JavaScript. It needs its own module.

**Prevention:**
1. Verify the base template name before writing the SSH template (`ls app/templates/`)
2. The SSH results template should extend the same base as other pages but should NOT trigger the
   enrichment module — either exclude the enrichment JS from the SSH page bundle, or ensure
   `enrichment.ts:init()` has a guard: `if (!document.querySelector('.page-results')) return;`
3. The SSH TypeScript module should be in its own file (e.g., `ssh.ts`) and registered in `main.ts`
   with a similar guard: `if (document.querySelector('.page-ssh')) { sshModule.init(); }`

**Phase:** Phase 2 (TypeScript module) + Phase 3 (template integration).

---

## Minor Pitfalls

### Pitfall 14: Haversine Distance Precision at Short Distances

**What goes wrong:**
The haversine formula computes great-circle distance on a sphere. For "impossible travel" detection
at continental distances (e.g., New York to Tokyo = 10,838 km in 2 minutes = 325,140 km/h), the
formula is accurate enough. For short distances (e.g., two GeoIP results that both resolve to
"United States" but different cities), the city-level coordinates from a free GeoIP API have
accuracy of ±50–100 km. Two logins from the same user in New York and New Jersey may geolocate to
coordinates 150 km apart, implying 150 km travel between sessions — well within physical possibility
but flagged as "new location" by a naive coordinate-change detector.

**Prevention:**
For v1.2 rule-based detection, do not flag impossible travel based on city-level coordinate changes.
Use country-level "new country" detection (which is accurate) and impossible travel (which only fires
at intercontinental speeds). Ignore intra-country coordinate differences.

**Phase:** Phase 2 (anomaly detector thresholds).

---

### Pitfall 15: sshd PID Reuse Across Log Lines

**What goes wrong:**
Multiple simultaneous SSH connections produce log lines with different PIDs:
```
Jan 5 03:22:11 sshd[1234]: Accepted publickey for alice from 1.2.3.4 port 54321 ssh2
Jan 5 03:22:11 sshd[5678]: Accepted publickey for alice from 1.2.3.5 port 54322 ssh2
```
PIDs are reused after process termination. If the parser uses PID to correlate "Accepted" with the
subsequent PAM "session opened" line (to detect session duration), PID correlation is unreliable
across log rotation boundaries.

**Prevention:**
For v1.2, do not attempt session correlation via PID. Treat each "Accepted" line as a complete login
event with timestamp, user, and source IP. Session duration analysis (connection close time) requires
PAM session close lines and PID correlation, which is out of scope for this milestone.

**Phase:** Phase 1 (parser scope definition). Explicitly document: "session duration is not tracked."

---

### Pitfall 16: "Unusual Hours" Alert Based on Server Timezone, Not User Timezone

**What goes wrong:**
The unusual-hours detector fires when a login occurs outside the configured window (default 06:00–22:00).
The comparison uses the server's local time (from auth.log timestamps). A user in UTC-5 connecting
at 23:00 their time (04:00 server time, which is UTC+0) will trigger an "unusual hours" alert even
though it is a normal evening login for them.

**Prevention:**
Document clearly: "Unusual hours is evaluated in server local time. Configure the hours window to
match the expected working hours of users of this server, not individual user timezones." Add this
as a UI tooltip or inline help text on the configuration page. Do not attempt per-user timezone
correction — GeoIP-based timezone inference adds complexity and is often wrong for VPN users.

**Phase:** Phase 3 (UI configuration + alert presentation).

---

## Integration-Specific Risks (SentinelX-Specific)

These risks are specific to adding this feature to the existing SentinelX codebase.

| Risk | Component | Impact | Mitigation |
|------|-----------|--------|------------|
| `ipinfo.io` vs `ip-api.com` naming confusion | config.py ALLOWED_API_HOSTS | SSRF validator rejects all GeoIP calls (silent ValueError) | Add `"ip-api.com"` explicitly to allowlist; do NOT rename the existing `ipinfo.io` entry — it serves the IOC enrichment adapter |
| 512 KB MAX_CONTENT_LENGTH | config.py, app factory | All real auth.log uploads rejected with 413 | Raise to 10 MB; update 413 error message to mention log files |
| CSRF on upload form | SSH blueprint | HTTP 400 on POST with confusing error | Include `csrf_token()` in upload form template |
| Blueprint name collision | app/__init__.py | AssertionError at startup | Use unique name `"ssh"` with `url_prefix="/ssh"` |
| enrichment.ts init() runs on SSH pages | main.ts | JS errors in console; possible TypeError | Guard enrichment init with page-presence check |
| SEC-08 (textContent-only) | SSH results TypeScript | XSS from attacker-controlled usernames in log | Enforce textContent in SSH TypeScript module; no innerHTML shortcuts |
| ip-api.com not in SSRF allowlist | http_safety.py validate_endpoint | ValueError on first batch GeoIP call | Add to ALLOWED_API_HOSTS in Phase 1 |
| Rate limit on ip-api.com batch | GeoIP enrichment | HTTP 429 / IP ban for large logs | Deduplicate IPs; check X-Rl header; cap at 1000 unique IPs per upload |

---

## Phase-to-Pitfall Mapping

| Phase | Pitfalls to Address |
|-------|---------------------|
| Phase 1: Parser + Contracts | Pitfall 1 (year rollover), Pitfall 3 (format variants), Pitfall 5 (bounded history model), Pitfall 7 (blueprint naming), Pitfall 8 (MAX_CONTENT_LENGTH), Pitfall 11 (CSRF), Pitfall 12 (secure_filename), Pitfall 15 (PID correlation scope) |
| Phase 2: GeoIP + Anomaly Detector | Pitfall 2 (ip-api.com rate limits + SSRF allowlist), Pitfall 4 (naive datetimes), Pitfall 9 (private IPs), Pitfall 13 (Jinja template inheritance), Pitfall 14 (haversine precision) |
| Phase 3: UI + Alert Presentation | Pitfall 6 (XSS via textContent), Pitfall 10 (false positive framing), Pitfall 16 (unusual hours timezone) |

---

## Security Mistakes to Never Make

| Mistake | Risk | Prevention |
|---------|------|------------|
| `innerHTML` in SSH results TypeScript | Stored XSS from attacker-controlled usernames in auth.log | textContent-only, same as rest of codebase (SEC-08) |
| Saving uploaded log to disk with user-provided filename | Path traversal, arbitrary file write | Process entirely in-memory; never write to disk |
| Not validating file size before `file.read()` | Memory exhaustion | Check `Content-Length` header AND read with a byte counter; reject > 10 MB |
| Adding ip-api.com calls outside SSRF allowlist | SEC-16 violation | ALLOWED_API_HOSTS must be updated before any ip-api.com call |
| CSRF exempting the SSH blueprint | CSRF vulnerability on file upload | Only `bp_api` is CSRF-exempt; SSH blueprint must require CSRF |
| Logging parsed usernames to app log | Log injection / sensitive data exposure | If logging login events for debugging, sanitize or omit username field |

---

## Sources

- Direct inspection: `app/config.py` — ALLOWED_API_HOSTS allowlist (ipinfo.io present; ip-api.com absent), MAX_CONTENT_LENGTH = 512 KB
- Direct inspection: `app/__init__.py` — blueprint registration pattern, CSRF exemption for bp_api only
- Direct inspection: `app/enrichment/adapters/ip_api.py` — existing adapter calls ipinfo.io (not ip-api.com), no batch support
- Direct inspection: `app/enrichment/http_safety.py` — SSRF validation via validate_endpoint(); ValueError on disallowed hosts
- [ip-api.com batch API docs](https://ip-api.com/docs/api:batch) — 15 req/min limit, 100 IPs per request, private range returns fail status
- [ip-api.com JSON API docs](https://ip-api.com/docs/api:json) — 45 req/min single endpoint
- [Grafana Loki issue #692](https://github.com/grafana/loki/issues/692) — yearless syslog timestamp produces year=0
- [Logstash date filter issue #46](https://github.com/logstash-plugins/logstash-filter-date/issues/46) — New Year rollover handling
- [Elastic: Grokking Linux auth logs](https://www.elastic.co/blog/grokking-the-linux-authorization-logs) — format variants, Grok patterns
- [fail2ban issue #2726](https://github.com/fail2ban/fail2ban/issues/2726) — "Failed publickey" variant not recognized by naive parsers
- [Microsoft: Detecting Impossible Travel](https://techcommunity.microsoft.com/blog/microsoftthreatprotectionblog/detecting-and-remediating-impossible-travel/3366017) — VPN/proxy false positive catalog
- [CyberMSI: Why So Many Impossible Travels in MCAS?](https://cybermsi.com/blog/security/why-are-there-so-many-impossible-travels-in-mcas/) — cloud NAT, mobile roaming false positive patterns
- [OWASP Log Injection](https://owasp.org/www-community/attacks/Log_Injection) — XSS via log content rendered in browser
- [HackerOne: Secure File Uploads in Flask](https://www.hackerone.com/blog/secure-file-uploads-flask-filtering-and-validation-techniques) — path traversal, file type validation
- [Werkzeug secure_filename docs](https://werkzeug.palletsprojects.com/en/stable/utils/) — strips non-ASCII, may return empty string
- [Python memory: deque maxlen](https://tedboy.github.io/python_stdlib/generated/generated/collections.deque.maxlen.html) — bounded history pattern

---

*Pitfalls research for: SentinelX v1.2 SSH Login Anomaly Detection*
*Researched: 2026-04-12*
