"""Tests for deterministic backend diagnostic export assembly."""
from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest

from app.diagnostics.assembler import DiagnosticSource, assemble_diagnostic_bundle
from app.diagnostics.contract import MAX_SAFE_ERROR_SUMMARY_CHARS


CONFIGURED_SECRET = "assembler-configured-secret-123456"
RUNTIME_TOKEN = "assembler-runtime-token-secret"
INLINE_API_KEY = "assembler-inline-api-key-secret"


class _SecretStore:
    def get_vt_api_key(self) -> str:
        return CONFIGURED_SECRET

    def all_provider_keys(self) -> dict[str, str]:
        return {"RuntimeProvider": RUNTIME_TOKEN}


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
    assert records["history.error"]["redaction_count"] >= 2
    assert records["health.ok"]["status"] == "included"

    names, entries = _read_archive(bundle.archive_bytes)
    assert names == ["manifest.json", "sources/health.json"]
    assert b"history.error" in entries["manifest.json"]
    assert CONFIGURED_SECRET.encode("utf-8") not in bundle.archive_bytes
    assert RUNTIME_TOKEN.encode("utf-8") not in bundle.archive_bytes


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
