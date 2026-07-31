"""Tests for the backend-only diagnostic export manifest contract."""
from __future__ import annotations

import builtins
import dis
import inspect
import json
import re
from pathlib import Path

import pytest

from app.diagnostics.contract import (
    DEFAULT_SOURCE_MAX_BYTES,
    DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
    DiagnosticManifest,
    DiagnosticSourceRecord,
    manifest_to_json,
    manifest_to_json_bytes,
    serialize_manifest,
)
import app.diagnostics.source_record_fields as source_record_fields
from app.diagnostics.source_record_fields import MAX_SAFE_ERROR_SUMMARY_CHARS


def test_schema_version_is_pinned() -> None:
    assert DIAGNOSTIC_EXPORT_SCHEMA_VERSION == "diagnostic-export-manifest/v1"


def test_contract_static_frozensets_avoid_temporary_set_literals() -> None:
    source = Path("app/diagnostics/contract.py").read_text(encoding="utf-8")

    assert re.search(r"frozenset\s*\(\s*\{", source) is None


def test_source_record_status_groups_are_static_frozensets() -> None:
    import app.diagnostics.source_record_fields as fields

    source = Path("app/diagnostics/contract.py").read_text(encoding="utf-8")

    assert "{SOURCE_STATUS_OMITTED, SOURCE_STATUS_TRUNCATED}" not in source
    assert "{SOURCE_STATUS_OMITTED, SOURCE_STATUS_ERROR}" not in source
    assert isinstance(fields._OMITTED_REASON_STATUSES, frozenset)
    assert isinstance(fields._ZERO_INCLUDED_BYTES_STATUSES, frozenset)
    assert fields._OMITTED_REASON_STATUSES == frozenset((
        fields.SOURCE_STATUS_OMITTED,
        fields.SOURCE_STATUS_TRUNCATED,
    ))
    assert fields._ZERO_INCLUDED_BYTES_STATUSES == frozenset((
        fields.SOURCE_STATUS_OMITTED,
        fields.SOURCE_STATUS_ERROR,
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
    from app.diagnostics.source_record_fields import _copy_redaction_labels

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
    assert _copy_redaction_labels(("api_key", "bearer", "secret", "token")) == [
        "api_key",
        "bearer",
        "secret",
        "token",
    ]
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
    calls: list[tuple[str, int]] = []

    def normalize(value: str, *, max_chars: int) -> str | None:
        calls.append((value, max_chars))
        stripped = value.strip()
        return stripped[:max_chars] if stripped else None

    monkeypatch.setattr(source_record_fields, "stripped_bounded_text", normalize)

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


def test_source_record_delegates_field_normalization_and_payload_builder() -> None:
    import inspect

    import app.diagnostics.contract as contract
    import app.diagnostics.source_record_fields as fields

    post_init_source = inspect.getsource(contract.DiagnosticSourceRecord.__post_init__)
    to_dict_source = inspect.getsource(contract.DiagnosticSourceRecord.to_dict)
    fields_source = inspect.getsource(fields.normalize_source_record_fields)
    label_source = inspect.getsource(fields._normalize_redaction_labels)
    payload_source = inspect.getsource(fields.source_record_payload)

    source = DiagnosticSourceRecord(
        source_id=" health.payload ",
        name=" Health payload ",
        category="health",
        status="included",
        redaction_labels=("token", "api_key"),
    )

    assert source.source_id == "health.payload"
    assert source.to_dict()["redaction_labels"] == ["api_key", "token"]
    assert contract.DEFAULT_SOURCE_MAX_BYTES is fields.DEFAULT_SOURCE_MAX_BYTES
    assert not hasattr(contract, "MAX_SAFE_ERROR_SUMMARY_CHARS")
    assert not hasattr(contract, "SOURCE_STATUS_INCLUDED")
    assert not hasattr(contract, "SOURCE_STATUS_OMITTED")
    assert not hasattr(contract, "SOURCE_CATEGORIES")
    assert not hasattr(contract, "MAX_SOURCE_TEXT_CHARS")
    assert "normalize_source_record_fields(" in post_init_source
    assert "source_record_payload(" in to_dict_source
    assert "included_bytes cannot exceed max_bytes" not in post_init_source
    assert "redaction_labels" in fields_source
    assert "_normalize_redaction_label(" in label_source
    assert "_copy_redaction_labels(" in payload_source


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
    from app.diagnostics.source_record_fields import _normalize_error_summary

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
    from app.diagnostics.source_record_fields import (
        _append_normalized_redaction_label,
        _append_ordered_unique_redaction_label,
        _normalize_redaction_label,
        _normalize_redaction_labels,
    )

    labels = _normalize_redaction_labels(("token", "api_key", "token", "bearer"))
    nested_code_names = {
        const.co_name
        for const in _normalize_redaction_labels.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert labels == ("api_key", "bearer", "token")
    assert "<setcomp>" not in nested_code_names
    assert "normalize" not in nested_code_names
    assert "_append_normalized_redaction_label" in _normalize_redaction_labels.__code__.co_names
    assert "input_count == 4" in inspect.getsource(_normalize_redaction_labels)
    assert "sorted" not in _normalize_redaction_labels.__code__.co_names
    assert "set" not in _normalize_redaction_labels.__code__.co_names
    assert _normalize_redaction_label(" token ") == "token"

    normalized_ordered = ["api_key", "token"]
    _append_normalized_redaction_label(normalized_ordered, " bearer ")
    _append_normalized_redaction_label(normalized_ordered, "token")
    assert normalized_ordered == ["api_key", "bearer", "token"]

    ordered = ["api_key", "token"]
    _append_ordered_unique_redaction_label(ordered, "bearer")
    _append_ordered_unique_redaction_label(ordered, "token")
    _append_ordered_unique_redaction_label(ordered, "z_secret")
    assert ordered == ["api_key", "bearer", "token", "z_secret"]
    append_source = inspect.getsource(_append_normalized_redaction_label)
    assert "_normalize_redaction_label(label)" in append_source
    assert "_append_ordered_unique_redaction_label(" in append_source


def test_redaction_label_normalization_fast_paths_zero_one_two_or_three_labels(monkeypatch) -> None:
    from app.diagnostics.source_record_fields import _normalize_redaction_labels

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
    assert _normalize_redaction_labels(("token", "api_key", "bearer", "token")) == (
        "api_key",
        "bearer",
        "token",
    )


def test_manifest_construction_uses_direct_ordered_source_insertion(monkeypatch) -> None:
    import app.diagnostics.contract as contract
    import app.diagnostics.bundle_layout as bundle_layout

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
    zeta = DiagnosticSourceRecord(
        source_id="zeta",
        name="Zeta",
        category="health",
        status="included",
        logical_label="zeta",
        original_bytes=1,
        included_bytes=1,
    )

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("manifest sources should not be sorted")

    monkeypatch.setattr(builtins, "sorted", fail_sorted)

    assert DiagnosticManifest(sources=()).sorted_sources == ()
    assert DiagnosticManifest(sources=(source,)).sorted_sources == (source,)
    assert DiagnosticManifest(sources=(source, earlier)).sorted_sources == (earlier, source)
    assert DiagnosticManifest(sources=(source, middle, earlier)).sorted_sources == (
        earlier,
        source,
        middle,
    )
    assert DiagnosticManifest(sources=(source, zeta, middle, earlier)).sorted_sources == (
        earlier,
        source,
        middle,
        zeta,
    )
    post_init_source = inspect.getsource(DiagnosticManifest.__post_init__)
    assert "ordered_by_source_id(self.sources)" in post_init_source
    assert "source_count == 4" not in post_init_source
    assert "source_count == 4" in inspect.getsource(bundle_layout.ordered_by_source_id)

    ordered: list[DiagnosticSourceRecord] = []
    bundle_layout.append_ordered_source(ordered, source)
    bundle_layout.append_ordered_source(ordered, zeta)
    bundle_layout.append_ordered_source(ordered, earlier)
    bundle_layout.append_ordered_source(ordered, middle)
    assert ordered == [earlier, source, middle, zeta]
    assert not hasattr(contract, "append_ordered_manifest_source")


def test_manifest_serialization_computes_counts_in_one_source_pass(monkeypatch) -> None:
    import app.diagnostics.manifest_payloads as manifest_payloads

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
    assert "manifest_payload" in DiagnosticManifest.to_dict.__code__.co_names
    assert "sum" not in manifest_payloads.manifest_payload.__code__.co_names
    assert "sum" not in manifest_payloads.source_counts_payload.__code__.co_names
    assert "SourceCountsAccumulator" in manifest_payloads.manifest_payload.__code__.co_names


def test_manifest_to_dict_delegates_payload_builder() -> None:
    import inspect

    import app.diagnostics.contract as contract
    import app.diagnostics.manifest_payloads as manifest_payloads

    source = inspect.getsource(contract.DiagnosticManifest.to_dict)
    payload_source = inspect.getsource(manifest_payloads.manifest_payload)
    counts_source = inspect.getsource(manifest_payloads.source_counts_payload)
    accumulator_source = inspect.getsource(manifest_payloads.SourceCountsAccumulator.add)
    add_and_append_source = inspect.getsource(manifest_payloads._add_and_append_source)
    final_payload_source = inspect.getsource(manifest_payloads.manifest_payload_from_counts)

    assert "manifest_payload(" in source
    assert "for source in sources" in payload_source
    assert "source_counts_payload(sources)" not in payload_source
    assert payload_source.count("for source in sources") <= 1
    assert "_add_and_append_source(counts, serialized_sources, source)" in payload_source
    assert "append_serialized_source(serialized_sources, source)" not in payload_source
    assert "counts.add(source)" in counts_source
    assert "counts.add(source)" in add_and_append_source
    assert "append_serialized_source(serialized_sources, source)" in add_and_append_source
    assert "manifest_payload_from_counts(" in payload_source
    assert "payload.update(counts_payload)" in final_payload_source
    assert 'payload["sources"] = serialized_sources' in final_payload_source
    assert payload_source.count('"schema_version": schema_version') == 0
    assert payload_source.count('payload["sources"] = serialized_sources') == 0
    assert "source.to_dict()" not in counts_source
    assert "source.status == SOURCE_STATUS_INCLUDED" in accumulator_source
    assert manifest_payloads.SOURCE_STATUS_INCLUDED is source_record_fields.SOURCE_STATUS_INCLUDED
    assert manifest_payloads.SOURCE_STATUS_TRUNCATED is source_record_fields.SOURCE_STATUS_TRUNCATED
    assert 'SOURCE_STATUS_INCLUDED = "included"' not in Path(
        "app/diagnostics/manifest_payloads.py"
    ).read_text(encoding="utf-8")
    assert "serialized_sources.append(source.to_dict())" not in payload_source
    assert "included_count" not in source


def test_manifest_payload_skips_iteration_for_empty_single_pair_three_or_four_sources() -> None:
    import inspect

    import app.diagnostics.manifest_payloads as manifest_payloads

    class NoIterSources(tuple):
        def __iter__(self):
            raise AssertionError("short manifest payloads should not iterate sources")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("short manifest payloads should not slice sources")
            return super().__getitem__(index)

    included = DiagnosticSourceRecord(
        source_id="included",
        name="Included",
        category="health",
        status="included",
        logical_label="health",
        original_bytes=12,
        included_bytes=12,
        redaction_count=2,
    )
    truncated = DiagnosticSourceRecord(
        source_id="truncated",
        name="Truncated",
        category="cache",
        status="truncated",
        logical_label="cache",
        original_bytes=2048,
        included_bytes=1024,
        max_bytes=1024,
    )
    omitted = DiagnosticSourceRecord(
        source_id="omitted",
        name="Omitted",
        category="config",
        status="omitted",
        logical_label="config",
        omitted_reason="secret_only_source",
    )
    error = DiagnosticSourceRecord(
        source_id="error",
        name="Error",
        category="history",
        status="error",
        logical_label="history",
        safe_error_summary="OSError while reading history",
        redaction_count=1,
    )

    assert manifest_payloads.source_counts_payload(NoIterSources(())) == {
        "source_count": 0,
        "included_count": 0,
        "truncated_count": 0,
        "omitted_count": 0,
        "error_count": 0,
        "redaction_count": 0,
    }
    assert manifest_payloads.source_counts_payload(NoIterSources((included,))) == {
        "source_count": 1,
        "included_count": 1,
        "truncated_count": 0,
        "omitted_count": 0,
        "error_count": 0,
        "redaction_count": 2,
    }
    assert manifest_payloads.source_counts_payload(NoIterSources((included, truncated))) == {
        "source_count": 2,
        "included_count": 1,
        "truncated_count": 1,
        "omitted_count": 0,
        "error_count": 0,
        "redaction_count": 2,
    }
    assert manifest_payloads.source_counts_payload(
        NoIterSources((included, truncated, omitted))
    ) == {
        "source_count": 3,
        "included_count": 1,
        "truncated_count": 1,
        "omitted_count": 1,
        "error_count": 0,
        "redaction_count": 2,
    }
    assert manifest_payloads.source_counts_payload(
        NoIterSources((included, truncated, omitted, error))
    ) == {
        "source_count": 4,
        "included_count": 1,
        "truncated_count": 1,
        "omitted_count": 1,
        "error_count": 1,
        "redaction_count": 3,
    }

    serialized = manifest_payloads.manifest_payload(
        NoIterSources((included, truncated, omitted, error)),
        schema_version=DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
        generated_at="2026-01-02T03:04:05Z",
    )

    assert serialized["source_count"] == 4
    assert serialized["included_count"] == 1
    assert serialized["truncated_count"] == 1
    assert serialized["omitted_count"] == 1
    assert serialized["error_count"] == 1
    assert serialized["redaction_count"] == 3
    assert [entry["source_id"] for entry in serialized["sources"]] == [
        "included",
        "truncated",
        "omitted",
        "error",
    ]
    assert "len" in manifest_payloads.manifest_payload.__code__.co_names
    payload_source = inspect.getsource(manifest_payloads.manifest_payload)
    counts_source = inspect.getsource(manifest_payloads.source_counts_payload)
    assert "source_count == 4" in payload_source
    assert "source_count == 4" in counts_source
    assert "manifest_payload_from_counts(" in payload_source


def test_manifest_payload_from_counts_owns_public_shape() -> None:
    import inspect

    import app.diagnostics.manifest_payloads as manifest_payloads

    serialized_sources = [{"source_id": "source-one"}]
    counts_payload = {
        "source_count": 1,
        "included_count": 1,
        "truncated_count": 0,
        "omitted_count": 0,
        "error_count": 0,
        "redaction_count": 2,
    }

    payload = manifest_payloads.manifest_payload_from_counts(
        schema_version=DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
        generated_at="2026-01-02T03:04:05Z",
        counts_payload=counts_payload,
        serialized_sources=serialized_sources,
    )

    assert payload == {
        "schema_version": DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
        "generated_at": "2026-01-02T03:04:05Z",
        "source_count": 1,
        "included_count": 1,
        "truncated_count": 0,
        "omitted_count": 0,
        "error_count": 0,
        "redaction_count": 2,
        "sources": serialized_sources,
    }
    assert "payload.update(counts_payload)" in inspect.getsource(
        manifest_payloads.manifest_payload_from_counts
    )


def test_manifest_serialized_source_append_owns_record_serialization() -> None:
    import inspect

    import app.diagnostics.manifest_payloads as manifest_payloads

    source = DiagnosticSourceRecord(
        source_id="included",
        name="Included",
        category="health",
        status="included",
        logical_label="health",
        original_bytes=12,
        included_bytes=12,
        redaction_count=2,
    )
    serialized_sources: list[dict[str, object]] = []

    manifest_payloads.append_serialized_source(serialized_sources, source)

    assert serialized_sources == [source.to_dict()]
    assert "source.to_dict()" in inspect.getsource(manifest_payloads.append_serialized_source)
    assert "_add_and_append_source" in manifest_payloads.manifest_payload.__code__.co_names
    assert "append_serialized_source" in manifest_payloads._add_and_append_source.__code__.co_names


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
    import inspect

    import app.diagnostics.contract as contract

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

    post_init_source = inspect.getsource(DiagnosticManifest.__post_init__)
    assert "append_manifest_source(sources, source)" in post_init_source
    assert "sources.append(source)" not in post_init_source
    assert "sources.append(source)" in inspect.getsource(contract.append_manifest_source)
