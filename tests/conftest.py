"""Pytest fixtures for sentinelx tests.

Provides `app` and `client` fixtures used across all test modules.
The test app uses TestConfig: TESTING=True, WTF_CSRF_ENABLED=False, SERVER_NAME='localhost'.
"""
import pytest

from app import create_app


@pytest.fixture()
def app():
    """Create Flask test application with security scaffold active.

    CSRF is disabled for testing convenience. All other security config
    (TRUSTED_HOSTS, MAX_CONTENT_LENGTH, CSP headers, debug=False) is active.
    """
    test_app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost",
        }
    )
    yield test_app


@pytest.fixture()
def client(app):  # noqa: F811
    """Create Flask test client."""
    return app.test_client()
