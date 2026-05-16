import json
import dis
import zipfile
from io import BytesIO

from app.diagnostics import sources as sources_module
from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
from app.diagnostics.policy import (
    DIAGNOSTIC_SANITIZATION_POLICY,
    DiagnosticSanitizationPolicy,
)
from app.enrichment.config_store import ConfigStore

GENERATED_AT = "2026-01-02T03:04:05Z"


class FakeCacheStore:
    def __init__(self, stats_payload=None, error=None):
        self.stats_payload = stats_payload or {"total_entries": 2, "oldest": None}
        self.error = error
        self.calls = 0

    def stats(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.stats_payload


class FakeHistoryStore:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.limits = []

    def list_recent(self, limit=20):
        self.limits.append(limit)
        if self.error is not None:
            raise self.error
        return self.rows[:limit]


class FailingConfigStore:
    def get_vt_api_key(self):
        raise RuntimeError("could not read config with Bearer SHOULD_NOT_LEAK")

    def all_provider_keys(self):
        raise AssertionError("all_provider_keys should not run after vt failure")


class _BoundedItemsMapping(dict):
    def __init__(self, pairs, *, max_reads: int):
        super().__init__()
        self._items = dict(pairs)
        self._keys = tuple(self._items)
        self.max_reads = max_reads
        self.reads = 0

    def __iter__(self):
        for key in self._keys:
            self.reads += 1
            if self.reads > self.max_reads:
                raise AssertionError("safe diagnostics should stop at the mapping cap")
            yield key

    def __getitem__(self, key):
        return self._items[key]

    def items(self):
        raise AssertionError("safe diagnostics should iterate mapping keys directly")


class _NoSliceList(list):
    def __getitem__(self, index):
        if isinstance(index, slice):
            raise AssertionError("recent history diagnostics should use bounded iteration")
        return super().__getitem__(index)


def _bundle_payloads(bundle):
    with zipfile.ZipFile(BytesIO(bundle.archive_bytes)) as archive:
        payloads = {}
        for name in archive.namelist():
            if name.endswith(".json"):
                payloads[name] = json.loads(archive.read(name).decode("utf-8"))
        return payloads


def _records_by_id(bundle):
    manifest = bundle.manifest.to_dict()
    return {record["source_id"]: record for record in manifest["sources"]}


def test_default_sources_include_safe_runtime_snapshots_without_request_context(tmp_path):
    config = ConfigStore(tmp_path / "sentinelx.ini")
    config.set_vt_api_key("vt-secret-value-123456")
    config.set_provider_key("Abuse IP DB", "provider-secret-value-abcdef")
    cache = FakeCacheStore({"total_entries": 3, "oldest": "2025-01-01T00:00:00Z"})
    history = FakeHistoryStore(
        [
            {
                "id": "analysis-1",
                "input_text": "example input",
                "mode": "offline",
                "total_count": 1,
                "top_verdict": "suspicious",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ]
    )

    def job_accessor(job_id):
        return {
            "job_id": job_id,
            "found": True,
            "diagnostics": {
                "last_error": "provider failed with Bearer runtime-token-1234567890",
            },
        }

    sources = build_default_diagnostic_sources(
        config_store=config,
        cache_store=cache,
        history_store=history,
        history_limit=99,
        job_id="job-1",
        job_diagnostics_accessor=job_accessor,
        generated_at=GENERATED_AT,
    )
    bundle = assemble_diagnostic_bundle(sources, generated_at=GENERATED_AT, config_store=config)

    records = _records_by_id(bundle)
    assert records["config-secret-inventory"]["status"] == "included"
    assert records["cache-stats"]["status"] == "included"
    assert records["recent-history"]["status"] == "included"
    assert records["orchestration-diagnostics"]["status"] == "included"
    assert cache.calls == 1
    assert history.limits == [10]

    payloads = _bundle_payloads(bundle)
    config_payload = payloads["runtime/config-secret-inventory.json"]
    assert config_payload == {
        "configured_secret_count": 2,
        "configured_secret_labels": [
            "configured_secret:provider:abuse_ip_db",
            "configured_secret:virustotal",
        ],
        "provider_count": 1,
        "provider_labels": ["abuse_ip_db"],
        "config_error": None,
    }
    recent_payload = payloads["runtime/recent-history.json"]
    assert recent_payload["limit"] == 10
    assert recent_payload["returned_count"] == 1
    health_payload = payloads["runtime/health-checks.json"]
    assert health_payload["service"] == "sentinelx"
    assert health_payload["status"] == "ok"

    archive_text = bundle.archive_bytes.decode("latin1")
    assert "vt-secret-value" not in archive_text
    assert "provider-secret-value" not in archive_text
    assert "123456" not in json.dumps(config_payload)
    assert "runtime-token-1234567890" not in archive_text
    assert "[REDACTED]" in archive_text


def test_diagnostic_sanitization_policy_centralizes_source_bounds() -> None:
    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert not hasattr(policy, "__dict__")
    assert DiagnosticSanitizationPolicy().runtime_source_max_bytes == 16 * 1024
    assert sources_module._SOURCE_MAX_BYTES == policy.runtime_source_max_bytes
    assert sources_module._MAX_SAFE_STRING_CHARS == policy.max_safe_string_chars
    assert sources_module._MAX_LIST_ITEMS == policy.max_list_items
    assert sources_module._MAX_DICT_ITEMS == policy.max_dict_items
    assert sources_module._MAX_DEPTH == policy.max_jsonish_depth


def test_failing_runtime_dependencies_become_source_errors_and_do_not_abort(tmp_path):
    cache = FakeCacheStore(error=RuntimeError("cache down Bearer cache-token-123456"))
    history = FakeHistoryStore(error=ValueError("history unavailable"))

    def failing_health_checks():
        raise OSError("health probe failed")

    sources = build_default_diagnostic_sources(
        config_store=FailingConfigStore(),
        cache_store=cache,
        history_store=history,
        health_checks=failing_health_checks,
        generated_at=GENERATED_AT,
    )
    bundle = assemble_diagnostic_bundle(sources, generated_at=GENERATED_AT)

    records = _records_by_id(bundle)
    assert records["diagnostic-export-metadata"]["status"] == "included"
    assert records["history-save-diagnostics"]["status"] == "included"
    assert records["config-secret-inventory"]["status"] == "error"
    assert records["cache-stats"]["status"] == "error"
    assert records["recent-history"]["status"] == "error"
    assert records["health-checks"]["status"] == "error"
    assert records["orchestration-diagnostics"]["status"] == "omitted"
    assert records["orchestration-diagnostics"]["omitted_reason"] == "job_id_not_provided"

    manifest_text = json.dumps(bundle.manifest.to_dict())
    assert "cache-token-123456" not in manifest_text
    assert "SHOULD_NOT_LEAK" not in manifest_text
    assert "Bearer [REDACTED]" in manifest_text


def test_config_secret_inventory_payload_accumulates_labels_without_list_constructor() -> None:
    instructions = list(dis.get_instructions(sources_module._config_secret_inventory_payload))
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

    assert list_calls == []


def test_copy_label_tuple_skips_iteration_for_empty_single_pair_or_three_labels() -> None:
    class NoIterTuple(tuple):
        def __iter__(self):
            raise AssertionError("short label copies should not iterate")

    assert sources_module._copy_label_tuple(NoIterTuple(())) == []
    assert sources_module._copy_label_tuple(NoIterTuple(("configured_secret:virustotal",))) == [
        "configured_secret:virustotal"
    ]
    assert sources_module._copy_label_tuple(NoIterTuple(("b", "a"))) == ["b", "a"]
    assert sources_module._copy_label_tuple(NoIterTuple(("c", "b", "a"))) == ["c", "b", "a"]
    assert "len" in sources_module._copy_label_tuple.__code__.co_names


def test_missing_optional_runtime_objects_are_explicitly_omitted():
    sources = build_default_diagnostic_sources(generated_at=GENERATED_AT)
    bundle = assemble_diagnostic_bundle(sources, generated_at=GENERATED_AT)

    records = _records_by_id(bundle)
    assert records["config-secret-inventory"]["status"] == "omitted"
    assert records["config-secret-inventory"]["omitted_reason"] == "config_store_not_provided"
    assert records["cache-stats"]["status"] == "omitted"
    assert records["cache-stats"]["omitted_reason"] == "cache_store_not_provided"
    assert records["recent-history"]["status"] == "omitted"
    assert records["recent-history"]["omitted_reason"] == "history_store_not_provided"
    assert records["orchestration-diagnostics"]["status"] == "omitted"
    assert records["health-checks"]["status"] == "included"

    payloads = _bundle_payloads(bundle)
    health_payload = payloads["runtime/health-checks.json"]
    assert health_payload["status"] == "degraded"
    assert health_payload["checks"]["cache"]["detail"] == "cache_store_not_provided"


def test_safe_mapping_uses_bounded_iteration_for_nested_mappings():
    from app.diagnostics.sources import _safe_mapping

    child = _BoundedItemsMapping(
        [(f"child-{index}", index) for index in range(55)],
        max_reads=50,
    )
    raw = _BoundedItemsMapping(
        [("nested", child), *[(f"key-{index}", index) for index in range(54)]],
        max_reads=50,
    )

    payload = _safe_mapping(raw)

    assert raw.reads == 50
    assert child.reads == 50
    assert "key-48" in payload
    assert "key-49" not in payload
    assert payload["nested"]["child-49"] == 49
    assert "child-50" not in payload["nested"]


def test_safe_jsonish_uses_direct_recursive_loops():
    from app.diagnostics.sources import _safe_jsonish

    nested_code_names = {
        const.co_name
        for const in _safe_jsonish.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert _safe_jsonish({"items": [1, "two"]}) == {"items": [1, "two"]}
    assert "<dictcomp>" not in nested_code_names
    assert "<listcomp>" not in nested_code_names


def test_safe_jsonish_skips_iteration_for_exact_empty_single_or_pair_containers():
    from app.diagnostics.sources import _safe_jsonish

    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short list diagnostics should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("diagnostic list sanitization should not slice")
            return super().__getitem__(index)

    assert _safe_jsonish({}) == {}
    assert _safe_jsonish({"item": NoIterList(["value"])}) == {"item": ["value"]}
    assert _safe_jsonish(NoIterList([])) == []
    assert _safe_jsonish(NoIterList(["value"])) == ["value"]
    assert _safe_jsonish(NoIterList(["first", "second"])) == ["first", "second"]
    assert "len" in _safe_jsonish.__code__.co_names


def test_job_diagnostics_payload_adds_defaults_without_setdefault() -> None:
    from app.diagnostics.sources import _job_diagnostics_payload

    payload = _job_diagnostics_payload(lambda _job_id: {"diagnostics": {}}, "job-1")
    explicit = _job_diagnostics_payload(
        lambda _job_id: {"job_id": "custom-job", "found": False},
        "job-1",
    )

    assert payload == {"diagnostics": {}, "job_id": "job-1", "found": True}
    assert explicit == {"job_id": "custom-job", "found": False}
    assert "setdefault" not in _job_diagnostics_payload.__code__.co_names


def test_recent_history_payload_uses_bounded_iteration_not_slice():
    from app.diagnostics.sources import _recent_history_payload

    class NoSliceHistoryStore:
        def __init__(self, rows):
            self.rows = rows
            self.limits = []

        def list_recent(self, limit=20):
            self.limits.append(limit)
            return self.rows

    rows = _NoSliceList(
        {"id": f"analysis-{index}", "input_text": f"row {index}"}
        for index in range(20)
    )
    history = NoSliceHistoryStore(rows)

    payload = _recent_history_payload(history, limit=10)

    assert history.limits == [10]
    assert payload["limit"] == 10
    assert payload["returned_count"] == 10
    assert payload["items"][0]["id"] == "analysis-0"
    assert payload["items"][-1]["id"] == "analysis-9"


def test_recent_history_payload_skips_iteration_for_empty_or_single_rows():
    from app.diagnostics.sources import _recent_history_payload

    class NoIterRows(list):
        def __iter__(self):
            raise AssertionError("empty/single recent history payloads should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("recent history payloads should not slice")
            return super().__getitem__(index)

    class HistoryStore:
        def __init__(self, rows):
            self.rows = rows

        def list_recent(self, limit=20):
            return self.rows

    empty_payload = _recent_history_payload(HistoryStore(NoIterRows([])), limit=10)
    single_payload = _recent_history_payload(
        HistoryStore(NoIterRows([{"id": "analysis-1"}])),
        limit=10,
    )
    zero_limit_payload = _recent_history_payload(
        HistoryStore(NoIterRows([{"id": "analysis-1"}])),
        limit=0,
    )

    assert empty_payload == {"limit": 10, "returned_count": 0, "items": []}
    assert single_payload == {
        "limit": 10,
        "returned_count": 1,
        "items": [{"id": "analysis-1"}],
    }
    assert zero_limit_payload == {"limit": 0, "returned_count": 0, "items": []}
    assert "len" in _recent_history_payload.__code__.co_names


def test_recent_history_payload_accumulates_without_list_comprehension_frame():
    from app.diagnostics.sources import _recent_history_payload

    nested_code_names = {
        const.co_name
        for const in _recent_history_payload.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<listcomp>" not in nested_code_names


def test_runtime_source_descriptors_use_shared_cap_for_truncation_boundary():
    policy = DIAGNOSTIC_SANITIZATION_POLICY

    sources = build_default_diagnostic_sources(
        job_id="job-large",
        job_diagnostics_accessor=lambda _job_id: {"blob": "x"},
        generated_at=GENERATED_AT,
    )

    orchestration = next(
        source for source in sources if source.source_id == "orchestration-diagnostics"
    )
    assert orchestration.max_bytes == policy.runtime_source_max_bytes

    bundle = assemble_diagnostic_bundle(
        [
            sources_module.DiagnosticSource(
                source_id="runtime.large",
                name="Large runtime payload",
                category="runtime",
                payload="x" * (policy.runtime_source_max_bytes + 1),
                relative_path="runtime/large.txt",
                max_bytes=orchestration.max_bytes,
            )
        ],
        generated_at=GENERATED_AT,
    )

    record = bundle.manifest.sources[0]
    assert record.status == "truncated"
    assert record.max_bytes == policy.runtime_source_max_bytes
    assert record.included_bytes == policy.runtime_source_max_bytes


def test_nested_runtime_payloads_stop_at_shared_depth_cap():
    policy = DIAGNOSTIC_SANITIZATION_POLICY
    payload = {"level": "root"}
    cursor = payload
    for index in range(policy.max_jsonish_depth + 3):
        child = {"level": index}
        cursor["child"] = child
        cursor = child

    safe = sources_module._safe_jsonish(payload)
    cursor = safe
    for _index in range(policy.max_jsonish_depth):
        if not isinstance(cursor, dict) or cursor.get("child") == "<max-depth>":
            break
        cursor = cursor["child"]

    dumped = json.dumps(safe)
    assert "<max-depth>" in dumped
    assert f'"level": {policy.max_jsonish_depth + 2}' not in dumped
