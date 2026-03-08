"""Tests for bulk IOC parser."""
from __future__ import annotations

from app.pipeline.bulk import parse_bulk_iocs
from app.pipeline.models import IOCType


class TestParseBulkIocs:
    def test_single_ipv4(self) -> None:
        result = parse_bulk_iocs("1.2.3.4")
        assert len(result) == 1
        assert result[0].type == IOCType.IPV4
        assert result[0].value == "1.2.3.4"

    def test_mixed_types(self) -> None:
        text = "1.2.3.4\nevil.com\n" + "a" * 64
        result = parse_bulk_iocs(text)
        types = {ioc.type for ioc in result}
        assert IOCType.IPV4 in types
        assert IOCType.DOMAIN in types
        assert IOCType.SHA256 in types

    def test_blank_lines_skipped(self) -> None:
        text = "1.2.3.4\n\n\n8.8.8.8\n"
        result = parse_bulk_iocs(text)
        assert len(result) == 2

    def test_deduplication(self) -> None:
        text = "1.2.3.4\n1.2.3.4\n1.2.3.4"
        result = parse_bulk_iocs(text)
        assert len(result) == 1

    def test_invalid_lines_skipped(self) -> None:
        text = "1.2.3.4\nhello world\n8.8.8.8"
        result = parse_bulk_iocs(text)
        assert len(result) == 2

    def test_defanged_iocs(self) -> None:
        text = "1[.]2[.]3[.]4\nhxxps://evil[.]com/path"
        result = parse_bulk_iocs(text)
        assert len(result) >= 1
        values = {ioc.value for ioc in result}
        assert "1.2.3.4" in values

    def test_empty_input(self) -> None:
        assert parse_bulk_iocs("") == []

    def test_whitespace_only(self) -> None:
        assert parse_bulk_iocs("  \n\t\n  ") == []
