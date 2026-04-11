"""Comprehensive tests for app/ssh/parser.py.

Tests parse_auth_log() covering:
- BSD syslog and RFC3339 timestamp formats (PARSE-01, PARSE-02)
- Year rollover for December-to-January transitions (PARSE-02 critical)
- IPv4, IPv6, and hostname source classification (PARSE-03, PARSE-04)
- ParseSummary invariant: parsed_count + skipped_count + warning_count == total_lines
- Partial-match warnings (D-06) and silent skipping of unrecognized lines (D-07)
- BytesIO and StringIO stream types
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

import pytest

from app.ssh.parser import parse_auth_log


# ---------------------------------------------------------------------------
# Helper to build test streams
# ---------------------------------------------------------------------------


def _str_stream(text: str) -> io.StringIO:
    return io.StringIO(text)


def _bytes_stream(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# TestParserAccepted (PARSE-01)
# ---------------------------------------------------------------------------


class TestParserAccepted:
    """Tests for correct extraction of LoginEvent from Accepted lines."""

    def test_bsd_accepted_password(self) -> None:
        """BSD 'Accepted password' line produces a LoginEvent with expected fields."""
        line = "Jan 15 14:30:00 server sshd[1234]: Accepted password for alice from 1.2.3.4 port 54321 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15, 14, 30, 0))
        assert len(events) == 1
        ev = events[0]
        assert ev.username == "alice"
        assert ev.source_ip == "1.2.3.4"
        assert ev.hostname is None
        assert ev.auth_method == "password"
        assert ev.line_number == 1
        assert ev.raw_line == line

    def test_bsd_accepted_publickey(self) -> None:
        """BSD 'Accepted publickey' line produces a LoginEvent with correct fields."""
        line = "Jan 20 08:00:00 server sshd[5678]: Accepted publickey for bob from 10.0.0.1 port 22222 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 20, 8, 0, 0))
        assert len(events) == 1
        ev = events[0]
        assert ev.username == "bob"
        assert ev.source_ip == "10.0.0.1"
        assert ev.auth_method == "publickey"

    def test_rfc3339_accepted_password(self) -> None:
        """RFC3339 'Accepted password' line produces a timezone-aware LoginEvent."""
        line = "2024-01-15T14:23:45+00:00 server sshd[100]: Accepted password for carol from 192.168.1.1 port 11111 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"))
        assert len(events) == 1
        ev = events[0]
        assert ev.username == "carol"
        assert ev.source_ip == "192.168.1.1"
        assert ev.auth_method == "password"
        # Timestamp must be timezone-aware
        assert ev.timestamp.tzinfo is not None
        assert ev.timestamp.year == 2024
        assert ev.timestamp.month == 1
        assert ev.timestamp.day == 15
        assert ev.timestamp.hour == 14
        assert ev.timestamp.minute == 23
        assert ev.timestamp.second == 45

    def test_bsd_keyboard_interactive(self) -> None:
        """'Accepted keyboard-interactive/pam' line stores full method string."""
        line = "Mar 10 12:00:00 server sshd[9999]: Accepted keyboard-interactive/pam for dave from 10.1.1.1 port 33333 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 3, 10, 12, 0, 0))
        assert len(events) == 1
        ev = events[0]
        assert ev.auth_method == "keyboard-interactive/pam"
        assert ev.username == "dave"

    def test_empty_stream(self) -> None:
        """Empty stream returns empty list and all-zero ParseSummary."""
        events, summary = parse_auth_log(_str_stream(""))
        assert events == []
        assert summary.total_lines == 0
        assert summary.parsed_count == 0
        assert summary.skipped_count == 0
        assert summary.warning_count == 0

    def test_multi_line_stream(self) -> None:
        """Multi-line stream with 3 accepted lines among 10 total returns 3 events."""
        accepted1 = "Jan 15 09:00:00 server sshd[1]: Accepted password for u1 from 1.1.1.1 port 1 ssh2"
        accepted2 = "Jan 15 10:00:00 server sshd[2]: Accepted publickey for u2 from 2.2.2.2 port 2 ssh2"
        accepted3 = "Jan 15 11:00:00 server sshd[3]: Accepted password for u3 from 3.3.3.3 port 3 ssh2"
        non_ssh = [
            "Jan 15 09:01:00 server CRON[100]: some cron job",
            "Jan 15 09:02:00 server systemd[1]: Started service",
            "Jan 15 09:03:00 server kernel: some kernel message",
            "",
            "Jan 15 09:05:00 server sudo[200]: user : TTY=pts/0",
            "Jan 15 09:06:00 server sshd[10]: Failed password for root from 9.9.9.9 port 9 ssh2",
            "Jan 15 09:07:00 server sshd[11]: Connection closed",
        ]
        all_lines = [accepted1, non_ssh[0], non_ssh[1], accepted2,
                     non_ssh[2], non_ssh[3], non_ssh[4], accepted3,
                     non_ssh[5], non_ssh[6]]
        text = "\n".join(all_lines) + "\n"
        events, summary = parse_auth_log(_str_stream(text),
                                         now=datetime(2025, 1, 15, 12, 0, 0))
        assert len(events) == 3
        assert summary.parsed_count == 3
        assert summary.total_lines == 10


# ---------------------------------------------------------------------------
# TestParseSummary (PARSE-01)
# ---------------------------------------------------------------------------


class TestParseSummary:
    """Tests for ParseSummary correctness."""

    def test_invariant_mixed_fixture(self) -> None:
        """Invariant: parsed + skipped + warnings == total for mixed content."""
        text = "\n".join([
            "Jan 15 09:00:00 server sshd[1]: Accepted password for u1 from 1.1.1.1 port 1 ssh2",
            "CRON: some job",
            "",
            "garbage line here",
            "Jan 15 10:00:00 server sshd[2]: Accepted publickey for u2 from 2.2.2.2 port 2 ssh2",
        ]) + "\n"
        events, summary = parse_auth_log(_str_stream(text),
                                         now=datetime(2025, 1, 15, 12, 0, 0))
        assert summary.parsed_count + summary.skipped_count + summary.warning_count == summary.total_lines

    def test_only_non_ssh_lines(self) -> None:
        """File with only non-SSH lines: parsed_count=0, all lines in skipped_count."""
        text = "\n".join([
            "Jan 15 09:00:00 server CRON[1]: something",
            "Jan 15 09:01:00 server kernel: boot",
            "Jan 15 09:02:00 server systemd[1]: Service started",
        ]) + "\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert len(events) == 0
        assert summary.parsed_count == 0
        assert summary.skipped_count == 3
        assert summary.total_lines == 3

    def test_blank_lines_counted_in_skipped(self) -> None:
        """Blank lines are counted in skipped_count."""
        text = "\n\n\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert summary.skipped_count == 3
        assert summary.parsed_count == 0
        assert summary.total_lines == 3


# ---------------------------------------------------------------------------
# TestTimestampBSD (PARSE-02)
# ---------------------------------------------------------------------------


class TestTimestampBSD:
    """Tests for BSD syslog timestamp parsing."""

    def test_single_digit_day_with_double_space(self) -> None:
        """'Jan  5 03:22:11' (double space before day) parses correctly."""
        line = "Jan  5 03:22:11 server sshd[1]: Accepted password for alice from 1.2.3.4 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 10, 12, 0, 0))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.month == 1
        assert ev.timestamp.day == 5
        assert ev.timestamp.hour == 3
        assert ev.timestamp.minute == 22
        assert ev.timestamp.second == 11

    def test_dec_31_timestamp(self) -> None:
        """'Dec 31 23:59:59' parses with correct month, day, and time."""
        line = "Dec 31 23:59:59 server sshd[1]: Accepted password for alice from 1.2.3.4 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 12, 31, 23, 59, 59))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.month == 12
        assert ev.timestamp.day == 31
        assert ev.timestamp.hour == 23
        assert ev.timestamp.minute == 59
        assert ev.timestamp.second == 59

    def test_feb_28_timestamp(self) -> None:
        """'Feb 28 12:00:00' parses to datetime with month=2, day=28."""
        line = "Feb 28 12:00:00 server sshd[1]: Accepted publickey for bob from 10.0.0.1 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 2, 28, 12, 0, 0))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.month == 2
        assert ev.timestamp.day == 28
        assert ev.timestamp.hour == 12


# ---------------------------------------------------------------------------
# TestTimestampRFC3339 (PARSE-02)
# ---------------------------------------------------------------------------


class TestTimestampRFC3339:
    """Tests for RFC3339 timestamp parsing."""

    def test_utc_offset(self) -> None:
        """RFC3339 with +00:00 offset produces timezone-aware datetime."""
        line = "2024-01-15T14:23:45+00:00 server sshd[1]: Accepted password for alice from 1.1.1.1 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.tzinfo is not None
        assert ev.timestamp.year == 2024
        assert ev.timestamp.month == 1
        assert ev.timestamp.day == 15
        assert ev.timestamp.hour == 14
        assert ev.timestamp.minute == 23
        assert ev.timestamp.second == 45

    def test_z_suffix_utc(self) -> None:
        """RFC3339 with Z suffix (Python 3.11+) or equivalent parses to UTC datetime."""
        # Python 3.11+ fromisoformat handles 'Z', but we test the format produced
        # by systemd (which uses +00:00). Use +00:00 for Python 3.10 compat.
        line = "2024-06-30T08:15:30+00:00 server sshd[1]: Accepted publickey for bob from 2.2.2.2 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.year == 2024
        assert ev.timestamp.month == 6
        assert ev.timestamp.day == 30
        assert ev.timestamp.hour == 8
        assert ev.timestamp.minute == 15
        assert ev.timestamp.second == 30

    def test_with_microseconds_and_offset(self) -> None:
        """RFC3339 with microseconds and non-UTC offset parses correctly."""
        line = "2024-01-15T14:23:45.123456+05:30 server sshd[1]: Accepted password for carol from 3.3.3.3 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"))
        assert len(events) == 1
        ev = events[0]
        assert ev.timestamp.microsecond == 123456
        assert ev.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# TestYearRollover (PARSE-02 — CRITICAL)
# ---------------------------------------------------------------------------


class TestYearRollover:
    """Tests for BSD year-inference year-rollover handling."""

    def test_dec_jan_rollover(self) -> None:
        """Dec entries get previous year when analyzed in January."""
        lines = [
            # December entries (should get year 2024)
            "Dec 29 10:00:00 server sshd[1]: Accepted password for u1 from 1.1.1.1 port 22 ssh2",
            "Dec 30 10:00:00 server sshd[2]: Accepted password for u2 from 1.1.1.2 port 22 ssh2",
            "Dec 31 10:00:00 server sshd[3]: Accepted password for u3 from 1.1.1.3 port 22 ssh2",
            # January entries (should get year 2025)
            "Jan  1 10:00:00 server sshd[4]: Accepted password for u4 from 1.1.1.4 port 22 ssh2",
            "Jan  2 10:00:00 server sshd[5]: Accepted password for u5 from 1.1.1.5 port 22 ssh2",
        ]
        text = "\n".join(lines) + "\n"
        events, summary = parse_auth_log(_str_stream(text),
                                         now=datetime(2025, 1, 5, 12, 0, 0))
        assert len(events) == 5
        # Dec entries
        assert events[0].timestamp.year == 2024  # Dec 29
        assert events[1].timestamp.year == 2024  # Dec 30
        assert events[2].timestamp.year == 2024  # Dec 31
        # Jan entries
        assert events[3].timestamp.year == 2025  # Jan 1
        assert events[4].timestamp.year == 2025  # Jan 2

    def test_all_january_no_false_rollover(self) -> None:
        """All January lines analyzed in January get current year (no false rollover)."""
        lines = [
            "Jan 10 10:00:00 server sshd[1]: Accepted password for u1 from 1.1.1.1 port 22 ssh2",
            "Jan 15 10:00:00 server sshd[2]: Accepted password for u2 from 1.1.1.2 port 22 ssh2",
            "Jan 20 10:00:00 server sshd[3]: Accepted password for u3 from 1.1.1.3 port 22 ssh2",
        ]
        text = "\n".join(lines) + "\n"
        events, summary = parse_auth_log(_str_stream(text),
                                         now=datetime(2025, 1, 25, 12, 0, 0))
        assert all(ev.timestamp.year == 2025 for ev in events)

    def test_all_december_no_rollover_needed(self) -> None:
        """All December lines analyzed in December get current year."""
        lines = [
            "Dec 10 10:00:00 server sshd[1]: Accepted password for u1 from 1.1.1.1 port 22 ssh2",
            "Dec 20 10:00:00 server sshd[2]: Accepted password for u2 from 1.1.1.2 port 22 ssh2",
        ]
        text = "\n".join(lines) + "\n"
        events, summary = parse_auth_log(_str_stream(text),
                                         now=datetime(2025, 12, 25, 12, 0, 0))
        assert all(ev.timestamp.year == 2025 for ev in events)


# ---------------------------------------------------------------------------
# TestSourceExtraction (PARSE-03, PARSE-04)
# ---------------------------------------------------------------------------


class TestSourceExtraction:
    """Tests for IPv4, IPv6, and hostname source classification."""

    def test_ipv4_source(self) -> None:
        """'from 192.168.1.1' → source_ip='192.168.1.1', hostname=None."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted password for u1 from 192.168.1.1 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip == "192.168.1.1"
        assert ev.hostname is None

    def test_ipv6_full_address(self) -> None:
        """'from 2001:db8::1' → source_ip='2001:db8::1', hostname=None."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted password for u1 from 2001:db8::1 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip == "2001:db8::1"
        assert ev.hostname is None

    def test_ipv6_mapped_ipv4(self) -> None:
        """'from ::ffff:192.0.2.1' → stored as source_ip, hostname=None."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted password for u1 from ::ffff:192.0.2.1 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip == "::ffff:192.0.2.1"
        assert ev.hostname is None

    def test_fqdn_hostname(self) -> None:
        """'from vpn.corp.example.com' → source_ip=None, hostname='vpn.corp.example.com'."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted publickey for bob from vpn.corp.example.com port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip is None
        assert ev.hostname == "vpn.corp.example.com"

    def test_single_label_hostname(self) -> None:
        """'from server01' → source_ip=None, hostname='server01'."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted publickey for bob from server01 port 22 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip is None
        assert ev.hostname == "server01"


# ---------------------------------------------------------------------------
# TestPartialMatch (D-06)
# ---------------------------------------------------------------------------


class TestPartialMatch:
    """Tests for partial-match warning behaviour (D-06)."""

    def test_sshd_line_without_accepted_is_skipped(self) -> None:
        """sshd line without 'Accepted' keyword goes to skipped_count, not warned."""
        line = "Jan 15 09:01:00 server sshd[1234]: Failed password for root from 9.9.9.9 port 9 ssh2"
        events, summary = parse_auth_log(_str_stream(line + "\n"),
                                         now=datetime(2025, 1, 15))
        assert summary.skipped_count == 1
        assert summary.warning_count == 0

    def test_partial_accepted_generates_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Line with 'Accepted <method>' but malformed source field generates warning."""
        # This line has 'Accepted password' but no valid 'from <source> port <n>'
        malformed = "Jan 15 09:00:00 server sshd[1234]: Accepted password MALFORMED_NO_FROM_CLAUSE"
        with caplog.at_level(logging.WARNING, logger="app.ssh.parser"):
            events, summary = parse_auth_log(_str_stream(malformed + "\n"),
                                             now=datetime(2025, 1, 15))
        assert summary.warning_count == 1
        assert summary.parsed_count == 0
        assert any("partially matched" in rec.message.lower() or "1" in rec.message
                   for rec in caplog.records)


# ---------------------------------------------------------------------------
# TestSkippedLines (D-07)
# ---------------------------------------------------------------------------


class TestSkippedLines:
    """Tests for silent skipping of unrecognized lines (D-07)."""

    def test_blank_lines_skipped(self) -> None:
        """Blank lines increment skipped_count."""
        text = "\n\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert summary.skipped_count == 2
        assert summary.parsed_count == 0

    def test_cron_lines_skipped(self) -> None:
        """Non-SSH syslog lines (CRON) are skipped silently."""
        text = "Jan 15 09:00:00 server CRON[100]: some cron job\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert summary.skipped_count == 1

    def test_systemd_lines_skipped(self) -> None:
        """systemd syslog lines are skipped silently."""
        text = "Jan 15 09:00:00 server systemd[1]: Started service unit\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert summary.skipped_count == 1

    def test_comment_garbage_skipped(self) -> None:
        """Comment-like or garbage lines are skipped silently."""
        text = "# this is a comment\n garbage line here\n"
        events, summary = parse_auth_log(_str_stream(text))
        assert summary.skipped_count == 2
        assert summary.parsed_count == 0


# ---------------------------------------------------------------------------
# TestStreamTypes
# ---------------------------------------------------------------------------


class TestStreamTypes:
    """Tests for BytesIO and StringIO stream handling."""

    def test_bytes_io_input(self) -> None:
        """BytesIO (UTF-8 encoded) input is parsed correctly."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted password for alice from 1.2.3.4 port 22 ssh2"
        stream = _bytes_stream(line + "\n")
        events, summary = parse_auth_log(stream, now=datetime(2025, 1, 15))
        assert len(events) == 1
        ev = events[0]
        assert ev.username == "alice"
        assert ev.source_ip == "1.2.3.4"

    def test_string_io_input(self) -> None:
        """StringIO input is parsed correctly."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted publickey for bob from 10.0.0.1 port 22 ssh2"
        stream = _str_stream(line + "\n")
        events, summary = parse_auth_log(stream, now=datetime(2025, 1, 15))
        assert len(events) == 1
        ev = events[0]
        assert ev.username == "bob"
        assert ev.source_ip == "10.0.0.1"

    def test_bytes_io_malformed_utf8_does_not_crash(self) -> None:
        """Malformed UTF-8 bytes are decoded with errors='replace', not raised."""
        # Non-SSH content with a bad byte sequence — should just be skipped
        bad_bytes = b"Jan 15 10:00:00 server CRON: \xff\xfe garbage\n"
        stream = io.BytesIO(bad_bytes)
        events, summary = parse_auth_log(stream, now=datetime(2025, 1, 15))
        # No crash — malformed bytes replaced, line skipped
        assert summary.total_lines == 1
        assert summary.parsed_count == 0


# ---------------------------------------------------------------------------
# TestD02Invariant — parser-level enforcement
# ---------------------------------------------------------------------------


class TestD02Invariant:
    """Parser enforces D-02: exactly one of source_ip / hostname is non-None."""

    def test_ip_source_gives_none_hostname(self) -> None:
        """When source is an IP, hostname is None."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted password for u from 10.0.0.1 port 22 ssh2"
        events, _ = parse_auth_log(_str_stream(line + "\n"), now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip is not None
        assert ev.hostname is None

    def test_hostname_source_gives_none_ip(self) -> None:
        """When source is a hostname, source_ip is None."""
        line = "Jan 15 10:00:00 server sshd[1]: Accepted publickey for u from jump.example.com port 22 ssh2"
        events, _ = parse_auth_log(_str_stream(line + "\n"), now=datetime(2025, 1, 15))
        ev = events[0]
        assert ev.source_ip is None
        assert ev.hostname is not None
