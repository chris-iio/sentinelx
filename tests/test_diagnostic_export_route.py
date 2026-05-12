"""Route-level coverage for the analyst diagnostic export download."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO

import pytest

from app.diagnostics import DiagnosticBundle, DiagnosticManifest, DiagnosticSourceRecord

FIXED_NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
ROUTE_SECRET = "route-secret-token-123456789"


class RouteConfigStore:
    def get_vt_api_key(self) -> str | None:
        return ROUTE_SECRET

    def all_provider_keys(self) -> dict[str, str]:
        return {"RouteProvider": ROUTE_SECRET}


class RouteCacheStore:
    def stats(self) -> dict[str, object]:
        return {"total_entries": 1, "authorization": f"Bearer {ROUTE_SECRET}"}


class RouteHistoryStore:
    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        return [{"id": "analysis-1", "note": f"Bearer {ROUTE_SECRET}"}][:limit]


def _archive_entries(archive_bytes: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _patch_route_runtime(monkeypatch: pytest.MonkeyPatch, app) -> None:  # noqa: ANN001
    import app.routes.diagnostics as diagnostics_route

    monkeypatch.setattr(diagnostics_route, "ConfigStore", RouteConfigStore)
    monkeypatch.setattr(diagnostics_route, "_utcnow", lambda: FIXED_NOW)
    app.cache_store = RouteCacheStore()
    app.history_store = RouteHistoryStore()


def test_diagnostic_export_route_returns_zip_headers_manifest_and_redacted_payloads(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    _patch_route_runtime(monkeypatch, app)

    page = client.get("/")
    assert page.status_code == 200
    page_text = page.get_data(as_text=True)
    assert 'href="/diagnostics/export"' in page_text
    assert 'aria-label="Download diagnostic export"' in page_text

    response = client.get("/diagnostics/export")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="sentinelx-diagnostic-2026-01-02.zip"'
    )

    entries = _archive_entries(response.data)
    manifest = json.loads(entries["manifest.json"].decode("utf-8"))
    assert response.headers["X-Diagnostic-Sources"] == str(manifest["source_count"])
    assert manifest["generated_at"] == "2026-01-02T03:04:05Z"
    assert manifest["source_count"] >= 6
    assert manifest["redaction_count"] >= 1
    assert "runtime/cache-stats.json" in entries
    assert "runtime/recent-history.json" in entries
    assert ROUTE_SECRET not in response.data.decode("latin1")
    assert b"[REDACTED]" in response.data


def test_diagnostic_export_route_logs_bounded_assembly_error(
    app, client, monkeypatch: pytest.MonkeyPatch, caplog  # noqa: ANN001
) -> None:
    import app.routes.diagnostics as diagnostics_route

    _patch_route_runtime(monkeypatch, app)

    def fail_assembly(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError(f"boom with {ROUTE_SECRET}")

    monkeypatch.setattr(diagnostics_route, "assemble_diagnostic_bundle", fail_assembly)

    with caplog.at_level("ERROR", logger="app.routes.diagnostics"):
        response = client.get("/diagnostics/export")

    assert response.status_code == 500
    assert response.headers["Content-Type"].startswith("text/plain")
    assert response.get_data(as_text=True) == "Diagnostic export failed. Check server logs."
    assert ROUTE_SECRET not in response.get_data(as_text=True)
    assert any(record.getMessage() == "Diagnostic export assembly failed" for record in caplog.records)
    assert all(ROUTE_SECRET not in record.getMessage() for record in caplog.records)
    assert any(record.exc_info for record in caplog.records)


def test_diagnostic_export_route_is_rate_limited(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    import app.routes.diagnostics as diagnostics_route

    _patch_route_runtime(monkeypatch, app)
    fake_manifest = DiagnosticManifest(
        sources=(
            DiagnosticSourceRecord(
                source_id="rate-limit-source",
                name="Rate limit source",
                category="metadata",
                status="included",
                logical_label="Rate limit source",
                original_bytes=2,
                included_bytes=2,
                max_bytes=2,
            ),
        ),
        generated_at="2026-01-02T03:04:05Z",
    )
    fake_bundle = DiagnosticBundle(
        archive_bytes=b"PK\x05\x06" + (b"\x00" * 18),
        manifest=fake_manifest,  # type: ignore[arg-type]
        archive_paths=("manifest.json",),
    )
    monkeypatch.setattr(diagnostics_route, "assemble_diagnostic_bundle", lambda *args, **kwargs: fake_bundle)

    responses = [client.get("/diagnostics/export") for _ in range(4)]

    assert [response.status_code for response in responses] == [200, 200, 200, 429]
