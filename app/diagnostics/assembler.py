"""Deterministic backend-only diagnostic bundle assembly.

The assembler consumes caller-supplied diagnostic source descriptors and returns a
bounded ZIP archive plus the manifest object describing every considered source.
It deliberately does not know about Flask routes or filesystem traversal; callers
are responsible for collecting runtime/fixture data and handing it to this module
as values or lazy callables.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .archive_writer import write_stable_zip
from .bundle_layout import (
    archive_entries,
    archive_entry_paths,
    bundle_summary,
    ordered_by_source_id,
)
from .contract import (
    DiagnosticManifest,
    manifest_to_json_bytes,
)
from .source_preparation import (
    prepare_sources,
)
from .source_results import collect_source_results

if TYPE_CHECKING:
    from .redaction import ConfigSecretStore
    from .source_preparation import DiagnosticSource


@dataclass(frozen=True, slots=True)
class DiagnosticBundle:
    """Assembled diagnostic ZIP bytes and safe inspection metadata."""

    archive_bytes: bytes
    manifest: DiagnosticManifest
    archive_paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def archive_size_bytes(self) -> int:
        """Return the final ZIP size in bytes."""
        return len(self.archive_bytes)

    @property
    def summary(self) -> dict[str, int | str | None]:
        """Return secret-free aggregate fields useful to routes/tests."""
        return bundle_summary(
            self.manifest.sorted_sources,
            schema_version=self.manifest.schema_version,
            generated_at=self.manifest.generated_at,
            archive_size_bytes=self.archive_size_bytes,
        )


def assemble_diagnostic_bundle(
    sources: Iterable[DiagnosticSource],
    *,
    generated_at: str,
    config_store: ConfigSecretStore | None = None,
) -> DiagnosticBundle:
    """Assemble a deterministic bounded diagnostic ZIP archive.

    Validation for duplicate IDs, duplicate archive paths, unsafe paths, malformed
    categories, and ambiguous source descriptors happens before any source
    callable is evaluated.  Individual source collection failures are captured as
    manifest ``error`` records and do not abort unrelated sources.
    """
    prepared_sources = prepare_sources(sources)

    ordered_sources = ordered_by_source_id(prepared_sources)
    records, payload_entries = collect_source_results(
        ordered_sources,
        config_store=config_store,
    )

    manifest = DiagnosticManifest(sources=records, generated_at=generated_at)
    manifest_bytes = manifest_to_json_bytes(manifest, indent=2)
    entries = archive_entries(manifest_bytes, payload_entries)
    archive_bytes = write_stable_zip(entries)

    return DiagnosticBundle(
        archive_bytes=archive_bytes,
        manifest=manifest,
        archive_paths=archive_entry_paths(entries),
    )

__all__ = [
    "DiagnosticBundle",
    "assemble_diagnostic_bundle",
]
