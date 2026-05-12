"""Tests for the backend-only diagnostic export manifest contract."""
from __future__ import annotations

import json

import pytest

from app.diagnostics.contract import (
    DEFAULT_SOURCE_MAX_BYTES,
    DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
    MAX_SAFE_ERROR_SUMMARY_CHARS,
    DiagnosticManifest,
    DiagnosticSourceRecord,
    manifest_to_json,
    serialize_manifest,
)


def test_schema_version_is_pinned() -> None:
    assert DIAGNOSTIC_EXPORT_SCHEMA_VERSION == "diagnostic-export-manifest/v1"


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
