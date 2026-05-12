"""Integration-style tests for diagnostic export primitives composing safely."""
from __future__ import annotations

import json
from pathlib import Path

from app.diagnostics.contract import (
    DiagnosticManifest,
    DiagnosticSourceRecord,
    manifest_to_json,
)
from app.diagnostics.redaction import redact_diagnostic_payload, redact_diagnostic_text
from app.enrichment.config_store import ConfigStore


VT_SECRET = "vt-s01-composition-secret-123456"
GREYNOISE_SECRET = "gn-s01-composition-secret-abcdef"
ABUSEIPDB_SECRET = "abuse-s01-composition-secret-xyz987"
RUNTIME_BEARER = "runtime-bearer-secret-for-export"
RUNTIME_X_API_KEY = "runtime-x-api-key-for-export"
QUERY_TOKEN = "query-token-secret-for-export"
INLINE_API_KEY = "inline-api-key-secret-for-export"


def _configured_store(tmp_path: Path) -> ConfigStore:
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_vt_api_key(VT_SECRET)
    store.set_provider_key("GreyNoise", GREYNOISE_SECRET)
    store.set_provider_key("AbuseIPDB", ABUSEIPDB_SECRET)
    return store


def _dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _json_payload_source(
    *,
    source_id: str,
    name: str,
    category: str,
    payload: object,
    store: ConfigStore,
) -> tuple[DiagnosticSourceRecord, object]:
    redacted, metadata = redact_diagnostic_payload(payload, config_store=store)
    encoded = _dump(redacted).encode("utf-8")
    return (
        DiagnosticSourceRecord(
            source_id=source_id,
            name=name,
            category=category,
            status="included",
            logical_label=name,
            content_type="application/json",
            original_bytes=len(encoded),
            included_bytes=len(encoded),
            redaction_count=metadata.redaction_count,
            redaction_labels=metadata.redaction_labels,
        ),
        redacted,
    )


def test_redaction_then_manifest_contract_preserves_safe_diagnostic_context(tmp_path: Path) -> None:
    store = _configured_store(tmp_path)
    orchestrator_payload = {
        "provider": "VirusTotal",
        "dispatch_count": 4,
        "error_count": 1,
        "last_error": f"VT lookup failed with {VT_SECRET}; api_key={INLINE_API_KEY}",
        "headers": {"Authorization": f"Bearer {RUNTIME_BEARER}"},
    }
    history_payload = {
        "source": "history.save",
        "saved_count": 2,
        "provider_results": [
            {"provider": "GreyNoise", "verdict": "benign", "key": GREYNOISE_SECRET},
            {
                "provider": "AbuseIPDB",
                "verdict": "suspicious",
                "url": f"https://api.example.test/check?token={QUERY_TOKEN}",
            },
        ],
    }
    settings_payload = {
        "virustotal": {"configured": True, "api_key": VT_SECRET},
        "providers": {
            "GreyNoise": {"enabled": True, "api_key": GREYNOISE_SECRET},
            "AbuseIPDB": {"enabled": False, "api_key": ABUSEIPDB_SECRET},
        },
        "cache_ttl_hours": 24,
    }

    orchestrator_source, redacted_orchestrator = _json_payload_source(
        source_id="orchestrator.summary",
        name="Orchestrator summary",
        category="orchestrator",
        payload=orchestrator_payload,
        store=store,
    )
    history_source, redacted_history = _json_payload_source(
        source_id="history.save.summary",
        name="History save summary",
        category="history",
        payload=history_payload,
        store=store,
    )
    settings_source, redacted_settings = _json_payload_source(
        source_id="settings.config.excerpt",
        name="Settings config excerpt",
        category="config",
        payload=settings_payload,
        store=store,
    )

    provider_error_text, provider_error_metadata = redact_diagnostic_text(
        (
            f"GreyNoise request failed Authorization: Bearer {RUNTIME_BEARER}; "
            f"x-api-key: {RUNTIME_X_API_KEY}; configured={GREYNOISE_SECRET}"
        ),
        config_store=store,
    )
    provider_error_source = DiagnosticSourceRecord(
        source_id="provider.error.greynoise",
        name="GreyNoise provider error",
        category="orchestrator",
        status="error",
        logical_label="GreyNoise provider error summary",
        safe_error_summary=provider_error_text,
        redaction_count=provider_error_metadata.redaction_count,
        redaction_labels=provider_error_metadata.redaction_labels,
    )

    log_bound = 512
    oversized_log = (
        f"provider=AbuseIPDB dispatch_count=4 error_count=1 api_key={INLINE_API_KEY} "
        f"configured_vt={VT_SECRET} configured_provider={ABUSEIPDB_SECRET}\n"
    ) * 20
    redacted_log, log_metadata = redact_diagnostic_text(oversized_log, config_store=store)
    redacted_log_bytes = redacted_log.encode("utf-8")
    included_log = redacted_log_bytes[:log_bound].decode("utf-8", errors="ignore")
    truncated_log_source = DiagnosticSourceRecord(
        source_id="runtime.oversized.log",
        name="Oversized runtime log",
        category="runtime",
        status="truncated",
        logical_label="bounded runtime diagnostic log",
        content_type="text/plain",
        original_bytes=len(redacted_log_bytes),
        included_bytes=len(included_log.encode("utf-8")),
        max_bytes=log_bound,
        redaction_count=log_metadata.redaction_count,
        redaction_labels=log_metadata.redaction_labels,
    )
    omitted_source = DiagnosticSourceRecord(
        source_id="config.raw.provider_secrets",
        name="Raw provider secrets",
        category="config",
        status="omitted",
        logical_label="configured provider secret values",
        omitted_reason="secret_only_source",
    )

    manifest = DiagnosticManifest(
        sources=(
            truncated_log_source,
            settings_source,
            omitted_source,
            provider_error_source,
            history_source,
            orchestrator_source,
        ),
        generated_at="2026-01-02T03:04:05Z",
    )
    manifest_json = manifest_to_json(manifest)
    bundle_document = {
        "manifest": json.loads(manifest_json),
        "payloads": {
            "orchestrator.summary": redacted_orchestrator,
            "history.save.summary": redacted_history,
            "settings.config.excerpt": redacted_settings,
            "provider.error.greynoise": provider_error_text,
            "runtime.oversized.log": included_log,
        },
    }
    serialized_bundle = _dump(bundle_document)

    assert manifest_json == manifest_to_json(manifest)
    assert [source["source_id"] for source in bundle_document["manifest"]["sources"]] == [
        "config.raw.provider_secrets",
        "history.save.summary",
        "orchestrator.summary",
        "provider.error.greynoise",
        "runtime.oversized.log",
        "settings.config.excerpt",
    ]
    assert bundle_document["manifest"]["included_count"] == 3
    assert bundle_document["manifest"]["truncated_count"] == 1
    assert bundle_document["manifest"]["omitted_count"] == 1
    assert bundle_document["manifest"]["error_count"] == 1
    assert bundle_document["manifest"]["redaction_count"] >= 10

    statuses_by_source = {
        source["source_id"]: source["status"] for source in bundle_document["manifest"]["sources"]
    }
    assert statuses_by_source == {
        "config.raw.provider_secrets": "omitted",
        "history.save.summary": "included",
        "orchestrator.summary": "included",
        "provider.error.greynoise": "error",
        "runtime.oversized.log": "truncated",
        "settings.config.excerpt": "included",
    }
    runtime_source = next(
        source
        for source in bundle_document["manifest"]["sources"]
        if source["source_id"] == "runtime.oversized.log"
    )
    assert runtime_source["truncated"] is True
    assert runtime_source["included_bytes"] == runtime_source["max_bytes"] == log_bound
    assert runtime_source["original_bytes"] > runtime_source["included_bytes"]
    assert "configured_secret:virustotal" in runtime_source["redaction_labels"]
    assert "configured_secret:provider:abuseipdb" in runtime_source["redaction_labels"]

    assert "VirusTotal" in serialized_bundle
    assert "GreyNoise" in serialized_bundle
    assert "AbuseIPDB" in serialized_bundle
    assert "dispatch_count" in serialized_bundle
    assert "error_count" in serialized_bundle
    assert "saved_count" in serialized_bundle
    assert "source_id" in serialized_bundle
    assert "safe_error_summary" in serialized_bundle
    assert "secret_only_source" in serialized_bundle

    for forbidden in [
        VT_SECRET,
        GREYNOISE_SECRET,
        ABUSEIPDB_SECRET,
        RUNTIME_BEARER,
        RUNTIME_X_API_KEY,
        QUERY_TOKEN,
        INLINE_API_KEY,
    ]:
        assert forbidden not in serialized_bundle


def test_flask_exposes_supported_diagnostic_export_route(app, client) -> None:  # noqa: ANN001
    registered_rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/diagnostics/export" in registered_rules
    assert "/api/diagnostics/export" not in registered_rules
    assert client.get("/api/diagnostics/export").status_code == 404
