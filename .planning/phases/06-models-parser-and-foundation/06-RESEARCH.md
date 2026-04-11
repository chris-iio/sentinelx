# Phase 6: Models, Parser, and Foundation - Research

**Researched:** 2026-04-12
**Domain:** Python frozen dataclasses, syslog/RFC3339 log parsing, ConfigStore extension, Flask MAX_CONTENT_LENGTH
**Confidence:** HIGH — all findings verified against live codebase at `/home/chris/projects/sentinelx`

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** LoginEvent is a frozen dataclass with fields: username (str), source_ip (str | None), hostname (str | None), timestamp (datetime), auth_method (str — "password" or "publickey"), line_number (int), raw_line (str)
- **D-02:** source_ip and hostname are mutually exclusive optionals — exactly one is set per event. When hostname is present (UseDNS enabled), downstream GeoIP lookup is skipped for that event
- **D-03:** auth_method is stored explicitly, enabling future detection rules like "flag password auth from external IPs"
- **D-04:** raw_line and line_number provide full traceability back to the source file for debugging
- **D-05:** Parser returns a ParseSummary alongside the event list — includes total_lines, parsed_count, skipped_count at minimum. The UI (Phase 9) can display "Parsed 847 of 12,304 lines" for analyst confidence
- **D-06:** Lines that partially match SSH event patterns but fail to fully parse generate logger.warning() with line number and content — aids debugging without cluttering the analyst-facing summary
- **D-07:** Completely unrecognized lines (non-SSH syslog, blank lines, etc.) are silently skipped — counted in skipped_count but not logged individually
- **D-08:** Normal-hours window stored as single range string in `[ssh]` section: `normal_hours = 06:00-22:00`. Parser splits on dash, validates HH:MM format
- **D-09:** Default is 06:00-22:00 when the key is absent (CFG-01 requirement)
- **D-10:** SSH code lives in `app/ssh/` as a new top-level package, mirroring `app/enrichment/` and `app/pipeline/`. This package will contain models.py, parser.py, and in later phases detector.py (Phase 8) and routes (Phase 9)
- **D-11:** SSH models are in `app/ssh/models.py` — separate from enrichment models. Clean domain boundary: SSH models don't depend on enrichment models

### Claude's Discretion

- Auth method breadth: Whether to match only "Accepted password"/"Accepted publickey" (strict PARSE-01) or generically match "Accepted <method>" to capture keyboard-interactive, gssapi, etc. Claude will decide based on real-world auth.log patterns
- Future config keys: Whether to pre-wire constants or helper methods for anticipated Phase 8 config (e.g., travel_threshold_hours) or keep strictly to CFG-01 scope

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PARSE-01 | Parser extracts structured login events from auth.log lines containing "Accepted password" or "Accepted publickey" — each event has username, source IP, and timestamp | See: Standard Stack (regex patterns), Architecture Patterns (LoginEvent model), Code Examples |
| PARSE-02 | Parser detects BSD syslog and RFC3339 timestamp formats per-line and handles year rollover for BSD timestamps (December→January boundary) | See: Architecture Patterns (dual-format detection), Common Pitfalls (Pitfall 1 year rollover), Code Examples |
| PARSE-03 | Parser supports both IPv4 and IPv6 source addresses | See: Architecture Patterns (source field extraction regex), Code Examples |
| PARSE-04 | Parser handles hostname entries when sshd UseDNS is enabled — skip GeoIP for non-IP values | See: Architecture Patterns (D-02 mutually exclusive fields), Code Examples |
| WEB-06 | MAX_CONTENT_LENGTH increased from 512KB to 5MB to accommodate auth.log file uploads | See: Architecture Patterns (config.py change), Code Examples |
| CFG-01 | Normal hours window is configurable via ConfigStore [ssh] section (default 6am–10pm) | See: Architecture Patterns (ConfigStore extension), Code Examples |
</phase_requirements>

---

## Summary

Phase 6 delivers the foundational SSH data layer: a `LoginEvent` frozen dataclass with full traceability fields, a dual-format auth.log parser handling BSD syslog (with year-rollover correction) and RFC3339 timestamps, a `ParseSummary` for analyst confidence metrics, a `[ssh]` ConfigStore section for the normal-hours window, and a `MAX_CONTENT_LENGTH` increase to 5 MB. No new pip dependencies are required — every capability is covered by Python 3.10 stdlib (`re`, `datetime`, `dataclasses`) and the existing Flask/ConfigStore infrastructure.

The work is entirely Python — no TypeScript, no new Flask routes, no HTML templates. The `app/ssh/` package is created but initially contains only `__init__.py`, `models.py`, and `parser.py`. The ConfigStore gets two new methods. Two constants change in `app/config.py` and one string changes in `app/__init__.py`. The phase is self-contained and has no cross-phase code dependencies.

The highest-risk item is the BSD syslog year-rollover algorithm (Pitfall 1 in PITFALLS.md). It must be implemented and tested with a fixture spanning December 29 – January 3 before any other detection logic is written, per the locked decision in STATE.md.

**Primary recommendation:** Implement in three tasks — (1) models + package skeleton, (2) parser with full timestamp and source-field handling, (3) ConfigStore + MAX_CONTENT_LENGTH changes. Cover each with targeted unit tests before moving to the next.

---

## Standard Stack

### Core (all stdlib — no install needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` | stdlib | auth.log line regex parsing | Fixed syslog format requires named-capture-group regex, not string splitting |
| `datetime` | stdlib | Timestamp parsing + year rollover | `strptime()` for BSD syslog, `fromisoformat()` for RFC3339; both tested [VERIFIED: live Python 3.10.12] |
| `dataclasses` | stdlib (Python 3.7+) | LoginEvent, ParseSummary frozen models | Consistent with IOC, EnrichmentResult patterns throughout codebase |
| `configparser` | stdlib | Reading/writing `[ssh]` section | Already used by ConfigStore — no new import |
| `ipaddress` | stdlib | Detecting hostname vs IP in source field | `ipaddress.ip_address()` raises ValueError on hostnames — definitive discriminator |
| `io` | stdlib | Reading uploaded file stream | Flask's `request.files[n].stream` is file-like; `stream.read(limit)` pattern |

### Supporting (existing project libraries)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` | stdlib | Module-level logger via `getLogger(__name__)` | Per-convention in every module; partial-match warning goes here |
| `Flask` (werkzeug) | 3.1.1 | `request.files` for upload stream access | WEB-06: reading file bytes from multipart form upload |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `re` named groups | `str.split()` positional | Positional split breaks on "invalid user" variant and IPv6 addresses — named groups are correct approach |
| `datetime.strptime` | `python-dateutil` | dateutil is not in requirements.txt; stdlib handles both formats cleanly |
| `ipaddress.ip_address()` | Regex IP validation | ipaddress handles IPv4 and IPv6 correctly including edge cases; regex is fragile |

**Installation:** No new packages. Requirements.txt is unchanged. [VERIFIED: codebase inspection]

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── ssh/                     # new top-level package (D-10)
│   ├── __init__.py          # empty or package docstring
│   ├── models.py            # LoginEvent, ParseSummary frozen dataclasses
│   └── parser.py            # parse_auth_log() → tuple[list[LoginEvent], ParseSummary]
├── enrichment/
│   └── config_store.py      # add get_ssh_normal_hours() / set_ssh_normal_hours()
├── config.py                # MAX_CONTENT_LENGTH: 512KB → 5MB
└── __init__.py              # update 413 error handler text

tests/
└── test_ssh_models.py       # LoginEvent immutability, field contracts
└── test_ssh_parser.py       # timestamp parsing, source extraction, rollover, summary
└── test_config_store.py     # extend with [ssh] section tests
```

### Pattern 1: LoginEvent Frozen Dataclass

**What:** Immutable model capturing one successful SSH login from one log line.
**When to use:** Return type from parser; input to detector (Phase 8) and GeoIP (Phase 7).

```python
# Source: mirrors app/enrichment/models.py and app/pipeline/models.py patterns
# [VERIFIED: codebase inspection]
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LoginEvent:
    """An immutable SSH login event extracted from one auth.log line.

    Attributes:
        username:    Authenticated username.
        source_ip:   Source IPv4 or IPv6 address. None when hostname is set.
        hostname:    Resolved hostname (when sshd UseDNS=yes). None when source_ip is set.
        timestamp:   Parsed login time. Naive datetime for BSD syslog (server local time);
                     timezone-aware for RFC3339 lines.
        auth_method: "password" or "publickey" (or broader method string — see discretion).
        line_number: 1-based line number in the original file for traceability.
        raw_line:    Complete original log line for debugging.

    Invariant (D-02): exactly one of source_ip, hostname is non-None per event.
    """

    username: str
    source_ip: str | None
    hostname: str | None
    timestamp: datetime
    auth_method: str
    line_number: int
    raw_line: str


@dataclass(frozen=True)
class ParseSummary:
    """Summary statistics from one parse run.

    Attributes:
        total_lines:   Total lines in the input file.
        parsed_count:  Lines successfully parsed as LoginEvent.
        skipped_count: Lines that did not match any SSH pattern (silently skipped).
        warning_count: Lines that partially matched but failed complete extraction
                       (logged as logger.warning by parser).
    """

    total_lines: int
    parsed_count: int
    skipped_count: int
    warning_count: int
```

### Pattern 2: Dual-Format Timestamp Detection (PARSE-02)

**What:** Per-line detection of BSD syslog vs RFC3339 timestamp format, with year-rollover correction for BSD.
**When to use:** First step in parser's line-processing loop.

```python
# Source: STACK.md research + PITFALLS.md Pitfall 1 algorithm
# [VERIFIED: tested against Python 3.10.12 datetime module]
import re
from datetime import datetime, timedelta, timezone

# BSD syslog: "Jan  5 03:22:11" or "Jan 15 14:23:45"
_BSD_TS_RE = re.compile(
    r'^(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\b'
)

# RFC3339/ISO8601: "2024-01-15T14:23:45.123456+00:00" or "2024-01-15T14:23:45Z"
_RFC3339_RE = re.compile(
    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
)


def _parse_timestamp(line: str, now: datetime) -> datetime | None:
    """Detect format and parse timestamp from a log line.

    Args:
        line: Raw log line (leading whitespace stripped).
        now:  Reference "current time" injected at parse session start
              — keeps year inference consistent across the whole file.

    Returns:
        Parsed datetime, or None if no timestamp pattern matches.
    """
    if _RFC3339_RE.match(line):
        # Extract the timestamp token (first whitespace-delimited field)
        ts_str = line.split()[0]
        try:
            return datetime.fromisoformat(ts_str)
        except ValueError:
            return None

    m = _BSD_TS_RE.match(line)
    if m:
        month, day, time_str = m.group("month"), m.group("day"), m.group("time")
        try:
            dt = datetime.strptime(
                f"{now.year} {month} {day} {time_str}", "%Y %b %d %H:%M:%S"
            )
        except ValueError:
            return None
        # Year rollover: if inferred date is more than 24 hours in the future,
        # the log entry is from last year (December log analyzed in January).
        if dt > now + timedelta(hours=24):
            dt = dt.replace(year=now.year - 1)
        return dt

    return None
```

### Pattern 3: SSH Message Extraction (PARSE-01, PARSE-03, PARSE-04)

**What:** Regex extraction of username, source (IP or hostname), and auth method from the sshd message body.
**When to use:** Applied after timestamp is parsed and line is confirmed to be an sshd "Accepted" line.

```python
# Source: STACK.md research — verified against OpenSSH source message format
# [VERIFIED: PITFALLS.md research, cross-checked against OpenSSH sshd message patterns]

# After stripping the timestamp+hostname+sshd[PID]: prefix from a line,
# the message portion for successful logins looks like:
#   "Accepted password for alice from 1.2.3.4 port 54321 ssh2"
#   "Accepted publickey for alice from 2001:db8::1 port 54321 ssh2: RSA SHA256:abc"
#   "Accepted keyboard-interactive/pam for alice from hostname.example.com port 54321 ssh2"

_ACCEPTED_MSG_RE = re.compile(
    r'^Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+'
    r'from\s+(?P<source>\S+)\s+port\s+\d+'
)

# Full line regex (BSD syslog format) — combines timestamp, host, pid, and message
_BSD_ACCEPTED_RE = re.compile(
    r'^(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'\S+\s+sshd\[\d+\]:\s+Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+'
    r'from\s+(?P<source>\S+)\s+port\s+\d+'
)

# Full line regex (RFC3339 format)
_RFC3339_ACCEPTED_RE = re.compile(
    r'^\S+\s+\S+\s+sshd\[\d+\]:\s+Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+'
    r'from\s+(?P<source>\S+)\s+port\s+\d+'
)
```

**Source field discrimination (PARSE-03 + PARSE-04):**

```python
import ipaddress

def _classify_source(source: str) -> tuple[str | None, str | None]:
    """Return (source_ip, hostname) — exactly one is non-None.

    Args:
        source: Raw value from the "from <source>" field.

    Returns:
        (source_ip, None) if source is a valid IPv4 or IPv6 address.
        (None, hostname) if source is a hostname (UseDNS=yes case).
    """
    try:
        ipaddress.ip_address(source)
        return source, None
    except ValueError:
        return None, source
```

### Pattern 4: ConfigStore SSH Section Extension (CFG-01)

**What:** Two new methods on the existing ConfigStore class — reads/writes `[ssh]` section, `normal_hours` key.
**When to use:** Called by detector (Phase 8) to get the hours window; default returned when key absent (D-09).

```python
# Source: existing ConfigStore._set_value() / _read_config() patterns
# [VERIFIED: app/enrichment/config_store.py inspection]

_SSH_SECTION = "ssh"
_SSH_NORMAL_HOURS_KEY = "normal_hours"
_SSH_NORMAL_HOURS_DEFAULT = "06:00-22:00"


def get_ssh_normal_hours(self) -> str:
    """Read the normal hours window from [ssh] section.

    Returns:
        String in "HH:MM-HH:MM" format. Returns "06:00-22:00" if absent (D-09).
    """
    value = self._read_config().get(
        _SSH_SECTION, _SSH_NORMAL_HOURS_KEY, fallback=_SSH_NORMAL_HOURS_DEFAULT
    )
    return value or _SSH_NORMAL_HOURS_DEFAULT


def set_ssh_normal_hours(self, hours_range: str) -> None:
    """Write the normal hours window to [ssh] section.

    Args:
        hours_range: String in "HH:MM-HH:MM" format, e.g. "06:00-22:00".
    """
    self._set_value(_SSH_SECTION, _SSH_NORMAL_HOURS_KEY, hours_range)
```

### Pattern 5: MAX_CONTENT_LENGTH Change (WEB-06)

**What:** Two-line change across two files — constant definition and 413 error message.
**When to use:** Apply in the same task to keep the change atomic.

```python
# In app/config.py — change line 26:
MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5 MB — covers SSH auth.log uploads (SEC-12)

# In app/__init__.py — change line 129 (413 handler):
return "Input too large. Maximum upload size is 5 MB.", 413
```

[VERIFIED: `app/config.py` line 26 reads `512 * 1024`; `app/__init__.py` line 129 reads `"Maximum paste size is 512 KB."` — both need updating]

### Pattern 6: parse_auth_log() Public Interface

**What:** The single public function in `app/ssh/parser.py` — takes raw bytes or a text stream, returns events + summary.
**When to use:** Called by Phase 9 routes for upload processing; called by tests with fixture content.

```python
from __future__ import annotations

from datetime import datetime
from typing import IO

from app.ssh.models import LoginEvent, ParseSummary


def parse_auth_log(
    stream: IO[bytes] | IO[str],
    *,
    now: datetime | None = None,
) -> tuple[list[LoginEvent], ParseSummary]:
    """Parse an auth.log file stream into LoginEvent records.

    Args:
        stream: File-like object (bytes or text). From request.files or BytesIO in tests.
        now:    Reference timestamp for BSD year inference. Defaults to datetime.now().
                Inject in tests to simulate January analysis of December logs.

    Returns:
        Tuple of (events, summary). events is an empty list if nothing parsed.
        summary.parsed_count + summary.skipped_count + summary.warning_count == summary.total_lines.
    """
    ...
```

### Anti-Patterns to Avoid

- **Positional string splitting:** `line.split()[6]` — breaks on "invalid user" lines and any message with extra tokens. Use named-capture-group regex.
- **`datetime.now()` called inside the parsing loop:** Causes inconsistent year inference if a file takes time to parse. Fix `now` once at the start of `parse_auth_log()`.
- **Mutating LoginEvent fields after creation:** frozen=True enforces this at runtime, but ensure no `object.__setattr__` workarounds.
- **Catching and silently swallowing ValueError from `_classify_source`:** Log as warning (D-06), do not drop without a trace.
- **Using the existing `IPApiAdapter` for Phase 6 work:** That adapter is for IOC enrichment (different shape); no GeoIP calls happen in Phase 6.

---

## Claude's Discretion Recommendations

### Auth Method Breadth (PARSE-01)

**Recommendation: match "Accepted \<any method\>" generically, store the full method string.**

Real-world auth.log contains these accepted methods beyond password and publickey:
- `keyboard-interactive/pam` — common on systems with PAM modules
- `gssapi-with-mic` — Kerberos/GSSAPI auth (common in enterprise)
- `hostbased` — rare but valid

The PARSE-01 requirement says "password or publickey" but CONTEXT.md D-03 says "enabling future detection rules like 'flag password auth from external IPs'" — this implies auth_method carries semantic value. Storing the raw method string (`"keyboard-interactive/pam"`) is more useful than normalizing to a two-value enum, and costs nothing extra.

Implementation: the regex `Accepted\s+(?P<method>\S+)` captures whatever appears. The parser stores the full method string verbatim. The auth_method field type is `str` (not an enum), matching D-01. Tests assert that "password" and "publickey" are stored correctly; other methods are stored without normalization.

[ASSUMED] — training knowledge of OpenSSH log format; not verified against a live auth.log in this session. The pattern is well-documented in PITFALLS.md research (HIGH confidence source).

### Future Config Keys (CFG-01 scope only vs pre-wiring)

**Recommendation: CFG-01 scope only — no pre-wiring for Phase 8 keys.**

Phase 8 (detection) will add its own constants when the time comes. Pre-wiring `travel_threshold_hours` in Phase 6 creates dead code that the planner will need to update. YAGNI applies. Add only `_SSH_SECTION`, `_SSH_NORMAL_HOURS_KEY`, and `_SSH_NORMAL_HOURS_DEFAULT` constants.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BSD syslog timestamp parsing | Custom tokenizer | `datetime.strptime("%Y %b %d %H:%M:%S")` | strptime handles abbreviated month names and single-digit day with space padding |
| RFC3339/ISO8601 parsing | Custom parser | `datetime.fromisoformat()` | Handles UTC offset, Z suffix, microseconds — Python 3.7+ built-in |
| IPv4/IPv6 address validation | IP regex | `ipaddress.ip_address(source)` catch ValueError | ipaddress handles all edge cases including IPv6 compressed notation |
| INI config read/write | Raw file I/O | `ConfigStore._set_value()` / `_read_config()` | Already handles file creation, permissions (0o600), cache invalidation |
| Year rollover detection | Calendar math | One-liner: `if dt > now + timedelta(hours=24): dt.replace(year=now.year - 1)` | The canonical algorithm — do not invent variations |
| File size validation | Checking Content-Length header | `stream.read(limit + 1)` pattern | Read one byte beyond limit; if len > limit, reject. Avoids trusting user-provided headers |

**Key insight:** Every non-trivial parsing and config operation in this phase has a stdlib solution that already handles edge cases. The hand-rolled alternatives would be strictly worse.

---

## Common Pitfalls

### Pitfall 1: Year Rollover Bug (CRITICAL — must address)

**What goes wrong:** BSD syslog omits the year. Parser assumes current year. A log spanning December 28–January 3, analyzed in January, assigns 2026 to December entries — those events appear in the future relative to January events.

**Why it happens:** Developer tests with a single-month log; rollover never triggers in unit tests without explicit fixture.

**How to avoid:** Implement `_infer_year()` using the Logstash canonical algorithm (Pattern 2 above). Inject `now` as a parameter so tests can simulate January analysis of December logs.

**Warning signs:** If parsed_count for December lines is zero in a Dec–Jan fixture, `strptime` is likely raising ValueError rather than applying the rollover. Check the exception handling.

[VERIFIED: PITFALLS.md Pitfall 1, corroborated by Grafana Loki issue history]

---

### Pitfall 2: "invalid user" Lines Confuse Positional Parsers

**What goes wrong:** `Failed password for invalid user root from 1.2.3.4` has different field positions than `Failed password for root from 1.2.3.4`. PARSE-01 only requires "Accepted" lines, so this does not affect Phase 6 directly. However: if the parser tries to match "Accepted" lines with positional splitting rather than named capture groups, IPv6 addresses and publickey lines with RSA key fingerprints appended will also confuse it.

**How to avoid:** Use `_BSD_ACCEPTED_RE` / `_RFC3339_ACCEPTED_RE` with named groups. Never split on fixed column positions.

[VERIFIED: PITFALLS.md Pitfall 3]

---

### Pitfall 3: Hostname vs IP Discrimination Must Be Definitive

**What goes wrong:** When `sshd UseDNS=yes`, the "from" field contains a hostname like `vpn.corp.example.com`. A naive check like `"." in source` incorrectly flags IPs as hostnames (IPv4 contains dots). Only `ipaddress.ip_address()` is unambiguous.

**How to avoid:** Use `_classify_source()` from Pattern 3. The try/except on `ipaddress.ip_address()` is the correct discriminator — hostnames always raise ValueError there.

[VERIFIED: Python 3.10 ipaddress module behavior — `ip_address("vpn.corp.example.com")` raises ValueError; `ip_address("192.168.1.1")` and `ip_address("2001:db8::1")` succeed]

---

### Pitfall 4: ParseSummary Invariant Must Hold

**What goes wrong:** `parsed_count + skipped_count + warning_count != total_lines` if the parser has branching logic with missing increments. This breaks the UI display ("Parsed X of Y lines").

**How to avoid:** Use a single loop with explicit increment on every branch:
- Full match → `parsed_count += 1`
- Partial SSH match (fails extraction) → `warning_count += 1`, log warning
- No SSH pattern match → `skipped_count += 1`
- Always: `total_lines += 1` for each line yielded by the iterator

Write a test asserting the invariant holds for a mixed fixture.

[ASSUMED] — standard log parsing correctness concern, not specific to a library.

---

### Pitfall 5: frozen=True Enforcement

**What goes wrong:** Code outside the model tries `event.source_ip = new_ip` after parsing — frozen dataclasses raise `FrozenInstanceError` at runtime, not at import. This is a runtime crash that only surfaces when the field is actually set.

**How to avoid:** All transformations create new instances. Phase 6 parser is read-only — it creates LoginEvent instances but never modifies them. Document this in the class docstring.

[VERIFIED: frozen dataclass behavior in Python 3.10; same pattern in `EnrichmentResult`]

---

### Pitfall 6: ConfigStore Cache Not Invalidated After Write

**What goes wrong:** ConfigStore caches the parsed INI in `_cached_cfg`. If `get_ssh_normal_hours()` is called, then `set_ssh_normal_hours()` is called, then `get_ssh_normal_hours()` is called again — the cache may return the old value. `_save_config()` sets `self._cached_cfg = None`, which invalidates the cache. As long as the new methods use `_set_value()` (which calls `_save_config()`), this is handled correctly.

**How to avoid:** Both new methods must use the existing `_set_value()` / `_read_config()` pattern. Do not access `self._config_path` directly.

[VERIFIED: `config_store.py` line 64 — `_save_config()` sets `self._cached_cfg = None`]

---

## Code Examples

### Verified Pattern: Using ConfigStore._set_value()

```python
# Source: app/enrichment/config_store.py lines 66-72 [VERIFIED]
def _set_value(self, section: str, key: str, value: str) -> None:
    """Set a single value in the config file, creating the section if needed."""
    cfg = self._read_config()
    if section not in cfg:
        cfg[section] = {}
    cfg[section][key] = value
    self._save_config(cfg)
```

New SSH methods follow this exactly — no reimplementation needed.

### Verified Pattern: Frozen Dataclass Declaration

```python
# Source: app/enrichment/models.py lines 13-33 [VERIFIED]
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EnrichmentResult:
    ioc: IOC
    provider: str
    verdict: str
    # ... fields
```

LoginEvent follows this pattern verbatim, using `from __future__ import annotations` for forward references.

### Verified Pattern: Module-Level Logger

```python
# Source: every module in app/ [VERIFIED]
import logging
logger = logging.getLogger(__name__)

# In parser — for D-06 partial match warnings:
logger.warning("Line %d partially matched SSH pattern but failed extraction: %r", line_number, raw_line)
```

### Verified Pattern: MAX_CONTENT_LENGTH in Config

```python
# Source: app/config.py line 26 [VERIFIED — currently 512 * 1024]
MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5 MB
```

The 413 handler at `app/__init__.py` line 129 must also be updated from "512 KB" to "5 MB".

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python-dateutil.parser.parse()` for log timestamps | `datetime.strptime()` + `datetime.fromisoformat()` | Python 3.7+ | No dependency needed for the formats this phase uses |
| `pytz` for timezone handling | `datetime.timezone` (stdlib) | Python 3.2+; zoneinfo added 3.9 | BSD syslog timestamps are timezone-naive anyway; no timezone library needed |
| `ip-api.com` as GeoIP provider | `ipinfo.io` | Discovered during v1.2 research | Phase 6 makes no GeoIP calls, but Phase 7 uses ipinfo.io — no allowlist change needed |
| Separate constants for start/end hours | Single `"HH:MM-HH:MM"` range string | User decision D-08 | One INI key instead of two; familiar sysadmin format |

**Deprecated/outdated:**
- The PITFALLS.md and STACK.md research (written earlier in v1.2) refers to `ip-api.com` in some places. Per STATE.md Accumulated Context: `ipinfo.io` is authoritative. Treat any `ip-api.com` references in older research files as stale.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Generic `Accepted \<method\>` regex captures all real-world auth methods including `keyboard-interactive/pam` and `gssapi-with-mic` without requiring per-method special cases | Claude's Discretion / PARSE-01 | Low — if a method contains spaces, the `\S+` pattern would truncate it; but OpenSSH method names are single tokens in practice |
| A2 | `ParseSummary.warning_count` covers lines that partially match SSH patterns (sshd process line without complete Accepted message body) — this is a meaningful category distinct from "skipped" | Architecture Patterns / D-06 | Low — if the warning category is empty in practice, it is still correct to count zero; the field does not cause breakage |
| A3 | The `[ssh]` section in config.ini does not conflict with any existing sections (`[virustotal]`, `[providers]`, `[cache]`) | ConfigStore Extension | Very low — section name "ssh" is unique; configparser handles multiple sections cleanly |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All stdlib modules | ✓ | 3.10.12 | — |
| `re`, `datetime`, `dataclasses`, `ipaddress` | Parser + models | ✓ | stdlib | — |
| `configparser` | ConfigStore extension | ✓ | stdlib | — |
| Flask 3.1 (werkzeug) | MAX_CONTENT_LENGTH change | ✓ | 3.1.1 | — |
| pytest | Unit tests | ✓ | (installed per STACK.md) | — |

**Missing dependencies with no fallback:** None.

**Step 2.6: No new external tools needed.** This phase is purely Python stdlib + existing Flask. No new CLI utilities, databases, or services are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (configured in pyproject.toml) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_ssh_models.py tests/test_ssh_parser.py tests/test_config_store.py -x` |
| Full suite command | `pytest -m 'not e2e'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PARSE-01 | LoginEvent produced for "Accepted password" and "Accepted publickey" lines | unit | `pytest tests/test_ssh_parser.py::TestParserAccepted -x` | Wave 0 |
| PARSE-01 | ParseSummary counts match actual line counts | unit | `pytest tests/test_ssh_parser.py::TestParseSummary -x` | Wave 0 |
| PARSE-02 | BSD syslog timestamps parsed correctly | unit | `pytest tests/test_ssh_parser.py::TestTimestampBSD -x` | Wave 0 |
| PARSE-02 | RFC3339 timestamps parsed correctly | unit | `pytest tests/test_ssh_parser.py::TestTimestampRFC3339 -x` | Wave 0 |
| PARSE-02 | December→January year rollover produces correct year | unit | `pytest tests/test_ssh_parser.py::TestYearRollover -x` | Wave 0 |
| PARSE-03 | IPv4 source addresses extracted into source_ip | unit | `pytest tests/test_ssh_parser.py::TestSourceExtraction -x` | Wave 0 |
| PARSE-03 | IPv6 source addresses extracted into source_ip | unit | `pytest tests/test_ssh_parser.py::TestSourceExtraction -x` | Wave 0 |
| PARSE-04 | Hostname source (UseDNS) sets hostname field, source_ip=None | unit | `pytest tests/test_ssh_parser.py::TestSourceExtraction -x` | Wave 0 |
| PARSE-04 | source_ip and hostname are mutually exclusive (never both set) | unit | `pytest tests/test_ssh_models.py::TestLoginEventInvariant -x` | Wave 0 |
| WEB-06 | MAX_CONTENT_LENGTH is 5MB in config | unit | `pytest tests/test_routes.py -k "content_length" -x` | ❌ Wave 0 |
| CFG-01 | `get_ssh_normal_hours()` returns "06:00-22:00" when key absent | unit | `pytest tests/test_config_store.py::TestSshSection -x` | ❌ Wave 0 |
| CFG-01 | `set_ssh_normal_hours()` writes and reads back correctly | unit | `pytest tests/test_config_store.py::TestSshSection -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_ssh_models.py tests/test_ssh_parser.py tests/test_config_store.py -x`
- **Per wave merge:** `pytest -m 'not e2e'`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ssh_models.py` — covers PARSE-01 (LoginEvent), PARSE-04 (invariant), ParseSummary fields
- [ ] `tests/test_ssh_parser.py` — covers PARSE-01, PARSE-02, PARSE-03, PARSE-04 with comprehensive fixtures
- [ ] `tests/test_config_store.py` — extend with `TestSshSection` class (file exists; add new class)
- [ ] `tests/test_routes.py` or dedicated test — assert `MAX_CONTENT_LENGTH == 5 * 1024 * 1024` (file exists; add test)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a — Phase 6 has no auth endpoints |
| V3 Session Management | no | n/a — no sessions created |
| V4 Access Control | no | n/a — no access control added |
| V5 Input Validation | yes | All log content treated as untrusted; no eval/exec; max size enforced |
| V6 Cryptography | no | n/a — no crypto operations |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed log lines causing parser crash | Tampering | Wrap per-line parsing in try/except; return ParseSummary with warning_count |
| Log content containing attacker-controlled strings (usernames with `<script>`) | Tampering | raw_line stored as-is; rendering is Phase 9's responsibility (textContent enforcement); parser does not render |
| Oversized log file exhausting memory | DoS | `stream.read(5 * 1024 * 1024 + 1)` pattern: read one byte beyond limit, reject if exceeded — do not read entire stream first |
| Filename path traversal via upload | Tampering | Phase 6 does not process uploads directly (no route); WEB-06 change is config-only. Phase 9 will use in-memory stream, never `open(filename)` |
| SEC-12 regression: reducing MAX_CONTENT_LENGTH | Tampering | New value must be larger (5 MB > 512 KB); tests should assert the exact constant value |

**SEC-08 note:** Phase 6 produces no HTML output. The `raw_line` field in LoginEvent contains attacker-controlled content. The security obligation is that Phase 9 (routes/templates) must use `textContent` when rendering it. Phase 6 research should flag this in the LoginEvent docstring so Phase 9 implementers see the warning at the source.

---

## Sources

### Primary (HIGH confidence — verified by codebase inspection)

- `app/enrichment/models.py` — frozen dataclass pattern for EnrichmentResult/EnrichmentError
- `app/enrichment/config_store.py` — `_set_value()`, `_read_config()`, existing section constants
- `app/__init__.py` — MAX_CONTENT_LENGTH usage, 413 handler text (line 129)
- `app/config.py` — MAX_CONTENT_LENGTH constant (line 26: `512 * 1024`)
- `app/pipeline/models.py` — IOC frozen dataclass pattern, `from __future__ import annotations` usage
- `tests/test_config_store.py` — existing test structure, tmp_path isolation pattern
- `pyproject.toml` — pytest configuration, testpaths, ruff rules

### Secondary (HIGH confidence — prior project research)

- `.planning/research/STACK.md` — stdlib module availability verified, datetime patterns, no new pip deps conclusion
- `.planning/research/PITFALLS.md` — Pitfall 1 (year rollover algorithm), Pitfall 3 (format variants), Pitfall 8 (MAX_CONTENT_LENGTH)
- `.planning/codebase/ARCHITECTURE.md` — layered package structure, frozen dataclass conventions
- `.planning/codebase/CONVENTIONS.md` — naming patterns, import order, docstring requirements

### Tertiary (ASSUMED — training knowledge)

- OpenSSH log message format for "Accepted" lines (method names: password, publickey, keyboard-interactive/pam, gssapi-with-mic) — consistent with PITFALLS.md research but not verified against a live log file in this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib; verified Python 3.10.12 has every module needed
- Architecture: HIGH — LoginEvent shape and module structure are fully locked by CONTEXT.md decisions
- Pitfalls: HIGH — year rollover algorithm verified in prior research; others are based on codebase inspection
- Regex patterns: MEDIUM — patterns follow PITFALLS.md research but not run against a live auth.log in this session

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stdlib domain; prior to Phase 7 GeoIP work which adds new concerns)
