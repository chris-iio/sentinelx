"""SSH login event data models.

Provides immutable data structures for parsed SSH login events.
All models are frozen dataclasses matching the project convention
(see app/enrichment/models.py).

Security note: raw_line contains attacker-controlled content from log files.
Downstream renderers (Phase 9) MUST use createElement + textContent,
never innerHTML, when displaying raw_line values (SEC-08).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LoginEvent:
    """An immutable record of a successful SSH login event.

    Parsed from a single line in /var/log/auth.log matching the pattern
    "Accepted <method> for <user> from <host> port <n> ssh2".

    D-02 invariant: Exactly one of source_ip and hostname is non-None per
    event. When hostname is present (UseDNS enabled on the server), the
    source_ip field is None and downstream GeoIP lookup should be skipped
    for that event. The parser (app/ssh/parser.py) is responsible for
    enforcing this invariant — the model itself does not validate it.

    Attributes:
        username:    The authenticated username.
        source_ip:   IPv4 or IPv6 address string, or None when hostname is set.
        hostname:    Resolved hostname when UseDNS is enabled, or None.
        timestamp:   Parsed datetime of the login event.
        auth_method: Authentication method string (e.g. "password",
                     "publickey", "keyboard-interactive/pam"). Stored as-is
                     to support future detection rules such as flagging
                     password auth from external IPs (D-03).
        line_number: 1-based line number in the source file for traceability
                     back to the original log (D-04).
        raw_line:    Original unparsed log line for full traceability (D-04).
                     Contains attacker-controlled content — see module
                     Security note above.
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
    """Immutable summary of a completed auth.log parse run.

    Provides analyst-facing feedback on parse quality (D-05).
    Example display: "Parsed 847 of 12,304 lines (45 warnings)".

    Invariant: parsed_count + skipped_count + warning_count == total_lines

    Attributes:
        total_lines:   Total lines read from the log file.
        parsed_count:  Lines that produced a LoginEvent successfully.
        skipped_count: Lines that were silently ignored (blank lines,
                       non-SSH syslog entries, etc.) per D-07.
        warning_count: Lines that partially matched SSH event patterns
                       but failed to fully parse (logged at WARNING level
                       per D-06).
    """

    total_lines: int
    parsed_count: int
    skipped_count: int
    warning_count: int
