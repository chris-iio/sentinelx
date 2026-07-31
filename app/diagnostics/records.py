"""Diagnostic manifest record builders."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .contract import DiagnosticSourceRecord
from .source_record_fields import (
    DEFAULT_OMITTED_REASON,
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_INCLUDED,
    SOURCE_STATUS_OMITTED,
    SOURCE_STATUS_TRUNCATED,
)
from .redaction import (
    redact_diagnostic_text,
)

if TYPE_CHECKING:
    from .redaction import ConfigSecretStore, RedactionMetadata


def omitted_record(prepared: Any) -> DiagnosticSourceRecord:
    """Return an omitted manifest record for a prepared diagnostic source."""
    return DiagnosticSourceRecord(
        source_id=prepared.source_id,
        name=prepared.name,
        category=prepared.category,
        status=SOURCE_STATUS_OMITTED,
        display_path=prepared.display_path,
        logical_label=prepared.logical_label,
        content_type=prepared.content_type,
        max_bytes=prepared.max_bytes,
        omitted_reason=prepared.omitted_reason or DEFAULT_OMITTED_REASON,
    )


def error_record(
    prepared: Any,
    exc: Exception,
    *,
    config_store: ConfigSecretStore | None,
) -> DiagnosticSourceRecord:
    """Return a redacted error manifest record for a failed source collection."""
    error_text = exception_summary(exc)
    safe_error_summary, metadata = redact_diagnostic_text(error_text, config_store=config_store)
    return DiagnosticSourceRecord(
        source_id=prepared.source_id,
        name=prepared.name,
        category=prepared.category,
        status=SOURCE_STATUS_ERROR,
        display_path=prepared.display_path,
        logical_label=prepared.logical_label,
        content_type=prepared.content_type,
        max_bytes=prepared.max_bytes,
        safe_error_summary=safe_error_summary,
        redaction_count=metadata.redaction_count,
        redaction_labels=metadata.redaction_labels,
    )


def included_record(
    prepared: Any,
    encoded: bytes,
    metadata: RedactionMetadata,
) -> tuple[DiagnosticSourceRecord, bytes]:
    """Return an included/truncated manifest record and bounded payload bytes."""
    included = encoded[: prepared.max_bytes]
    status = (
        SOURCE_STATUS_TRUNCATED
        if len(encoded) > prepared.max_bytes
        else SOURCE_STATUS_INCLUDED
    )
    return (
        DiagnosticSourceRecord(
            source_id=prepared.source_id,
            name=prepared.name,
            category=prepared.category,
            status=status,
            relative_path=prepared.relative_path,
            display_path=prepared.display_path,
            logical_label=prepared.logical_label,
            content_type=prepared.content_type,
            original_bytes=len(encoded),
            included_bytes=len(included),
            max_bytes=prepared.max_bytes,
            redaction_count=metadata.redaction_count,
            redaction_labels=metadata.redaction_labels,
        ),
        included,
    )


def exception_summary(exc: Exception) -> str:
    """Return a useful error class without exporting exception-controlled text.

    Collector exceptions can contain file paths, submitted indicators, or secrets
    that are not part of the configured-secret inventory. The source identifier
    already gives the analyst the failed operation, so the class is sufficient.
    """
    return f"{type(exc).__name__}: source collection failed"
