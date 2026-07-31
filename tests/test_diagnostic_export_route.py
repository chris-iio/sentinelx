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
    import app.routes.diagnostic_export as export_helpers

    monkeypatch.setattr(diagnostics_route, "ConfigStore", RouteConfigStore)
    monkeypatch.setattr(export_helpers, "utc_now", lambda: FIXED_NOW)
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
    content_disposition = response.headers["Content-Disposition"]
    assert "attachment" in content_disposition.lower()
    assert content_disposition == 'attachment; filename="sentinelx-diagnostic-2026-01-02.zip"'
    assert ".zip" in content_disposition

    entries = _archive_entries(response.data)
    manifest = json.loads(entries["manifest.json"].decode("utf-8"))
    source_header = response.headers["X-Diagnostic-Sources"]
    assert source_header.isdecimal()
    assert source_header == str(manifest["source_count"])
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
    import app.routes.diagnostic_export as export_helpers

    _patch_route_runtime(monkeypatch, app)

    def fail_assembly(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError(f"boom with {ROUTE_SECRET}")

    monkeypatch.setattr(export_helpers, "assemble_diagnostic_bundle", fail_assembly)

    with caplog.at_level("ERROR", logger="app.routes.diagnostics"):
        response = client.get("/diagnostics/export")

    assert response.status_code == 500
    assert response.headers["Content-Type"].startswith("text/plain")
    body = response.get_data(as_text=True)
    assert "Diagnostic export failed" in body
    assert body == "Diagnostic export failed. Check server logs."
    assert ROUTE_SECRET not in body
    assert "boom with" not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    assert any(record.getMessage() == "Diagnostic export assembly failed" for record in caplog.records)
    assert all(ROUTE_SECRET not in record.getMessage() for record in caplog.records)
    assert any(record.exc_info for record in caplog.records)


def test_diagnostic_export_route_is_rate_limited(
    app, client, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    import app.routes.diagnostic_export as export_helpers

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
    monkeypatch.setattr(export_helpers, "assemble_diagnostic_bundle", lambda *args, **kwargs: fake_bundle)

    responses = [client.get("/diagnostics/export") for _ in range(4)]

    assert [response.status_code for response in responses] == [200, 200, 200, 429]


def test_diagnostic_export_route_delegates_response_helper() -> None:
    """The Flask route should not own diagnostic export response construction."""
    import inspect

    import app.routes.diagnostic_export as export_helpers
    import app.routes.diagnostics as diagnostics_route

    route_source = inspect.getsource(diagnostics_route.diagnostics_export)
    route_helper_source = inspect.getsource(export_helpers.diagnostic_export_route_response)
    helper_source = inspect.getsource(export_helpers.diagnostic_export_response)
    failure_source = inspect.getsource(export_helpers.diagnostic_export_failure_response)
    applier_source = inspect.getsource(export_helpers.apply_diagnostic_export_http_response)

    assert "diagnostic_export_route_response(" in route_source
    assert "cache_store=current_app.cache_store" in route_source
    assert "history_store=current_app.history_store" in route_source
    assert "utc_now" not in route_source
    assert not hasattr(diagnostics_route, "_utcnow")
    assert "diagnostic_export_response(" not in route_source
    assert "diagnostic_export_failure_response()" not in route_source
    assert "ConfigStore()" not in route_source
    assert "app=current_app" not in route_source
    assert "logger.error(" not in route_source
    assert "build_default_diagnostic_sources(" not in route_source
    assert "assemble_diagnostic_bundle(" not in route_source
    assert "Content-Disposition" not in route_source
    assert "X-Diagnostic-Sources" not in route_source
    assert "Diagnostic export failed. Check server logs." not in route_source
    assert "Response(" not in route_source
    assert "config_store_factory()" in route_helper_source
    assert "resolved_now_factory = utc_now if now_factory is None else now_factory" in route_helper_source
    assert "resolved_now_factory()" in route_helper_source
    assert "app.cache_store" not in route_helper_source
    assert "app.history_store" not in route_helper_source
    assert "cache_store=cache_store" in route_helper_source
    assert "history_store=history_store" in route_helper_source
    assert "failure_logger.error(" in route_helper_source
    assert "diagnostic_export_failure_response()" in route_helper_source
    assert "apply_diagnostic_export_http_response(" in route_helper_source
    assert "build_default_diagnostic_sources(" in helper_source
    assert "assemble_diagnostic_bundle(" in helper_source
    assert "Content-Disposition" in helper_source
    assert "return Response(" not in helper_source
    assert export_helpers.DIAGNOSTIC_EXPORT_FAILURE_BODY == (
        "Diagnostic export failed. Check server logs."
    )
    assert "DIAGNOSTIC_EXPORT_FAILURE_BODY" in failure_source
    assert "mimetype=\"text/plain\"" in failure_source
    assert "return Response(" not in failure_source
    assert "response_factory(" in applier_source


def test_diagnostic_export_route_response_accepts_explicit_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route helper clock capture should be injectable without monkeypatching utc_now."""
    import inspect

    import app.routes.diagnostic_export as export_helpers

    calls: list[dict[str, object]] = []
    config_store = RouteConfigStore()
    cache_store = RouteCacheStore()
    history_store = RouteHistoryStore()

    def export_response(**kwargs):
        calls.append(kwargs)
        return export_helpers.DiagnosticExportHttpResponse("ok", mimetype="text/plain")

    monkeypatch.setattr(export_helpers, "diagnostic_export_response", export_response)

    response = export_helpers.diagnostic_export_route_response(
        cache_store=cache_store,
        history_store=history_store,
        now_factory=lambda: FIXED_NOW,
        config_store_factory=lambda: config_store,
        failure_logger=object(),
    )
    helper_source = inspect.getsource(export_helpers.diagnostic_export_route_response)

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
    assert calls == [{
        "timestamp": FIXED_NOW,
        "config_store": config_store,
        "cache_store": cache_store,
        "history_store": history_store,
    }]
    assert "now_factory" in helper_source
    assert "utc_now()" not in helper_source
