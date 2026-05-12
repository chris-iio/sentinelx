import json
import zipfile
from io import BytesIO

from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
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
