"""Integration tests for the IOC detail page route.

Tests cover:
- Basic 200 response for valid IOC type
- Empty cache shows informative message
- Populated cache shows provider tabs
- URL IOCs with slashes route correctly via path converter
- Invalid type returns 404
- Graph data attributes present when provider results exist
- Annotation API routes (notes CRUD, tags CRUD, CSRF-free test client)
- Tags on results page via annotations_map
"""
from __future__ import annotations

import json
from pathlib import Path

from app.cache.store import CacheStore
from app.annotations.store import AnnotationStore


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

    def test_detail_page_empty_cache(self, client, tmp_path, monkeypatch) -> None:
        """Detail page with no cached data shows 'No enrichment data' message."""
        import app.routes  # noqa: F401 — side-effect: registers routes
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        # Patch DEFAULT_DB_PATH so the route instantiates isolated DBs
        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

        response = client.get("/ioc/ipv4/10.20.30.40")
        assert response.status_code == 200
        html = response.data.decode()
        assert "No enrichment data" in html

    def test_detail_page_with_results(self, client, tmp_path, monkeypatch) -> None:
        """Detail page with cached results shows provider tab labels."""
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

        _seed_cache(tmp_path, "1.2.3.4", "ipv4")

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        # Both provider names should appear as tab labels
        assert "virustotal" in html
        assert "abuseipdb" in html

    def test_detail_url_ioc(self, client, tmp_path, monkeypatch) -> None:
        """GET /ioc/url/https://evil.com/beacon routes correctly via path converter."""
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

        response = client.get("/ioc/url/https://evil.com/beacon")
        assert response.status_code == 200

    def test_graph_data_in_context(self, client, tmp_path, monkeypatch) -> None:
        """Detail page with cached results includes data-graph-nodes and data-graph-edges attributes."""
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

        _seed_cache(tmp_path, "1.2.3.4", "ipv4")

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        assert "data-graph-nodes" in html
        assert "data-graph-edges" in html

    def test_detail_annotations_prepopulated(self, client, tmp_path, monkeypatch) -> None:
        """Existing notes are pre-populated in the textarea."""
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

        ann = AnnotationStore(db_path=tmp_path / "annotations.db")
        ann.set_notes("1.2.3.4", "ipv4", "Seen in incident #42")

        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        assert "Seen in incident #42" in html


class TestAnnotationApiRoutes:
    """Tests for the annotation API routes (notes and tags CRUD)."""

    def _patch_stores(self, monkeypatch, tmp_path: Path) -> None:
        """Monkeypatch both store default paths to tmp_path-isolated DBs."""
        import app.cache.store as cache_store_module
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(cache_store_module, "DEFAULT_DB_PATH", tmp_path / "cache.db")
        monkeypatch.setattr(annotations_store_module, "DEFAULT_ANNOTATIONS_PATH", tmp_path / "annotations.db")

    def test_api_set_notes(self, client, tmp_path, monkeypatch) -> None:
        """POST /api/ioc/ipv4/1.2.3.4/notes returns {"ok": true, "notes": "test"}."""
        self._patch_stores(monkeypatch, tmp_path)
        response = client.post(
            "/api/ioc/ipv4/1.2.3.4/notes",
            data=json.dumps({"notes": "test"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["notes"] == "test"

    def test_api_notes_size_cap(self, client, tmp_path, monkeypatch) -> None:
        """POST with notes > 10000 chars truncates to 10000."""
        self._patch_stores(monkeypatch, tmp_path)
        big_notes = "x" * 15000
        response = client.post(
            "/api/ioc/ipv4/1.2.3.4/notes",
            data=json.dumps({"notes": big_notes}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["notes"]) == 10000

    def test_api_add_tag(self, client, tmp_path, monkeypatch) -> None:
        """POST /api/ioc/ipv4/1.2.3.4/tags with {"tag": "apt29"} returns {"ok": true, "tags": ["apt29"]}."""
        self._patch_stores(monkeypatch, tmp_path)
        response = client.post(
            "/api/ioc/ipv4/1.2.3.4/tags",
            data=json.dumps({"tag": "apt29"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["tags"] == ["apt29"]

    def test_api_add_tag_empty_rejected(self, client, tmp_path, monkeypatch) -> None:
        """POST with {"tag": ""} returns 400."""
        self._patch_stores(monkeypatch, tmp_path)
        response = client.post(
            "/api/ioc/ipv4/1.2.3.4/tags",
            data=json.dumps({"tag": ""}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_api_delete_tag(self, client, tmp_path, monkeypatch) -> None:
        """DELETE /api/ioc/ipv4/1.2.3.4/tags/apt29 returns {"ok": true, "tags": []}."""
        self._patch_stores(monkeypatch, tmp_path)
        # First add a tag
        client.post(
            "/api/ioc/ipv4/1.2.3.4/tags",
            data=json.dumps({"tag": "apt29"}),
            content_type="application/json",
        )
        # Then delete it
        response = client.delete("/api/ioc/ipv4/1.2.3.4/tags/apt29")
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        assert data["tags"] == []

    def test_api_duplicate_tag_not_stored(self, client, tmp_path, monkeypatch) -> None:
        """POST same tag twice returns only one instance in tags list."""
        self._patch_stores(monkeypatch, tmp_path)
        client.post(
            "/api/ioc/ipv4/1.2.3.4/tags",
            data=json.dumps({"tag": "apt29"}),
            content_type="application/json",
        )
        response = client.post(
            "/api/ioc/ipv4/1.2.3.4/tags",
            data=json.dumps({"tag": "apt29"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["tags"].count("apt29") == 1

    def test_api_notes_persist_refresh(self, client, tmp_path, monkeypatch) -> None:
        """POST notes, then GET detail page shows notes in textarea."""
        self._patch_stores(monkeypatch, tmp_path)
        client.post(
            "/api/ioc/ipv4/1.2.3.4/notes",
            data=json.dumps({"notes": "persisted note"}),
            content_type="application/json",
        )
        response = client.get("/ioc/ipv4/1.2.3.4")
        assert response.status_code == 200
        html = response.data.decode()
        assert "persisted note" in html


class TestTagsOnResultsPage:
    """Tests for tags appearing on the results page via annotations_map."""

    def test_tags_on_results_page(self, client, tmp_path, monkeypatch) -> None:
        """POST /analyze with IOCs that have tags, verify response HTML contains data-tags."""
        import app.annotations.store as annotations_store_module

        monkeypatch.setattr(
            annotations_store_module,
            "DEFAULT_ANNOTATIONS_PATH",
            tmp_path / "annotations.db",
        )

        # Seed a tag for the IOC we will analyze
        ann = AnnotationStore(db_path=tmp_path / "annotations.db")
        ann.set_tags("1.2.3.4", "ipv4", ["apt29"])

        response = client.post(
            "/analyze",
            data={"text": "1.2.3.4", "mode": "offline"},
        )
        assert response.status_code == 200
        html = response.data.decode()
        assert 'data-tags' in html
        assert "apt29" in html
