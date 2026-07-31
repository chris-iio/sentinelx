"""Tests for shared UTC timestamp helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.time_utils import (
    utc_display_seconds,
    utc_iso,
    utc_iso_seconds,
    utc_now,
    utc_timestamp_slug,
    utcnow_iso,
)
from app.text_utils import (
    collapse_whitespace,
    decode_utf8_replace,
    has_non_whitespace,
    stripped_bounded_non_whitespace,
    stripped_bounded_text,
    stripped_text_or_none,
)
from app.json_utils import (
    EMPTY_JSON_ARRAY,
    EMPTY_JSON_OBJECT,
    decode_json_array,
    decode_json_object,
    encode_json_array,
    encode_json_object,
)


def test_utc_now_returns_timezone_aware_utc_datetime() -> None:
    now = utc_now()

    assert now.tzinfo is timezone.utc


def test_utc_iso_formats_utc_with_zulu_suffix() -> None:
    timestamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    assert utc_iso(timestamp) == "2026-01-02T03:04:05Z"


def test_utc_iso_normalizes_offsets_to_utc() -> None:
    timestamp = datetime(2026, 1, 2, 12, 4, 5, tzinfo=timezone(timedelta(hours=9)))

    assert utc_iso(timestamp) == "2026-01-02T03:04:05Z"


def test_utc_iso_seconds_removes_fractional_seconds() -> None:
    timestamp = datetime(2026, 1, 2, 3, 4, 5, 987654, tzinfo=timezone.utc)

    assert utc_iso_seconds(timestamp) == "2026-01-02T03:04:05Z"


def test_utc_timestamp_slug_uses_second_precision_utc() -> None:
    timestamp = datetime(2026, 1, 2, 12, 4, 5, 987654, tzinfo=timezone(timedelta(hours=9)))

    assert utc_timestamp_slug(timestamp) == "20260102T030405Z"


def test_utc_display_seconds_uses_utc_suffix() -> None:
    timestamp = datetime(2026, 1, 2, 12, 4, 5, 987654, tzinfo=timezone(timedelta(hours=9)))

    assert utc_display_seconds(timestamp) == "2026-01-02 03:04:05 UTC"


def test_utcnow_iso_uses_shared_formatter() -> None:
    assert "utc_iso" in utcnow_iso.__code__.co_names


def test_has_non_whitespace_scans_without_generator_frame() -> None:
    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("text presence should scan directly")

    nested_code_names = {
        const.co_name
        for const in has_non_whitespace.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert has_non_whitespace(NoStripText("  alpha  ")) is True
    assert has_non_whitespace(NoStripText("  \n\t  ")) is False
    assert "<genexpr>" not in nested_code_names
    assert "any" not in has_non_whitespace.__code__.co_names


def test_stripped_bounded_non_whitespace_scans_before_stripping() -> None:
    class NoStripWhitespace(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("whitespace-only values should not be stripped")

    assert stripped_bounded_non_whitespace(NoStripWhitespace("  \n\t  "), max_chars=10) is None
    assert stripped_bounded_non_whitespace("  abcdef  ", max_chars=3) == "abc"


def test_stripped_bounded_text_uses_bounded_index_slice_without_strip() -> None:
    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("bounded text trimming should avoid full strip allocation")

    assert stripped_bounded_text(NoStripText("  abcdef  "), max_chars=3) == "abc"
    assert stripped_bounded_text(NoStripText("  abc  "), max_chars=10) == "abc"
    assert stripped_bounded_text(NoStripText(" \n\t "), max_chars=10) is None
    assert "strip" not in stripped_bounded_text.__code__.co_names
    assert "min" not in stripped_bounded_text.__code__.co_names


def test_stripped_text_or_none_uses_index_slice_without_strip() -> None:
    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("text trimming should avoid full strip allocation")

    assert stripped_text_or_none(NoStripText("  abcdef  ")) == "abcdef"
    assert stripped_text_or_none(NoStripText(" \n\t ")) is None
    assert "strip" not in stripped_text_or_none.__code__.co_names


def test_collapse_whitespace_avoids_split_and_strip_allocation() -> None:
    class NoSplitStripText(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("whitespace collapse should use the shared regex helper")

        def strip(self, *_args, **_kwargs):
            raise AssertionError("whitespace collapse should trim by index")

    assert collapse_whitespace(NoSplitStripText("  alpha\t beta\n\n gamma  ")) == "alpha beta gamma"
    assert collapse_whitespace(NoSplitStripText(" \n\t ")) == ""
    assert "strip" not in collapse_whitespace.__code__.co_names
    assert "_stripped_bounds" in collapse_whitespace.__code__.co_names


def test_decode_utf8_replace_handles_malformed_bytes() -> None:
    assert decode_utf8_replace(b"alpha-\xff-beta") == "alpha-�-beta"


def test_shared_empty_json_literals_are_stable() -> None:
    assert EMPTY_JSON_ARRAY == "[]"
    assert EMPTY_JSON_OBJECT == "{}"


def test_empty_aware_json_helpers_skip_empty_payloads() -> None:
    assert encode_json_object({}) == EMPTY_JSON_OBJECT
    assert decode_json_object(EMPTY_JSON_OBJECT) == {}
    assert encode_json_array([]) == EMPTY_JSON_ARRAY
    assert decode_json_array(EMPTY_JSON_ARRAY) == []


def test_empty_aware_json_helpers_encode_nonempty_payloads() -> None:
    assert decode_json_object(encode_json_object({"verdict": "clean"})) == {"verdict": "clean"}
    assert decode_json_array(encode_json_array([{"value": "1.2.3.4"}])) == [{"value": "1.2.3.4"}]
