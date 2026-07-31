"""Tests for deterministic backend diagnostic export assembly."""
from __future__ import annotations

import json
import inspect
import zipfile
import builtins
import re
from io import BytesIO
from pathlib import Path

import pytest

import app.diagnostics.archive_writer as archive_writer
from app.diagnostics.archive_paths import (
    _DOT_PATH_SEGMENTS,
    _iter_archive_path_segments,
    _safe_source_filename,
)
import app.diagnostics.bundle_layout as bundle_layout
import app.diagnostics.json_safe as json_safe
import app.diagnostics.payload_encoding as payload_encoding
import app.diagnostics.records as diagnostic_records
import app.diagnostics.source_preparation as source_preparation
import app.diagnostics.source_results as source_results
from app.diagnostics.assembler import (
    DiagnosticBundle,
    assemble_diagnostic_bundle,
)
from app.diagnostics.contract import DiagnosticSourceRecord
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.diagnostics.redaction import RedactionMetadata
from app.diagnostics.source_record_fields import MAX_SAFE_ERROR_SUMMARY_CHARS
from app.diagnostics.source_preparation import DiagnosticSource, _PreparedSource


CONFIGURED_SECRET = "assembler-configured-secret-123456"
RUNTIME_TOKEN = "assembler-runtime-token-secret"
INLINE_API_KEY = "assembler-inline-api-key-secret"


def test_diagnostic_modules_use_relative_sibling_imports() -> None:
    """Diagnostic internals should not import siblings through the package facade."""
    package_imports: list[str] = []

    for path in sorted(Path("app/diagnostics").glob("*.py")):
        if path.name == "__init__.py":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("from app.diagnostics") or line.startswith("import app.diagnostics"):
                package_imports.append(f"{path}:{line}")

    assert package_imports == []


class _SecretStore:
    def get_vt_api_key(self) -> str:
        return CONFIGURED_SECRET

    def all_provider_keys(self) -> dict[str, str]:
        return {"RuntimeProvider": RUNTIME_TOKEN}


def test_assembler_uses_shared_diagnostic_sanitization_policy_bounds() -> None:
    import app.diagnostics.assembler as assembler
    import app.diagnostics.archive_paths as archive_paths

    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert archive_paths._ARCHIVE_PATH_MAX_CHARS == policy.max_archive_path_chars
    assert archive_paths._SAFE_SOURCE_FILENAME_MAX_CHARS == policy.max_generated_filename_chars
    assert not hasattr(assembler, "_ARCHIVE_PATH_MAX_CHARS")
    assert not hasattr(assembler, "_SAFE_SOURCE_FILENAME_MAX_CHARS")
    assert not hasattr(assembler, "DEFAULT_SOURCE_PREFIX")
    assert not hasattr(assembler, "MANIFEST_ARCHIVE_PATH")
    assert "DiagnosticSource" not in assembler.__all__
    assert "DEFAULT_SOURCE_PREFIX" not in assembler.__all__
    assert "MANIFEST_ARCHIVE_PATH" not in assembler.__all__
    assert "DiagnosticBundle" in assembler.__all__
    assert "assemble_diagnostic_bundle" in assembler.__all__
    assert "DIAGNOSTIC_SANITIZATION_POLICY.max_archive_path_chars" in Path(
        "app/diagnostics/archive_paths.py"
    ).read_text(encoding="utf-8")


def _read_archive(archive_bytes: bytes) -> tuple[list[str], dict[str, bytes]]:
    with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
        names = archive.namelist()
        return names, {name: archive.read(name) for name in names}


def _manifest_from_archive(archive_bytes: bytes) -> dict[str, object]:
    _, entries = _read_archive(archive_bytes)
    return json.loads(entries["manifest.json"].decode("utf-8"))


def test_assemble_diagnostic_bundle_is_deterministic_and_records_mixed_outcomes() -> None:
    sources = [
        DiagnosticSource(
            source_id="runtime.large",
            name="Large runtime text",
            category="runtime",
            collect=lambda: (f"api_key={INLINE_API_KEY}; safe=context\n" * 8),
            relative_path="sources/runtime-large.txt",
            content_type="text/plain",
            max_bytes=64,
        ),
        DiagnosticSource(
            source_id="config.secret_values",
            name="Raw configured secret values",
            category="config",
            omitted_reason="secret_only_source",
            logical_label="provider API key values",
        ),
        DiagnosticSource(
            source_id="health.payload",
            name="Health payload",
            category="health",
            payload={
                "provider": "VirusTotal",
                "ok": True,
                "api_key": CONFIGURED_SECRET,
                "headers": {"Authorization": f"Bearer {RUNTIME_TOKEN}"},
            },
            relative_path="sources/health.json",
            content_type="application/json",
        ),
    ]

    first = assemble_diagnostic_bundle(
        sources,
        generated_at="2026-01-02T03:04:05Z",
        config_store=_SecretStore(),
    )
    second = assemble_diagnostic_bundle(
        list(reversed(sources)),
        generated_at="2026-01-02T03:04:05Z",
        config_store=_SecretStore(),
    )

    assert first.archive_bytes == second.archive_bytes
    assert first.archive_paths == (
        "manifest.json",
        "sources/health.json",
        "sources/runtime-large.txt",
    )
    assert first.summary["source_count"] == 3
    assert first.summary["included_count"] == 1
    assert first.summary["truncated_count"] == 1
    assert first.summary["omitted_count"] == 1
    assert first.summary["error_count"] == 0
    assert first.summary["archive_size_bytes"] == len(first.archive_bytes)

    names, entries = _read_archive(first.archive_bytes)
    assert names == ["manifest.json", "sources/health.json", "sources/runtime-large.txt"]
    assert all(info not in first.archive_bytes.decode("utf-8", errors="ignore") for info in [
        CONFIGURED_SECRET,
        RUNTIME_TOKEN,
        INLINE_API_KEY,
    ])

    manifest = json.loads(entries["manifest.json"].decode("utf-8"))
    assert [source["source_id"] for source in manifest["sources"]] == [
        "config.secret_values",
        "health.payload",
        "runtime.large",
    ]
    records = {source["source_id"]: source for source in manifest["sources"]}
    assert records["config.secret_values"]["status"] == "omitted"
    assert records["config.secret_values"]["omitted_reason"] == "secret_only_source"
    assert records["config.secret_values"]["relative_path"] is None
    assert records["health.payload"]["status"] == "included"
    assert records["health.payload"]["relative_path"] == "sources/health.json"
    assert records["health.payload"]["redaction_count"] >= 2
    assert "configured_secret:virustotal" in records["health.payload"]["redaction_labels"]
    assert "pattern:authorization_bearer" in records["health.payload"]["redaction_labels"]
    assert records["runtime.large"]["status"] == "truncated"
    assert records["runtime.large"]["truncated"] is True
    assert records["runtime.large"]["original_bytes"] > records["runtime.large"]["included_bytes"]
    assert records["runtime.large"]["included_bytes"] == 64
    assert len(entries["sources/runtime-large.txt"]) == 64

    health_payload = json.loads(entries["sources/health.json"].decode("utf-8"))
    assert health_payload["provider"] == "VirusTotal"
    assert health_payload["api_key"] == "[REDACTED]"
    assert health_payload["headers"]["Authorization"] == "Bearer [REDACTED]"


def test_archive_entry_order_uses_explicit_extension() -> None:
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")
    layout_source = Path("app/diagnostics/bundle_layout.py").read_text(encoding="utf-8")

    assert "*sorted(payload_entries)" not in assembler_source
    assert "archive_entries.extend(ordered_payload_entries(payload_entries))" not in assembler_source
    assert "archive_entries(manifest_bytes, payload_entries)" in assembler_source
    assert "archive_entry_paths(entries)" in assembler_source
    assert "tuple(path for path" not in assembler_source
    assert "tuple(path for path" not in layout_source
    assert "*(ordered_payload_entries" not in layout_source
    assert re.search(r"frozenset\s*\(\s*\{", assembler_source) is None


def test_archive_writer_owns_stable_zip_metadata() -> None:
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")
    writer_source = Path("app/diagnostics/archive_writer.py").read_text(encoding="utf-8")
    stable_info_source = inspect.getsource(archive_writer.stable_zip_info)
    write_entry_source = inspect.getsource(archive_writer.write_zip_entry)
    write_stable_source = inspect.getsource(archive_writer.write_stable_zip)

    archive_bytes = archive_writer.write_stable_zip(
        (
            ("manifest.json", b"manifest"),
            ("sources/health.json", b"health"),
        )
    )

    with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
        infos = archive.infolist()
        assert [info.filename for info in infos] == ["manifest.json", "sources/health.json"]
        assert {info.date_time for info in infos} == {archive_writer.ZIP_TIMESTAMP}
        assert {info.compress_type for info in infos} == {zipfile.ZIP_STORED}
        assert {info.create_system for info in infos} == {3}
        assert {info.external_attr for info in infos} == {0o600 << 16}

    info = archive_writer.stable_zip_info("sources/health.json")
    assert info.filename == "sources/health.json"
    assert info.date_time == archive_writer.ZIP_TIMESTAMP
    assert info.compress_type == zipfile.ZIP_STORED
    assert info.create_system == 3
    assert info.external_attr == 0o600 << 16
    assert "write_stable_zip(entries)" in assembler_source
    assert "ZipInfo(" not in assembler_source
    assert "ZIP_STORED" not in assembler_source
    assert "writestr(" not in assembler_source
    assert "ZipInfo(" in writer_source
    assert "writestr(" in writer_source
    assert "write_zip_entry(archive, path, payload)" in write_stable_source
    assert "ZipInfo(" not in write_stable_source
    assert "archive.writestr(" not in write_stable_source
    assert "ZipInfo(" in stable_info_source
    assert "archive.writestr(stable_zip_info(path), payload)" in write_entry_source


def test_assembler_records_use_slots_to_avoid_instance_dict() -> None:
    source = DiagnosticSource(
        source_id="health.ok",
        name="Health OK",
        category="health",
        payload={"ok": True},
        relative_path="sources/health.json",
    )
    bundle = DiagnosticBundle(archive_bytes=b"", manifest=assemble_diagnostic_bundle(
        [source],
        generated_at="2026-01-02T03:04:05Z",
    ).manifest)
    prepared = _PreparedSource(
        source=source,
        source_id="health.ok",
        name="Health OK",
        category="health",
        relative_path="sources/health.json",
        content_type="application/json",
        max_bytes=1024,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    assert not hasattr(source, "__dict__")
    assert not hasattr(bundle, "__dict__")
    assert not hasattr(prepared, "__dict__")


def test_bundle_summary_does_not_serialize_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="health.ok",
                name="Health OK",
                category="health",
                payload={"ok": True},
                relative_path="sources/health.json",
            ),
            DiagnosticSource(
                source_id="config.secret_values",
                name="Raw configured secret values",
                category="config",
                omitted_reason="secret_only_source",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    def fail_to_dict(self: DiagnosticSourceRecord) -> dict[str, object]:
        raise AssertionError("bundle summary should not serialize source records")

    monkeypatch.setattr(DiagnosticSourceRecord, "to_dict", fail_to_dict)

    assert bundle.summary == {
        "schema_version": "diagnostic-export-manifest/v1",
        "generated_at": "2026-01-02T03:04:05Z",
        "source_count": 2,
        "included_count": 1,
        "truncated_count": 0,
        "omitted_count": 1,
        "error_count": 0,
        "redaction_count": 0,
        "archive_size_bytes": len(bundle.archive_bytes),
    }
    assert "bundle_summary" in DiagnosticBundle.summary.fget.__code__.co_names


def test_bundle_layout_owns_summary_and_ordering_helpers() -> None:
    """Assembler should delegate pure summary and ordering logic to bundle_layout."""
    import inspect

    summary_source = inspect.getsource(DiagnosticBundle.summary.fget)
    layout_source = inspect.getsource(bundle_layout.bundle_summary)
    bundle_layout_source = Path("app/diagnostics/bundle_layout.py").read_text(encoding="utf-8")
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")

    assert "bundle_summary(" in summary_source
    assert "source_counts_payload(sources)" in layout_source
    assert "source.to_dict()" not in layout_source
    assert "SourceCountsAccumulator" not in layout_source
    assert "if TYPE_CHECKING:" in bundle_layout_source
    assert "from .contract import DiagnosticSourceRecord" in bundle_layout_source
    assert "from .contract import DiagnosticSourceRecord" not in bundle_layout_source.split(
        "if TYPE_CHECKING:", 1
    )[0]
    assert "def _ordered_prepared_sources" not in assembler_source
    assert "def _ordered_payload_entries" not in assembler_source
    assert "ordered_by_source_id(prepared_sources)" in assembler_source
    assert "archive_entries(manifest_bytes, payload_entries)" in assembler_source
    assert "ordered_payload_entries(payload_entries)" in inspect.getsource(
        bundle_layout.archive_entries
    )
    assert bundle_layout.ordered_payload_entries([
        ("sources/z.json", b"z"),
        ("sources/a.json", b"a"),
    ]) == (
        ("sources/a.json", b"a"),
        ("sources/z.json", b"z"),
    )
    assert bundle_layout.ordered_payload_entries([
        ("sources/z.json", b"z"),
        ("sources/a.json", b"a"),
        ("sources/m.json", b"m"),
        ("sources/b.json", b"b"),
    ]) == (
        ("sources/a.json", b"a"),
        ("sources/b.json", b"b"),
        ("sources/m.json", b"m"),
        ("sources/z.json", b"z"),
    )
    assert "entry_count == 4" in inspect.getsource(bundle_layout.ordered_payload_entries)


def test_bundle_layout_owns_archive_entries_and_paths() -> None:
    class NoIterEntries(tuple):
        def __iter__(self):
            raise AssertionError("short archive path projection should not iterate")

    entries = bundle_layout.archive_entries(
        b"manifest",
        [
            ("sources/z.json", b"z"),
            ("sources/a.json", b"a"),
            ("sources/m.json", b"m"),
            ("sources/b.json", b"b"),
        ],
    )

    assert entries == (
        ("manifest.json", b"manifest"),
        ("sources/a.json", b"a"),
        ("sources/b.json", b"b"),
        ("sources/m.json", b"m"),
        ("sources/z.json", b"z"),
    )
    assert bundle_layout.archive_entry_paths(entries) == (
        "manifest.json",
        "sources/a.json",
        "sources/b.json",
        "sources/m.json",
        "sources/z.json",
    )
    assert bundle_layout.archive_entry_paths(NoIterEntries(entries)) == (
        "manifest.json",
        "sources/a.json",
        "sources/b.json",
        "sources/m.json",
        "sources/z.json",
    )
    assert "ordered_payload_entries" in bundle_layout.archive_entries.__code__.co_names
    assert "append_archive_entry" in bundle_layout.archive_entries.__code__.co_names
    assert "append_archive_entry_path" in bundle_layout.archive_entry_paths.__code__.co_names
    assert "payload_count == 4" in inspect.getsource(bundle_layout.archive_entries)
    assert "entry_count == 5" in inspect.getsource(bundle_layout.archive_entry_paths)
    assert "len" in bundle_layout.archive_entry_paths.__code__.co_names
    assert "entries.append(entry)" in inspect.getsource(bundle_layout.append_archive_entry)
    assert "paths.append(path)" in inspect.getsource(bundle_layout.append_archive_entry_path)


def test_single_source_bundle_skips_sorting(monkeypatch: pytest.MonkeyPatch) -> None:
    original_sorted = builtins.sorted

    def fail_assembler_sorted(iterable: object, *args: object, **kwargs: object) -> object:
        if kwargs.get("key") is not None:
            raise AssertionError("single-source bundle assembly should not sort sources")
        if isinstance(iterable, list) and iterable and isinstance(iterable[0], tuple):
            path, payload = iterable[0]
            if isinstance(path, str) and isinstance(payload, bytes):
                raise AssertionError("single-source bundle assembly should not sort payload entries")
        return original_sorted(iterable, *args, **kwargs)

    monkeypatch.setattr(builtins, "sorted", fail_assembler_sorted)

    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="health.ok",
                name="Health OK",
                category="health",
                payload={"ok": True},
                relative_path="sources/health.json",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    assert bundle.archive_paths == ("manifest.json", "sources/health.json")
    assert bundle.summary["source_count"] == 1


def test_two_or_three_source_bundle_orders_directly_without_sorting(monkeypatch: pytest.MonkeyPatch) -> None:
    original_sorted = builtins.sorted

    def fail_assembler_sorted(iterable: object, *args: object, **kwargs: object) -> object:
        items = list(iterable) if isinstance(iterable, tuple | list) else []
        if items and isinstance(items[0], _PreparedSource):
            raise AssertionError("bundle assembly should order prepared sources directly")
        if (
            isinstance(iterable, list)
            and len(iterable) >= 2
            and isinstance(iterable[0], tuple)
            and isinstance(iterable[0][0], str)
            and isinstance(iterable[0][1], bytes)
        ):
            raise AssertionError("bundle assembly should order payload entries directly")
        return original_sorted(iterable, *args, **kwargs)

    monkeypatch.setattr(builtins, "sorted", fail_assembler_sorted)

    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="zeta.payload",
                name="Zeta",
                category="runtime",
                payload={"z": True},
                relative_path="sources/zeta.json",
            ),
            DiagnosticSource(
                source_id="alpha.payload",
                name="Alpha",
                category="health",
                payload={"a": True},
                relative_path="sources/alpha.json",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    assert bundle.archive_paths == (
        "manifest.json",
        "sources/alpha.json",
        "sources/zeta.json",
    )
    assert [source.source_id for source in bundle.manifest.sorted_sources] == [
        "alpha.payload",
        "zeta.payload",
    ]

    three_bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="zeta.payload",
                name="Zeta",
                category="runtime",
                payload={"z": True},
                relative_path="sources/zeta.json",
            ),
            DiagnosticSource(
                source_id="middle.payload",
                name="Middle",
                category="runtime",
                payload={"m": True},
                relative_path="sources/middle.json",
            ),
            DiagnosticSource(
                source_id="alpha.payload",
                name="Alpha",
                category="health",
                payload={"a": True},
                relative_path="sources/alpha.json",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    assert three_bundle.archive_paths == (
        "manifest.json",
        "sources/alpha.json",
        "sources/middle.json",
        "sources/zeta.json",
    )
    assert [source.source_id for source in three_bundle.manifest.sorted_sources] == [
        "alpha.payload",
        "middle.payload",
        "zeta.payload",
    ]

    four_bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="zeta.payload",
                name="Zeta",
                category="runtime",
                payload={"z": True},
                relative_path="sources/zeta.json",
            ),
            DiagnosticSource(
                source_id="beta.payload",
                name="Beta",
                category="runtime",
                payload={"b": True},
                relative_path="sources/beta.json",
            ),
            DiagnosticSource(
                source_id="middle.payload",
                name="Middle",
                category="runtime",
                payload={"m": True},
                relative_path="sources/middle.json",
            ),
            DiagnosticSource(
                source_id="alpha.payload",
                name="Alpha",
                category="health",
                payload={"a": True},
                relative_path="sources/alpha.json",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    assert four_bundle.archive_paths == (
        "manifest.json",
        "sources/alpha.json",
        "sources/beta.json",
        "sources/middle.json",
        "sources/zeta.json",
    )
    assert [source.source_id for source in four_bundle.manifest.sorted_sources] == [
        "alpha.payload",
        "beta.payload",
        "middle.payload",
        "zeta.payload",
    ]
    assert "source_count == 4" in inspect.getsource(bundle_layout.ordered_by_source_id)
    ordered_sources: list[DiagnosticSourceRecord] = []
    for source in reversed(four_bundle.manifest.sorted_sources):
        bundle_layout.append_ordered_source(ordered_sources, source)
    assert [source.source_id for source in ordered_sources] == [
        "alpha.payload",
        "beta.payload",
        "middle.payload",
        "zeta.payload",
    ]
    ordered_payload_entries: list[tuple[str, bytes]] = []
    bundle_layout.append_ordered_payload_entry(ordered_payload_entries, ("sources/zeta.json", b"z"))
    bundle_layout.append_ordered_payload_entry(ordered_payload_entries, ("sources/alpha.json", b"a"))
    bundle_layout.append_ordered_payload_entry(ordered_payload_entries, ("sources/middle.json", b"m"))
    assert [entry[0] for entry in ordered_payload_entries] == [
        "sources/alpha.json",
        "sources/middle.json",
        "sources/zeta.json",
    ]
    assert "ordered_by_source_id" in assemble_diagnostic_bundle.__code__.co_names
    assert "archive_entries" in assemble_diagnostic_bundle.__code__.co_names
    assert "archive_entry_paths" in assemble_diagnostic_bundle.__code__.co_names
    assert "append_ordered_source" in bundle_layout.ordered_by_source_id.__code__.co_names
    assert "append_ordered_payload_entry" in bundle_layout.ordered_payload_entries.__code__.co_names


def test_source_exception_becomes_bounded_redacted_error_record() -> None:
    def raises_secret() -> object:
        raise RuntimeError(f"provider failed with token={RUNTIME_TOKEN} and {CONFIGURED_SECRET}")

    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="history.error",
                name="History failure",
                category="history",
                collect=raises_secret,
                relative_path="sources/history.json",
            ),
            DiagnosticSource(
                source_id="health.ok",
                name="Health OK",
                category="health",
                payload={"ok": True},
                relative_path="sources/health.json",
            ),
        ],
        generated_at="2026-01-02T03:04:05Z",
        config_store=_SecretStore(),
    )

    manifest = _manifest_from_archive(bundle.archive_bytes)
    records = {source["source_id"]: source for source in manifest["sources"]}  # type: ignore[index]
    assert records["history.error"]["status"] == "error"
    assert records["history.error"]["relative_path"] is None
    assert len(records["history.error"]["safe_error_summary"]) <= MAX_SAFE_ERROR_SUMMARY_CHARS
    assert "RuntimeError" in records["history.error"]["safe_error_summary"]
    assert CONFIGURED_SECRET not in records["history.error"]["safe_error_summary"]
    assert RUNTIME_TOKEN not in records["history.error"]["safe_error_summary"]
    assert records["history.error"]["redaction_count"] == 0
    assert records["health.ok"]["status"] == "included"

    names, entries = _read_archive(bundle.archive_bytes)
    assert names == ["manifest.json", "sources/health.json"]
    assert b"history.error" in entries["manifest.json"]
    assert CONFIGURED_SECRET.encode("utf-8") not in bundle.archive_bytes
    assert RUNTIME_TOKEN.encode("utf-8") not in bundle.archive_bytes


def test_assembler_delegates_manifest_record_builders() -> None:
    """Manifest record construction should live outside assembler."""
    import app.diagnostics.source_record_fields as source_record_fields

    prepared = _PreparedSource(
        source=DiagnosticSource(
            source_id="cache.error",
            name="Cache error",
            category="cache",
            omitted_reason="disabled",
        ),
        source_id="cache.error",
        name="Cache error",
        category="cache",
        relative_path=None,
        content_type="application/json",
        max_bytes=256,
        display_path="/cache",
        logical_label="cache",
        omitted_reason="disabled",
    )
    source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")
    records_source = Path("app/diagnostics/records.py").read_text(encoding="utf-8")
    included, included_payload = diagnostic_records.included_record(
        prepared,
        b"abcdef",
        RedactionMetadata(redaction_count=1, redaction_labels=("secret",)),
    )

    assert diagnostic_records.SOURCE_STATUS_INCLUDED is source_record_fields.SOURCE_STATUS_INCLUDED
    assert diagnostic_records.SOURCE_STATUS_OMITTED is source_record_fields.SOURCE_STATUS_OMITTED
    assert diagnostic_records.SOURCE_STATUS_ERROR is source_record_fields.SOURCE_STATUS_ERROR
    assert diagnostic_records.DEFAULT_OMITTED_REASON is source_record_fields.DEFAULT_OMITTED_REASON
    assert "from .contract import (" not in records_source
    assert "from .source_record_fields import" in records_source
    assert "if TYPE_CHECKING:" in records_source
    assert "from .redaction import ConfigSecretStore, RedactionMetadata" in records_source
    records_runtime_source = records_source.split("if TYPE_CHECKING:", 1)[0]
    assert "redact_diagnostic_text" in records_runtime_source
    assert "ConfigSecretStore" not in records_runtime_source
    assert "RedactionMetadata" not in records_runtime_source
    assert diagnostic_records.omitted_record(prepared).status == "omitted"
    assert included.status == "included"
    assert included_payload == b"abcdef"
    assert included.redaction_count == 1
    assert included.redaction_labels == ("secret",)
    assert diagnostic_records.error_record(
        prepared,
        RuntimeError("boom"),
        config_store=None,
    ).safe_error_summary == diagnostic_records.exception_summary(
        RuntimeError("boom")
    )
    assert "_omitted_record(" not in source
    assert "_error_record(" not in source
    assert "_exception_summary(" not in source
    assert "DiagnosticSourceRecord(" not in inspect.getsource(assemble_diagnostic_bundle)
    assert "def omitted_record" not in source
    assert "def error_record" not in source
    assert "def included_record" not in source


def test_included_record_helper_owns_truncation_and_metadata() -> None:
    prepared = _PreparedSource(
        source=DiagnosticSource(
            source_id="runtime.large",
            name="Runtime large",
            category="runtime",
            payload=b"abcdef",
        ),
        source_id="runtime.large",
        name="Runtime large",
        category="runtime",
        relative_path="runtime/large.txt",
        content_type="text/plain",
        max_bytes=3,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    record, included = diagnostic_records.included_record(
        prepared,
        b"abcdef",
        RedactionMetadata(redaction_count=2, redaction_labels=("secret:a", "secret:b")),
    )

    assert included == b"abc"
    assert record.status == "truncated"
    assert record.relative_path == "runtime/large.txt"
    assert record.original_bytes == 6
    assert record.included_bytes == 3
    assert record.max_bytes == 3
    assert record.redaction_count == 2
    assert record.redaction_labels == ("secret:a", "secret:b")


def test_source_collection_result_owns_per_source_outcomes() -> None:
    omitted = _PreparedSource(
        source=DiagnosticSource("runtime.omitted", "Runtime omitted", "runtime"),
        source_id="runtime.omitted",
        name="Runtime omitted",
        category="runtime",
        relative_path=None,
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )
    included = _PreparedSource(
        source=DiagnosticSource(
            "runtime.included",
            "Runtime included",
            "runtime",
            payload={"ok": True},
            relative_path="runtime/included.json",
        ),
        source_id="runtime.included",
        name="Runtime included",
        category="runtime",
        relative_path="runtime/included.json",
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    omitted_result = source_results.source_collection_result(omitted, config_store=None)
    included_result = source_results.source_collection_result(included, config_store=None)
    source_result_source = inspect.getsource(source_results.source_collection_result)
    payload_entry_source = inspect.getsource(source_results.source_payload_entry)

    assert omitted_result.record.status == "omitted"
    assert omitted_result.payload_entry is None
    assert included_result.record.status == "included"
    assert included_result.payload_entry == ("runtime/included.json", b'{"ok":true}')
    assert "source_payload_entry(prepared, included)" in source_result_source
    assert "(prepared.relative_path, included)" not in source_result_source
    assert "(prepared.relative_path, included)" in payload_entry_source


def test_source_payload_entry_helper_owns_archive_entry_shape() -> None:
    prepared = _PreparedSource(
        source=DiagnosticSource(
            "runtime.included",
            "Runtime included",
            "runtime",
            payload={"ok": True},
            relative_path="runtime/included.json",
        ),
        source_id="runtime.included",
        name="Runtime included",
        category="runtime",
        relative_path="runtime/included.json",
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )
    omitted = _PreparedSource(
        source=DiagnosticSource("runtime.omitted", "Runtime omitted", "runtime"),
        source_id="runtime.omitted",
        name="Runtime omitted",
        category="runtime",
        relative_path=None,
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    assert source_results.source_payload_entry(prepared, b"payload") == (
        "runtime/included.json",
        b"payload",
    )
    with pytest.raises(ValueError, match="archive payload path"):
        source_results.source_payload_entry(omitted, b"payload")


def test_source_collection_result_captures_errors_without_payload_entry() -> None:
    def raises() -> object:
        raise RuntimeError("boom")

    prepared = _PreparedSource(
        source=DiagnosticSource(
            "runtime.error",
            "Runtime error",
            "runtime",
            collect=raises,
            relative_path="runtime/error.json",
        ),
        source_id="runtime.error",
        name="Runtime error",
        category="runtime",
        relative_path="runtime/error.json",
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    result = source_results.source_collection_result(prepared, config_store=None)

    assert result.record.status == "error"
    assert result.record.safe_error_summary == "RuntimeError: source collection failed"
    assert result.payload_entry is None


def test_collect_source_results_owns_record_and_payload_accumulation() -> None:
    module_source = Path("app/diagnostics/source_results.py").read_text(encoding="utf-8")

    class NoIterPreparedSources(tuple):
        def __iter__(self):
            raise AssertionError("short prepared-source collection should not iterate")

    omitted = _PreparedSource(
        source=DiagnosticSource("runtime.omitted", "Runtime omitted", "runtime"),
        source_id="runtime.omitted",
        name="Runtime omitted",
        category="runtime",
        relative_path=None,
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )
    included = _PreparedSource(
        source=DiagnosticSource(
            "runtime.included",
            "Runtime included",
            "runtime",
            payload={"ok": True},
            relative_path="runtime/included.json",
        ),
        source_id="runtime.included",
        name="Runtime included",
        category="runtime",
        relative_path="runtime/included.json",
        content_type="application/json",
        max_bytes=256,
        display_path=None,
        logical_label=None,
        omitted_reason=None,
    )

    records, payload_entries = source_results.collect_source_results(
        (omitted, included),
        config_store=None,
    )

    assert [record.status for record in records] == ["omitted", "included"]
    assert payload_entries == [("runtime/included.json", b'{"ok":true}')]
    assert "source_collection_result" in source_results.collect_source_results.__code__.co_names
    assert "from .contract import DiagnosticSourceRecord" in module_source
    assert "from .redaction import ConfigSecretStore" in module_source
    assert "from .source_preparation import _PreparedSource" in module_source
    assert "if TYPE_CHECKING:" in module_source
    module_runtime_source = module_source.split("if TYPE_CHECKING:", 1)[0]
    assert "from .contract import DiagnosticSourceRecord" not in module_runtime_source
    assert "ConfigSecretStore" not in module_runtime_source
    assert "_PreparedSource" not in module_runtime_source

    empty_records, empty_payload_entries = source_results.collect_source_results(
        NoIterPreparedSources(()),
        config_store=None,
    )
    single_records, single_payload_entries = source_results.collect_source_results(
        NoIterPreparedSources((included,)),
        config_store=None,
    )
    pair_records, pair_payload_entries = source_results.collect_source_results(
        NoIterPreparedSources((omitted, included)),
        config_store=None,
    )
    triple_records, triple_payload_entries = source_results.collect_source_results(
        NoIterPreparedSources((omitted, included, included)),
        config_store=None,
    )
    four_records, four_payload_entries = source_results.collect_source_results(
        NoIterPreparedSources((omitted, included, included, included)),
        config_store=None,
    )

    assert empty_records == ()
    assert empty_payload_entries == []
    assert [record.status for record in single_records] == ["included"]
    assert single_payload_entries == [("runtime/included.json", b'{"ok":true}')]
    assert [record.status for record in pair_records] == ["omitted", "included"]
    assert pair_payload_entries == [("runtime/included.json", b'{"ok":true}')]
    assert [record.status for record in triple_records] == ["omitted", "included", "included"]
    assert triple_payload_entries == [
        ("runtime/included.json", b'{"ok":true}'),
        ("runtime/included.json", b'{"ok":true}'),
    ]
    assert [record.status for record in four_records] == [
        "omitted",
        "included",
        "included",
        "included",
    ]
    assert four_payload_entries == [
        ("runtime/included.json", b'{"ok":true}'),
        ("runtime/included.json", b'{"ok":true}'),
        ("runtime/included.json", b'{"ok":true}'),
    ]
    assert "source_count == 4" in inspect.getsource(source_results.collect_source_results)
    assert "result_count == 4" in inspect.getsource(source_results._collection_result_tuple)


def test_collect_source_results_short_paths_delegate_append_helpers() -> None:
    source = inspect.getsource(source_results.collect_source_results)
    direct_path, fallback = source.split("records: list[DiagnosticSourceRecord] = []", 1)
    append_collected_source = inspect.getsource(source_results.append_collected_source_result)

    assert "_collection_result_tuple(" in direct_path
    assert "for prepared in prepared_sources" not in direct_path
    assert "for prepared in prepared_sources" in fallback
    assert "append_collected_source_result(" in fallback
    assert "source_collection_result(prepared, config_store=config_store)" not in fallback
    assert "append_source_collection_result(" in append_collected_source
    assert "source_collection_result(prepared, config_store=config_store)" in append_collected_source


def test_validation_fails_fast_for_duplicates_before_collecting_sources() -> None:
    calls: list[str] = []

    def collect() -> object:
        calls.append("called")
        return {"should": "not happen"}

    with pytest.raises(ValueError, match="duplicate diagnostic source_id"):
        assemble_diagnostic_bundle(
            [
                DiagnosticSource("duplicate", "First", "runtime", collect=collect),
                DiagnosticSource("duplicate", "Second", "runtime", payload={"ok": True}),
            ],
            generated_at="2026-01-02T03:04:05Z",
        )

    with pytest.raises(ValueError, match="duplicate diagnostic archive path"):
        assemble_diagnostic_bundle(
            [
                DiagnosticSource(
                    "first",
                    "First",
                    "runtime",
                    collect=collect,
                    relative_path="sources/shared.json",
                ),
                DiagnosticSource(
                    "second",
                    "Second",
                    "runtime",
                    payload={"ok": True},
                    relative_path="sources/shared.json",
                ),
            ],
            generated_at="2026-01-02T03:04:05Z",
        )

    assert calls == []


def test_diagnostic_source_text_normalization_uses_shared_helper(monkeypatch) -> None:
    from app.diagnostics import source_record_fields

    calls: list[tuple[str, int]] = []

    def normalize(value: str, *, max_chars: int) -> str | None:
        calls.append((value, max_chars))
        stripped = value.strip()
        return stripped[:max_chars] if stripped else None

    monkeypatch.setattr(source_record_fields, "stripped_bounded_text", normalize)

    source = DiagnosticSource(
        " source.id ",
        " Source name ",
        "runtime",
        logical_label=" Runtime payload ",
        payload={"ok": True},
    )
    bundle = assemble_diagnostic_bundle([source], generated_at="2026-01-02T03:04:05Z")
    manifest_source = bundle.manifest.sources[0]

    assert manifest_source.source_id == "source.id"
    assert manifest_source.name == "Source name"
    assert manifest_source.logical_label == "Runtime payload"
    assert (" source.id ", 160) in calls
    assert (" Source name ", 160) in calls
    assert (" Runtime payload ", 160) in calls
    module_source = inspect.getsource(source_preparation)
    assert "def _required_text(" not in module_source
    assert "def _optional_text(" not in module_source
    assert "def _nonnegative_int(" not in module_source
    assert "_strip_required_text(" in module_source
    assert "_normalize_optional_text(" in module_source
    assert "_normalize_nonnegative_int(" in module_source


def test_source_record_payload_copies_short_redaction_labels_without_iteration() -> None:
    from app.diagnostics import source_record_fields

    class NoIterTuple(tuple):
        def __iter__(self):
            raise AssertionError("short redaction-label payload copies should not iterate")

    class PayloadRecord:
        source_id = "source"
        name = "Source"
        category = "runtime"
        status = "included"
        relative_path = None
        display_path = None
        logical_label = None
        content_type = "application/json"
        original_bytes = 0
        included_bytes = 0
        max_bytes = 0
        truncated = False
        omitted_reason = None
        safe_error_summary = None
        redaction_count = 3
        redaction_labels = NoIterTuple(("secret:a", "secret:b", "secret:c"))

    payload = source_record_fields.source_record_payload(PayloadRecord())

    assert payload["redaction_labels"] == ["secret:a", "secret:b", "secret:c"]
    assert "_copy_redaction_labels" in source_record_fields.source_record_payload.__code__.co_names
    assert "len" in source_record_fields._copy_redaction_labels.__code__.co_names


def test_source_record_payload_copy_delegates_long_path_append() -> None:
    from app.diagnostics import source_record_fields

    labels = ("secret:a", "secret:b", "secret:c", "secret:d", "secret:e")

    copied = source_record_fields._copy_redaction_labels(labels)

    copy_source = inspect.getsource(source_record_fields._copy_redaction_labels)
    append_source = inspect.getsource(source_record_fields._append_redaction_label_copy)
    assert copied == ["secret:a", "secret:b", "secret:c", "secret:d", "secret:e"]
    assert "_append_redaction_label_copy(copied, label)" in copy_source
    assert "copied.append(label)" not in copy_source
    assert "copied.append(label)" in append_source


def test_assembler_delegates_source_preparation() -> None:
    import inspect

    import app.diagnostics.assembler as assembler
    import app.diagnostics.source_record_fields as source_record_fields

    assemble_source = inspect.getsource(assembler.assemble_diagnostic_bundle)
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")
    module_source = Path("app/diagnostics/source_preparation.py").read_text(encoding="utf-8")

    prepared = source_preparation.prepare_sources(
        [
            DiagnosticSource(
                " runtime.health ",
                " Runtime health ",
                "runtime",
                payload={"ok": True},
            )
        ]
    )

    assert prepared[0].source_id == "runtime.health"
    assert "prepare_sources(sources)" in assemble_source
    assert "if TYPE_CHECKING:" in assembler_source
    runtime_assembler_source = assembler_source.split("if TYPE_CHECKING:", 1)[0]
    assert "from .source_preparation import" in runtime_assembler_source
    assert "prepare_sources" in runtime_assembler_source
    assert "_PreparedSource" not in assembler_source
    assert "from .source_preparation import DiagnosticSource" in assembler_source
    assert (
        "from .source_preparation import DiagnosticSource"
        not in runtime_assembler_source
    )
    assert "from .redaction import ConfigSecretStore" in assembler_source
    assert (
        "from .redaction import ConfigSecretStore"
        not in runtime_assembler_source
    )
    assert "def _prepare_sources" not in assembler_source
    assert "seen_source_ids" not in assemble_source
    assert "seen_archive_paths" not in assemble_source
    assert "def prepare_sources(" in module_source
    assert "seen_source_ids" in module_source
    assert "seen_archive_paths" in module_source
    assert "validate_source_descriptor(source)" in module_source
    assert "_prepared_source" in source_preparation.prepare_sources.__code__.co_names
    assert "validate_source_descriptor" in source_preparation.prepare_sources.__code__.co_names
    assert "append_prepared_source" in source_preparation.prepare_sources.__code__.co_names
    assert "prepared.append(prepared_source)" not in inspect.getsource(
        source_preparation.prepare_sources
    )
    prepare_source = inspect.getsource(source_preparation.prepare_sources)
    validate_source = inspect.getsource(source_preparation.validate_source_descriptor)
    assert "diagnostic sources must be DiagnosticSource instances" not in prepare_source
    assert "cannot define both collect and payload" not in prepare_source
    assert "collect must be callable" not in prepare_source
    assert "diagnostic sources must be DiagnosticSource instances" in validate_source
    assert "cannot define both collect and payload" in validate_source
    assert "collect must be callable" in validate_source
    assert "prepared.append(prepared_source)" in inspect.getsource(
        source_preparation.append_prepared_source
    )
    assert "_PreparedSource(" not in inspect.getsource(source_preparation.prepare_sources)
    assert source_preparation.DEFAULT_SOURCE_MAX_BYTES is source_record_fields.DEFAULT_SOURCE_MAX_BYTES
    assert source_preparation.SOURCE_CATEGORIES is source_record_fields.SOURCE_CATEGORIES
    assert "from .contract import" not in module_source


def test_source_descriptor_validation_helper_owns_shape_rules() -> None:
    with pytest.raises(ValueError, match="DiagnosticSource instances"):
        source_preparation.validate_source_descriptor(object())

    with pytest.raises(ValueError, match="cannot define both collect and payload"):
        source_preparation.validate_source_descriptor(
            DiagnosticSource(
                "runtime.health",
                "Runtime health",
                "runtime",
                collect=lambda: {"ok": True},
                payload={"ok": True},
            )
        )

    with pytest.raises(ValueError, match="collect must be callable"):
        source_preparation.validate_source_descriptor(
            DiagnosticSource(
                "runtime.health",
                "Runtime health",
                "runtime",
                collect="not-callable",  # type: ignore[arg-type]
            )
        )

    source_preparation.validate_source_descriptor(
        DiagnosticSource(
            "runtime.health",
            "Runtime health",
            "runtime",
            payload={"ok": True},
        )
    )


def test_prepared_source_helper_owns_normalized_record_construction() -> None:
    source = DiagnosticSource(
        "runtime.health",
        " Runtime health ",
        " runtime ",
        content_type=" application/json ",
        max_bytes=512,
        display_path=" Runtime / Health ",
        logical_label=" Health ",
        payload={"ok": True},
    )

    prepared = source_preparation._prepared_source(source, "runtime.health")

    assert prepared.source is source
    assert prepared.source_id == "runtime.health"
    assert prepared.name == "Runtime health"
    assert prepared.category == "runtime"
    assert prepared.relative_path == "sources/runtime.health.json"
    assert prepared.content_type == "application/json"
    assert prepared.max_bytes == 512
    assert prepared.display_path == "Runtime / Health"
    assert prepared.logical_label == "Health"
    assert prepared.omitted_reason is None


def test_safe_source_filename_trims_boundary_punctuation_without_strip() -> None:
    class NoStripSourceId(str):
        def strip(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("source filename normalization should avoid direct strip allocation")

    assert _safe_source_filename(NoStripSourceId("...runtime--health___")) == "runtime--health"
    with pytest.raises(ValueError, match="does not produce a safe archive filename"):
        _safe_source_filename(NoStripSourceId("...---___"))


def test_validation_stops_consuming_source_iterable_at_first_duplicate() -> None:
    def source_iter():
        yield DiagnosticSource("duplicate", "First", "runtime", payload={"ok": True})
        yield DiagnosticSource("duplicate", "Second", "runtime", payload={"ok": True})
        raise AssertionError("source validation should stop at the first duplicate")

    with pytest.raises(ValueError, match="duplicate diagnostic source_id"):
        assemble_diagnostic_bundle(
            source_iter(),
            generated_at="2026-01-02T03:04:05Z",
        )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/tmp/source.json",
        "../source.json",
        "sources/../source.json",
        "manifest.json",
        ".git/config",
        ".gsd/state.json",
        ".planning/notes.json",
        ".audits/report.json",
        "sources\\windows.json",
        "C:/temp/source.json",
    ],
)
def test_unsafe_archive_paths_are_rejected(unsafe_path: str) -> None:
    with pytest.raises(ValueError, match="unsafe diagnostic archive path|manifest.json"):
        assemble_diagnostic_bundle(
            [
                DiagnosticSource(
                    source_id="runtime.path",
                    name="Runtime path",
                    category="runtime",
                    payload={"ok": True},
                    relative_path=unsafe_path,
                )
            ],
            generated_at="2026-01-02T03:04:05Z",
        )


def test_archive_path_validation_scans_segments_without_split_list() -> None:
    class NoSplitPath(str):
        def split(self, *args: object, **kwargs: object) -> list[str]:
            raise AssertionError("archive path validation should not allocate split parts")

    assert list(_iter_archive_path_segments(NoSplitPath("runtime/health.json"))) == [
        "runtime",
        "health.json",
    ]


def test_archive_path_dot_segments_use_static_membership_set() -> None:
    source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")

    assert '{"", ".", ".."}' not in source
    assert isinstance(_DOT_PATH_SEGMENTS, frozenset)
    assert _DOT_PATH_SEGMENTS == frozenset(("", ".", ".."))


def test_unserializable_objects_use_safe_type_name_representation() -> None:
    class SecretBearingObject:
        def __repr__(self) -> str:
            return f"SecretBearingObject({CONFIGURED_SECRET})"

    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id="runtime.unserializable",
                name="Unserializable runtime object",
                category="runtime",
                payload={"value": SecretBearingObject()},
                relative_path="sources/unserializable.json",
            )
        ],
        generated_at="2026-01-02T03:04:05Z",
        config_store=_SecretStore(),
    )

    _, entries = _read_archive(bundle.archive_bytes)
    payload = json.loads(entries["sources/unserializable.json"].decode("utf-8"))
    assert payload == {"value": "[Unserializable:SecretBearingObject]"}
    assert CONFIGURED_SECRET.encode("utf-8") not in bundle.archive_bytes


def test_json_safe_uses_direct_recursive_loops() -> None:
    """JSON-safe payload normalization should avoid recursive comprehension frames."""
    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("JSON-safe normalization should iterate mapping keys directly")

    payload = NoItemsDict({
        1: ("ok", object()),
        "nested": [{"value": object()}],
    })

    safe = json_safe.safe_json_payload(payload)
    nested_code_names = {
        const.co_name
        for const in json_safe.safe_json_payload.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert safe == {
        "1": ["ok", "[Unserializable:object]"],
        "nested": [{"value": "[Unserializable:object]"}],
    }
    assert "<dictcomp>" not in nested_code_names
    assert "<listcomp>" not in nested_code_names


def test_json_safe_sequence_types_share_owner_recursive_helper() -> None:
    assert json_safe.JSON_SAFE_SEQUENCE_TYPES == (tuple, list)
    assert json_safe.safe_json_payload({"tuple": ("ok",), "list": ["ok"]}) == {
        "tuple": ["ok"],
        "list": ["ok"],
    }
    assert "safe_json_sequence" in json_safe.safe_json_payload.__code__.co_names
    assert not hasattr(payload_encoding, "json_safe")
    assert not hasattr(payload_encoding, "json_safe_sequence")


def test_assembler_delegates_json_safe_payload_normalization() -> None:
    import inspect

    import app.diagnostics.json_safe as json_safe
    import app.diagnostics.payload_encoding as payload_encoding

    json_safe_source = inspect.getsource(json_safe.safe_json_payload)
    mapping_source = inspect.getsource(json_safe.safe_json_mapping)
    payload_encode_source = inspect.getsource(payload_encoding.redact_and_encode_payload)
    json_encode_source = inspect.getsource(payload_encoding.redact_and_encode_json_payload)
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")

    assert "def _json_safe" not in assembler_source
    assert "def _json_safe_sequence" not in assembler_source
    assert "_JSON_SAFE_SEQUENCE_TYPES" not in assembler_source
    assert "redact_and_encode_json_payload(" in payload_encode_source
    assert "safe_json_payload(" not in payload_encode_source
    assert "safe_json_payload(" in json_encode_source
    assert "safe_json_sequence(" not in payload_encode_source
    assert not hasattr(payload_encoding, "json_safe")
    assert not hasattr(payload_encoding, "json_safe_sequence")
    assert "safe_json_mapping" in json_safe.safe_json_payload.__code__.co_names
    assert "for key in value" not in json_safe_source
    assert ".items(" not in json_safe_source
    assert "for key in value" in mapping_source
    assert ".items(" not in mapping_source


def test_json_safe_mapping_owns_direct_key_iteration() -> None:
    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("JSON-safe mapping normalization should iterate keys directly")

    payload = NoItemsDict({1: ("ok", object())})
    nested_code_names = {
        const.co_name
        for const in json_safe.safe_json_mapping.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert json_safe.safe_json_mapping(payload) == {
        "1": ["ok", "[Unserializable:object]"]
    }
    assert "<dictcomp>" not in nested_code_names
    assert "<listcomp>" not in nested_code_names


def test_assembler_delegates_payload_collection_and_encoding() -> None:
    import inspect

    import app.diagnostics.assembler as assembler
    import app.diagnostics.payload_encoding as payload_encoding

    assemble_source = inspect.getsource(assembler.assemble_diagnostic_bundle)
    assembler_source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")
    payload_encode_source = inspect.getsource(payload_encoding.redact_and_encode_payload)
    payload_module_source = Path("app/diagnostics/payload_encoding.py").read_text(encoding="utf-8")
    text_encode_source = inspect.getsource(payload_encoding.redact_and_encode_text)
    json_encode_source = inspect.getsource(payload_encoding.redact_and_encode_json_payload)
    source_result_source = inspect.getsource(source_results.source_collection_result)

    assert "collect_source_results(" in assemble_source
    assert "source_collection_result(prepared, config_store=config_store)" not in assemble_source
    assert "records.append(" not in assemble_source
    assert "payload_entries.append(" not in assemble_source
    assert "collect_source_payload(prepared.source)" not in assemble_source
    assert "redact_and_encode_payload(" not in assemble_source
    assert "collect_source_payload(prepared.source)" in source_result_source
    assert "redact_and_encode_payload(" in source_result_source
    assert "def _collect_source_payload" not in assembler_source
    assert "def _redact_and_encode_payload" not in assembler_source
    assert "source.collect()" not in assemble_source
    assert "redact_diagnostic_text(" not in assemble_source
    assert "redact_diagnostic_payload(" not in assemble_source
    assert "json.dumps(" not in assemble_source
    assert "redact_and_encode_text(" in payload_encode_source
    assert "redact_and_encode_json_payload(" in payload_encode_source
    assert "if TYPE_CHECKING:" in payload_module_source
    assert "from .source_preparation import DiagnosticSource" in payload_module_source
    assert "from .redaction import ConfigSecretStore, RedactionMetadata" in payload_module_source
    assert "from .source_preparation import DiagnosticSource" not in payload_module_source.split(
        "if TYPE_CHECKING:", 1
    )[0]
    assert "ConfigSecretStore" not in payload_module_source.split("if TYPE_CHECKING:", 1)[0]
    assert "RedactionMetadata" not in payload_module_source.split("if TYPE_CHECKING:", 1)[0]
    assert "redact_diagnostic_text(" in text_encode_source
    assert "redact_diagnostic_payload(" not in payload_encode_source
    assert "redact_diagnostic_payload(" in json_encode_source
    assert "json.dumps(" not in payload_encode_source
    assert "json.dumps(" in json_encode_source


def test_text_payload_encoding_helper_owns_redacted_utf8_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    original_helper = payload_encoding.redact_and_encode_text

    def recording_helper(text: str, *, config_store: object) -> tuple[bytes, object]:
        calls.append(text)
        return original_helper(text, config_store=config_store)

    monkeypatch.setattr(payload_encoding, "redact_and_encode_text", recording_helper)

    encoded_text, text_metadata = payload_encoding.redact_and_encode_payload(
        f"secret {CONFIGURED_SECRET}",
        content_type="text/plain",
        config_store=None,
    )
    encoded_bytes, bytes_metadata = payload_encoding.redact_and_encode_payload(
        f"bytes {CONFIGURED_SECRET}".encode("utf-8"),
        content_type="text/plain",
        config_store=None,
    )

    assert calls == [f"secret {CONFIGURED_SECRET}", f"bytes {CONFIGURED_SECRET}"]
    assert encoded_text == f"secret {CONFIGURED_SECRET}".encode("utf-8")
    assert encoded_bytes == f"bytes {CONFIGURED_SECRET}".encode("utf-8")
    assert text_metadata.redaction_count == 0
    assert bytes_metadata.redaction_count == 0
    assert "redact_and_encode_text" in payload_encoding.redact_and_encode_payload.__code__.co_names


def test_json_payload_encoding_skips_text_encoding_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_text_helper(*_args: object, **_kwargs: object) -> tuple[bytes, object]:
        raise AssertionError("JSON object payloads should not use text encoding")

    monkeypatch.setattr(payload_encoding, "redact_and_encode_text", fail_text_helper)

    encoded, metadata = payload_encoding.redact_and_encode_payload(
        {"value": object()},
        content_type="application/json",
        config_store=None,
    )

    assert encoded == b'{"value":"[Unserializable:object]"}'
    assert metadata.redaction_count == 0
    assert "redact_and_encode_json_payload" in payload_encoding.redact_and_encode_payload.__code__.co_names


def test_json_payload_encoding_helper_owns_safe_json_encoding() -> None:
    encoded, metadata = payload_encoding.redact_and_encode_json_payload(
        {"tuple": ("ok", object())},
        config_store=None,
    )

    assert encoded == b'{"tuple":["ok","[Unserializable:object]"]}'
    assert metadata.redaction_count == 0
    assert "safe_json_payload" in payload_encoding.redact_and_encode_json_payload.__code__.co_names


def test_json_safe_skips_iteration_for_exact_empty_single_pair_three_or_four_containers() -> None:
    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short diagnostic sequences should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("diagnostic sequence sanitization should not slice")
            return super().__getitem__(index)

    assert json_safe.safe_json_payload({}) == {}
    assert json_safe.safe_json_payload({"item": NoIterList(["value"])}) == {"item": ["value"]}
    assert json_safe.safe_json_mapping({"first": "value", "second": object()}) == {
        "first": "value",
        "second": "[Unserializable:object]",
    }
    assert json_safe.safe_json_mapping({"first": 1, "second": ("ok",), "third": None}) == {
        "first": 1,
        "second": ["ok"],
        "third": None,
    }
    assert json_safe.safe_json_mapping({
        "first": 1,
        "second": ("ok",),
        "third": None,
        "fourth": object(),
    }) == {
        "first": 1,
        "second": ["ok"],
        "third": None,
        "fourth": "[Unserializable:object]",
    }
    assert json_safe.safe_json_sequence(NoIterList([])) == []
    assert json_safe.safe_json_sequence(NoIterList(["value"])) == ["value"]
    assert json_safe.safe_json_sequence(NoIterList(["first", "second"])) == [
        "first",
        "second",
    ]
    assert json_safe.safe_json_sequence(NoIterList(["first", "second", "third"])) == [
        "first",
        "second",
        "third",
    ]
    assert json_safe.safe_json_sequence(NoIterList(["first", "second", "third", "fourth"])) == [
        "first",
        "second",
        "third",
        "fourth",
    ]
    source = inspect.getsource(json_safe.safe_json_mapping)
    sequence_source = inspect.getsource(json_safe.safe_json_sequence)
    append_source = inspect.getsource(json_safe.append_safe_json_item)
    set_mapping_source = inspect.getsource(json_safe.set_safe_json_mapping_value)
    assert "value_count == 2" in source
    assert "value_count == 3" in source
    assert "value_count == 4" in source
    assert "set_safe_json_mapping_value(" in source
    assert "safe[str(key)] = safe_json_payload(" not in source
    assert "safe[str(key)] = safe_json_payload(" in set_mapping_source
    assert "append_safe_json_item(safe_items, child" in sequence_source
    assert "safe_items.append(" not in sequence_source
    assert "safe_items.append(" in append_source


def test_source_default_max_bytes_tracks_shared_policy_default_cap() -> None:
    policy = DIAGNOSTIC_SANITIZATION_POLICY
    source = DiagnosticSource(
        source_id="runtime.default-cap",
        name="Runtime default cap",
        category="runtime",
        payload="x" * (policy.default_source_max_bytes + 1),
        relative_path="sources/default-cap.txt",
    )

    bundle = assemble_diagnostic_bundle(
        [source],
        generated_at="2026-01-02T03:04:05Z",
    )

    record = bundle.manifest.sources[0]
    assert source.max_bytes == policy.default_source_max_bytes
    assert record.status == "truncated"
    assert record.max_bytes == policy.default_source_max_bytes
    assert record.included_bytes == policy.default_source_max_bytes


def test_generated_archive_filename_bound_comes_from_shared_policy() -> None:
    import app.diagnostics.json_safe as json_safe

    policy = DIAGNOSTIC_SANITIZATION_POLICY
    source_id = "runtime." + ("segment-" * 40)

    bundle = assemble_diagnostic_bundle(
        [
            DiagnosticSource(
                source_id=source_id,
                name="Generated filename bound",
                category="runtime",
                payload={"ok": True},
            )
        ],
        generated_at="2026-01-02T03:04:05Z",
    )

    generated_name = bundle.archive_paths[1].removeprefix("sources/").removesuffix(".json")
    assert len(generated_name) == policy.max_generated_filename_chars
    assert bundle.archive_paths[1] == f"sources/{_safe_source_filename(source_id)}.json"
    assert "len" in json_safe.safe_json_mapping.__code__.co_names
    assert "len" in json_safe.safe_json_sequence.__code__.co_names
