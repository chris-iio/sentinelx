"""Integration proof for backend-only diagnostic export bundle assembly."""
from __future__ import annotations

import json
import zipfile
from io import BytesIO

from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
from app.enrichment.config_store import ConfigStore

GENERATED_AT = "2026-01-02T03:04:05Z"
VT_SECRET = "vt-integration-secret-123456"
PROVIDER_SECRET = "provider-integration-secret-abcdef"
JOB_TOKEN = "job-bearer-token-987654321"
CACHE_TOKEN = "cache-bearer-token-123456789"


class IntegrationCacheStore:
    def stats(self) -> dict[str, object]:
        return {
            "total_entries": 7,
            "oldest": "2026-01-01T00:00:00Z",
            "authorization": f"Bearer {CACHE_TOKEN}",
        }


class IntegrationHistoryStore:
    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        return [
            {
                "id": "analysis-1",
                "mode": "online",
                "total_count": 2,
                "top_verdict": "malicious",
                "created_at": "2026-01-01T00:00:00Z",
                "input_text": "indicator example.com and no provider keys",
            }
        ][:limit]


def _archive_entries(archive_bytes: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _manifest(bundle) -> dict[str, object]:
    return json.loads(_archive_entries(bundle.archive_bytes)["manifest.json"].decode("utf-8"))


def test_runtime_sources_assemble_into_deterministic_secret_free_bundle(tmp_path) -> None:
    """Default runtime sources produce a deterministic inspectable backend archive."""
    config = ConfigStore(tmp_path / "sentinelx.ini")
    config.set_vt_api_key(VT_SECRET)
    config.set_provider_key("GreyNoise", PROVIDER_SECRET)

    def job_accessor(job_id: str) -> dict[str, object]:
        return {
            "job_id": job_id,
            "found": True,
            "diagnostics": {
                "phase": "provider_lookup",
                "last_error": f"upstream failed with Bearer {JOB_TOKEN}",
            },
        }

    sources = build_default_diagnostic_sources(
        config_store=config,
        cache_store=IntegrationCacheStore(),
        history_store=IntegrationHistoryStore(),
        job_id="job-integration-1",
        job_diagnostics_accessor=job_accessor,
        generated_at=GENERATED_AT,
    )

    first = assemble_diagnostic_bundle(sources, generated_at=GENERATED_AT, config_store=config)
    second = assemble_diagnostic_bundle(list(reversed(sources)), generated_at=GENERATED_AT, config_store=config)

    assert first.archive_bytes == second.archive_bytes
    assert first.archive_paths == (
        "manifest.json",
        "runtime/cache-stats.json",
        "runtime/config-secret-inventory.json",
        "runtime/diagnostic-export-metadata.json",
        "runtime/health-checks.json",
        "runtime/history-save-diagnostics.json",
        "runtime/orchestration-diagnostics.json",
        "runtime/recent-history.json",
    )

    manifest = _manifest(first)
    assert manifest["generated_at"] == GENERATED_AT
    assert manifest["source_count"] == 7
    assert manifest["included_count"] == 7
    assert manifest["omitted_count"] == 0
    assert manifest["error_count"] == 0
    assert manifest["redaction_count"] >= 2

    records = {record["source_id"]: record for record in manifest["sources"]}  # type: ignore[index]
    assert records["config-secret-inventory"]["status"] == "included"
    assert records["cache-stats"]["status"] == "included"
    assert records["recent-history"]["status"] == "included"
    assert records["orchestration-diagnostics"]["status"] == "included"
    assert all(record["included_bytes"] <= record["max_bytes"] for record in records.values())

    entries = _archive_entries(first.archive_bytes)
    archive_text = first.archive_bytes.decode("latin1")
    for secret in (VT_SECRET, PROVIDER_SECRET, JOB_TOKEN, CACHE_TOKEN):
        assert secret not in archive_text
    assert "[REDACTED]" in archive_text

    config_payload = json.loads(entries["runtime/config-secret-inventory.json"].decode("utf-8"))
    assert config_payload["configured_secret_labels"] == [
        "configured_secret:provider:greynoise",
        "configured_secret:virustotal",
    ]
    cache_payload = json.loads(entries["runtime/cache-stats.json"].decode("utf-8"))
    assert cache_payload["authorization"] == "Bearer [REDACTED]"
    orchestration_payload = json.loads(entries["runtime/orchestration-diagnostics.json"].decode("utf-8"))
    assert orchestration_payload["diagnostics"]["last_error"] == "upstream failed with Bearer [REDACTED]"


def test_runtime_bundle_records_omitted_and_error_sources_without_aborting(tmp_path) -> None:
    """Missing and failing runtime dependencies remain visible in the manifest."""

    class FailingHistoryStore:
        def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
            raise RuntimeError(f"history unavailable with Bearer {JOB_TOKEN}")

    sources = build_default_diagnostic_sources(
        cache_store=None,
        history_store=FailingHistoryStore(),
        health_checks={"cache": {"status": "degraded", "detail": "cache_store_not_provided"}},
        generated_at=GENERATED_AT,
    )
    bundle = assemble_diagnostic_bundle(sources, generated_at=GENERATED_AT)

    manifest = _manifest(bundle)
    records = {record["source_id"]: record for record in manifest["sources"]}  # type: ignore[index]
    assert records["cache-stats"]["status"] == "omitted"
    assert records["cache-stats"]["omitted_reason"] == "cache_store_not_provided"
    assert records["config-secret-inventory"]["status"] == "omitted"
    assert records["recent-history"]["status"] == "error"
    assert records["recent-history"]["relative_path"] is None
    assert "Bearer [REDACTED]" in records["recent-history"]["safe_error_summary"]
    assert JOB_TOKEN not in json.dumps(manifest)
    assert "runtime/recent-history.json" not in _archive_entries(bundle.archive_bytes)


def test_diagnostic_export_route_is_registered_for_supported_app_slice(app) -> None:
    """S03 exposes backend assembly through the supported Flask route only."""
    registered_rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/diagnostics/export" in registered_rules
    assert "/api/diagnostics/export" not in registered_rules
