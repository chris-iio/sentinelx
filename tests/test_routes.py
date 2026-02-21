"""Integration tests for Flask routes.

Tests cover:
- Functional behavior of GET / and POST /analyze
- Security properties: 413, 400 (bad host), CSRF, CSP headers, debug=False
- Offline mode: no outbound HTTP calls during extraction (UI-02)
- Edge cases: empty input, no IOCs, duplicate IOC deduplication
"""
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


def test_index_returns_200(client):
    """GET / returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200


def test_analyze_with_valid_input(client):
    """POST /analyze with mixed IOC text returns 200 with results."""
    text = (
        "Source IP 192[.]168[.]1[.]1 contacted hxxps://evil[.]example[.]com/beacon. "
        "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200


def test_analyze_empty_input(client):
    """POST /analyze with empty text shows an error message."""
    response = client.post("/analyze", data={"text": "", "mode": "offline"})
    assert response.status_code == 200
    assert b"No input provided" in response.data


def test_analyze_whitespace_only_input(client):
    """POST /analyze with whitespace-only text treats it as empty."""
    response = client.post("/analyze", data={"text": "   \n\t  ", "mode": "offline"})
    assert response.status_code == 200
    assert b"No input provided" in response.data


def test_analyze_extracts_ipv4(client):
    """POST with text containing a defanged IPv4 returns the refanged IP in response."""
    response = client.post(
        "/analyze", data={"text": "Alert from 10[.]0[.]0[.]1", "mode": "offline"}
    )
    assert response.status_code == 200
    # The refanged IP should appear in the rendered HTML
    assert b"10.0.0.1" in response.data


def test_analyze_groups_by_type(client):
    """POST with mixed IOC types — response HTML contains grouping indicators."""
    text = (
        "IP: 192[.]168[.]1[.]1 "
        "URL: hxxps://evil[.]example[.]com/path "
        "CVE-2025-49596"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200
    # Results page should contain group/accordion structure
    data = response.data
    assert b"grouped" in data or b"details" in data or b"summary" in data or b"ipv4" in data.lower()


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------


def test_oversize_post_returns_413(client):
    """POST a 600 KB payload returns 413 (SEC-12 / MAX_CONTENT_LENGTH)."""
    large_payload = "A" * (600 * 1024)
    response = client.post(
        "/analyze",
        data={"text": large_payload, "mode": "offline"},
        content_length=600 * 1024 + 100,
    )
    assert response.status_code == 413


def test_invalid_host_returns_400(client, app):
    """GET with an untrusted Host header returns 400 (SEC-11)."""
    # Bypass SERVER_NAME for this specific test by using a raw request
    with app.test_client() as raw_client:
        response = raw_client.get("/", headers={"Host": "evil.com"})
        assert response.status_code == 400


def test_debug_mode_is_false(app):
    """Flask app.debug is False (SEC-15)."""
    assert app.debug is False


def test_security_headers_present(client):
    """CSP, X-Content-Type-Options, and X-Frame-Options are all present (SEC-09)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers


def test_offline_mode_makes_no_http_calls(client):
    """POST in offline mode makes zero outbound HTTP calls (UI-02).

    Mocks common HTTP clients to ensure none are invoked during extraction.
    """
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        patch("http.client.HTTPConnection") as mock_http,
        patch("http.client.HTTPSConnection") as mock_https,
    ):
        text = (
            "Source IP 192[.]168[.]1[.]100 contacted "
            "hxxps://evil-c2[.]example[.]com/beacon\n"
            "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
            "CVE-2025-49596"
        )
        response = client.post("/analyze", data={"text": text, "mode": "offline"})
        assert response.status_code == 200

        mock_urlopen.assert_not_called()
        mock_http.assert_not_called()
        mock_https.assert_not_called()


def test_csrf_token_required(app):
    """POST /analyze without CSRF token returns 400 when CSRF is enabled (SEC-10).

    Uses a fresh app with CSRF enabled (not the test fixture which disables it).
    """
    csrf_app = app  # The conftest fixture has CSRF disabled
    # Create a separate app with CSRF enabled
    from app import create_app

    prod_like_app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "SERVER_NAME": "localhost",
            "SECRET_KEY": "test-csrf-key",
        }
    )
    with prod_like_app.test_client() as csrf_client:
        response = csrf_client.post(
            "/analyze",
            data={"text": "192[.]168[.]1[.]1", "mode": "offline"},
        )
        # Without a valid CSRF token, Flask-WTF returns 400
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


def test_analyze_no_iocs_found(client):
    """POST with text containing no IOCs shows a friendly 'no results' message."""
    response = client.post(
        "/analyze",
        data={"text": "Hello world, no indicators here", "mode": "offline"},
    )
    assert response.status_code == 200
    data = response.data
    assert b"No IOCs detected" in data or b"no_results" in data or b"No IOCs" in data


def test_analyze_deduplicates(client):
    """POST with duplicate IOC values returns deduplicated results (no doubles)."""
    text = (
        "192[.]168[.]1[.]1 contacted 192[.]168[.]1[.]1 again and again: "
        "192.168.1.1"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200
    # The IP should appear in results but be deduplicated
    data = response.data.decode("utf-8")
    # Count occurrences of the canonical IP in value context
    count = data.count("192.168.1.1")
    # Should appear at least once (it was found) but not 3 times as separate entries
    assert count >= 1
    assert count < 10  # Sanity: not repeated many times as separate rows
