import json
import dis
import inspect
import zipfile
from io import BytesIO

from app.diagnostics import sources as sources_module
from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
from app.diagnostics import runtime_payloads
from app.diagnostics.policy import (
    DIAGNOSTIC_SANITIZATION_POLICY,
    DiagnosticSanitizationPolicy,
)
from app.diagnostics.secret_inventory import ConfiguredSecretInventory
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
    import app.diagnostics as diagnostics_facade
    import app.diagnostics.policy as policy_module
    import app.diagnostics.source_record_fields as source_record_fields

    policy = DIAGNOSTIC_SANITIZATION_POLICY

    assert not hasattr(policy, "__dict__")
    assert diagnostics_facade.DEFAULT_SOURCE_MAX_BYTES is source_record_fields.DEFAULT_SOURCE_MAX_BYTES
    assert policy_module.DEFAULT_SOURCE_MAX_BYTES is source_record_fields.DEFAULT_SOURCE_MAX_BYTES
    assert DiagnosticSanitizationPolicy().runtime_source_max_bytes == 16 * 1024
    assert sources_module._SOURCE_MAX_BYTES == policy.runtime_source_max_bytes
    assert not hasattr(runtime_payloads, "_MAX_SAFE_STRING_CHARS")
    assert not hasattr(runtime_payloads, "_MAX_LIST_ITEMS")
    assert not hasattr(runtime_payloads, "_MAX_DICT_ITEMS")
    assert not hasattr(runtime_payloads, "_MAX_DEPTH")
    assert "from app.diagnostics.contract import DEFAULT_SOURCE_MAX_BYTES" not in inspect.getsource(
        policy_module
    )
    facade_source = inspect.getsource(diagnostics_facade)
    assert "from app.diagnostics.source_record_fields import" in facade_source
    assert "DEFAULT_SOURCE_MAX_BYTES" in facade_source
    assert "MAX_SAFE_ERROR_SUMMARY_CHARS" in facade_source
    assert "_MAX_SAFE_STRING_CHARS" not in inspect.getsource(sources_module)
    assert "_MAX_SAFE_STRING_CHARS" not in inspect.getsource(runtime_payloads)
    assert "_jsonish" not in inspect.getsource(sources_module)


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
    # Error summaries never export exception-controlled text, redacted or not:
    # collector exceptions can carry secrets outside the configured inventory.
    assert records["cache-stats"]["safe_error_summary"] == "RuntimeError: source collection failed"
    assert records["recent-history"]["safe_error_summary"] == "ValueError: source collection failed"
    assert "cache down" not in manifest_text


def test_config_secret_inventory_payload_accumulates_labels_without_list_constructor() -> None:
    instructions = list(
        dis.get_instructions(runtime_payloads.config_secret_inventory_payload_from_inventory)
    )
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

    assert (
        "config_secret_inventory_payload_from_inventory"
        in runtime_payloads.config_secret_inventory_payload.__code__.co_names
    )
    assert list_calls == []


def test_config_secret_inventory_payload_helper_owns_public_shape() -> None:
    inventory = ConfiguredSecretInventory(
        secret_labels=("configured_secret:provider:alpha", "configured_secret:virustotal"),
        provider_labels=("alpha",),
        config_error=None,
    )

    payload = runtime_payloads.config_secret_inventory_payload_from_inventory(inventory)

    assert payload == {
        "configured_secret_count": 2,
        "configured_secret_labels": [
            "configured_secret:provider:alpha",
            "configured_secret:virustotal",
        ],
        "provider_count": 1,
        "provider_labels": ["alpha"],
        "config_error": None,
    }
    assert "copy_label_tuple" in (
        runtime_payloads.config_secret_inventory_payload_from_inventory.__code__.co_names
    )


def test_sources_delegate_runtime_payload_builders() -> None:
    """Diagnostic source descriptors should delegate payload shaping to runtime_payloads."""
    import inspect

    source = inspect.getsource(sources_module.build_default_diagnostic_sources)
    default_sources_source = inspect.getsource(sources_module._default_runtime_sources)
    helper_source = inspect.getsource(sources_module._runtime_source)
    config_source = inspect.getsource(sources_module._config_secret_source)
    cache_source = inspect.getsource(sources_module._cache_stats_source)
    recent_source = inspect.getsource(sources_module._recent_history_source)
    history_save_source = inspect.getsource(sources_module._history_save_source)
    health_source = inspect.getsource(sources_module._health_source)
    health_collector_source = inspect.getsource(sources_module._health_payload_collector)
    orchestration_source = inspect.getsource(sources_module._orchestration_source)

    assert sources_module.DiagnosticSource.__module__ == "app.diagnostics.source_preparation"
    assert "from . import runtime_payloads" in inspect.getsource(
        sources_module
    )
    assert "from app.diagnostics import runtime_payloads" not in inspect.getsource(sources_module)
    assert "from app.diagnostics.runtime_payloads import" not in inspect.getsource(sources_module)
    assert sources_module.DEFAULT_HISTORY_LIMIT is runtime_payloads.DEFAULT_HISTORY_LIMIT
    assert sources_module.JobDiagnosticsAccessor is runtime_payloads.JobDiagnosticsAccessor
    assert sources_module.HealthChecksProvider is runtime_payloads.HealthChecksProvider
    assert "JobDiagnosticsAccessor" not in sources_module.__all__
    assert "HealthChecksProvider" not in sources_module.__all__
    assert "build_default_diagnostic_sources" in sources_module.__all__
    assert "DiagnosticSource(" not in source
    assert "DiagnosticSource(" not in default_sources_source
    assert "_default_runtime_sources(" in source
    assert "_runtime_payloads" not in inspect.getsource(sources_module)
    assert "_optional_runtime_source(" not in source
    assert "_optional_runtime_source(" in config_source
    assert "_optional_runtime_source(" in cache_source
    assert "_optional_runtime_source(" in recent_source
    assert "_optional_runtime_source(" not in default_sources_source
    assert "\n        _runtime_source(" not in default_sources_source
    assert "_history_save_source(" in default_sources_source
    assert "DiagnosticSource(" in helper_source
    assert "runtime_payloads.history_save_diagnostics_payload" not in source
    assert "runtime_payloads.history_save_diagnostics_payload" in history_save_source
    assert "_config_secret_source(" in default_sources_source
    assert "_cache_stats_source(" in default_sources_source
    assert "_recent_history_source(" in default_sources_source
    assert "runtime_payloads.config_secret_inventory_payload" not in source
    assert "runtime_payloads.config_secret_inventory_payload" in config_source
    assert "runtime_payloads.cache_stats_payload" not in source
    assert "runtime_payloads.cache_stats_payload" in cache_source
    assert "runtime_payloads.recent_history_payload(" not in source
    assert "runtime_payloads.recent_history_payload(" in recent_source
    assert "runtime_payloads.health_payload(" not in source
    assert "runtime_payloads.health_payload(" not in health_source
    assert "runtime_payloads.health_payload(" in health_collector_source
    assert "runtime_payloads.job_diagnostics_payload(" not in source
    assert "runtime_payloads.job_diagnostics_payload(" in orchestration_source
    assert "def _recent_history_payload" not in inspect.getsource(sources_module)


def test_default_runtime_sources_owns_source_ordering(tmp_path) -> None:
    config = ConfigStore(tmp_path / "sentinelx.ini")
    cache = FakeCacheStore({"total_entries": 1})
    history = FakeHistoryStore([{"id": "analysis-1"}])
    context = sources_module._DefaultSourceContext(
        history_limit=3,
        generated_at=GENERATED_AT,
    )

    sources = sources_module._default_runtime_sources(
        context=context,
        config_store=config,
        cache_store=cache,
        history_store=history,
        health_checks={"cache": {"status": "ok", "detail": "static"}},
        job_id="job-1",
        job_diagnostics_accessor=lambda job_id: {"job_id": job_id},
    )

    assert [source.source_id for source in sources] == [
        "diagnostic-export-metadata",
        "config-secret-inventory",
        "cache-stats",
        "recent-history",
        "history-save-diagnostics",
        "health-checks",
        "orchestration-diagnostics",
    ]
    assert sources[0].payload is not None
    assert sources[0].payload["generated_at"] == GENERATED_AT
    assert sources[0].payload["history_limit"] == 3
    assert sources[3].collect is not None
    assert sources[3].collect()["limit"] == 3


def test_runtime_source_helper_owns_descriptor_defaults() -> None:
    source = sources_module._runtime_source(
        source_id="runtime.test",
        name="Runtime test",
        category="runtime",
        collect=lambda: {"ok": True},
        relative_path="runtime/test.json",
    )

    assert source.source_id == "runtime.test"
    assert source.name == "Runtime test"
    assert source.category == "runtime"
    assert source.collect is not None
    assert source.relative_path == "runtime/test.json"
    assert source.max_bytes == sources_module._SOURCE_MAX_BYTES


def test_optional_runtime_source_helper_owns_missing_or_present_dependency() -> None:
    import inspect

    dependency = object()
    omitted = sources_module._optional_runtime_source(
        dependency=None,
        source_id="runtime.optional",
        name="Runtime optional",
        category="runtime",
        omitted_reason="dependency_missing",
        collect=lambda store: {"store": store is dependency},
        relative_path="runtime/optional.json",
    )
    present = sources_module._optional_runtime_source(
        dependency=dependency,
        source_id="runtime.optional",
        name="Runtime optional",
        category="runtime",
        omitted_reason="dependency_missing",
        collect=lambda store: {"store": store is dependency},
        relative_path="runtime/optional.json",
    )

    assert omitted.omitted_reason == "dependency_missing"
    assert omitted.collect is None
    assert present.collect is not None
    assert present.relative_path == "runtime/optional.json"
    assert present.max_bytes == sources_module._SOURCE_MAX_BYTES
    assert present.collect() == {"store": True}
    assert "_dependency_collector(" in inspect.getsource(
        sources_module._optional_runtime_source
    )


def test_dependency_collector_owns_dependency_capture() -> None:
    dependency = object()
    collector = sources_module._dependency_collector(
        dependency,
        lambda store: {"store": store is dependency},
    )

    assert collector() == {"store": True}


def test_optional_runtime_descriptor_helpers_own_fixed_source_shapes(tmp_path) -> None:
    config = ConfigStore(tmp_path / "sentinelx.ini")
    config.set_vt_api_key("vt-secret-value-123456")
    cache = FakeCacheStore({"total_entries": 1})
    history = FakeHistoryStore([{"id": "analysis-1"}])

    config_source = sources_module._config_secret_source(config)
    cache_source = sources_module._cache_stats_source(cache)
    history_source = sources_module._recent_history_source(history, 1)
    missing_history = sources_module._recent_history_source(None, 1)

    assert config_source.source_id == "config-secret-inventory"
    assert config_source.relative_path == "runtime/config-secret-inventory.json"
    assert config_source.collect is not None
    assert config_source.collect()["configured_secret_count"] == 1
    assert cache_source.source_id == "cache-stats"
    assert cache_source.collect is not None
    assert cache_source.collect()["total_entries"] == 1
    assert history_source.source_id == "recent-history"
    assert history_source.collect is not None
    assert history_source.collect()["returned_count"] == 1
    assert missing_history.omitted_reason == "history_store_not_provided"


def test_orchestration_source_helper_owns_request_branching() -> None:
    import inspect

    missing_job = sources_module._orchestration_source(
        job_id=None,
        job_diagnostics_accessor=lambda _job_id: {},
    )
    missing_accessor = sources_module._orchestration_source(
        job_id="job-1",
        job_diagnostics_accessor=None,
    )
    present = sources_module._orchestration_source(
        job_id="job-1",
        job_diagnostics_accessor=lambda job_id: {"job_id": job_id},
    )

    assert missing_job.omitted_reason == "job_id_not_provided"
    assert missing_accessor.omitted_reason == "job_diagnostics_accessor_not_provided"
    assert present.source_id == "orchestration-diagnostics"
    assert present.relative_path == "runtime/orchestration-diagnostics.json"
    assert present.collect is not None
    assert present.collect() == {"job_id": "job-1", "found": True}
    assert "_omitted_orchestration_source" in (
        sources_module._orchestration_source.__code__.co_names
    )
    assert "_omitted(" not in inspect.getsource(sources_module._orchestration_source)


def test_omitted_orchestration_source_helper_owns_fixed_descriptor() -> None:
    omitted = sources_module._omitted_orchestration_source("job_missing")

    assert omitted.source_id == "orchestration-diagnostics"
    assert omitted.name == "Orchestration diagnostics"
    assert omitted.category == "orchestrator"
    assert omitted.omitted_reason == "job_missing"
    assert omitted.max_bytes == sources_module._SOURCE_MAX_BYTES


def test_health_source_helper_owns_dependency_capture() -> None:
    import inspect

    checks = {"cache": {"status": "ok", "detail": "static"}}
    config_store = object()
    cache_store = object()
    history_store = object()

    source = sources_module._health_source(
        health_checks=checks,
        config_store=config_store,
        cache_store=cache_store,
        history_store=history_store,
    )

    assert source.source_id == "health-checks"
    assert source.relative_path == "runtime/health-checks.json"
    assert source.max_bytes == sources_module._SOURCE_MAX_BYTES
    assert source.collect is not None
    assert source.collect()["checks"]["cache"]["detail"] == "static"
    assert "_health_payload_collector(" in inspect.getsource(sources_module._health_source)
    assert "runtime_payloads.health_payload(" not in inspect.getsource(
        sources_module._health_source
    )


def test_health_payload_collector_owns_dependency_capture() -> None:
    checks = {"cache": {"status": "ok", "detail": "static"}}
    collector = sources_module._health_payload_collector(
        health_checks=checks,
        config_store=object(),
        cache_store=object(),
        history_store=None,
    )

    payload = collector()

    assert payload["checks"]["cache"]["detail"] == "static"
    assert payload["checks"]["history"]["detail"] == "unavailable"


def test_history_save_source_helper_owns_fixed_descriptor() -> None:
    source = sources_module._history_save_source()

    assert source.source_id == "history-save-diagnostics"
    assert source.name == "History save diagnostics"
    assert source.category == "history"
    assert source.relative_path == "runtime/history-save-diagnostics.json"
    assert source.max_bytes == sources_module._SOURCE_MAX_BYTES
    assert source.collect is sources_module.runtime_payloads.history_save_diagnostics_payload


def test_default_source_context_owns_history_limit_and_timestamp(monkeypatch) -> None:
    monkeypatch.setattr(sources_module, "_utcnow_iso", lambda: "clock-now")

    explicit = sources_module._default_source_context(
        history_limit=99,
        generated_at=GENERATED_AT,
    )
    fallback = sources_module._default_source_context(
        history_limit=True,
        generated_at=None,
    )

    assert explicit.history_limit == sources_module.DEFAULT_HISTORY_LIMIT
    assert explicit.generated_at == GENERATED_AT
    assert fallback.history_limit == sources_module.DEFAULT_HISTORY_LIMIT
    assert fallback.generated_at == "clock-now"


def test_diagnostic_metadata_source_owns_payload_shape() -> None:
    """Diagnostic export metadata payload shape should live outside the source list builder."""
    import inspect

    source = inspect.getsource(sources_module.build_default_diagnostic_sources)
    default_sources_source = inspect.getsource(sources_module._default_runtime_sources)
    helper_source = inspect.getsource(sources_module._metadata_source)
    payload_source = inspect.getsource(sources_module._metadata_payload)
    metadata = sources_module._metadata_source(
        generated_at=GENERATED_AT,
        history_limit=7,
        job_id_requested=True,
        config_store=object(),
        cache_store=None,
        history_store=object(),
        job_diagnostics_accessor=lambda _job_id: {},
    )
    payload = sources_module._metadata_payload(
        generated_at=GENERATED_AT,
        history_limit=7,
        job_id_requested=True,
        config_store=object(),
        cache_store=None,
        history_store=object(),
        job_diagnostics_accessor=lambda _job_id: {},
    )

    assert metadata.source_id == "diagnostic-export-metadata"
    assert metadata.relative_path == "runtime/diagnostic-export-metadata.json"
    assert metadata.payload == payload
    assert payload == {
        "schema": "sentinelx.diagnostic_sources.v1",
        "generated_at": GENERATED_AT,
        "history_limit": 7,
        "job_id_requested": True,
        "runtime_objects": {
            "config_store": True,
            "cache_store": False,
            "history_store": True,
            "job_diagnostics_accessor": True,
        },
    }
    assert "_default_runtime_sources(" in source
    assert "_metadata_source(" in default_sources_source
    assert "_default_source_context(" in source
    assert "_health_source(" in default_sources_source
    assert "_history_save_source(" in default_sources_source
    assert "_bounded_limit(" not in source
    assert "_utcnow_iso(" not in source
    assert "_orchestration_source(" in default_sources_source
    assert "config_store_not_provided" not in source
    assert "cache_store_not_provided" not in source
    assert "history_store_not_provided" not in source
    assert "job_diagnostics_accessor_not_provided" not in source
    assert "sentinelx.diagnostic_sources.v1" not in source
    assert "runtime_objects" not in source
    assert "_metadata_payload(" in helper_source
    assert "sentinelx.diagnostic_sources.v1" not in helper_source
    assert "runtime_objects" not in helper_source
    assert "sentinelx.diagnostic_sources.v1" in payload_source
    assert "runtime_objects" in payload_source


def test_copy_label_tuple_skips_iteration_for_empty_single_pair_three_or_four_labels() -> None:
    class NoIterTuple(tuple):
        def __iter__(self):
            raise AssertionError("short label copies should not iterate")

    assert runtime_payloads.copy_label_tuple(NoIterTuple(())) == []
    assert runtime_payloads.copy_label_tuple(NoIterTuple(("configured_secret:virustotal",))) == [
        "configured_secret:virustotal"
    ]
    assert runtime_payloads.copy_label_tuple(NoIterTuple(("b", "a"))) == ["b", "a"]
    assert runtime_payloads.copy_label_tuple(NoIterTuple(("c", "b", "a"))) == ["c", "b", "a"]
    assert runtime_payloads.copy_label_tuple(NoIterTuple(("d", "c", "b", "a"))) == [
        "d",
        "c",
        "b",
        "a",
    ]
    assert "len" in runtime_payloads.copy_label_tuple.__code__.co_names


def test_copy_label_tuple_delegates_long_path_append() -> None:
    labels = ("a", "b", "c", "d", "e")

    copied = runtime_payloads.copy_label_tuple(labels)

    source = inspect.getsource(runtime_payloads.copy_label_tuple)
    append_source = inspect.getsource(runtime_payloads.append_label_copy)
    assert copied == ["a", "b", "c", "d", "e"]
    assert "append_label_copy(copied, label)" in source
    assert "copied.append(label)" not in source
    assert "copied.append(label)" in append_source


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


def test_health_checks_mapping_owns_resolution_and_validation() -> None:
    from app.diagnostics.runtime_payloads import (
        health_checks_mapping,
        health_payload,
        resolved_health_checks,
    )

    static_checks = {"cache": {"status": "ok", "detail": "static"}}
    callable_checks = {"history": {"status": "degraded", "detail": "callable"}}
    config_store = object()
    cache_store = object()

    assert health_checks_mapping(static_checks, None, None, None) is static_checks
    assert health_checks_mapping(lambda: callable_checks, None, None, None) is callable_checks
    assert health_checks_mapping(None, config_store, cache_store, None) == {
        "cache": {"status": "ok", "detail": "available"},
        "history": {"status": "degraded", "detail": "history_store_not_provided"},
        "registry": {"status": "ok", "detail": "available"},
    }
    assert resolved_health_checks(static_checks, None, None, None) is static_checks
    assert resolved_health_checks(lambda: callable_checks, None, None, None) is callable_checks

    try:
        health_checks_mapping(lambda: ["not", "mapping"], None, None, None)
    except TypeError as exc:
        assert str(exc) == "health checks provider returned non-mapping diagnostics"
    else:
        raise AssertionError("non-mapping health checks should fail")

    assert "health_checks_mapping" in health_payload.__code__.co_names
    assert "resolved_health_checks" in health_checks_mapping.__code__.co_names
    assert "default_health_checks" not in health_payload.__code__.co_names
    assert "default_health_checks" not in health_checks_mapping.__code__.co_names


def test_resolved_health_checks_owns_source_selection() -> None:
    from app.diagnostics.runtime_payloads import resolved_health_checks

    static_checks = {"cache": {"status": "ok", "detail": "static"}}
    callable_checks = {"history": {"status": "degraded", "detail": "callable"}}

    assert resolved_health_checks(static_checks, None, None, None) is static_checks
    assert resolved_health_checks(lambda: callable_checks, None, None, None) is callable_checks
    assert resolved_health_checks(None, object(), None, object()) == {
        "cache": {"status": "degraded", "detail": "cache_store_not_provided"},
        "history": {"status": "ok", "detail": "available"},
        "registry": {"status": "ok", "detail": "available"},
    }
    assert "default_health_checks" in resolved_health_checks.__code__.co_names


def test_safe_mapping_uses_bounded_iteration_for_nested_mappings():
    from app.diagnostics.jsonish import _safe_mapping

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
    from app.diagnostics.jsonish import (
        _safe_jsonish,
        _safe_jsonish_mapping,
        _safe_jsonish_sequence,
        _safe_jsonish_set,
    )

    helper_codes = (
        _safe_jsonish.__code__,
        _safe_jsonish_mapping.__code__,
        _safe_jsonish_sequence.__code__,
        _safe_jsonish_set.__code__,
    )

    assert _safe_jsonish({"items": [1, "two"]}) == {"items": [1, "two"]}
    for code in helper_codes:
        nested_code_names = {
            const.co_name
            for const in code.co_consts
            if hasattr(const, "co_name")
        }
        assert "<dictcomp>" not in nested_code_names
        assert "<listcomp>" not in nested_code_names


def test_safe_jsonish_skips_iteration_for_exact_empty_single_pair_three_or_four_containers():
    import app.diagnostics.jsonish as jsonish
    from app.diagnostics.jsonish import (
        _safe_jsonish,
        _safe_jsonish_mapping,
        _safe_jsonish_sequence,
    )

    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short list diagnostics should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("diagnostic list sanitization should not slice")
            return super().__getitem__(index)

    assert _safe_jsonish({}) == {}
    assert _safe_jsonish({"item": NoIterList(["value"])}) == {"item": ["value"]}
    assert _safe_jsonish({"first": 1, "second": ("two",)}) == {
        "first": 1,
        "second": ["two"],
    }
    assert _safe_jsonish({"first": 1, "second": "two", "third": None}) == {
        "first": 1,
        "second": "two",
        "third": None,
    }
    assert _safe_jsonish(
        {"first": 1, "second": "two", "third": None, "fourth": True}
    ) == {
        "first": 1,
        "second": "two",
        "third": None,
        "fourth": True,
    }
    assert _safe_jsonish(NoIterList([])) == []
    assert _safe_jsonish(NoIterList(["value"])) == ["value"]
    assert _safe_jsonish(NoIterList(["first", "second"])) == ["first", "second"]
    assert _safe_jsonish(NoIterList(["first", "second", "third"])) == [
        "first",
        "second",
        "third",
    ]
    assert _safe_jsonish(NoIterList(["first", "second", "third", "fourth"])) == [
        "first",
        "second",
        "third",
        "fourth",
    ]
    assert "_safe_jsonish_sequence" in _safe_jsonish.__code__.co_names
    assert "len" in _safe_jsonish_sequence.__code__.co_names
    assert "value_count == 4" in inspect.getsource(_safe_jsonish_mapping)
    mapping_source = inspect.getsource(_safe_jsonish_mapping)
    sequence_source = inspect.getsource(_safe_jsonish_sequence)
    mapping_setter_source = inspect.getsource(jsonish._set_safe_jsonish_mapping_value)
    append_source = inspect.getsource(jsonish._append_safe_jsonish_item)
    assert (
        "_set_safe_jsonish_mapping_value(safe, key, value[key], depth=child_depth)"
        in mapping_source
    )
    assert (
        "safe[str(key)[:80]] = _safe_jsonish(value[key], depth=child_depth)"
        not in mapping_source
    )
    assert "safe[str(key)[:80]] = _safe_jsonish(child, depth=depth)" in mapping_setter_source
    assert "_append_safe_jsonish_item(safe_items, item, depth=child_depth)" in sequence_source
    assert "safe_items.append(_safe_jsonish(item, depth=child_depth))" not in sequence_source
    assert "safe_items.append(_safe_jsonish(item, depth=depth))" in append_source


def test_safe_jsonish_helpers_own_container_and_default_coercion():
    from app.diagnostics.jsonish import (
        _safe_jsonish,
        _safe_jsonish_default,
        _safe_jsonish_mapping,
        _safe_jsonish_sequence,
        _safe_jsonish_set,
    )

    payload = {"item": ("value", object())}

    assert _safe_jsonish_mapping(payload, depth=0)["item"][0] == "value"
    assert _safe_jsonish_sequence(("value", object()), depth=0)[0] == "value"
    assert _safe_jsonish_set({"value"}, depth=0) == ["value"]
    assert _safe_jsonish_default(object()).startswith("<object object at ")
    set_source = inspect.getsource(_safe_jsonish_set)
    assert "_append_safe_jsonish_item(safe_items, item, depth=child_depth)" in set_source
    assert "safe_items.append(_safe_jsonish(item, depth=child_depth))" not in set_source
    assert "_safe_jsonish_mapping" in _safe_jsonish.__code__.co_names
    assert "_safe_jsonish_sequence" in _safe_jsonish.__code__.co_names
    assert "_safe_jsonish_set" in _safe_jsonish.__code__.co_names
    assert "_safe_jsonish_default" in _safe_jsonish.__code__.co_names


def test_job_diagnostics_payload_adds_defaults_without_setdefault() -> None:
    from app.diagnostics.runtime_payloads import job_diagnostics_payload, safe_job_diagnostics_payload

    payload = job_diagnostics_payload(lambda _job_id: {"diagnostics": {}}, "job-1")
    explicit = job_diagnostics_payload(
        lambda _job_id: {"job_id": "custom-job", "found": False},
        "job-1",
    )

    assert payload == {"diagnostics": {}, "job_id": "job-1", "found": True}
    assert explicit == {"job_id": "custom-job", "found": False}
    assert "setdefault" not in job_diagnostics_payload.__code__.co_names
    assert "safe_job_diagnostics_payload" in job_diagnostics_payload.__code__.co_names
    assert "apply_job_diagnostics_defaults" in safe_job_diagnostics_payload.__code__.co_names


def test_safe_job_diagnostics_payload_owns_mapping_coercion_and_defaults() -> None:
    from app.diagnostics.runtime_payloads import safe_job_diagnostics_payload

    payload = safe_job_diagnostics_payload({"diagnostics": {"value": object()}}, "job-1")

    assert payload["job_id"] == "job-1"
    assert payload["found"] is True
    assert payload["diagnostics"]["value"].startswith("<object object at ")
    assert "_safe_mapping" in safe_job_diagnostics_payload.__code__.co_names
    assert "apply_job_diagnostics_defaults" in safe_job_diagnostics_payload.__code__.co_names


def test_job_diagnostics_defaults_helper_owns_payload_mutation() -> None:
    from app.diagnostics.runtime_payloads import apply_job_diagnostics_defaults

    payload = {"diagnostics": {}}
    explicit = {"job_id": "custom-job", "found": False}

    apply_job_diagnostics_defaults(payload, "job-1")
    apply_job_diagnostics_defaults(explicit, "job-1")

    assert payload == {"diagnostics": {}, "job_id": "job-1", "found": True}
    assert explicit == {"job_id": "custom-job", "found": False}
    assert "setdefault" not in apply_job_diagnostics_defaults.__code__.co_names


def test_recent_history_payload_uses_bounded_iteration_not_slice():
    from app.diagnostics.runtime_payloads import recent_history_payload, recent_history_items

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

    payload = recent_history_payload(history, limit=10)

    assert history.limits == [10]
    assert payload["limit"] == 10
    assert payload["returned_count"] == 10
    assert payload["items"][0]["id"] == "analysis-0"
    assert payload["items"][-1]["id"] == "analysis-9"
    assert "recent_history_items" in recent_history_payload.__code__.co_names
    assert "islice" not in recent_history_payload.__code__.co_names
    assert "islice" in recent_history_items.__code__.co_names


def test_recent_history_payload_skips_iteration_for_four_or_fewer_rows():
    from app.diagnostics.runtime_payloads import recent_history_items, recent_history_payload

    class NoIterRows(list):
        def __iter__(self):
            raise AssertionError("short recent history payloads should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("recent history payloads should not slice")
            return super().__getitem__(index)

    class HistoryStore:
        def __init__(self, rows):
            self.rows = rows

        def list_recent(self, limit=20):
            return self.rows

    empty_payload = recent_history_payload(HistoryStore(NoIterRows([])), limit=10)
    single_payload = recent_history_payload(
        HistoryStore(NoIterRows([{"id": "analysis-1"}])),
        limit=10,
    )
    pair_payload = recent_history_payload(
        HistoryStore(NoIterRows([{"id": "analysis-1"}, {"id": "analysis-2"}])),
        limit=10,
    )
    three_payload = recent_history_payload(
        HistoryStore(NoIterRows([
            {"id": "analysis-1"},
            {"id": "analysis-2"},
            {"id": "analysis-3"},
        ])),
        limit=10,
    )
    four_payload = recent_history_payload(
        HistoryStore(NoIterRows([
            {"id": "analysis-1"},
            {"id": "analysis-2"},
            {"id": "analysis-3"},
            {"id": "analysis-4"},
        ])),
        limit=10,
    )
    zero_limit_payload = recent_history_payload(
        HistoryStore(NoIterRows([{"id": "analysis-1"}])),
        limit=0,
    )

    assert empty_payload == {"limit": 10, "returned_count": 0, "items": []}
    assert single_payload == {
        "limit": 10,
        "returned_count": 1,
        "items": [{"id": "analysis-1"}],
    }
    assert pair_payload == {
        "limit": 10,
        "returned_count": 2,
        "items": [{"id": "analysis-1"}, {"id": "analysis-2"}],
    }
    assert three_payload == {
        "limit": 10,
        "returned_count": 3,
        "items": [
            {"id": "analysis-1"},
            {"id": "analysis-2"},
            {"id": "analysis-3"},
        ],
    }
    assert four_payload == {
        "limit": 10,
        "returned_count": 4,
        "items": [
            {"id": "analysis-1"},
            {"id": "analysis-2"},
            {"id": "analysis-3"},
            {"id": "analysis-4"},
        ],
    }
    assert zero_limit_payload == {"limit": 0, "returned_count": 0, "items": []}
    assert "len" in recent_history_payload.__code__.co_names
    assert "len" in recent_history_items.__code__.co_names
    assert "recent_count == 4" in inspect.getsource(recent_history_items)


def test_recent_history_payload_accumulates_without_list_comprehension_frame():
    from app.diagnostics.runtime_payloads import recent_history_items, recent_history_payload

    for code in (recent_history_payload.__code__, recent_history_items.__code__):
        nested_code_names = {
            const.co_name
            for const in code.co_consts
            if hasattr(const, "co_name")
        }
        assert "<listcomp>" not in nested_code_names


def test_recent_history_items_owns_safe_row_coercion() -> None:
    from app.diagnostics.runtime_payloads import append_recent_history_item, recent_history_items

    rows = _NoSliceList(
        {"id": f"analysis-{index}", "input_text": object()}
        for index in range(3)
    )

    items = recent_history_items(rows, limit=2)

    assert len(items) == 2
    assert items[0]["input_text"].startswith("<object object at ")
    items_source = inspect.getsource(recent_history_items)
    append_source = inspect.getsource(append_recent_history_item)
    assert "append_recent_history_item(safe_recent, item)" in items_source
    assert "safe_recent.append(_safe_jsonish(item))" not in items_source.split("safe_recent: list[Any] = []", 1)[1]
    assert "safe_recent.append(_safe_jsonish(item))" in append_source
    assert "islice" in recent_history_items.__code__.co_names
    assert "append_recent_history_item" in recent_history_items.__code__.co_names
    assert "_safe_jsonish" in append_recent_history_item.__code__.co_names


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

    from app.diagnostics.jsonish import _safe_jsonish

    safe = _safe_jsonish(payload)
    cursor = safe
    for _index in range(policy.max_jsonish_depth):
        if not isinstance(cursor, dict) or cursor.get("child") == "<max-depth>":
            break
        cursor = cursor["child"]

    dumped = json.dumps(safe)
    assert "<max-depth>" in dumped
    assert f'"level": {policy.max_jsonish_depth + 2}' not in dumped
