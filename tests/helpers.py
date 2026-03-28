"""Shared test helper factories for adapter tests.

Provides mock-response builders and IOC factories used across 10+ adapter
test files, eliminating duplicated setup code.

Usage:
    from tests.helpers import make_mock_response, make_ipv4_ioc
"""

import json

import requests
from unittest.mock import MagicMock

from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Mock HTTP response factory
# ---------------------------------------------------------------------------

def make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response with status code and optional JSON body."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# IOC factory helpers
# ---------------------------------------------------------------------------

def make_ioc(ioc_type: IOCType, value: str) -> IOC:
    """Build an IOC with raw_match equal to value."""
    return IOC(type=ioc_type, value=value, raw_match=value)


def make_ipv4_ioc(value: str = "1.2.3.4") -> IOC:
    return make_ioc(IOCType.IPV4, value)


def make_ipv6_ioc(value: str = "2001:db8::1") -> IOC:
    return make_ioc(IOCType.IPV6, value)


def make_domain_ioc(value: str = "evil.com") -> IOC:
    return make_ioc(IOCType.DOMAIN, value)


def make_sha256_ioc(value: str = "abc123def456") -> IOC:
    return make_ioc(IOCType.SHA256, value)


def make_md5_ioc(value: str = "d41d8cd98f00b204e9800998ecf8427e") -> IOC:
    return make_ioc(IOCType.MD5, value)


def make_url_ioc(value: str = "http://evil.com/path") -> IOC:
    return make_ioc(IOCType.URL, value)


def make_sha1_ioc(value: str = "b" * 40) -> IOC:
    return make_ioc(IOCType.SHA1, value)


def make_cve_ioc(value: str = "CVE-2021-44228") -> IOC:
    return make_ioc(IOCType.CVE, value)


def make_email_ioc(value: str = "user@evil.com") -> IOC:
    return make_ioc(IOCType.EMAIL, value)


# ---------------------------------------------------------------------------
# Mock adapter session helper
# ---------------------------------------------------------------------------

def mock_adapter_session(adapter, *, method="get", response=None, side_effect=None):
    """Replace adapter._session with a MagicMock and configure the given HTTP method.

    Returns the adapter for chaining.
    """
    adapter._session = MagicMock()
    target = getattr(adapter._session, method)
    if side_effect is not None:
        target.side_effect = side_effect
    elif response is not None:
        target.return_value = response
    return adapter
