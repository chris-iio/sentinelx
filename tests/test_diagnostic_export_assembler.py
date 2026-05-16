"""Tests for deterministic backend diagnostic export assembly."""
from __future__ import annotations

import json
import zipfile
import builtins
import re
from io import BytesIO
from pathlib import Path

import pytest

from app.diagnostics.assembler import (
    DiagnosticBundle,
    DiagnosticSource,
    _DOT_PATH_SEGMENTS,
    _JSON_SAFE_SEQUENCE_TYPES,
    _PreparedSource,
    _iter_archive_path_segments,
    _json_safe,
    _json_safe_sequence,
    _safe_source_filename,
    assemble_diagnostic_bundle,
)
from app.diagnostics.contract import DiagnosticSourceRecord, MAX_SAFE_ERROR_SUMMARY_CHARS
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY


CONFIGURED_SECRET = "assembler-configured-secret-123456"
RUNTIME_TOKEN = "assembler-runtime-token-secret"
INLINE_API_KEY = "assembler-inline-api-key-secret"


class _SecretStore:
    def get_vt_api_key(self) -> str:
        return CONFIGURED_SECRET

    def all_provider_keys(self) -> dict[str, str]:
        return {"RuntimeProvider": RUNTIME_TOKEN}


def test_assembler_uses_shared_diagnostic_sanitization_policy_bounds() -> None:
    import app.diagnostics.assembler as assembler

    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert assembler._ARCHIVE_PATH_MAX_CHARS == policy.max_archive_path_chars
    assert assembler._SAFE_SOURCE_FILENAME_MAX_CHARS == policy.max_generated_filename_chars
    assert "DIAGNOSTIC_SANITIZATION_POLICY.max_archive_path_chars" in Path(
        "app/diagnostics/assembler.py"
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
    source = Path("app/diagnostics/assembler.py").read_text(encoding="utf-8")

    assert "*sorted(payload_entries)" not in source
    assert "archive_entries.extend(_ordered_payload_entries(payload_entries))" in source
    assert "tuple(path for path" not in source
    assert re.search(r"frozenset\s*\(\s*\{", source) is None


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
            raise AssertionError("small bundle assembly should order prepared sources directly")
        if (
            isinstance(iterable, list)
            and len(iterable) in (2, 3)
            and isinstance(iterable[0], tuple)
            and isinstance(iterable[0][0], str)
            and isinstance(iterable[0][1], bytes)
        ):
            raise AssertionError("small bundle assembly should order payload entries directly")
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
    assert "_ordered_prepared_sources" in assemble_diagnostic_bundle.__code__.co_names
    assert "_ordered_payload_entries" in assemble_diagnostic_bundle.__code__.co_names


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


def test_diagnostic_source_text_normalization_uses_shared_helper(monkeypatch) -> None:
    import app.diagnostics.assembler as assembler

    calls: list[tuple[str, int]] = []

    def normalize(value: str, *, max_chars: int) -> str | None:
        calls.append((value, max_chars))
        stripped = value.strip()
        return stripped[:max_chars] if stripped else None

    monkeypatch.setattr(assembler, "stripped_bounded_text", normalize)

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
    """_json_safe should avoid recursive comprehension frames."""
    class NoItemsDict(dict):
        def items(self):
            raise AssertionError("_json_safe should iterate mapping keys directly")

    payload = NoItemsDict({
        1: ("ok", object()),
        "nested": [{"value": object()}],
    })

    safe = _json_safe(payload)
    nested_code_names = {
        const.co_name
        for const in _json_safe.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert safe == {
        "1": ["ok", "[Unserializable:object]"],
        "nested": [{"value": "[Unserializable:object]"}],
    }
    assert "<dictcomp>" not in nested_code_names
    assert "<listcomp>" not in nested_code_names


def test_json_safe_sequence_types_share_recursive_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.diagnostics.assembler as assembler

    calls: list[str] = []
    original = assembler._json_safe_sequence

    def json_safe_sequence(value: tuple[object, ...] | list[object]) -> list[object]:
        calls.append(type(value).__name__)
        return original(value)

    monkeypatch.setattr(assembler, "_json_safe_sequence", json_safe_sequence)

    assert _JSON_SAFE_SEQUENCE_TYPES == (tuple, list)
    assert assembler._json_safe({"tuple": ("ok",), "list": ["ok"]}) == {
        "tuple": ["ok"],
        "list": ["ok"],
    }
    assert calls == ["tuple", "list"]


def test_json_safe_skips_iteration_for_exact_empty_single_or_pair_containers() -> None:
    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short diagnostic sequences should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("diagnostic sequence sanitization should not slice")
            return super().__getitem__(index)

    assert _json_safe({}) == {}
    assert _json_safe({"item": NoIterList(["value"])}) == {"item": ["value"]}
    assert _json_safe_sequence(NoIterList([])) == []
    assert _json_safe_sequence(NoIterList(["value"])) == ["value"]
    assert _json_safe_sequence(NoIterList(["first", "second"])) == ["first", "second"]


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
    assert "len" in _json_safe.__code__.co_names
    assert "len" in _json_safe_sequence.__code__.co_names
