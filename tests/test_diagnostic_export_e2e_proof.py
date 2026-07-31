"""End-to-end proof for analyst diagnostic export archive consistency."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from io import BytesIO

import pytest

FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
PROOF_SECRET = "proof-secret-token-123456789"


class ProofConfigStore:
    def get_vt_api_key(self) -> str | None:
        return PROOF_SECRET

    def all_provider_keys(self) -> dict[str, str]:
        return {"ProofProvider": PROOF_SECRET}


class ProofCacheStore:
    def stats(self) -> dict[str, object]:
        return {"total_entries": 1, "authorization": f"Bearer {PROOF_SECRET}"}


class ProofHistoryStore:
    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        return [{"id": "analysis-1", "note": f"Bearer {PROOF_SECRET}"}][:limit]


def _patch_route_runtime(monkeypatch: pytest.MonkeyPatch, app) -> None:  # noqa: ANN001
    import app.routes.diagnostics as diagnostics_route
    import app.routes.diagnostic_export as export_helpers

    monkeypatch.setattr(diagnostics_route, "ConfigStore", ProofConfigStore)
    monkeypatch.setattr(export_helpers, "utc_now", lambda: FIXED_NOW)
    app.cache_store = ProofCacheStore()
    app.history_store = ProofHistoryStore()


def _download_manifest_and_entries(client) -> tuple[object, dict[str, object], dict[str, bytes]]:  # noqa: ANN001
    response = client.get("/diagnostics/export")
    assert response.status_code == 200

    with zipfile.ZipFile(BytesIO(response.data), "r") as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}

    manifest = json.loads(entries["manifest.json"].decode("utf-8"))
    return response, manifest, entries


def test_diagnostic_export_manifest_matches_archive_entries_and_runtime_json(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    _patch_route_runtime(monkeypatch, app)

    _response, manifest, entries = _download_manifest_and_entries(client)
    source_records = manifest["sources"]
    records_by_path = {
        record["relative_path"]: record
        for record in source_records
        if record["relative_path"] is not None
    }
    archive_payload_paths = set(entries) - {"manifest.json"}

    included_paths = {
        record["relative_path"]
        for record in source_records
        if record["status"] == "included"
    }
    assert None not in included_paths
    assert included_paths <= archive_payload_paths
    assert archive_payload_paths == set(records_by_path)
    assert all(
        records_by_path[path]["status"] in {"included", "truncated"}
        for path in archive_payload_paths
    )

    for path, payload in entries.items():
        if path.startswith("runtime/") and path.endswith(".json"):
            json.loads(payload.decode("utf-8"))

    assert manifest["source_count"] == len(source_records)
    assert manifest["included_count"] == sum(
        1 for record in source_records if record["status"] == "included"
    )


def test_diagnostic_export_raw_zip_bytes_do_not_include_configured_secrets(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    _patch_route_runtime(monkeypatch, app)

    response = client.get("/diagnostics/export")

    assert response.status_code == 200
    assert PROOF_SECRET.encode("utf-8") not in response.data
    assert b"[REDACTED]" in response.data


def test_diagnostic_export_download_headers_match_manifest_for_analysts(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    _patch_route_runtime(monkeypatch, app)

    response, manifest, _entries = _download_manifest_and_entries(client)

    assert response.headers["Content-Type"] == "application/zip"
    assert re.fullmatch(
        r'attachment; filename="sentinelx-diagnostic-\d{4}-\d{2}-\d{2}\.zip"',
        response.headers["Content-Disposition"],
    )
    source_header = response.headers["X-Diagnostic-Sources"]
    assert source_header.isdecimal()
    assert source_header == str(manifest["source_count"])
