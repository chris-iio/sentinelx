"""Unit tests for SSH login event data models.

Tests LoginEvent and ParseSummary frozen dataclasses defined in
app/ssh/models.py. Covers:

- Construction with valid field combinations
- Immutability enforcement (FrozenInstanceError on mutation)
- Equality semantics from frozen dataclass
- Field type and value accessibility
- D-02 invariant documentation (source_ip / hostname mutual exclusivity)
- IPv6 address storage
- Auth method variety (password, publickey, keyboard-interactive/pam)
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.ssh.models import LoginEvent, ParseSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TIMESTAMP = datetime(2025, 1, 15, 14, 30, 0)

RAW_LINE_IP = (
    "Jan 15 14:30:00 server sshd[1234]: Accepted password for alice "
    "from 1.2.3.4 port 54321 ssh2"
)

RAW_LINE_HOST = (
    "Jan 15 14:30:00 server sshd[1234]: Accepted publickey for bob "
    "from vpn.corp.example.com port 54321 ssh2"
)


# ---------------------------------------------------------------------------
# LoginEvent
# ---------------------------------------------------------------------------


class TestLoginEvent:
    """Tests for the LoginEvent frozen dataclass."""

    def test_instantiation_with_source_ip(self) -> None:
        """LoginEvent can be instantiated with source_ip set and hostname=None."""
        event = LoginEvent(
            username="alice",
            source_ip="1.2.3.4",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=42,
            raw_line=RAW_LINE_IP,
        )
        assert event.username == "alice"
        assert event.source_ip == "1.2.3.4"
        assert event.hostname is None
        assert event.timestamp == TIMESTAMP
        assert event.auth_method == "password"
        assert event.line_number == 42
        assert event.raw_line == RAW_LINE_IP

    def test_instantiation_with_hostname(self) -> None:
        """LoginEvent can be instantiated with hostname set and source_ip=None."""
        event = LoginEvent(
            username="bob",
            source_ip=None,
            hostname="vpn.corp.example.com",
            timestamp=TIMESTAMP,
            auth_method="publickey",
            line_number=100,
            raw_line=RAW_LINE_HOST,
        )
        assert event.username == "bob"
        assert event.source_ip is None
        assert event.hostname == "vpn.corp.example.com"
        assert event.auth_method == "publickey"
        assert event.line_number == 100

    def test_ipv6_source_ip(self) -> None:
        """LoginEvent accepts IPv6 addresses in source_ip (stored as plain string)."""
        event = LoginEvent(
            username="carol",
            source_ip="2001:db8::1",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="publickey",
            line_number=200,
            raw_line="raw",
        )
        assert event.source_ip == "2001:db8::1"

    def test_keyboard_interactive_auth_method(self) -> None:
        """LoginEvent accepts keyboard-interactive/pam as auth_method value."""
        event = LoginEvent(
            username="dave",
            source_ip="10.0.0.1",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="keyboard-interactive/pam",
            line_number=300,
            raw_line="raw",
        )
        assert event.auth_method == "keyboard-interactive/pam"

    def test_frozen_enforcement(self) -> None:
        """Assigning to any LoginEvent field raises FrozenInstanceError."""
        event = LoginEvent(
            username="mallory",
            source_ip="1.2.3.4",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=1,
            raw_line="raw",
        )
        with pytest.raises(FrozenInstanceError):
            event.username = "eve"  # type: ignore[misc]

    def test_equality_of_identical_instances(self) -> None:
        """Two LoginEvent instances with identical fields compare equal."""
        kwargs = dict(
            username="alice",
            source_ip="1.2.3.4",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=42,
            raw_line=RAW_LINE_IP,
        )
        assert LoginEvent(**kwargs) == LoginEvent(**kwargs)

    def test_all_fields_accessible(self) -> None:
        """All 7 LoginEvent fields are accessible after construction."""
        event = LoginEvent(
            username="alice",
            source_ip="1.2.3.4",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=42,
            raw_line=RAW_LINE_IP,
        )
        # Verify types match D-01 spec
        assert isinstance(event.username, str)
        assert isinstance(event.source_ip, str)  # non-None case
        assert event.hostname is None             # None case
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.auth_method, str)
        assert isinstance(event.line_number, int)
        assert isinstance(event.raw_line, str)

    def test_source_ip_none_type(self) -> None:
        """source_ip field is str | None — None is a valid value."""
        event = LoginEvent(
            username="bob",
            source_ip=None,
            hostname="host.example.com",
            timestamp=TIMESTAMP,
            auth_method="publickey",
            line_number=1,
            raw_line="raw",
        )
        assert event.source_ip is None
        assert isinstance(event.hostname, str)

    def test_hostname_none_type(self) -> None:
        """hostname field is str | None — None is a valid value."""
        event = LoginEvent(
            username="alice",
            source_ip="10.0.0.1",
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=1,
            raw_line="raw",
        )
        assert event.hostname is None


# ---------------------------------------------------------------------------
# ParseSummary
# ---------------------------------------------------------------------------


class TestParseSummary:
    """Tests for the ParseSummary frozen dataclass."""

    def test_instantiation(self) -> None:
        """ParseSummary can be instantiated with all 4 integer counter fields."""
        summary = ParseSummary(
            total_lines=100,
            parsed_count=50,
            skipped_count=45,
            warning_count=5,
        )
        assert summary.total_lines == 100
        assert summary.parsed_count == 50
        assert summary.skipped_count == 45
        assert summary.warning_count == 5

    def test_frozen_enforcement(self) -> None:
        """Assigning to any ParseSummary field raises FrozenInstanceError."""
        summary = ParseSummary(
            total_lines=100,
            parsed_count=50,
            skipped_count=45,
            warning_count=5,
        )
        with pytest.raises(FrozenInstanceError):
            summary.total_lines = 999  # type: ignore[misc]

    def test_invariant_parsed_plus_skipped_plus_warnings_equals_total(self) -> None:
        """Canonical invariant: parsed_count + skipped_count + warning_count == total_lines."""
        summary = ParseSummary(
            total_lines=100,
            parsed_count=50,
            skipped_count=45,
            warning_count=5,
        )
        assert summary.parsed_count + summary.skipped_count + summary.warning_count == summary.total_lines

    def test_all_zero_counts(self) -> None:
        """ParseSummary accepts all-zero counters (empty file edge case)."""
        summary = ParseSummary(
            total_lines=0,
            parsed_count=0,
            skipped_count=0,
            warning_count=0,
        )
        assert summary.total_lines == 0


# ---------------------------------------------------------------------------
# D-02 Invariant Documentation
# ---------------------------------------------------------------------------


class TestLoginEventInvariant:
    """Documents the D-02 mutual exclusivity invariant for source_ip / hostname.

    This invariant is a PARSER responsibility, not model-level enforcement.
    The LoginEvent model allows both fields to be None or both to be set
    (it is a plain frozen dataclass). The parser (app/ssh/parser.py, Phase 6
    Plan 02) MUST ensure exactly one is non-None per emitted LoginEvent.

    This test class documents the invariant via assertions that demonstrate
    model permissiveness — a downstream contract test in the parser test suite
    will enforce the stricter parser-level guarantee.
    """

    def test_model_permits_both_none(self) -> None:
        """Model does NOT enforce D-02 — both source_ip and hostname may be None.

        This is intentional: LoginEvent is a data container, not a validator.
        The parser is responsible for guaranteeing exactly-one invariant.
        """
        # The model itself does not raise even when both are None
        event = LoginEvent(
            username="test",
            source_ip=None,
            hostname=None,
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=1,
            raw_line="raw",
        )
        # Both are None — parser must never produce this in practice
        assert event.source_ip is None
        assert event.hostname is None

    def test_model_permits_both_set(self) -> None:
        """Model does NOT enforce D-02 — both source_ip and hostname may be set.

        Again, this is parser responsibility, not model enforcement.
        """
        event = LoginEvent(
            username="test",
            source_ip="1.2.3.4",
            hostname="host.example.com",
            timestamp=TIMESTAMP,
            auth_method="password",
            line_number=1,
            raw_line="raw",
        )
        # Both set — parser must never produce this in practice
        assert event.source_ip == "1.2.3.4"
        assert event.hostname == "host.example.com"
