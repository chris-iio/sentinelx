"""Integration tests for the IOC detail page route.

Tests cover:
- Basic 200 response for valid IOC type
- Empty cache shows informative message
- Populated cache shows provider tabs
- URL IOCs with slashes route correctly via path converter
- Invalid type returns 404
- Graph data attributes present when provider results exist
- Annotation API routes return 404 (CLEAN-02)
- No annotation UI on detail page or results page (CLEAN-01)
"""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

from app.cache.store import CacheStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_cache(tmp_path: Path, ioc_value: str, ioc_type: str) -> CacheStore:
    """Create an isolated CacheStore and seed one provider result."""
    cache = CacheStore(db_path=tmp_path / "cache.db")
    cache.put(ioc_value, ioc_type, "virustotal", {
        "verdict": "malicious",
        "detection_count": 12,
        "total_engines": 72,
        "scan_date": "2024-01-01T00:00:00Z",
    })
    cache.put(ioc_value, ioc_type, "abuseipdb", {
        "verdict": "suspicious",
        "detection_count": 3,
        "total_engines": None,
        "scan_date": "2024-01-01T01:00:00Z",
    })
    return cache


class _GraphAttributeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attributes: dict[str, str | None] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and ("id", "relationship-graph") in attrs:
            self.attributes = dict(attrs)


class _MockDetailCache:
    def __init__(self, provider_results: list[dict]) -> None:
        self.provider_results = provider_results
        self.calls: list[tuple[str, str]] = []

    def get_all_for_ioc(self, ioc_value: str, ioc_type: str) -> list[dict]:
        self.calls.append((ioc_value, ioc_type))
        return self.provider_results


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestIocDetailRoute:
    """Tests for GET /ioc/<ioc_type>/<path:ioc_value>."""

    def test_detail_page_200(self, client) -> None:
        """GET /ioc/ipv4/1.2.3.4 returns 200 for a valid IOC type."""
        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200

    def test_detail_invalid_type(self, client) -> None:
        """GET /ioc/invalid/1.2.3.4 returns 404 for an unknown IOC type."""
        response = client.get("/ioc/invalid/1.2.3.4")
        assert response.status_code == 404

    def test_valid_ioc_types_are_precomputed(self) -> None:
        """The detail route should not rebuild valid IOC type sets per request."""
        import app.routes.detail as detail_route
        from app.routes import detail_graph
        from app.pipeline.models import IOC_TYPE_VALUES, IOCType

        assert isinstance(detail_graph.VALID_IOC_TYPES, frozenset)
        assert "ipv4" in detail_graph.VALID_IOC_TYPES
        assert "invalid" not in detail_graph.VALID_IOC_TYPES
        assert IOC_TYPE_VALUES == tuple(ioc_type.value for ioc_type in IOCType)
        assert detail_graph.VALID_IOC_TYPES == frozenset(IOC_TYPE_VALUES)
        source = Path("app/routes/detail.py").read_text(encoding="utf-8")
        helper_source = Path("app/routes/detail_graph.py").read_text(encoding="utf-8")
        assert "_valid_ioc_types" not in source
        assert "_VALID_IOC_TYPES" not in source
        assert "_VALID_IOC_TYPES = frozenset(IOC_TYPE_VALUES)" not in source
        assert "VALID_IOC_TYPES = frozenset(IOC_TYPE_VALUES)" in helper_source

    def test_graph_fallback_literals_are_route_constants(self) -> None:
        """Graph construction should reuse fallback literals from one place."""
        from app.routes import detail_graph

        assert detail_graph._GRAPH_IOC_ID == "ioc"
        assert detail_graph._UNKNOWN_PROVIDER == "unknown"
        assert detail_graph._DEFAULT_VERDICT == "no_data"
        assert detail_graph.provider_graph_data.__code__.co_consts.count("unknown") == 0
        assert detail_graph.provider_graph_data.__code__.co_consts.count("no_data") == 0

    def test_append_provider_graph_payload_owns_long_path_mutation(self) -> None:
        """Long graph construction should share one node/edge append helper."""
        from app.routes import detail_graph

        nodes: list[dict[str, str]] = [{"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"}]
        edges: list[dict[str, str]] = []

        detail_graph._append_provider_graph_payload(
            nodes,
            edges,
            {"provider": "VirusTotal", "verdict": "malicious"},
        )
        detail_graph._append_provider_graph_payload(nodes, edges, {})

        assert nodes == [
            {"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"},
            {
                "id": "VirusTotal",
                "label": "VirusTotal",
                "verdict": "malicious",
                "role": "provider",
            },
            {"id": "unknown", "label": "unknown", "verdict": "no_data", "role": "provider"},
        ]
        assert edges == [
            {"from": "ioc", "to": "VirusTotal", "verdict": "malicious"},
            {"from": "ioc", "to": "unknown", "verdict": "no_data"},
        ]

    def test_graph_data_skips_iteration_for_empty_single_pair_three_or_four_results(self) -> None:
        """Short graph construction should not enter the general loop."""
        from app.routes import detail_graph

        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short graph data should not iterate results")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("graph data should not slice results")
                return super().__getitem__(index)

        assert detail_graph.provider_graph_data(NoIterList(), "1.2.3.4") == ([], [])

        nodes, edges = detail_graph.provider_graph_data(
            NoIterList([{"provider": "VirusTotal", "verdict": "malicious"}]),
            "1.2.3.4",
        )

        assert nodes == [
            {"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"},
            {
                "id": "VirusTotal",
                "label": "VirusTotal",
                "verdict": "malicious",
                "role": "provider",
            },
        ]
        assert edges == [{"from": "ioc", "to": "VirusTotal", "verdict": "malicious"}]

        pair_nodes, pair_edges = detail_graph.provider_graph_data(
            NoIterList([
                {"provider": "VirusTotal", "verdict": "malicious"},
                {"provider": "AbuseIPDB", "verdict": "suspicious"},
            ]),
            "1.2.3.4",
        )

        assert pair_nodes == [
            {"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"},
            {
                "id": "VirusTotal",
                "label": "VirusTotal",
                "verdict": "malicious",
                "role": "provider",
            },
            {
                "id": "AbuseIPDB",
                "label": "AbuseIPDB",
                "verdict": "suspicious",
                "role": "provider",
            },
        ]
        assert pair_edges == [
            {"from": "ioc", "to": "VirusTotal", "verdict": "malicious"},
            {"from": "ioc", "to": "AbuseIPDB", "verdict": "suspicious"},
        ]
        three_nodes, three_edges = detail_graph.provider_graph_data(
            NoIterList([
                {"provider": "VirusTotal", "verdict": "malicious"},
                {"provider": "AbuseIPDB", "verdict": "suspicious"},
                {"provider": "Shodan", "verdict": "clean"},
            ]),
            "1.2.3.4",
        )

        assert three_nodes == [
            {"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"},
            {
                "id": "VirusTotal",
                "label": "VirusTotal",
                "verdict": "malicious",
                "role": "provider",
            },
            {
                "id": "AbuseIPDB",
                "label": "AbuseIPDB",
                "verdict": "suspicious",
                "role": "provider",
            },
            {
                "id": "Shodan",
                "label": "Shodan",
                "verdict": "clean",
                "role": "provider",
            },
        ]
        assert three_edges == [
            {"from": "ioc", "to": "VirusTotal", "verdict": "malicious"},
            {"from": "ioc", "to": "AbuseIPDB", "verdict": "suspicious"},
            {"from": "ioc", "to": "Shodan", "verdict": "clean"},
        ]
        four_nodes, four_edges = detail_graph.provider_graph_data(
            NoIterList([
                {"provider": "VirusTotal", "verdict": "malicious"},
                {"provider": "AbuseIPDB", "verdict": "suspicious"},
                {"provider": "Shodan", "verdict": "clean"},
                {"provider": "GreyNoise", "verdict": "unknown"},
            ]),
            "1.2.3.4",
        )

        assert four_nodes == [
            {"id": "ioc", "label": "1.2.3.4", "verdict": "ioc", "role": "ioc"},
            {
                "id": "VirusTotal",
                "label": "VirusTotal",
                "verdict": "malicious",
                "role": "provider",
            },
            {
                "id": "AbuseIPDB",
                "label": "AbuseIPDB",
                "verdict": "suspicious",
                "role": "provider",
            },
            {
                "id": "Shodan",
                "label": "Shodan",
                "verdict": "clean",
                "role": "provider",
            },
            {
                "id": "GreyNoise",
                "label": "GreyNoise",
                "verdict": "unknown",
                "role": "provider",
            },
        ]
        assert four_edges == [
            {"from": "ioc", "to": "VirusTotal", "verdict": "malicious"},
            {"from": "ioc", "to": "AbuseIPDB", "verdict": "suspicious"},
            {"from": "ioc", "to": "Shodan", "verdict": "clean"},
            {"from": "ioc", "to": "GreyNoise", "verdict": "unknown"},
        ]
        assert detail_graph.provider_graph_data.__code__.co_names.count("len") == 1
        assert "_provider_graph_payload" in detail_graph.provider_graph_data.__code__.co_names
        assert "_append_provider_graph_payload" in detail_graph.provider_graph_data.__code__.co_names

    def test_detail_route_delegates_graph_payload_helpers(self) -> None:
        """IOC detail graph helper bodies should live outside the Flask route module."""
        import app.routes.detail as detail_route
        from app.routes import detail_graph

        source = Path("app/routes/detail.py").read_text(encoding="utf-8")

        assert "def _provider_graph_data" not in source
        assert "_provider_graph_data" not in source
        assert "provider_graph_data" not in source

    def test_detail_route_delegates_template_context_helper(self) -> None:
        """IOC detail template shape should live outside the Flask route body."""
        import inspect

        import app.routes.detail as detail_route
        from app.routes import detail_graph

        provider_results = [{"provider": "VirusTotal", "verdict": "malicious"}]
        context = detail_graph.detail_template_context(
            ioc_value="1.2.3.4",
            ioc_type="ipv4",
            provider_results=provider_results,
        )
        mock_cache = _MockDetailCache(provider_results)
        loaded_context = detail_graph.load_detail_template_context(
            mock_cache,
            ioc_type="ipv4",
            ioc_value="1.2.3.4",
        )
        missing_context = detail_graph.load_detail_template_context(
            mock_cache,
            ioc_type="invalid",
            ioc_value="1.2.3.4",
        )
        found_result = detail_graph.detail_page_result(
            mock_cache,
            ioc_type="ipv4",
            ioc_value="1.2.3.4",
        )
        missing_result = detail_graph.detail_page_result(
            mock_cache,
            ioc_type="invalid",
            ioc_value="1.2.3.4",
        )
        source = inspect.getsource(detail_route.ioc_detail.__wrapped__)
        result_helper_source = inspect.getsource(detail_graph.detail_page_result)
        route_helper_source = inspect.getsource(detail_graph.detail_page_route_response)
        import app.routes.template_results as template_results

        assert loaded_context == context
        assert missing_context is None
        assert found_result == template_results.TemplateResult("ioc_detail.html", context, 200)
        assert missing_result == template_results.TemplateResult(None, None, 404)
        assert found_result.found is True
        assert missing_result.found is False
        assert mock_cache.calls == [("1.2.3.4", "ipv4"), ("1.2.3.4", "ipv4")]
        assert context["ioc_value"] == "1.2.3.4"
        assert context["ioc_type"] == "ipv4"
        assert context["provider_results"] is provider_results
        assert context["graph_nodes"][0]["id"] == "ioc"
        assert context["graph_edges"] == [{"from": "ioc", "to": "VirusTotal", "verdict": "malicious"}]
        assert "detail_page_route_response(" in source
        assert "current_app.cache_store" in source
        assert "abort_request=abort" in source
        assert "render_template=render_template" in source
        assert "detail_page_result(" not in source
        assert "apply_template_result(" not in source
        assert "abort(result.status)" not in source
        assert "render_template(result.template_name" not in source
        assert "_load_detail_template_context(" not in source
        assert "load_detail_template_context(" in result_helper_source
        assert "TemplateResult(None, None, 404)" in result_helper_source
        assert "apply_template_result(" in route_helper_source
        assert "detail_page_result(" in route_helper_source
        assert "abort_request=abort_request" in route_helper_source
        assert "render_template=render_template" in route_helper_source
        assert not hasattr(detail_graph, "DetailPageResult")
        assert "**_detail_template_context(" not in source
        assert "get_all_for_ioc" not in source
        assert "ioc_type not in _VALID_IOC_TYPES" not in source
        assert "_provider_graph_data(" not in source
        assert "graph_nodes=" not in source
        assert "graph_edges=" not in source
        assert "ioc_detail.html" not in source

    def test_detail_page_empty_cache(self, client, tmp_path) -> None:
        """Detail page with no cached data shows 'No enrichment data' message."""
        client.application.cache_store = CacheStore(db_path=tmp_path / "cache.db")

        response = client.get("/ioc/ipv4/10.20.30.40")
        assert response.status_code == 200
        html = response.data.decode()
        assert "No enrichment data" in html
        assert 'data-graph-nodes="[]"' in html
        assert 'data-graph-edges="[]"' in html

    def test_detail_page_with_results(self, client, tmp_path) -> None:
        """Detail page with cached results shows provider tab labels."""
        cache = _seed_cache(tmp_path, "1.2.3.4", "ipv4")
        client.application.cache_store = cache

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        # Both provider names should appear as tab labels
        assert "virustotal" in html
        assert "abuseipdb" in html
        # M002 design tokens: stacked card layout, verdict-only color, no inline styles
        assert "detail-provider-card" in html
        assert "verdict-badge--malicious" in html
        assert "<style>" not in html

    def test_detail_url_ioc(self, client, tmp_path) -> None:
        """GET /ioc/url/https://evil.com/beacon routes correctly via path converter."""
        client.application.cache_store = CacheStore(db_path=tmp_path / "cache.db")

        response = client.get("/ioc/url/https://evil.com/beacon")
        assert response.status_code == 200

    def test_graph_data_in_context(self, client, tmp_path) -> None:
        """Detail page with cached results includes data-graph-nodes and data-graph-edges attributes."""
        cache = _seed_cache(tmp_path, "1.2.3.4", "ipv4")
        client.application.cache_store = cache

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        assert "data-graph-nodes" in html
        assert "data-graph-edges" in html

    def test_graph_json_survives_html_attribute_parsing(self, client, tmp_path) -> None:
        """A browser-level HTML parse must preserve provider graph nodes and edges."""
        cache = _seed_cache(tmp_path, "1.2.3.4", "ipv4")
        client.application.cache_store = cache

        response = client.get("/ioc/ipv4/1.2.3.4")
        parser = _GraphAttributeParser()
        parser.feed(response.get_data(as_text=True))

        nodes = json.loads(parser.attributes["data-graph-nodes"] or "[]")
        edges = json.loads(parser.attributes["data-graph-edges"] or "[]")
        assert [node["id"] for node in nodes] == ["ioc", "abuseipdb", "virustotal"]
        assert edges == [
            {"from": "ioc", "to": "abuseipdb", "verdict": "suspicious"},
            {"from": "ioc", "to": "virustotal", "verdict": "malicious"},
        ]

    def test_detail_graph_labels_untruncated(self, client, tmp_path) -> None:
        """Graph node labels are not truncated — full provider name appears in data-graph-nodes."""
        cache = CacheStore(db_path=tmp_path / "cache.db")
        cache.put("1.2.3.4", "ipv4", "Shodan InternetDB", {
            "verdict": "clean",
            "detection_count": 0,
        })
        client.application.cache_store = cache

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        # Full 17-char provider name must appear verbatim — previously truncated to 12 chars
        assert "Shodan InternetDB" in html

    def test_ioc_detail_no_annotation_ui(self, client, tmp_path, monkeypatch) -> None:
        """Detail page must not contain any annotation UI elements (CLEAN-01)."""
        import app.cache.store as cache_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")

        _seed_cache(tmp_path, "1.2.3.4", "ipv4")

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        assert "detail-annotations" not in html
        assert "ioc-notes" not in html
        assert "tag-input" not in html
        assert "Add tag" not in html


class TestAnnotationRoutes404:
    """Verify annotation API routes no longer exist (CLEAN-02)."""

    def test_annotation_notes_route_gone(self, client) -> None:
        response = client.post("/api/ioc/ipv4/1.2.3.4/notes",
                               json={"notes": "test"})
        assert response.status_code == 404

    def test_annotation_tags_route_gone(self, client) -> None:
        response = client.post("/api/ioc/ipv4/1.2.3.4/tags",
                               json={"tag": "apt29"})
        assert response.status_code == 404

    def test_annotation_tag_delete_route_gone(self, client) -> None:
        response = client.delete("/api/ioc/ipv4/1.2.3.4/tags/apt29")
        assert response.status_code == 404


class TestResultsPageNoAnnotationData:
    """Verify no annotation data appears on the results page (CLEAN-01)."""

    def test_offline_results_distinguish_extraction_from_provider_no_data(self, client) -> None:
        """Offline results must say providers were not queried."""
        response = client.post(
            "/analyze",
            data={"text": "1.2.3.4", "mode": "offline"},
        )
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Indicators were extracted locally. Provider reputation was not queried." in html
        assert ">EXTRACTED</span>" in html
        assert 'aria-label="Extracted locally; providers not queried"' in html
        assert ">NO DATA</span>" not in html

    def test_results_page_no_tag_data(self, client) -> None:
        """POST /analyze with offline mode must not produce data-tags attributes."""
        response = client.post(
            "/analyze",
            data={"text": "1.2.3.4", "mode": "offline"},
        )
        assert response.status_code == 200
        html = response.data.decode()
        assert 'data-tags="' not in html


def test_app_creates_without_import_error() -> None:
    """Flask app creates without ImportError after annotations module is removed."""
    from app import create_app
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                      "SERVER_NAME": "localhost"})
    assert app is not None
