"""Shared HTTP safety utilities for enrichment adapters.

Centralizes the security controls applied to all outbound API requests:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-16: SSRF allowlist enforcement before every network call

Each adapter imports these instead of duplicating the logic.
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

import requests


TIMEOUT = (5, 30)  # (connect, read) — SEC-04
MAX_RESPONSE_BYTES = 1 * 1024 * 1024  # 1 MB cap — SEC-05


def validate_endpoint(url: str, allowed_hosts: list[str]) -> None:
    """Raise ValueError if endpoint hostname is not on the SSRF allowlist.

    Enforces SEC-16: no outbound calls to hosts outside ALLOWED_API_HOSTS.
    Called before every network request.

    Args:
        url:           The full URL to be requested.
        allowed_hosts: SSRF allowlist of permitted hostnames.

    Raises:
        ValueError: If the URL hostname is not in the allowlist.
    """
    parsed = urlparse(url)
    if parsed.hostname not in allowed_hosts:
        raise ValueError(
            f"Endpoint hostname {parsed.hostname!r} not in allowed_hosts "
            f"(SSRF allowlist SEC-16). Allowed: {allowed_hosts!r}"
        )


def read_limited(resp: requests.Response) -> dict:
    """Read streaming response with byte cap (SEC-05).

    Reads response body in 8 KB chunks. Raises ValueError if total
    exceeds MAX_RESPONSE_BYTES before completing. Returns parsed JSON.

    Args:
        resp: An open streaming requests.Response.

    Raises:
        ValueError: If response body exceeds MAX_RESPONSE_BYTES.
        json.JSONDecodeError: If body is not valid JSON.
    """
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response exceeded size limit of {MAX_RESPONSE_BYTES} bytes (SEC-05)"
            )
        chunks.append(chunk)
    return json.loads(b"".join(chunks))
