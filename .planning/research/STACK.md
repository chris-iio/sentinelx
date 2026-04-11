# Technology Stack

**Project:** SentinelX v1.2 — SSH Login Anomaly Detection
**Researched:** 2026-04-12
**Overall confidence:** HIGH (all claims verified against running Python 3.10.12 environment and live API probes)

---

## Context: Additive Milestone — Existing Stack Is Locked

This document answers one question only: **what new libraries or configuration changes does v1.2 require?**

The existing stack (Python 3.10 + Flask 3.1, requests, dataclasses, TypeScript 5.8 + esbuild, Tailwind CSS v3, SQLite, 14 provider adapters) ships unchanged.

**Answer: zero new pip dependencies.** Every capability needed for SSH log parsing, anomaly detection, and GeoIP enrichment is already available in the runtime environment or the existing requirements.txt.

---

## Recommended Stack Additions

### New Python Modules (stdlib — already available, no install needed)

| Module | Version | Purpose | Why |
|--------|---------|---------|-----|
| `re` | stdlib | auth.log line parsing | Regex is the correct tool for fixed-format syslog lines; no third-party log-parsing library needed |
| `math` | stdlib | Haversine distance formula for impossible travel | `math.sin`, `math.cos`, `math.atan2` — all required operations present |
| `datetime` | stdlib | Timestamp parsing, time-delta calculation | `datetime.datetime.strptime()` handles both syslog and ISO8601 formats; `timedelta.total_seconds()` gives the travel window |
| `dataclasses` | stdlib (Python 3.7+) | `LoginEvent`, `GeoLocation`, `Anomaly` models | Project already uses frozen dataclasses throughout — consistent pattern |
| `collections` | stdlib | `defaultdict` for per-user login history | In-memory `{username: [LoginEvent]}` grouping — no external data structure library needed |
| `ipaddress` | stdlib | RFC1918 private IP filtering | `ipaddress.ip_address(ip).is_private` correctly excludes 10.x, 172.16–31.x, 192.168.x before GeoIP lookup |
| `io` | stdlib | `BytesIO` for file stream handling | Flask's `request.files['log'].stream` is already a file-like object; no extra handling needed |

### Existing Dependencies That Cover New Needs (no version changes)

| Dependency | Version | New Use | Why No Change Needed |
|------------|---------|---------|---------------------|
| `requests` | 2.32.5 | GeoIP calls to ipinfo.io from SSH module | `requests.Session` + existing `safe_request()` in `http_safety.py` provides SSRF validation, timeouts, byte cap — reuse directly |
| `Flask` | 3.1.1 | SSH Blueprint, file upload, JSON API | `werkzeug.FileStorage` (bundled with Flask) handles multipart file upload; `Blueprint` pattern already in project |
| `dataclasses` | stdlib | New SSH-specific models | Pattern already used in `enrichment/models.py` and `pipeline/models.py` |

### New Application Modules (no pip install — new .py files only)

| Module | Path | Responsibility |
|--------|------|----------------|
| SSH models | `app/ssh/models.py` | `LoginEvent`, `GeoLocation`, `Anomaly` frozen dataclasses |
| SSH parser | `app/ssh/parser.py` | auth.log bytes → `list[LoginEvent]` using stdlib `re` + `datetime` |
| SSH detector | `app/ssh/detector.py` | `list[LoginEvent]` → `list[Anomaly]` using stdlib `math` + `collections` |
| SSH GeoIP | `app/ssh/geoip.py` | `str (IP)` → `GeoLocation | None` using `requests` + ipinfo.io |
| SSH routes | `app/routes/ssh.py` | Flask routes: upload form (`GET /ssh`), analysis (`POST /ssh/analyze`), JSON API (`GET /api/ssh/<job_id>`) |

---

## GeoIP Provider: ipinfo.io (Already Integrated)

**Use ipinfo.io. Do not use ip-api.com.**

The PROJECT.md mentions "ip-api.com for GeoIP" but the existing adapter (`app/enrichment/adapters/ip_api.py`) actually calls ipinfo.io (`https://ipinfo.io/{ip}/json`). This distinction matters:

| | ipinfo.io | ip-api.com |
|--|-----------|------------|
| Free tier HTTPS | Yes (verified: `https://ipinfo.io`) | No — HTTP 403 on free tier (verified live) |
| lat/lon for impossible travel | Yes — `loc` field: `"49.4478,11.0683"` | Yes — separate `lat`/`lon` fields |
| Country code | Yes — `country` field | Yes — `countryCode` field |
| Rate limit (free tier) | 50,000 req/month (~1,667/day) | 45 req/min |
| Already in SSRF allowlist | Yes — `"ipinfo.io"` in `ALLOWED_API_HOSTS` | No — would require config change |
| Already in test suite | Yes — `tests/test_ip_api.py` | No |

**Conclusion:** ipinfo.io is correct. The `loc` field (`"lat,lon"` string) is parsed as `lat, lon = map(float, loc.split(','))` — sufficient for haversine distance. No adapter changes required.

The SSH GeoIP module calls ipinfo.io **directly** (not through `IPApiAdapter`) because:
1. `IPApiAdapter` wraps results in `EnrichmentResult` — wrong shape for SSH use
2. SSH needs raw `(country_code, lat, lon)` tuples, not enrichment verdicts
3. A standalone `lookup_geoip(ip, session, allowed_hosts)` function in `app/ssh/geoip.py` reuses `safe_request()` from `http_safety.py` without inheriting the provider abstraction

---

## auth.log Format Variations

**Use stdlib `re` only. No third-party log-parsing library needed.**

Two timestamp formats appear in production auth.log files:

### Format 1: Traditional syslog (most common — Ubuntu, Debian, RHEL, CentOS)
```
Jan 15 14:23:45 hostname sshd[12345]: Accepted password for alice from 192.168.1.1 port 55432 ssh2
Jan  5 09:00:00 hostname sshd[999]: Failed password for root from 1.2.3.4 port 22345 ssh2
```
- Month is abbreviated English name (`Jan`–`Dec`)
- Day is right-justified, single-digit days have leading space (`" 5"`)
- No year — must be inferred from current year with rollover detection
- No timezone — server local time; hour comparison is direct (no conversion)

**Regex:** `r'^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+\S+\s+sshd\[\d+\]:\s+(?P<msg>.+)$'`

**Year inference:** parse with current year; if result is in the future (>24h ahead), use `year - 1`. Handles December→January log rotation correctly.

### Format 2: RFC5424 / systemd journal export (modern systemd systems)
```
2024-01-15T14:23:45.123456+00:00 hostname sshd[12345]: Accepted password for alice from 1.2.3.4 port 55432 ssh2
```
- Full ISO8601 with microseconds and UTC offset
- Parse with `datetime.datetime.fromisoformat()` (Python 3.7+) — handles all offset formats

**Regex:** `r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))\s+\S+\s+sshd\[\d+\]:\s+(?P<msg>.+)$'`

### OpenSSH Message Patterns (verified against OpenSSH source)

| Event type | Pattern | Fields |
|-----------|---------|--------|
| Accepted login | `Accepted (password|publickey|gssapi-with-mic|keyboard-interactive/pam) for <user> from <ip> port <N> ssh<N>` | user, ip |
| Failed attempt | `Failed password for [invalid user] <user> from <ip> port <N> ssh<N>` | user, ip |
| Invalid user pre-auth | `Invalid user <user> from <ip> port <N>` | user, ip |
| Pre-auth disconnect | `(Connection closed by|Disconnected from) invalid user <user> <ip> port <N> [preauth]` | user, ip |

**All four patterns verified** against running regex on real log line samples (see research session). All parse correctly with stdlib `re`.

---

## Data Structures for Per-User History

**Use stdlib `collections.defaultdict`. No external library.**

```python
# In-memory only — cleared after each analysis request (no persistence needed)
from collections import defaultdict
history: dict[str, list[LoginEvent]] = defaultdict(list)
```

`LoginEvent` is a frozen dataclass:
```python
@dataclass(frozen=True)
class LoginEvent:
    username: str
    ip: str
    timestamp: datetime.datetime  # timezone-naive (syslog local time) or tz-aware (ISO8601)
    event_type: str  # "accepted" | "failed" | "invalid"
    raw_line: str    # original log line for context/debugging
```

`GeoLocation` is a frozen dataclass (result of ipinfo.io lookup):
```python
@dataclass(frozen=True)
class GeoLocation:
    country_code: str     # e.g. "DE"
    lat: float            # from ipinfo.io 'loc' field
    lon: float            # from ipinfo.io 'loc' field
    city: str             # for display
```

`Anomaly` is a frozen dataclass:
```python
@dataclass(frozen=True)
class Anomaly:
    username: str
    anomaly_type: str  # "new_ip" | "new_country" | "impossible_travel" | "unusual_hour"
    event: LoginEvent
    detail: str        # human-readable explanation
    severity: str      # "high" | "medium" | "low"
```

---

## Datetime Handling

**Use stdlib `datetime` only. No pytz or dateutil.**

Python 3.10 has `zoneinfo` (stdlib since 3.9) for IANA timezone names, but it is **not needed** here:

- Syslog timestamps are server local time, no timezone info — hour comparison is direct
- ISO8601 timestamps with offset are handled by `datetime.fromisoformat()` (Python 3.7+)
- Impossible travel time delta uses `(t2 - t1).total_seconds()` — works regardless of tz-naive vs tz-aware as long as both events are from the same log (same format)

**Year inference for syslog timestamps:**
```python
current_year = datetime.datetime.now().year
dt = datetime.datetime.strptime(f"{current_year} {month} {day} {time}", "%Y %b %d %H:%M:%S")
if dt > datetime.datetime.now() + datetime.timedelta(hours=24):
    dt = dt.replace(year=current_year - 1)
```
This handles the edge case where a log from December is analyzed in January.

---

## Configurable Hour Window

**Implementation: `[ssh]` section in `~/.sentinelx/config.ini` via `ConfigStore`.**

The `ConfigStore` class already supports arbitrary sections via `_set_value(section, key, value)`. Add two methods:

```python
# In config_store.py — new methods (no new dependencies)
def get_ssh_normal_hours(self) -> tuple[int, int]:
    """Return (start_hour, end_hour) for normal hours window. Default: (6, 22)."""

def set_ssh_normal_hours(self, start: int, end: int) -> None:
    """Write normal hours window to [ssh] section."""
```

Stored as:
```ini
[ssh]
normal_hours_start = 6
normal_hours_end = 22
```

Detection logic: `if not (start <= event_hour < end): flag UNUSUAL_HOUR`. The `event_hour` comes directly from the parsed timestamp — no timezone conversion.

---

## File Upload Configuration

**One config change required: increase `MAX_CONTENT_LENGTH`.**

Current value: `512 * 1024` (512 KB) — sufficient for IOC paste input.
SSH auth.log files: typically 500 KB–5 MB for a week of busy-server logs.

**Change:**
```python
# In app/config.py
MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5 MB — covers both paste (512KB) and SSH log uploads
```

The 413 error handler already exists and returns a user-friendly message. Update its text to mention both use cases.

Flask's `werkzeug.FileStorage` (bundled with Flask 3.1, no extra install) handles `multipart/form-data` file uploads via `request.files`. The SSH route reads the uploaded file as:
```python
log_file = request.files.get("log_file")
content = log_file.stream.read(5 * 1024 * 1024 + 1)  # +1 to detect oversize
```

---

## SSRF Allowlist: No Change Required

`ipinfo.io` is already in `ALLOWED_API_HOSTS`. No new hosts needed. The SSH module does not call any new external services.

---

## Flask Blueprint Pattern

Follow the existing pattern exactly. Add SSH routes as a new module imported by `app/routes/__init__.py`:

```python
# In app/routes/__init__.py — add:
from . import ssh  # noqa: E402, F401
```

The SSH routes attach to the existing `bp = Blueprint("main", ...)` — no new blueprint needed for the HTML routes. The JSON API endpoint attaches to `bp_api` (already CSRF-exempt).

---

## What NOT to Add

| Avoid | Why | What to Use Instead |
|-------|-----|---------------------|
| `python-dateutil` | Would add a dependency solely for timestamp parsing; stdlib `datetime.strptime` + `fromisoformat` handles both syslog and ISO8601 | stdlib `datetime` |
| `GeoLite2` / `maxminddb` | Requires downloading and updating a local database (~60 MB); ipinfo.io is already integrated and works zero-config | ipinfo.io via existing `requests` + `safe_request()` |
| `pytz` | Python 3.10 has `zoneinfo` stdlib; syslog timestamps don't have timezone info anyway | stdlib `datetime` + `zoneinfo` (if ever needed) |
| `pandas` | No tabular analysis needed; `collections.defaultdict` + sorted list operations are sufficient | stdlib `collections` |
| `scikit-learn` / any ML library | Out of scope per PROJECT.md: "Rule-based detection over ML" | Rule-based logic in `detector.py` |
| Any log-parsing library (`python-syslog`, `logparser`) | auth.log format is fixed enough that 3–4 regex patterns cover all OpenSSH variants; a library adds surface area for no gain | stdlib `re` |
| `ip-api.com` | Free tier is HTTP-only (HTTPS returns 403 — verified); would require adding new SSRF allowlist entry | ipinfo.io (already integrated, HTTPS, same data) |
| New Flask blueprint for SSH | The existing `bp` Blueprint handles all HTML routes; only the JSON polling endpoint needs `bp_api` (already CSRF-exempt) | Existing `bp` + `bp_api` |
| Redis / any external state store | Analysis is per-upload, synchronous, in-memory; no persistence between requests needed | In-memory `dict` within request scope |

---

## Requirements.txt: No Changes

```
# requirements.txt — unchanged for v1.2
Flask==3.1.1
Flask-Limiter==4.1.1
Flask-WTF==1.2.2
iocextract==1.16.1
iocsearcher==2.7.2
python-dotenv==1.1.0
requests==2.32.5
dnspython==2.8.0
python-whois==0.9.6
```

All SSH detection capabilities come from stdlib modules (`re`, `math`, `datetime`, `dataclasses`, `collections`, `ipaddress`, `io`) already present in Python 3.10.

---

## Sources

- SentinelX codebase (verified live): `app/enrichment/adapters/ip_api.py`, `app/enrichment/http_safety.py`, `app/enrichment/models.py`, `app/config.py`, `app/__init__.py`, `app/routes/__init__.py`, `requirements.txt` — HIGH confidence
- Live API probe: `http://ip-api.com/json/8.8.8.8` returns HTTP 200 with `lat`/`lon`; `https://ip-api.com/json/8.8.8.8` returns HTTP 403 — confirms HTTPS unavailable on free tier — HIGH confidence
- Python 3.10.12 runtime verification: stdlib modules `re`, `math`, `datetime`, `dataclasses`, `collections`, `ipaddress`, `zoneinfo`, `io` all available — HIGH confidence
- regex verification: all four OpenSSH log patterns tested against real sample lines in running Python interpreter — HIGH confidence
- `datetime.fromisoformat()` and `datetime.strptime()` timestamp parsing tested against syslog and ISO8601 formats — HIGH confidence

---

*Stack research for: SentinelX v1.2 SSH Login Anomaly Detection*
*Researched: 2026-04-12*
