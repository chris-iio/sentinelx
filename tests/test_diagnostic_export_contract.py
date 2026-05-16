"""Tests for the backend-only diagnostic export manifest contract."""
from __future__ import annotations

import builtins
import dis
import json
import re
from pathlib import Path

import pytest

from app.diagnostics.contract import (
    DEFAULT_SOURCE_MAX_BYTES,
    DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
    MAX_SAFE_ERROR_SUMMARY_CHARS,
    DiagnosticManifest,
    DiagnosticSourceRecord,
    manifest_to_json,
    manifest_to_json_bytes,
    serialize_manifest,
)


def test_schema_version_is_pinned() -> None:
    assert DIAGNOSTIC_EXPORT_SCHEMA_VERSION == "diagnostic-export-manifest/v1"


def test_contract_static_frozensets_avoid_temporary_set_literals() -> None:
    source = Path("app/diagnostics/contract.py").read_text(encoding="utf-8")

    assert re.search(r"frozenset\s*\(\s*\{", source) is None


def test_source_record_status_groups_are_static_frozensets() -> None:
    import app.diagnostics.contract as contract

    source = Path("app/diagnostics/contract.py").read_text(encoding="utf-8")

    assert "{SOURCE_STATUS_OMITTED, SOURCE_STATUS_TRUNCATED}" not in source
    assert "{SOURCE_STATUS_OMITTED, SOURCE_STATUS_ERROR}" not in source
    assert isinstance(contract._OMITTED_REASON_STATUSES, frozenset)
    assert isinstance(contract._ZERO_INCLUDED_BYTES_STATUSES, frozenset)
    assert contract._OMITTED_REASON_STATUSES == frozenset((
        contract.SOURCE_STATUS_OMITTED,
        contract.SOURCE_STATUS_TRUNCATED,
    ))
    assert contract._ZERO_INCLUDED_BYTES_STATUSES == frozenset((
        contract.SOURCE_STATUS_OMITTED,
        contract.SOURCE_STATUS_ERROR,
    ))


def test_source_record_serializes_safe_defaults_for_included_source() -> None:
    source = DiagnosticSourceRecord(
        source_id="health.payload",
        name="Health payload",
        category="health",
        status="included",
        logical_label="/api/health payload",
        content_type="application/json",
        original_bytes=128,
        included_bytes=128,
    )

    assert source.to_dict() == {
        "source_id": "health.payload",
        "name": "Health payload",
        "category": "health",
        "status": "included",
        "relative_path": None,
        "display_path": None,
        "logical_label": "/api/health payload",
        "content_type": "application/json",
        "original_bytes": 128,
        "included_bytes": 128,
        "max_bytes": DEFAULT_SOURCE_MAX_BYTES,
        "truncated": False,
        "omitted_reason": None,
        "safe_error_summary": None,
        "redaction_count": 0,
        "redaction_labels": [],
    }


def test_source_record_uses_slots_to_avoid_instance_dict() -> None:
    source = DiagnosticSourceRecord(
        source_id="health.payload",
        name="Health payload",
        category="health",
        status="included",
        logical_label="/api/health payload",
    )

    assert not hasattr(source, "__dict__")


def test_source_record_serializes_redaction_labels_without_list_constructor() -> None:
    from app.diagnostics.contract import _copy_redaction_labels

    source = DiagnosticSourceRecord(
        source_id="health.payload",
        name="Health payload",
        category="health",
        status="included",
        redaction_count=2,
        redaction_labels=("token", "api_key"),
    )
    instructions = list(dis.get_instructions(DiagnosticSourceRecord.to_dict))
    list_calls = [
        instruction
        for index, instruction in enumerate(instructions)
        if instruction.opname == "LOAD_GLOBAL"
        and instruction.argval == "list"
        and any(
            later.opname.startswith("CALL")
            for later in instructions[index + 1 : index + 4]
        )
    ]

    assert source.to_dict()["redaction_labels"] == ["api_key", "token"]
    assert _copy_redaction_labels(()) == []
    assert _copy_redaction_labels(("token",)) == ["token"]
    assert _copy_redaction_labels(("api_key", "token")) == ["api_key", "token"]
    assert "list" not in _copy_redaction_labels.__code__.co_names
    assert list_calls == []


def test_invalid_status_and_category_are_rejected() -> None:
    with pytest.raises(ValueError, match="invalid diagnostic source status"):
        DiagnosticSourceRecord(
            source_id="bad.status",
            name="Bad status",
            category="health",
            status="partial",
        )

    with pytest.raises(ValueError, match="invalid diagnostic source category"):
        DiagnosticSourceRecord(
            source_id="bad.category",
            name="Bad category",
            category="secrets",
            status="omitted",
        )


def test_empty_source_id_or_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="source_id"):
        DiagnosticSourceRecord(source_id=" ", name="Config", category="config", status="omitted")

    with pytest.raises(ValueError, match="name"):
        DiagnosticSourceRecord(source_id="config", name="", category="config", status="omitted")


def test_source_record_text_normalization_uses_shared_helper(monkeypatch) -> None:
    import app.diagnostics.contract as contract

    calls: list[tuple[str, int]] = []

    def normalize(value: str, *, max_chars: int) -> str | None:
        calls.append((value, max_chars))
        stripped = value.strip()
        return stripped[:max_chars] if stripped else None

    monkeypatch.setattr(contract, "stripped_bounded_text", normalize)

    source = DiagnosticSourceRecord(
        source_id=" source.id ",
        name=" Source name ",
        category="runtime",
        status="included",
        logical_label=" Runtime payload ",
    )

    assert source.source_id == "source.id"
    assert source.name == "Source name"
    assert source.logical_label == "Runtime payload"
    assert (" source.id ", 160) in calls
    assert (" Source name ", 160) in calls
    assert (" Runtime payload ", 240) in calls


def test_truncated_source_requires_explicit_status_and_bounded_bytes() -> None:
    source = DiagnosticSourceRecord(
        source_id="cache.entries",
        name="Cache entries",
        category="cache",
        status="truncated",
        relative_path="cache/export.json",
        content_type="application/json",
        original_bytes=4096,
        included_bytes=1024,
        max_bytes=1024,
    )

    serialized = source.to_dict()
    assert serialized["status"] == "truncated"
    assert serialized["truncated"] is True
    assert serialized["original_bytes"] == 4096
    assert serialized["included_bytes"] == 1024
    assert serialized["max_bytes"] == 1024

    with pytest.raises(ValueError, match="included_bytes cannot exceed max_bytes"):
        DiagnosticSourceRecord(
            source_id="too.large",
            name="Too large",
            category="cache",
            status="truncated",
            original_bytes=4096,
            included_bytes=2048,
            max_bytes=1024,
        )

    with pytest.raises(ValueError, match="truncated flag is only valid"):
        DiagnosticSourceRecord(
            source_id="ambiguous",
            name="Ambiguous",
            category="cache",
            status="included",
            original_bytes=100,
            included_bytes=50,
            truncated=True,
        )


def test_omitted_and_error_sources_serialize_explicit_reasons() -> None:
    omitted = DiagnosticSourceRecord(
        source_id="provider.secrets",
        name="Provider secrets",
        category="config",
        status="omitted",
        logical_label="provider API key inventory",
    )
    error = DiagnosticSourceRecord(
        source_id="history.read",
        name="History read",
        category="history",
        status="error",
        logical_label="history store snapshot",
        safe_error_summary="PermissionError while reading history store",
    )

    assert omitted.to_dict()["omitted_reason"] == "not_collected"
    assert omitted.to_dict()["included_bytes"] == 0
    assert error.to_dict()["safe_error_summary"] == "PermissionError while reading history store"
    assert error.to_dict()["omitted_reason"] is None


def test_oversized_safe_error_summary_is_normalized_and_bounded() -> None:
    source = DiagnosticSourceRecord(
        source_id="history.error",
        name="History error",
        category="history",
        status="error",
        logical_label="history store",
        safe_error_summary="x" * (MAX_SAFE_ERROR_SUMMARY_CHARS + 100),
    )

    summary = source.to_dict()["safe_error_summary"]
    assert len(summary) == MAX_SAFE_ERROR_SUMMARY_CHARS
    assert summary.endswith("...")


def test_safe_error_summary_normalizes_whitespace_without_split_list() -> None:
    from app.diagnostics.contract import _normalize_error_summary

    class NoSplitText(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("safe error summary normalization should not allocate split parts")

    summary = _normalize_error_summary(NoSplitText("  OSError\twhile\nreading   history  "))

    assert summary == "OSError while reading history"


def test_manifest_serialization_is_deterministic_and_sorted_by_source_id() -> None:
    later = DiagnosticSourceRecord(
        source_id="zeta",
        name="Zeta",
        category="runtime",
        status="included",
        logical_label="zeta runtime state",
        original_bytes=10,
        included_bytes=10,
    )
    earlier = DiagnosticSourceRecord(
        source_id="alpha",
        name="Alpha",
        category="runtime",
        status="included",
        logical_label="alpha runtime state",
        original_bytes=20,
        included_bytes=20,
    )
    manifest = DiagnosticManifest(sources=(later, earlier), generated_at="2026-01-02T03:04:05Z")

    as_dict = serialize_manifest(manifest)
    as_json = manifest_to_json(manifest)

    assert [source["source_id"] for source in as_dict["sources"]] == ["alpha", "zeta"]
    assert as_json == manifest_to_json(manifest)
    assert json.loads(as_json) == as_dict
    assert as_json.index('"alpha"') < as_json.index('"zeta"')


def test_manifest_uses_slots_to_avoid_instance_dict() -> None:
    manifest = DiagnosticManifest()

    assert not hasattr(manifest, "__dict__")


def test_manifest_json_bytes_use_shared_json_formatter() -> None:
    manifest = DiagnosticManifest(
        sources=(
            DiagnosticSourceRecord(
                source_id="cache",
                name="Cache",
                category="cache",
                status="included",
                logical_label="cache stats",
            ),
        ),
        generated_at="2026-01-01T00:00:00Z",
    )

    payload = manifest_to_json_bytes(manifest, indent=2)

    assert payload.endswith(b"\n")
    assert payload[:-1].decode("utf-8") == manifest_to_json(manifest, indent=2)


def test_manifest_reuses_construction_time_sorted_sources(monkeypatch) -> None:
    later = DiagnosticSourceRecord(
        source_id="zeta",
        name="Zeta",
        category="runtime",
        status="included",
        logical_label="zeta runtime state",
        original_bytes=10,
        included_bytes=10,
    )
    earlier = DiagnosticSourceRecord(
        source_id="alpha",
        name="Alpha",
        category="runtime",
        status="included",
        logical_label="alpha runtime state",
        original_bytes=20,
        included_bytes=20,
    )
    manifest = DiagnosticManifest(sources=(later, earlier))

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("manifest serialization should reuse construction-time sorted sources")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    assert [source.source_id for source in manifest.sorted_sources] == ["alpha", "zeta"]
    assert [source["source_id"] for source in manifest.to_dict()["sources"]] == ["alpha", "zeta"]


def test_manifest_aggregate_counts_cover_mixed_outcomes() -> None:
    sources = (
        DiagnosticSourceRecord(
            source_id="included",
            name="Included",
            category="health",
            status="included",
            logical_label="health",
            original_bytes=12,
            included_bytes=12,
            redaction_count=2,
            redaction_labels=("api_key", "token"),
        ),
        DiagnosticSourceRecord(
            source_id="truncated",
            name="Truncated",
            category="cache",
            status="truncated",
            logical_label="cache",
            original_bytes=2048,
            included_bytes=1024,
            max_bytes=1024,
        ),
        DiagnosticSourceRecord(
            source_id="omitted",
            name="Omitted",
            category="config",
            status="omitted",
            logical_label="provider secrets",
            omitted_reason="secret_only_source",
        ),
        DiagnosticSourceRecord(
            source_id="error",
            name="Error",
            category="history",
            status="error",
            logical_label="history",
            safe_error_summary="OSError while reading history",
        ),
    )
    manifest = DiagnosticManifest(sources=sources)

    serialized = manifest.to_dict()

    assert serialized["source_count"] == 4
    assert serialized["included_count"] == 1
    assert serialized["truncated_count"] == 1
    assert serialized["omitted_count"] == 1
    assert serialized["error_count"] == 1
    assert serialized["redaction_count"] == 2
    assert len(serialized["sources"]) == 4


def test_redaction_label_normalization_uses_direct_accumulation() -> None:
    from app.diagnostics.contract import _normalize_redaction_labels

    labels = _normalize_redaction_labels(("token", "api_key", "token"))
    nested_code_names = {
        const.co_name
        for const in _normalize_redaction_labels.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert labels == ("api_key", "token")
    assert "<setcomp>" not in nested_code_names


def test_redaction_label_normalization_fast_paths_zero_one_two_or_three_labels(monkeypatch) -> None:
    from app.diagnostics.contract import _normalize_redaction_labels

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("short redaction labels should not be sorted")

    def fail_set(*_args, **_kwargs):
        raise AssertionError("short redaction labels should not allocate a set")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)
    monkeypatch.setattr(builtins, "set", fail_set)

    assert _normalize_redaction_labels(()) == ()
    assert _normalize_redaction_labels(("token",)) == ("token",)
    assert _normalize_redaction_labels(("token", "api_key")) == ("api_key", "token")
    assert _normalize_redaction_labels(("token", "token")) == ("token",)
    assert _normalize_redaction_labels(("token", "api_key", "bearer")) == (
        "api_key",
        "bearer",
        "token",
    )
    assert _normalize_redaction_labels(("token", "api_key", "token")) == ("api_key", "token")


def test_manifest_construction_skips_sort_for_zero_one_two_or_three_sources(monkeypatch) -> None:
    source = DiagnosticSourceRecord(
        source_id="health",
        name="Health",
        category="health",
        status="included",
        logical_label="health",
        original_bytes=1,
        included_bytes=1,
    )
    earlier = DiagnosticSourceRecord(
        source_id="alpha",
        name="Alpha",
        category="health",
        status="included",
        logical_label="alpha",
        original_bytes=1,
        included_bytes=1,
    )
    middle = DiagnosticSourceRecord(
        source_id="middle",
        name="Middle",
        category="health",
        status="included",
        logical_label="middle",
        original_bytes=1,
        included_bytes=1,
    )

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("zero, one, two, or three manifest sources should not be sorted")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    assert DiagnosticManifest(sources=()).sorted_sources == ()
    assert DiagnosticManifest(sources=(source,)).sorted_sources == (source,)
    assert DiagnosticManifest(sources=(source, earlier)).sorted_sources == (earlier, source)
    assert DiagnosticManifest(sources=(source, middle, earlier)).sorted_sources == (
        earlier,
        source,
        middle,
    )


def test_manifest_serialization_computes_counts_in_one_source_pass(monkeypatch) -> None:
    sources = (
        DiagnosticSourceRecord(
            source_id="included",
            name="Included",
            category="health",
            status="included",
            logical_label="health",
            original_bytes=12,
            included_bytes=12,
            redaction_count=2,
        ),
        DiagnosticSourceRecord(
            source_id="error",
            name="Error",
            category="history",
            status="error",
            logical_label="history",
            safe_error_summary="OSError while reading history",
            redaction_count=1,
        ),
    )
    manifest = DiagnosticManifest(sources=sources)

    def fail_sum(*_args, **_kwargs):
        raise AssertionError("manifest serialization should not rescan sources with sum")

    monkeypatch.setattr(builtins, "sum", fail_sum)

    serialized = manifest.to_dict()

    assert serialized["included_count"] == 1
    assert serialized["error_count"] == 1
    assert serialized["redaction_count"] == 3
    assert [source["source_id"] for source in serialized["sources"]] == ["error", "included"]


def test_empty_manifest_serializes_zero_counts() -> None:
    serialized = DiagnosticManifest(sources=()).to_dict()

    assert serialized["source_count"] == 0
    assert serialized["included_count"] == 0
    assert serialized["truncated_count"] == 0
    assert serialized["omitted_count"] == 0
    assert serialized["error_count"] == 0
    assert serialized["sources"] == []


def test_duplicate_source_ids_are_rejected() -> None:
    first = DiagnosticSourceRecord(
        source_id="duplicate",
        name="First",
        category="runtime",
        status="included",
        logical_label="first",
        original_bytes=1,
        included_bytes=1,
    )
    second = DiagnosticSourceRecord(
        source_id="duplicate",
        name="Second",
        category="runtime",
        status="omitted",
        logical_label="second",
    )

    with pytest.raises(ValueError, match="duplicate diagnostic source_id"):
        DiagnosticManifest(sources=(first, second))


def test_manifest_duplicate_source_validation_stops_at_first_duplicate() -> None:
    first = DiagnosticSourceRecord(
        source_id="duplicate",
        name="First",
        category="runtime",
        status="included",
        logical_label="first",
        original_bytes=1,
        included_bytes=1,
    )
    second = DiagnosticSourceRecord(
        source_id="duplicate",
        name="Second",
        category="runtime",
        status="included",
        logical_label="second",
        original_bytes=1,
        included_bytes=1,
    )

    def source_records():
        yield first
        yield second
        raise AssertionError("manifest duplicate validation should stop at the first duplicate")

    with pytest.raises(ValueError, match="duplicate diagnostic source_id"):
        DiagnosticManifest(sources=source_records())
