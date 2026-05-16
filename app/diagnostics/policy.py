"""Shared bounds for diagnostic sanitization and bundle assembly."""
from __future__ import annotations

from dataclasses import dataclass

from app.diagnostics.contract import DEFAULT_SOURCE_MAX_BYTES


@dataclass(frozen=True, slots=True)
class DiagnosticSanitizationPolicy:
    """Immutable caps shared by diagnostics assembly, sources, and redaction."""

    default_source_max_bytes: int = DEFAULT_SOURCE_MAX_BYTES
    runtime_source_max_bytes: int = 16 * 1024
    max_safe_string_chars: int = 240
    max_list_items: int = 25
    max_dict_items: int = 50
    max_jsonish_depth: int = 5
    max_archive_path_chars: int = 240
    max_generated_filename_chars: int = 120
    max_redaction_depth: int = 20
    max_redaction_label_chars: int = 64


DIAGNOSTIC_SANITIZATION_POLICY = DiagnosticSanitizationPolicy()


__all__ = [
    "DIAGNOSTIC_SANITIZATION_POLICY",
    "DiagnosticSanitizationPolicy",
]
