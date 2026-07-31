"""SSH auth.log parser.

Converts raw auth.log content into structured LoginEvent records and a
ParseSummary. This is the core deliverable of Phase 6 — downstream phases
(Phase 7 GeoIP, Phase 8 detector, Phase 9 routes) all consume the output.

Supported log formats:
- BSD syslog:  "Jan 15 14:30:00 hostname sshd[PID]: Accepted <method> ..."
- RFC 3339:    "2024-01-15T14:30:00+00:00 hostname sshd[PID]: Accepted <method> ..."

Year inference:
  BSD timestamps carry no year. This parser infers the year from the ``now``
  parameter (defaults to ``datetime.now()``). December entries are rolled back
  one year when the file is analyzed in January (year-rollover heuristic).

Security notes:
- T-06-06: All regexes are anchored (^) with non-greedy word groups. No nested
  quantifiers — no catastrophic backtracking possible. Patterns compiled once.
- T-06-07: LoginEvent.raw_line, .username, and .hostname contain
  attacker-controlled content. Downstream renderers (Phase 9) MUST use
  createElement + textContent, never innerHTML (SEC-08).
- T-06-08: Large files are processed line-by-line. MAX_CONTENT_LENGTH (5 MB,
  Plan 02) bounds input size before this parser is invoked.
- T-06-09: Bytes streams are decoded with errors='replace' to prevent
  UnicodeDecodeError from malformed log content.
"""
from __future__ import annotations

import ipaddress
import logging
import re
from datetime import datetime, timedelta
from functools import lru_cache
from types import MappingProxyType
from typing import IO

from . import line_streams
from .models import LoginEvent, ParseSummary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compiled regex patterns — module-level for performance
# ---------------------------------------------------------------------------

# BSD syslog full-line match.
# Matches:  "Jan 15 14:30:00 hostname sshd[1234]: Accepted password for user from source port N"
# Groups:   month, day, time, method, user, source
_BSD_ACCEPTED_RE = re.compile(
    r'^(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'\S+\s+sshd\[\d+\]:\s+Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+'
    r'from\s+(?P<source>\S+)\s+port\s+\d+'
)

# RFC 3339 full-line match.
# Matches an RFC 3339 sshd "Accepted" line with source host and port.
# Groups:   ts, method, user, source
_RFC3339_ACCEPTED_RE = re.compile(
    r'^(?P<ts>\S+)\s+\S+\s+sshd\[\d+\]:\s+Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+'
    r'from\s+(?P<source>\S+)\s+port\s+\d+'
)

# Partial-match sentinel: sshd lines that contain "Accepted " but failed full
# extraction. Triggers a logger.warning with line number and content (D-06).
_PARTIAL_SSH_RE = re.compile(r'sshd\[\d+\]:\s+Accepted\s+')

_BSD_MONTHS = MappingProxyType({
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4096)
def _classify_source(source: str) -> tuple[str | None, str | None]:
    """Classify a source string as IP address or hostname.

    Args:
        source: The token after "from" in the log line.

    Returns:
        Tuple of (source_ip, hostname). Exactly one element is non-None.

    Security note: This function does not validate or sanitise the value.
    It is the caller's responsibility to store the result only in a frozen
    LoginEvent and to render it with textContent (SEC-08).
    """
    try:
        ipaddress.ip_address(source)
        return source, None
    except ValueError:
        return None, source


def _parse_bsd_timestamp(month: str, day: str, time_str: str, now: datetime) -> datetime:
    """Parse a BSD syslog timestamp and infer the year from *now*.

    Year-rollover heuristic: If the inferred datetime is more than 24 hours in
    the future relative to *now*, assume the log entry is from the previous
    calendar year (e.g. a December entry viewed in January).

    Args:
        month:    Three-letter month abbreviation, e.g. "Jan", "Dec".
        day:      Day of month as a string, e.g. "5" or "15".
        time_str: Time as "HH:MM:SS".
        now:      Reference timestamp for year inference (typically datetime.now()).

    Returns:
        A naive datetime with year inferred from *now*.
    """
    dt = datetime(
        now.year,
        _BSD_MONTHS[month],
        int(day),
        int(time_str[0:2]),
        int(time_str[3:5]),
        int(time_str[6:8]),
    )
    if dt > now + timedelta(hours=24):
        dt = dt.replace(year=now.year - 1)
    return dt


def _append_login_event(
    events: list[LoginEvent],
    *,
    user: str,
    source: str,
    timestamp: datetime,
    auth_method: str,
    line_number: int,
    raw_line: str,
) -> None:
    source_ip, hostname = _classify_source(source)
    events.append(LoginEvent(
        username=user,
        source_ip=source_ip,
        hostname=hostname,
        timestamp=timestamp,
        auth_method=auth_method,
        line_number=line_number,
        raw_line=raw_line,
    ))


def _warn_partial_match(line_number: int, line: str, reason: str) -> None:
    logger.warning(
        "Line %d partially matched SSH pattern but failed %s: %r",
        line_number,
        reason,
        line,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def parse_auth_log(
    stream: IO[bytes] | IO[str],
    *,
    now: datetime | None = None,
) -> tuple[list[LoginEvent], ParseSummary]:
    """Parse an auth.log file stream into LoginEvent records.

    Processes each line exactly once. BSD syslog format is tried first, then
    RFC 3339. Lines that contain "sshd[N]: Accepted " but fail full extraction
    generate a logger.warning (D-06). All other unrecognised lines are silently
    counted in skipped_count (D-07).

    Args:
        stream: File-like object (bytes or text). BytesIO or StringIO in tests,
                open file handles in production.
        now:    Reference timestamp for BSD year inference.
                Defaults to datetime.now() when None.

    Returns:
        Tuple of (events, summary) where summary satisfies the invariant:
        parsed_count + skipped_count + warning_count == total_lines.
    """
    if now is None:
        now = datetime.now()

    events: list[LoginEvent] = []
    parsed_count = 0
    skipped_count = 0
    warning_count = 0
    total_lines = 0

    for line_number, raw_line in enumerate(line_streams.iter_lines(stream), start=1):
        total_lines += 1
        line = line_streams.strip_line_ending(raw_line)

        # -- BSD syslog format -----------------------------------------------
        bsd_match = _BSD_ACCEPTED_RE.match(line)
        if bsd_match:
            month = bsd_match.group("month")
            day = bsd_match.group("day")
            time_str = bsd_match.group("time")
            method = bsd_match.group("method")
            user = bsd_match.group("user")
            source = bsd_match.group("source")
            ts = _parse_bsd_timestamp(month, day, time_str, now)
            _append_login_event(
                events,
                user=user,
                source=source,
                timestamp=ts,
                auth_method=method,
                line_number=line_number,
                raw_line=line,
            )
            parsed_count += 1
            continue

        # -- RFC 3339 format -------------------------------------------------
        rfc_match = _RFC3339_ACCEPTED_RE.match(line)
        if rfc_match:
            ts_str = rfc_match.group("ts")
            method = rfc_match.group("method")
            user = rfc_match.group("user")
            source = rfc_match.group("source")
            try:
                ts = datetime.fromisoformat(ts_str)
            except ValueError:
                # Malformed RFC 3339 timestamp — treat as partial match
                _warn_partial_match(line_number, line, "timestamp extraction")
                warning_count += 1
                continue
            _append_login_event(
                events,
                user=user,
                source=source,
                timestamp=ts,
                auth_method=method,
                line_number=line_number,
                raw_line=line,
            )
            parsed_count += 1
            continue

        # -- Partial-match sentinel (D-06) ------------------------------------
        if _PARTIAL_SSH_RE.search(line):
            _warn_partial_match(line_number, line, "extraction")
            warning_count += 1
            continue

        # -- Unrecognised line (D-07) -----------------------------------------
        skipped_count += 1

    return events, ParseSummary(
        total_lines=total_lines,
        parsed_count=parsed_count,
        skipped_count=skipped_count,
        warning_count=warning_count,
    )
